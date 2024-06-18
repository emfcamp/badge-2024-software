"""
Generate version based on the status of the local git checkout.

By default, a plain string will be emitted to stdout. Append command with `-c`
to generate a C source instead.

See docs/badge/firmware(-development).rst for information about version naming
and the release process.
"""

import subprocess
import sys
import os
import re


def get_git_based_version():
    root = os.environ.get('GITHUB_WORKSPACE', '/firmware')
    os.chdir(root)
    version = subprocess.check_output(
        ["git", "describe", "--tags", "--always"]
    ).decode().strip()
    commit_hash = subprocess.check_output(
        ["git", "describe", "--always"]
    ).decode().strip()
    if version.endswith(commit_hash):
        build_info = re.compile(f"\-(\d+)\-(.*?{re.escape(commit_hash)})").findall(version)
        if build_info:
            ahead, commit_hash = build_info[0]
            version = version.replace(f"-{ahead}-{commit_hash}", f"+{ahead}.{commit_hash}", 1)
    return version

fmt = None
if len(sys.argv) > 1:
    if sys.argv[1] == "-c":
        fmt = "C"

v = None
if os.environ.get('CI') is not None:
    if os.environ.get('GITHUB_REF_TYPE') == 'tag':
        # If we're building a tag, just use that as a version.
        v = os.environ.get('GITHUB_REF_NAME')
if v is None:
    v = get_git_based_version()

if fmt == "C":
    print('const char *st3m_version = "' + v + '";')
else:
    print(v)
