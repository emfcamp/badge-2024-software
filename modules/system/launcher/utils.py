import json
import os
import sys
from perf_timer import PerfTimer


APP_DIR = ["/apps"]
APP_INSTALL_DIR = "/apps"


def load_manifest(folder, name):
    try:
        info_file = f"{folder}/{name}/tildagon.json"
        with open(info_file) as f:
            information = f.read()
        return json.loads(information)
    except BaseException:
        return {}


def load_info(folder, name):
    try:
        info_file = "{}/{}/metadata.json".format(folder, name)
        with open(info_file) as f:
            information = f.read()
        return json.loads(information)
    except BaseException:
        return {}


def list_user_apps(include_hidden=False):
    with PerfTimer("List user apps"):
        apps = []
        contents = []
        for d in APP_DIR:
            try:
                contents.extend([(d, x) for x in os.listdir(d)])
            except (OSError, UnicodeError):
                # directory or mount point don't exist
                pass

        for dirname, name in contents:
            path = dirname
            for p in sys.path:
                if p and dirname.startswith(p):
                    path = dirname[len(p) :]
                    break
            path = ".".join(path.lstrip("/").split("/"))
            app = {
                "path": f"{path}.{name}.app",
                "callable": "__app_export__",
                "name": name,
                "folder": name,
                "hidden": False,
                "app_dir": dirname,
            }
            metadata = load_info(dirname, name)
            if "version" not in metadata:
                app["version"] = "0.0.0"
            app.update(metadata)
            if include_hidden or not app["hidden"]:
                apps.append(app)
        return apps
