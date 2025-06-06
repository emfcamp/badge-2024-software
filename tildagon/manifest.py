import os
def freeze_images(path, generated_dir):
    path = convert_path(path)
    generated_dir = convert_path(generated_dir)
    embed_file = convert_path("$(MPY_DIR)/../scripts/embed_file.py")
    generated_modules = []
    for (dirpath, dirnames, filenames) in os.walk(path):
        for filename in filenames:
            ext = os.path.splitext(filename)[1]
            if ext == ".png" or ext == ".jpg":
                filepath = os.path.join(dirpath, filename)

                relpath = os.path.relpath(filepath, path)
                genpath = os.path.splitext(os.path.join(generated_dir, relpath))[0] + ext.replace(".", "_") + ".py"
                if not os.path.isfile(genpath):
                    os.makedirs(os.path.dirname(genpath), exist_ok=True)
                    output = subprocess.check_output([
                        sys.executable,
                        embed_file,
                        filepath
                    ])
                    with open(genpath, "wb") as f:
                        f.write(output)
                generated_modules.append(os.path.relpath(genpath, generated_dir))

    if generated_modules:
        freeze(generated_dir, generated_modules)


freeze("$(PORT_DIR)/modules")
#freeze("$(MPY_DIR)/tools", ("upip.py", "upip_utarfile.py"))
#freeze("$(MPY_DIR)/lib/micropython-lib/micropython/net/ntptime", "ntptime.py")
freeze("$(MPY_DIR)/../modules") # modules - don't freeze while developing as it overrides filesystem stuff apparently?
# freeze("$(MPY_DIR)/../modules", "boot.py")
module("bdevice.py", base_path="$(MPY_DIR)/../modules/lib")
module("eep_i2c.py", base_path="$(MPY_DIR)/../modules/lib")
module("eeprom_i2c.py", base_path="$(MPY_DIR)/../modules/lib")
freeze("$(MPY_DIR)/../modules/lib", "typing.py")
freeze("$(MPY_DIR)/../modules/lib", "typing_extensions.py")
freeze("$(MPY_DIR)/../modules/lib", "shutil.py")
freeze("$(MPY_DIR)/../modules/lib", "simple_tildagon.py")
#freeze("$(MPY_DIR)/../micropython-lib/python-ecosys/urequests", "urequests.py")
#freeze("$(MPY_DIR)/../micropython-lib/micropython/upysh", "upysh.py")
#freeze("$(MPY_DIR)/../micropython-lib/python-stdlib/functools", "functools.py")
#freeze_images("$(MPY_DIR)/../modules", "$(PORT_DIR)/build-tildagon/modules_generated")

#include("$(MPY_DIR)/extmod/uasyncio/manifest.py")
#include("$(MPY_DIR)/extmod/webrepl/manifest.py")
#include("$(MPY_DIR)/lib/micropython-lib/micropython/drivers/led/neopixel/manifest.py")
include("$(MPY_DIR)/extmod/asyncio/manifest.py")
require("neopixel")
require("ntptime")
require("requests")
require("umqtt.robust")
require("umqtt.simple")
require("mip")

require("aioble")
require("aiorepl")
require("aioespnow")
require("gzip")
require("tarfile")
