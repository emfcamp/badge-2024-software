import hmac

def digest(key_slot, msg):
    key = bytes(32)
    if key_slot == HMAC_KEY0:
        key = b'\x96\xd6I\x0c\x8f\x81\x0f\xc1\x95a\xe2K\xef\xa5xT~\x8d\xcd\xa7~\xd9H\x0b\xdc\xf2\x9dD\xd3\xd3>Y'
    return hmac.digest(key, msg, "sha256")
    

HMAC_KEY0 = 0
HMAC_KEY1 = 1
HMAC_KEY2 = 2
HMAC_KEY3 = 3
HMAC_KEY4 = 4
HMAC_KEY5 = 5