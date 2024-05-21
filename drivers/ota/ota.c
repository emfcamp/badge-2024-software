#include "py/runtime.h"
#include "esp_log.h"
#include "sdkconfig.h"
#include "mphalport.h"
#include "esp_ota_ops.h"
#include "esp_https_ota.h"
#include "esp_crt_bundle.h"
#include "py/objstr.h"

// static const char *TAG = "ota";

#define IMAGE_URL "https://github.com/emfcamp/badge-2024-software/releases/download/latest/micropython.bin"
//#define IMAGE_URL "https://61a450d7332f.ngrok.app/micropython.bin"
//

// openssl x509 -text -inform DER -in "DigiCert Global Root CA.cer"
/*static const char kGithubCertificate[] = "-----BEGIN CERTIFICATE-----\n"
"MIICjzCCAhWgAwIBAgIQXIuZxVqUxdJxVt7NiYDMJjAKBggqhkjOPQQDAzCBiDEL\n"
"MAkGA1UEBhMCVVMxEzARBgNVBAgTCk5ldyBKZXJzZXkxFDASBgNVBAcTC0plcnNl\n"
"eSBDaXR5MR4wHAYDVQQKExVUaGUgVVNFUlRSVVNUIE5ldHdvcmsxLjAsBgNVBAMT\n"
"JVVTRVJUcnVzdCBFQ0MgQ2VydGlmaWNhdGlvbiBBdXRob3JpdHkwHhcNMTAwMjAx\n"
"MDAwMDAwWhcNMzgwMTE4MjM1OTU5WjCBiDELMAkGA1UEBhMCVVMxEzARBgNVBAgT\n"
"Ck5ldyBKZXJzZXkxFDASBgNVBAcTC0plcnNleSBDaXR5MR4wHAYDVQQKExVUaGUg\n"
"VVNFUlRSVVNUIE5ldHdvcmsxLjAsBgNVBAMTJVVTRVJUcnVzdCBFQ0MgQ2VydGlm\n"
"aWNhdGlvbiBBdXRob3JpdHkwdjAQBgcqhkjOPQIBBgUrgQQAIgNiAAQarFRaqflo\n"
"I+d61SRvU8Za2EurxtW20eZzca7dnNYMYf3boIkDuAUU7FfO7l0/4iGzzvfUinng\n"
"o4N+LZfQYcTxmdwlkWOrfzCjtHDix6EznPO/LlxTsV+zfTJ/ijTjeXmjQjBAMB0G\n"
"A1UdDgQWBBQ64QmG1M8ZwpZ2dEl23OA1xmNjmjAOBgNVHQ8BAf8EBAMCAQYwDwYD\n"
"VR0TAQH/BAUwAwEB/zAKBggqhkjOPQQDAwNoADBlAjA2Z6EWCNzklwBBHU6+4WMB\n"
"zzuqQhFkoJ2UOQIReVx7Hfpkue4WQrO/isIJxOzksU0CMQDpKmFHjFJKS04YcPbW\n"
"RNZu9YO6bVi9JNlWSOrvxKJGgYhqOkbRqZtNyWHa0V1Xahg=\n"
"-----END CERTIFICATE-----\n";*/


static mp_obj_t ota_update(mp_obj_t cb_obj, mp_obj_t url_obj) {
    GET_STR_DATA_LEN(url_obj, url, url_len);
    MP_THREAD_GIL_EXIT();

    esp_http_client_config_t config = {
        .url = (const char *) url,
        .buffer_size_tx = 2000,
        .crt_bundle_attach = esp_crt_bundle_attach,
    };
    esp_https_ota_config_t ota_config = {
        .http_config = &config
    };

    esp_https_ota_handle_t handle;
    esp_err_t err = esp_https_ota_begin(&ota_config, &handle);
    check_esp_err(err);

    const int sz = esp_https_ota_get_image_size(handle);
    int count = 0;
    int last_progress = -1;
    
    esp_app_desc_t info = {0};
    err = esp_https_ota_get_img_desc(handle, &info);
    check_esp_err(err);
    mp_obj_t version = mp_obj_new_str(info.version, strlen(info.version));

    int aborted = 0;
    while (!aborted) {
        err = esp_https_ota_perform(handle);
        if (err == ESP_ERR_HTTPS_OTA_IN_PROGRESS) {
            count = esp_https_ota_get_image_len_read(handle);
            int progress = (count * 100) / sz;
            if (progress > last_progress) {
                mp_obj_t progress_obj = mp_obj_new_int(progress);
                MP_THREAD_GIL_ENTER();
                aborted = !mp_obj_is_true(mp_call_function_2(cb_obj, version, progress_obj));
                MP_THREAD_GIL_EXIT();
            }
        } else {
            break;
        }
    }

    if (err == ESP_OK && !aborted) {
        MP_THREAD_GIL_ENTER();
        mp_call_function_2(cb_obj, version, mp_obj_new_int(100));
        MP_THREAD_GIL_EXIT();
        err = esp_https_ota_finish(handle);
    } else {
        esp_https_ota_abort(handle);
    }
    if (!aborted) {
        check_esp_err(err);
    }

    MP_THREAD_GIL_ENTER();
    // Return true if updated
    return mp_obj_new_bool(!aborted);
}
static MP_DEFINE_CONST_FUN_OBJ_2(ota_update_obj, ota_update);

static mp_obj_t ota_get_version() {
    esp_app_desc_t info = {0};
    const esp_partition_t *p = esp_ota_get_running_partition();
    esp_err_t err = esp_ota_get_partition_description(p, &info);
    check_esp_err(err);
    return mp_obj_new_str(info.version, strlen(info.version));
}
static MP_DEFINE_CONST_FUN_OBJ_0(ota_get_version_obj, ota_get_version);

static const mp_rom_map_elem_t ota_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_ota) },
    { MP_ROM_QSTR(MP_QSTR_update), MP_ROM_PTR(&ota_update_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_version), MP_ROM_PTR(&ota_get_version_obj) },
};
static MP_DEFINE_CONST_DICT(ota_module_globals, ota_module_globals_table);

const mp_obj_module_t ota_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&ota_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_ota, ota_user_cmodule);
