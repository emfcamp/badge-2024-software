#include "st3m_imu.h"

#include "flow3r_bsp_imu.h"

static const char *TAG = "st3m-imu";
#include "esp_err.h"
#include "esp_log.h"

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

static flow3r_bsp_imu_t _imu;

static SemaphoreHandle_t _mu;
#define LOCK xSemaphoreTake(_mu, portMAX_DELAY)
#define UNLOCK xSemaphoreGive(_mu)

static float _acc_x, _acc_y, _acc_z;
static float _gyro_x, _gyro_y, _gyro_z;
static float _temperature;
static uint32_t _steps;

esp_err_t st3m_imu_init() {
    _mu = xSemaphoreCreateMutex();
    assert(_mu != NULL);

    esp_err_t ret = flow3r_bsp_imu_init(&_imu);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "IMU init failed: %s", esp_err_to_name(ret));
        return ESP_FAIL;
    }

    return ESP_OK;
}

void st3m_imu_read_acc_mps(float *x, float *y, float *z) {
    LOCK;
    *x = _acc_x;
    *y = _acc_y;
    *z = _acc_z;
    UNLOCK;
}

void st3m_imu_read_gyro_dps(float *x, float *y, float *z) {
    LOCK;
    *x = _gyro_x;
    *y = _gyro_y;
    *z = _gyro_z;
    UNLOCK;
}

void st3m_imu_read_steps(uint32_t *steps) {
    LOCK;
    *steps = _steps;
    UNLOCK;
}

void st3m_imu_read_temperature(float *temperature) {
    LOCK;
    *temperature = _temperature;
    UNLOCK;
}

int st3m_imu_read(uint8_t reg_addr, uint8_t *reg_data, uint8_t len) {
    return bmi2_i2c_read(reg_addr, reg_data, len, &_imu );
}

int st3m_imu_write(uint8_t reg_addr, uint8_t *reg_data, uint8_t len) {
    return bmi2_i2c_write(reg_addr, reg_data, len, &_imu );
}

void st3m_imu_task(void *data) {
    TickType_t last_wake = xTaskGetTickCount();
    esp_err_t ret;
    float a, b, c, temperature;
    uint32_t steps;
    while (1) {
        vTaskDelayUntil(&last_wake, pdMS_TO_TICKS(10));  // 100 Hz

        ret = flow3r_bsp_imu_update(&_imu);
        if (ret != ESP_OK) {
            continue;
        }

        LOCK;
        ret = flow3r_bsp_imu_read_acc_mps(&_imu, &a, &b, &c);
        if (ret == ESP_OK) {
            _acc_x = a;
            _acc_y = b;
            _acc_z = c;
        }

        ret = flow3r_bsp_imu_read_gyro_dps(&_imu, &a, &b, &c);
        if (ret == ESP_OK) {
            _gyro_x = a;
            _gyro_y = b;
            _gyro_z = c;
        }

        ret = flow3r_bsp_imu_read_steps(&_imu, &steps);
        if (ret == ESP_OK) {
            _steps = steps;
        }

        ret = flow3r_bsp_imu_read_temperature(&_imu, &temperature);
        if (ret == ESP_OK) {
            _temperature = temperature;
        }

        UNLOCK;
    }
}
