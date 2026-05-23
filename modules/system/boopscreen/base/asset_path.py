from .is_badge import is_badge

if is_badge():
    # full path to wherever this is
    full_path = __file__.split("/")

    # index of `apps` in that list
    # (assume it's unique, if it's not, behaviour is undefined)
    apps_index = full_path.index("apps")

    # and then our app's homedir is `/apps/` plus the next item from that path list
    ASSET_PATH = "/" + "/".join(full_path[apps_index : apps_index + 2]) + "/"

else:
    ASSET_PATH = ""
