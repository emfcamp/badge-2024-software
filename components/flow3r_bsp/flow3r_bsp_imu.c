#include "flow3r_bsp_imu.h"

#include "bmi270.h"
#include "bmi2_defs.h"

static const char *TAG = "flow3r-imu";
#include "esp_log.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include <inttypes.h>
#include <math.h>
#include <string.h>

/*! Macro that defines read write length */
#define READ_WRITE_LEN 256

#define I2C_TIMEOUT_MS 1000

#define GRAVITY_EARTH (9.80665f)

static void bmi2_error_codes_print_result(int8_t rslt);
static int8_t set_accel_config(flow3r_bsp_imu_t *imu);
static int8_t set_gyro_config(flow3r_bsp_imu_t *imu);
static int8_t set_step_counter_config(flow3r_bsp_imu_t *imu);
static float lsb_to_mps(int16_t val, float g_range, uint8_t bit_width);
static float lsb_to_dps(int16_t val, float dps, uint8_t bit_width);

static struct bmi2_sens_data _bmi_sens_data;
static struct bmi2_feat_sensor_data _bmi_feat_data = {.type = BMI2_STEP_COUNTER};

static tildagon_mux_i2c_obj_t* mux;

#define READ ( MP_MACHINE_I2C_FLAG_WRITE1 | MP_MACHINE_I2C_FLAG_READ | MP_MACHINE_I2C_FLAG_STOP )
#define WRITE MP_MACHINE_I2C_FLAG_STOP

static BMI2_INTF_RETURN_TYPE bmi2_i2c_read(uint8_t reg_addr, uint8_t *reg_data,
                                           uint32_t len, void *intf_ptr) {
    flow3r_bsp_imu_t *imu = (flow3r_bsp_imu_t *)intf_ptr;

    uint8_t tx[] = { reg_addr };

    ESP_LOGD(TAG, "bhi read register %02X (%" PRIu32 " bytes)", reg_addr, len);

    mp_machine_i2c_buf_t buffer[2] = { { .len = 1, .buf = tx },
                                       { .len = len, .buf = reg_data } };
    esp_err_t ret = tildagon_mux_i2c_transaction (mux, imu->bmi_dev_addr, 2, buffer, READ);
    
    if (ret < 0) {
        ESP_LOGE(TAG, "i2c read/write fail: %s", esp_err_to_name(ret));
        return BMI2_E_COM_FAIL;
    }
    ESP_LOG_BUFFER_HEX_LEVEL(TAG, reg_data, len, ESP_LOG_DEBUG);
    return BMI2_OK;
}

static BMI2_INTF_RETURN_TYPE bmi2_i2c_write(uint8_t reg_addr,
                                            const uint8_t *reg_data,
                                            uint32_t len, void *intf_ptr) {
    flow3r_bsp_imu_t *imu = (flow3r_bsp_imu_t *)intf_ptr;

    uint8_t tx[len + 1];
    tx[0] = reg_addr;
    memcpy(tx + 1, reg_data, len);

    ESP_LOGD(TAG, "bhi write to register %02X (%" PRIu32 " bytes)", reg_addr,
             len);
    ESP_LOG_BUFFER_HEX_LEVEL(TAG, reg_data, len, ESP_LOG_DEBUG);

    mp_machine_i2c_buf_t buffer[1] = { { .len = sizeof(tx), .buf = tx } };
    esp_err_t ret = tildagon_mux_i2c_transaction (mux, imu->bmi_dev_addr, 1, buffer, WRITE);

    if (ret < 0) {
        ESP_LOGE(TAG, "i2c write fail: %s", esp_err_to_name(ret));
        return BMI2_E_COM_FAIL;
    }

    return BMI2_OK;
}

static void bmi2_delay_us(uint32_t period, void *intf_ptr) {
    int period_ms = (period + 999) / 1000;
    int port_ms = period_ms + portTICK_PERIOD_MS - 1;
    int port_ticks = port_ms / portTICK_PERIOD_MS;

    ESP_LOGD(TAG, "delay %d, %d, %d, %d", period_ms, port_ms, port_ticks,
             (int)portTICK_PERIOD_MS);
    vTaskDelay(port_ticks);
}

esp_err_t flow3r_bsp_imu_init(flow3r_bsp_imu_t *imu) {
    memset(imu, 0, sizeof(*imu));
    mux = tildagon_get_mux_obj( 7 );
    imu->bmi_dev_addr = BMI2_I2C_SEC_ADDR;
    imu->bmi.intf = BMI2_I2C_INTF;
    imu->bmi.read = bmi2_i2c_read;
    imu->bmi.write = bmi2_i2c_write;
    imu->bmi.delay_us = bmi2_delay_us;

    imu->bmi.intf_ptr = ((void *)imu);

    /* Configure max read/write length (in bytes) ( Supported length depends on
     * target machine) */
    imu->bmi.read_write_len = READ_WRITE_LEN;

    /* Assign to NULL to load the default config file. */
    imu->bmi.config_file_ptr = NULL;

    int8_t rslt = bmi270_init(&(imu->bmi));

    bmi2_error_codes_print_result(rslt);
    if (rslt != BMI2_OK) return ESP_FAIL;

    imu->acc_range = 2;  // 2 g default range
    rslt = set_accel_config(imu);
    bmi2_error_codes_print_result(rslt);
    if (rslt != BMI2_OK) return ESP_FAIL;

    imu->gyro_range = 2000;  // 2 deg per second default range
    rslt = set_gyro_config(imu);
    bmi2_error_codes_print_result(rslt);
    if (rslt != BMI2_OK) return ESP_FAIL;

    uint8_t sensor_list[] = { BMI2_ACCEL, BMI2_GYRO, BMI2_STEP_COUNTER };

    rslt = bmi270_sensor_enable(sensor_list, sizeof(sensor_list), &(imu->bmi));
    bmi2_error_codes_print_result(rslt);
    if (rslt != BMI2_OK) return ESP_FAIL;

    rslt = set_step_counter_config(imu);
    bmi2_error_codes_print_result(rslt);
    if (rslt != BMI2_OK) return ESP_FAIL;

    struct bmi2_sens_config config;
    config.type = BMI2_ACCEL;

    /* Get the accel configurations. */
    rslt = bmi2_get_sensor_config(&config, 1, &(imu->bmi));
    bmi2_error_codes_print_result(rslt);
    if (rslt != BMI2_OK) return ESP_FAIL;

    rslt = bmi2_set_adv_power_save(BMI2_DISABLE, &imu->bmi);
    bmi2_error_codes_print_result(rslt);
    if (rslt != BMI2_OK) return ESP_FAIL;

    return ESP_OK;
}

esp_err_t flow3r_bsp_imu_update(flow3r_bsp_imu_t *imu) {
    struct bmi2_sens_data sens_data = {
        0,
    };
    int8_t rslt = bmi2_get_sensor_data(&sens_data, &(imu->bmi));
    bmi2_error_codes_print_result(rslt);

    if (rslt == BMI2_OK) {
        _bmi_sens_data = sens_data;
    }
    return rslt;
}

esp_err_t flow3r_bsp_imu_read_acc(flow3r_bsp_imu_t *imu, int *x, int *y,
                                  int *z) {
    if (_bmi_sens_data.status & BMI2_DRDY_ACC) {
        *x = _bmi_sens_data.acc.x;
        *y = _bmi_sens_data.acc.y;
        *z = _bmi_sens_data.acc.z;
        return ESP_OK;
    }
    return ESP_ERR_NOT_FOUND;
}

esp_err_t flow3r_bsp_imu_read_acc_mps(flow3r_bsp_imu_t *imu, float *x, float *y,
                                      float *z) {
    int ix, iy, iz;

    esp_err_t res = flow3r_bsp_imu_read_acc(imu, &ix, &iy, &iz);

    if (res == ESP_OK) {
        *x = lsb_to_mps(ix, imu->acc_range, imu->bmi.resolution);
        *y = lsb_to_mps(iy, imu->acc_range, imu->bmi.resolution);
        *z = lsb_to_mps(iz, imu->acc_range, imu->bmi.resolution);
    }

    return res;
}

esp_err_t flow3r_bsp_imu_read_gyro(flow3r_bsp_imu_t *imu, int *x, int *y,
                                   int *z) {
    if (_bmi_sens_data.status & BMI2_DRDY_GYR) {
        *x = _bmi_sens_data.gyr.x;
        *y = _bmi_sens_data.gyr.y;
        *z = _bmi_sens_data.gyr.z;
        return ESP_OK;
    }
    return ESP_ERR_NOT_FOUND;
}

esp_err_t flow3r_bsp_imu_read_gyro_dps(flow3r_bsp_imu_t *imu, float *x,
                                       float *y, float *z) {
    int ix, iy, iz;

    esp_err_t res = flow3r_bsp_imu_read_gyro(imu, &ix, &iy, &iz);

    if (res == ESP_OK) {
        *x = lsb_to_dps(ix, imu->gyro_range, imu->bmi.resolution);
        *y = lsb_to_dps(iy, imu->gyro_range, imu->bmi.resolution);
        *z = lsb_to_dps(iz, imu->gyro_range, imu->bmi.resolution);
    }

    return res;
}

esp_err_t flow3r_bsp_imu_read_steps(flow3r_bsp_imu_t *imu, uint32_t *steps) {
    uint16_t int_status;

    int8_t rslt = bmi2_get_int_status(&int_status, &(imu->bmi));
    bmi2_error_codes_print_result(rslt);
    if (rslt != BMI2_OK) return ESP_FAIL;

    if (int_status & BMI270_STEP_CNT_STATUS_MASK)
    {
        /* Step counter interrupt occurred when watermark level (20 steps) is reached */
        rslt = bmi270_get_feature_data(&_bmi_feat_data, 1, &(imu->bmi));
        bmi2_error_codes_print_result(rslt);
        if (rslt != BMI2_OK) return ESP_FAIL;

        *steps = _bmi_feat_data.sens_data.step_counter_output;
        return ESP_OK;
    }
    return ESP_ERR_NOT_FOUND;
}

/*!
 *  @brief Prints the execution status of the APIs.
 */
static void bmi2_error_codes_print_result(int8_t rslt) {
    switch (rslt) {
        case BMI2_OK:

            /* Do nothing */
            break;

        case BMI2_W_FIFO_EMPTY:
            ESP_LOGW(TAG, "Warning [%d] : FIFO empty", rslt);
            break;
        case BMI2_W_PARTIAL_READ:
            ESP_LOGW(TAG, "Warning [%d] : FIFO partial read", rslt);
            break;
        case BMI2_E_NULL_PTR:
            ESP_LOGE(TAG,
                     "Error [%d] : Null pointer error. It occurs when the user "
                     "tries to assign value (not address) to a pointer,"
                     " which has been initialized to NULL.",
                     rslt);
            break;

        case BMI2_E_COM_FAIL:
            ESP_LOGE(
                TAG,
                "Error [%d] : Communication failure error. It occurs due to "
                "read/write operation failure and also due "
                "to power failure during communication",
                rslt);
            break;

        case BMI2_E_DEV_NOT_FOUND:
            ESP_LOGE(TAG,
                     "Error [%d] : Device not found error. It occurs when the "
                     "device chip id is incorrectly read",
                     rslt);
            break;

        case BMI2_E_INVALID_SENSOR:
            ESP_LOGE(
                TAG,
                "Error [%d] : Invalid sensor error. It occurs when there is a "
                "mismatch in the requested feature with the "
                "available one",
                rslt);
            break;

        case BMI2_E_SELF_TEST_FAIL:
            ESP_LOGE(TAG,
                     "Error [%d] : Self-test failed error. It occurs when the "
                     "validation of accel self-test data is "
                     "not satisfied",
                     rslt);
            break;

        case BMI2_E_INVALID_INT_PIN:
            ESP_LOGE(
                TAG,
                "Error [%d] : Invalid interrupt pin error. It occurs when the "
                "user tries to configure interrupt pins "
                "apart from INT1 and INT2",
                rslt);
            break;

        case BMI2_E_OUT_OF_RANGE:
            ESP_LOGE(
                TAG,
                "Error [%d] : Out of range error. It occurs when the data "
                "exceeds from filtered or unfiltered data from "
                "fifo and also when the range exceeds the maximum range for "
                "accel and gyro while performing FOC",
                rslt);
            break;

        case BMI2_E_ACC_INVALID_CFG:
            ESP_LOGE(
                TAG,
                "Error [%d] : Invalid Accel configuration error. It occurs "
                "when there is an error in accel configuration"
                " register which could be one among range, BW or filter "
                "performance in reg address 0x40",
                rslt);
            break;

        case BMI2_E_GYRO_INVALID_CFG:
            ESP_LOGE(
                TAG,
                "Error [%d] : Invalid Gyro configuration error. It occurs when "
                "there is a error in gyro configuration"
                "register which could be one among range, BW or filter "
                "performance in reg address 0x42",
                rslt);
            break;

        case BMI2_E_ACC_GYR_INVALID_CFG:
            ESP_LOGE(
                TAG,
                "Error [%d] : Invalid Accel-Gyro configuration error. It "
                "occurs when there is a error in accel and gyro"
                " configuration registers which could be one among range, BW "
                "or filter performance in reg address 0x40 "
                "and 0x42",
                rslt);
            break;

        case BMI2_E_CONFIG_LOAD:
            ESP_LOGE(
                TAG,
                "Error [%d] : Configuration load error. It occurs when failure "
                "observed while loading the configuration "
                "into the sensor",
                rslt);
            break;

        case BMI2_E_INVALID_PAGE:
            ESP_LOGE(
                TAG,
                "Error [%d] : Invalid page error. It occurs due to failure in "
                "writing the correct feature configuration "
                "from selected page",
                rslt);
            break;

        case BMI2_E_SET_APS_FAIL:
            ESP_LOGE(
                TAG,
                "Error [%d] : APS failure error. It occurs due to failure in "
                "write of advance power mode configuration "
                "register",
                rslt);
            break;

        case BMI2_E_AUX_INVALID_CFG:
            ESP_LOGE(
                TAG,
                "Error [%d] : Invalid AUX configuration error. It occurs when "
                "the auxiliary interface settings are not "
                "enabled properly",
                rslt);
            break;

        case BMI2_E_AUX_BUSY:
            ESP_LOGE(
                TAG,
                "Error [%d] : AUX busy error. It occurs when the auxiliary "
                "interface buses are engaged while configuring"
                " the AUX",
                rslt);
            break;

        case BMI2_E_REMAP_ERROR:
            ESP_LOGE(TAG,
                     "Error [%d] : Remap error. It occurs due to failure in "
                     "assigning the remap axes data for all the axes "
                     "after change in axis position",
                     rslt);
            break;

        case BMI2_E_GYR_USER_GAIN_UPD_FAIL:
            ESP_LOGE(
                TAG,
                "Error [%d] : Gyro user gain update fail error. It occurs when "
                "the reading of user gain update status "
                "fails",
                rslt);
            break;

        case BMI2_E_SELF_TEST_NOT_DONE:
            ESP_LOGE(
                TAG,
                "Error [%d] : Self-test not done error. It occurs when the "
                "self-test process is ongoing or not "
                "completed",
                rslt);
            break;

        case BMI2_E_INVALID_INPUT:
            ESP_LOGE(
                TAG,
                "Error [%d] : Invalid input error. It occurs when the sensor "
                "input validity fails",
                rslt);
            break;

        case BMI2_E_INVALID_STATUS:
            ESP_LOGE(TAG,
                     "Error [%d] : Invalid status error. It occurs when the "
                     "feature/sensor validity fails",
                     rslt);
            break;

        case BMI2_E_CRT_ERROR:
            ESP_LOGE(TAG,
                     "Error [%d] : CRT error. It occurs when the CRT test has "
                     "failed",
                     rslt);
            break;

        case BMI2_E_ST_ALREADY_RUNNING:
            ESP_LOGE(
                TAG,
                "Error [%d] : Self-test already running error. It occurs when "
                "the self-test is already running and "
                "another has been initiated",
                rslt);
            break;

        case BMI2_E_CRT_READY_FOR_DL_FAIL_ABORT:
            ESP_LOGE(TAG,
                     "Error [%d] : CRT ready for download fail abort error. It "
                     "occurs when download in CRT fails due to wrong "
                     "address location",
                     rslt);
            break;

        case BMI2_E_DL_ERROR:
            ESP_LOGE(TAG,
                     "Error [%d] : Download error. It occurs when write length "
                     "exceeds that of the maximum burst length",
                     rslt);
            break;

        case BMI2_E_PRECON_ERROR:
            ESP_LOGE(TAG,
                     "Error [%d] : Pre-conditional error. It occurs when "
                     "precondition to start the feature was not "
                     "completed",
                     rslt);
            break;

        case BMI2_E_ABORT_ERROR:
            ESP_LOGE(TAG,
                     "Error [%d] : Abort error. It occurs when the device was "
                     "shaken during CRT test",
                     rslt);
            break;

        case BMI2_E_WRITE_CYCLE_ONGOING:
            ESP_LOGE(
                TAG,
                "Error [%d] : Write cycle ongoing error. It occurs when the "
                "write cycle is already running and another "
                "has been initiated",
                rslt);
            break;

        case BMI2_E_ST_NOT_RUNING:
            ESP_LOGE(
                TAG,
                "Error [%d] : Self-test is not running error. It occurs when "
                "self-test running is disabled while it's "
                "running",
                rslt);
            break;

        case BMI2_E_DATA_RDY_INT_FAILED:
            ESP_LOGE(
                TAG,
                "Error [%d] : Data ready interrupt error. It occurs when the "
                "sample count exceeds the FOC sample limit "
                "and data ready status is not updated",
                rslt);
            break;

        case BMI2_E_INVALID_FOC_POSITION:
            ESP_LOGE(TAG,
                     "Error [%d] : Invalid FOC position error. It occurs when "
                     "average FOC data is obtained for the wrong"
                     " axes",
                     rslt);
            break;

        default:
            ESP_LOGE(TAG, "Error [%d] : Unknown error code", rslt);
            break;
    }
}


static int8_t set_accel_config(flow3r_bsp_imu_t *imu) {
    int8_t rslt;
    struct bmi2_sens_config config;

    config.type = BMI2_ACCEL;

    /* Get default configurations for the type of feature selected. */
    rslt = bmi2_get_sensor_config(&config, 1, &imu->bmi);
    bmi2_error_codes_print_result(rslt);

    if (rslt == BMI2_OK) {
        /* Output Data Rate */
        config.cfg.acc.odr = BMI2_ACC_ODR_100HZ;

        /* Gravity range (+/- 2G, 4G, 8G, 16G). */
        switch (imu->acc_range) {
            case 2:
                config.cfg.acc.range = BMI2_ACC_RANGE_2G;
                break;
            case 4:
                config.cfg.acc.range = BMI2_ACC_RANGE_2G;
                break;
            case 6:
                config.cfg.acc.range = BMI2_ACC_RANGE_2G;
                break;
            case 8:
                config.cfg.acc.range = BMI2_ACC_RANGE_2G;
                break;
            default:
                return BMI2_E_OUT_OF_RANGE;
        };
        /* The bandwidth parameter is used to configure the number of sensor
         * samples that are averaged if it is set to 2, then 2^(bandwidth
         * parameter) samples are averaged, resulting in 4 averaged samples.
         * Note1 : For more information, refer the datasheet.
         * Note2 : A higher number of averaged samples will result in a lower
         * noise level of the signal, but this has an adverse effect on the
         * power consumed.
         */
        config.cfg.acc.bwp = BMI2_ACC_NORMAL_AVG4;

        // Full performance mode
        config.cfg.acc.filter_perf = BMI2_PERF_OPT_MODE;

        /* Set the accel configurations. */
        rslt = bmi2_set_sensor_config(&config, 1, &imu->bmi);
        bmi2_error_codes_print_result(rslt);
    }

    return rslt;
}

static int8_t set_gyro_config(flow3r_bsp_imu_t *imu) {
    int8_t rslt;
    struct bmi2_sens_config config;

    config.type = BMI2_GYRO;

    /* Get default configurations for the type of feature selected. */
    rslt = bmi2_get_sensor_config(&config, 1, &imu->bmi);
    bmi2_error_codes_print_result(rslt);

    if (rslt == BMI2_OK) {
        // Output Data Rate
        config.cfg.gyr.odr = BMI2_GYR_ODR_100HZ;

        switch (imu->gyro_range) {
            case 125:
                config.cfg.gyr.range = BMI2_GYR_RANGE_125;
                break;
            case 250:
                config.cfg.gyr.range = BMI2_GYR_RANGE_250;
                break;
            case 500:
                config.cfg.gyr.range = BMI2_GYR_RANGE_500;
                break;
            case 1000:
                config.cfg.gyr.range = BMI2_GYR_RANGE_1000;
                break;
            case 2000:
                config.cfg.gyr.range = BMI2_GYR_RANGE_2000;
                break;
            default:
                return BMI2_E_OUT_OF_RANGE;
        };

        config.cfg.gyr.bwp = BMI2_GYR_NORMAL_MODE;

        // Full performance mode
        config.cfg.gyr.filter_perf = BMI2_PERF_OPT_MODE;
        config.cfg.gyr.noise_perf = BMI2_POWER_OPT_MODE;

        rslt = bmi2_set_sensor_config(&config, 1, &imu->bmi);
        bmi2_error_codes_print_result(rslt);
    }

    return rslt;
}

static int8_t set_step_counter_config(flow3r_bsp_imu_t *imu)
{
    int8_t rslt;
    struct bmi2_sens_config config;

    config.type = BMI2_STEP_COUNTER;

    rslt = bmi270_get_sensor_config(&config, 1, &imu->bmi);
    bmi2_error_codes_print_result(rslt);

    if (rslt == BMI2_OK)
    {
        config.cfg.step_counter.watermark_level = 1;

        rslt = bmi270_set_sensor_config(&config, 1, &imu->bmi);
        bmi2_error_codes_print_result(rslt);
    }

    return rslt;
}

// Convert raw measurements to meters / second
static float lsb_to_mps(int16_t val, float g_range, uint8_t bit_width) {
    double power = 2;

    float half_scale = powf(power, bit_width) / 2.0f;

    return (GRAVITY_EARTH * val * g_range) / half_scale;
}

// Convert lsb to degree per second for 16 bit gyro at
// range 125, 250, 500, 1000 or 2000dps.
static float lsb_to_dps(int16_t val, float dps, uint8_t bit_width) {
    double power = 2;

    float half_scale = powf(power, bit_width) / 2.0f;

    return (dps / (half_scale)) * (val);
}
