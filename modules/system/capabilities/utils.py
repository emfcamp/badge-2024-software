import ota
from system.ota.ota import parse_version
from system.launcher.utils import list_user_apps, load_manifest, APP_DIR
from frontboards.utils import detect_frontboard


def get_app_capabilities(manifest):
    # Get the list of capability identifiers provided by the app described by manifest
    capability_ids = [
        providedCapability["capability"]["identifier"]
        for providedCapability in manifest.get("metadata", {}).get(
            "providedCapabilities", []
        )
    ]
    return capability_ids


def get_app_requirements(manifest):
    # Get the hard requirements of the app described by the manifest
    requirements = {
        "hexpansions": [],
        "frontboard": None,
        "tildagonOs": None,
        "capabilities": [],
    }
    supported = {
        "hexpansions": [],
        "frontboard": None,
        "tildagonOs": None,
        "capabilities": [],
    }
    for req in manifest.get("metadata", {}).get("capabilities", []):
        dest = requirements if req.get("required", False) else supported
        feature_type = req["feature"]["type"]
        if feature_type == "Capability":
            dest["capabilities"].append(req["feature"]["identifier"])
        elif feature_type == "2024 Frontboard":
            dest["frontboard"] = "2024 Frontboard"
        elif feature_type == "2026 Frontboard":
            dest["frontboard"] = "2026 Frontboard"
        elif feature_type == "TildagonOsMinimumVersion":
            dest["tildagonOs"] = req["feature"]["version"]
        elif feature_type == "Hexpansion":
            dest["hexpansions"].append(req["feature"]["identifier"])
    return {"requirements": requirements, "supported": supported}


def get_frontboard():
    # TODO: Remove this, and refactor the frontboard requirements to work
    # like hexpansions, to support non-official frontboards
    front_board = detect_frontboard()
    if (front_board & 0xFF00) == 0x2600:
        return ("2026 Frontboard", 0x2600)
    elif (front_board & 0xFF00) == 0x2400:
        return ("2024 Frontboard", 0x2400)
    else:
        return None


def get_unmet_requirements(
    app_requirements,
    available_capabilities=None,
    available_hexpansions=None,
    tildagon_os="not_set",
    frontboard="not_set",
):
    # For the given set of app requirements, compare with the available capabilities and hexpansions, and return any unfulfilled requirements"""
    from system.hexpansion.app import _hexpansion_manager

    if available_capabilities is None:
        available_capabilities = [
            cap
            for entry in list_capabilities()
            for cap in entry.get("capabilities", [])
        ]

    if available_hexpansions is None:
        available_hexpansions = [
            h for h in _hexpansion_manager.hexpansion_headers.values() if h is not None
        ]

    unmet_requirements = {}

    # Capability Requirements
    for required_capability in app_requirements.get("capabilities", []):
        if required_capability not in available_capabilities:
            unmet_requirements.setdefault("capabilities", []).append(
                required_capability
            )

    # Hexpansion Requirements
    unmet_hexps = [
        hexpansion_requirement
        for hexpansion_requirement in app_requirements.get("hexpansions", [])
        if not any(
            available_hexpansion.vid == int(hexpansion_requirement["vid"], 0)
            and available_hexpansion.pid == int(hexpansion_requirement["pid"], 0)
            for available_hexpansion in available_hexpansions
        )
    ]
    if unmet_hexps:
        unmet_requirements["hexpansions"] = unmet_hexps

    # Frontboard Requirements
    if (
        app_requirements.get("frontboard")
        and app_requirements["frontboard"] != get_frontboard()
        and frontboard
    ):
        unmet_requirements["frontboard"] = app_requirements["frontboard"]

    # TildagonOsRequirements
    required_os = app_requirements.get("tildagonOs")
    if (
        required_os
        and parse_version(required_os) > parse_version(ota.get_version())
        and tildagon_os
    ):
        unmet_requirements["tildagon_os_version"] = required_os

    if unmet_requirements:
        return unmet_requirements

    return None


def check_app_requirements(manifest):
    """Check whether an app's requirements are satisfied. Returns None if all met,
    otherwise a dict of unmet requirements."""
    parsed = get_app_requirements(manifest)
    return get_unmet_requirements(parsed["requirements"])


def get_app_capabilities_by_name(name, folder=APP_DIR[0]):
    """Get the provided capabilities of an app by its directory name."""
    manifest = load_manifest(folder, name)
    return get_app_capabilities(manifest)


def get_app_requirements_by_name(name, folder=APP_DIR[0]):
    """Get the requirements of an app by its directory name."""
    manifest = load_manifest(folder, name)
    return get_app_requirements(manifest)


def list_installed_app_capabilities(app):
    manifest = load_manifest(app["app_dir"], app["name"])
    return {"app": app, "capabilities": get_app_capabilities(manifest)}


def get_app_capabilities_by_hexpansion_slot(slot):
    from system.hexpansion.app import _hexpansion_manager

    running_app = _hexpansion_manager.hexpansion_apps.get(slot, None)
    if running_app is None:
        return None
    app = {
        "path": running_app.__class__.__module__,
        "callable": "__app_export__",
        "name": running_app.__class__.__name__,
        "folder": "",
        "hidden": False,
        "app_dir": "",
    }
    return {
        "app": app,
        "capabilities": get_app_capabilities(
            _hexpansion_manager.hexpansion_manifests.get(slot, {})
        ),
    }


def list_hexpansion_capabilities():
    results = []
    for i in range(1, 7):
        slot_capabilities = get_app_capabilities_by_hexpansion_slot(i)
        if slot_capabilities:
            results.append(slot_capabilities)
    return results


def list_capabilities():
    """Return a list of {app, capabilities} dicts for all installed apps."""
    return [
        list_installed_app_capabilities(app)
        for app in list_user_apps(include_hidden=True)
    ] + list_hexpansion_capabilities()


def list_all_requirements():
    """Return a list of {app, requirements, supported} dicts for all installed apps."""
    result = []
    for app in list_user_apps(include_hidden=True):
        manifest = load_manifest(app["app_dir"], app["name"])
        parsed = get_app_requirements(manifest)
        result.append(
            {
                "app": app,
                "requirements": parsed["requirements"],
                "supported": parsed["supported"],
            }
        )
    return result


def get_manifest_from_compact_app_format(app_obj):
    identifiers = getattr(app_obj, "CAP", [])
    identifiers = [
        identifier.replace(
            "@", "https://tildagon.badge.emfcamp.org/capabilities/registry/"
        )
        for identifier in identifiers
    ]
    capabilities = [
        {"capability": {"identifier": identifier}} for identifier in identifiers
    ]
    return {"metadata": {"providedCapabilities": capabilities}}


def app_sort_key(app):
    try:
        return getattr(app, "priority", 1)
    except Exception:
        return 1


def get_running_apps_by_capability(capability):
    from system.hexpansion import app as hexpansion_app
    from system.scheduler import scheduler

    hexpansion_apps = hexpansion_app._hexpansion_manager.hexpansion_apps.values()
    running_apps = sorted(scheduler.apps, key=app_sort_key)
    running_apps = sorted(running_apps, key=lambda a: a in hexpansion_apps)
    apps = [
        app
        for app in running_apps
        if capability in get_app_capabilities(scheduler.app_manifests[app])
    ]

    return apps
