#include "py/runtime.h"
#include "esp_log.h"
#include "sdkconfig.h"
#include "mphalport.h"
#include "esp_sleep.h"
#include "esp_wifi.h"
#include "rom/uart.h"
#include "soc/rtc_cntl_reg.h"
#include "esp_wpa2.h"
#include "driver/ledc.h"

// static const char *TAG = "tildagon_helpers";


static mp_obj_t tildagon_esp_sleep_pd_config(mp_obj_t domain_obj, mp_obj_t option_obj) {
    esp_sleep_pd_domain_t domain = (esp_sleep_pd_domain_t)mp_obj_get_int(domain_obj);
    esp_sleep_pd_option_t option = (esp_sleep_pd_option_t)mp_obj_get_int(option_obj);
    esp_err_t err = esp_sleep_pd_config(domain, option);
    check_esp_err(err);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(tildagon_esp_sleep_pd_config_obj, tildagon_esp_sleep_pd_config);

static mp_obj_t tildagon_lightsleep(mp_obj_t time_obj) {
    int time_ms = mp_obj_get_int(time_obj);
    if (time_ms) {
        esp_sleep_enable_timer_wakeup(((uint64_t)time_ms) * 1000);
    }

    esp_light_sleep_start();

    if (time_ms) {
        // Reset this
        esp_sleep_disable_wakeup_source(ESP_SLEEP_WAKEUP_TIMER);
    }

    return MP_OBJ_NEW_SMALL_INT(esp_sleep_get_wakeup_cause());
}
static MP_DEFINE_CONST_FUN_OBJ_1(tildagon_lightsleep_obj, tildagon_lightsleep);

static mp_obj_t tildagon_esp_wifi_set_max_tx_power(mp_obj_t pwr_obj) {
    int8_t pwr = mp_obj_get_int(pwr_obj);
    esp_err_t err = esp_wifi_set_max_tx_power(pwr);
    check_esp_err(err);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(tildagon_esp_wifi_set_max_tx_power_obj, tildagon_esp_wifi_set_max_tx_power);

static mp_obj_t tildagon_esp_wifi_sta_wpa2_ent_enable(mp_obj_t flag_obj) {
    esp_err_t err;
    if (mp_obj_is_true(flag_obj)) {
        err = esp_wifi_sta_wpa2_ent_enable();
    } else {
        err = esp_wifi_sta_wpa2_ent_disable();
    }
    check_esp_err(err);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(tildagon_esp_wifi_sta_wpa2_ent_enable_obj, tildagon_esp_wifi_sta_wpa2_ent_enable);

static mp_obj_t tildagon_esp_wifi_sta_wpa2_ent_set_identity(mp_obj_t id_obj) {
    if (mp_obj_is_true(id_obj)) {
        size_t len = 0;
        const char* id = mp_obj_str_get_data(id_obj, &len);
        esp_err_t err = esp_wifi_sta_wpa2_ent_set_identity((const unsigned char*)id, len);
        check_esp_err(err);
    } else {
        esp_wifi_sta_wpa2_ent_clear_identity();
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(tildagon_esp_wifi_sta_wpa2_ent_set_identity_obj, tildagon_esp_wifi_sta_wpa2_ent_set_identity);

static mp_obj_t tildagon_esp_wifi_sta_wpa2_ent_set_username(mp_obj_t username_obj) {
    if (mp_obj_is_true(username_obj)) {
        size_t len = 0;
        const char* username = mp_obj_str_get_data(username_obj, &len);
        esp_err_t err = esp_wifi_sta_wpa2_ent_set_username((const unsigned char*)username, len);
        check_esp_err(err);
    } else {
        esp_wifi_sta_wpa2_ent_clear_username();
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(tildagon_esp_wifi_sta_wpa2_ent_set_username_obj, tildagon_esp_wifi_sta_wpa2_ent_set_username);

static mp_obj_t tildagon_esp_wifi_sta_wpa2_ent_set_password(mp_obj_t pass_obj) {
    if (mp_obj_is_true(pass_obj)) {
        size_t len = 0;
        const char* password = mp_obj_str_get_data(pass_obj, &len);
        esp_err_t err = esp_wifi_sta_wpa2_ent_set_password((const unsigned char*)password, len);
        check_esp_err(err);
    } else {
        esp_wifi_sta_wpa2_ent_clear_password();
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(tildagon_esp_wifi_sta_wpa2_ent_set_password_obj, tildagon_esp_wifi_sta_wpa2_ent_set_password);

static const mp_rom_map_elem_t tildagon_helpers_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_ota) },
    { MP_ROM_QSTR(MP_QSTR_esp_sleep_pd_config), MP_ROM_PTR(&tildagon_esp_sleep_pd_config_obj) },
    { MP_ROM_QSTR(MP_QSTR_lightsleep), MP_ROM_PTR(&tildagon_lightsleep_obj) },
    { MP_ROM_QSTR(MP_QSTR_esp_wifi_set_max_tx_power), MP_ROM_PTR(&tildagon_esp_wifi_set_max_tx_power_obj) },
    { MP_ROM_QSTR(MP_QSTR_esp_wifi_sta_wpa2_ent_enable), MP_ROM_PTR(&tildagon_esp_wifi_sta_wpa2_ent_enable_obj) },
    { MP_ROM_QSTR(MP_QSTR_esp_wifi_sta_wpa2_ent_set_identity), MP_ROM_PTR(&tildagon_esp_wifi_sta_wpa2_ent_set_identity_obj) },
    { MP_ROM_QSTR(MP_QSTR_esp_wifi_sta_wpa2_ent_set_username), MP_ROM_PTR(&tildagon_esp_wifi_sta_wpa2_ent_set_username_obj) },
    { MP_ROM_QSTR(MP_QSTR_esp_wifi_sta_wpa2_ent_set_password), MP_ROM_PTR(&tildagon_esp_wifi_sta_wpa2_ent_set_password_obj) },
    { MP_ROM_QSTR(MP_QSTR_ESP_PD_DOMAIN_RTC_PERIPH), MP_ROM_INT(ESP_PD_DOMAIN_RTC_PERIPH) },
    { MP_ROM_QSTR(MP_QSTR_ESP_PD_DOMAIN_RTC8M), MP_ROM_INT(ESP_PD_DOMAIN_RTC8M) },
    { MP_ROM_QSTR(MP_QSTR_ESP_PD_OPTION_OFF), MP_ROM_INT(ESP_PD_OPTION_OFF) },
    { MP_ROM_QSTR(MP_QSTR_ESP_PD_OPTION_ON), MP_ROM_INT(ESP_PD_OPTION_ON) },
    { MP_ROM_QSTR(MP_QSTR_ESP_PD_OPTION_AUTO), MP_ROM_INT(ESP_PD_OPTION_AUTO) },
};
static MP_DEFINE_CONST_DICT(tildagon_helpers_module_globals, tildagon_helpers_module_globals_table);

const mp_obj_module_t tildagon_helpers_user_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&tildagon_helpers_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_tildagon_helpers, tildagon_helpers_user_module);