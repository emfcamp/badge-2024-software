#ifndef _TILDAGON_HID_HOST
#define _TILDAGON_HID_HOST 1

extern const mp_obj_type_t tildagon_usb_KeyEvent_type;

void hid_host_init(void);
void hid_host_device_event(hid_host_device_handle_t hid_device_handle,
                           const hid_host_driver_event_t event,
                           void *arg);

#endif /* ifndef _TILDAGON_HID_HOST */
