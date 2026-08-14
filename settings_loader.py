# settings_loader.py
# Lets an alternate settings file be used for a run without ever touching
# the real settings.py.
#
# If the NEURON_SETTINGS_FILE environment variable is set, that file is
# loaded as the "settings" module instead of the settings.py next to these
# scripts. Otherwise settings.py loads as normal.
#
# Usage: `import settings_loader` before `import settings` in any
# entry-point script (guard.py, pulse.py, archive_update.py, install.py,
# restore_desktop.py). This registers the module in sys.modules, so the
# `import settings` right after it (here or in any other file already
# running in this process, e.g. guard.py importing archive_update.py)
# just picks up the same already-loaded module - no filesystem copying,
# no changes needed to how settings.xxx is used anywhere else.
#
# To use an alternate file:
#   set NEURON_SETTINGS_FILE=C:\path\to\settings-edit.py
# (launch.cmd does this for you when given a filename argument.)

import os
import sys
import importlib.util

if "settings" not in sys.modules:
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _settings_path = os.environ.get("NEURON_SETTINGS_FILE") or os.path.join(_script_dir, "settings.py")

    if not os.path.isfile(_settings_path):
        raise FileNotFoundError(
            f"Settings file not found: {_settings_path}"
            + (" (from NEURON_SETTINGS_FILE)" if os.environ.get("NEURON_SETTINGS_FILE") else "")
        )

    _spec = importlib.util.spec_from_file_location("settings", _settings_path)
    _module = importlib.util.module_from_spec(_spec)
    sys.modules["settings"] = _module
    _spec.loader.exec_module(_module)
