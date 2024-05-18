import tildagonos
import tildagon_hid
import time

def kb_cb(unused):
    x = tildagon_hid.get_kb_event()
    while (x != None):
        print(f"Key {x.key}, mod {x.mod}, release {x.release}")
        x = tildagon_hid.get_kb_event()

tildagon_hid.set_kb_cb(kb_cb)

t = tildagonos.tildagonos()

t.set_egpio_pin((0x59, 0, (3 << 4)), 1)

# just keep running so the callback gets called
while True:
    time.sleep(5)