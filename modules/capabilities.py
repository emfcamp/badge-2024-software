import ota
from system.ota.ota import parse_version
from system.launcher.app import list_user_apps, load_manifest, APP_DIR
from system.hexpansion.app import _hexpansion_manager
from frontboards.utils import detect_frontboard


def get_app_manifest(name, folder=APP_DIR[0]):
    """Load the contents of a tildagon.json file for a given app in a given folder"""
    return load_manifest(folder, name)


def get_app_capabilities(manifest):
    """Get the list of capability identifiers provided by the app described by manifest"""
    capability_ids = [
        providedCapability["capability"]
        for providedCapability in manifest["metadata"].get("providedCapabilities", [])
    ]
    return capability_ids


def get_app_requirements(manifest):
    """Get the hard requirements of the app described by the manifest"""
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


FRONTBOARD_MAP = {
    "2024 Frontboard": 0x2400,
    "2026 Frontboard": 0x2600,
}


def get_frontboard():
    """Get the current frontboard on the badge"""
    """Return the current frontboard name, e.g. '2024 Frontboard' or None if unknown."""
    return next(
        (name for name, pid in FRONTBOARD_MAP.items() if pid == detect_frontboard()),
        None,
    )


def get_os_version():
    """Return the current Tildagon OS version string, e.g. 'v2.0.0'."""
    return ota.get_version()


def list_hexpansions():
    """Return a list of currently attached HexpansionHeader objects."""
    return [h for h in _hexpansion_manager.hexpansion_headers.values() if h is not None]


def get_unmet_requirements(
    app_requirements,
    available_capabilities=None,
    available_hexpansions=None,
    tildagon_os="not_set",
    frontboard="not_set",
):
    """For the given set of app requirements, compare with the available capabilities and hexpansions, and return any unfulfilled requirements"""
    if available_capabilities is None:
        available_capabilities = [
            cap
            for entry in list_capabilities()
            for cap in entry.get("capabilities", [])
        ]
    if available_hexpansions is None:
        available_hexpansions = list_hexpansions()

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
    manifest = get_app_manifest(name, folder)
    return get_app_capabilities(manifest)


def get_app_requirements_by_name(name, folder=APP_DIR[0]):
    """Get the requirements of an app by its directory name."""
    manifest = get_app_manifest(name, folder)
    return get_app_requirements(manifest)


def prep_capabilities(app):
    manifest = get_app_manifest(app.get("name"))
    return {"app": app, "capabilities": get_app_capabilities(manifest)}


def list_capabilities():
    """Return a list of {app, capabilities} dicts for all installed apps."""
    return [prep_capabilities(app) for app in list_user_apps(include_hidden=True)]


def list_all_requirements():
    """Return a list of {app, requirements, supported} dicts for all installed apps."""
    result = []
    for app in list_user_apps(include_hidden=True):
        manifest = get_app_manifest(app["name"])
        parsed = get_app_requirements(manifest)
        result.append(
            {
                "app": app,
                "requirements": parsed["requirements"],
                "supported": parsed["supported"],
            }
        )
    return result
