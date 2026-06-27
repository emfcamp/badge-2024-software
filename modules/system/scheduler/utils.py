from . import scheduler


def app_sort_key(app):
    try:
        return getattr(app, "priority", 1)
    except Exception:
        return 1


def get_apps_by_capability(capability):
    from system.hexpansion import app as hexpansion_app

    hexpansion_apps = hexpansion_app._hexpansion_manager.hexpansion_apps.values()
    running_apps = sorted(scheduler.apps, key=app_sort_key)
    running_apps = sorted(running_apps, lambda a: a in hexpansion_apps)
    apps = [
        app for app in running_apps if capability in getattr(app, "capabilities", None)
    ]

    return apps
