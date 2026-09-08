#!/bin/bash
# Launcher script with auto restart and logging (Linux equivalent of
# launch.cmd)
# (c) Neuronic 2023

echo "============================================================"
echo " Neuron Launcher"
echo "============================================================"

NEURON_DIR="$HOME/Documents/Neuronic/neuron-scripts"

# Optional parameter: an alternate settings file to use instead of
# settings.py, e.g.  ./launch.sh settings-edit.py
# Captured here (before any cd) so a bare filename resolves relative to
# wherever launch.sh was run from.
ALT_SETTINGS="$1"
if [ -n "$ALT_SETTINGS" ]; then
    ALT_SETTINGS="$(cd "$(dirname "$ALT_SETTINGS")" 2>/dev/null && pwd)/$(basename "$ALT_SETTINGS")"
fi

# Always clear any NEURON_SETTINGS_FILE left over from a previous run
# first. Without this, sourcing `launch.sh settings-edit.py` once and then
# plain `launch.sh` later in the same shell would silently keep reusing
# settings-edit.py instead of falling back to settings.py. (Only matters
# if this script is sourced rather than executed - a plain ./launch.sh
# run gets a fresh environment either way.)
unset NEURON_SETTINGS_FILE

if [ -z "$1" ]; then
    echo "Settings file: settings.py [default]"
elif [ -f "$ALT_SETTINGS" ]; then
    echo "Settings file: $ALT_SETTINGS"
    export NEURON_SETTINGS_FILE="$ALT_SETTINGS"
else
    echo "WARNING: settings file not found: $1"
    echo "Falling back to settings.py [default]"
fi

echo
echo "============================================================"

echo
echo "Stopping any previously running python3 processes..."
pkill -x python3 2>/dev/null

echo
echo "Pulling latest scripts from git..."
cd "$NEURON_DIR" || { echo "ERROR: $NEURON_DIR not found"; exit 1; }
git pull

# COMMENT & UNCOMMENT BELOW SCRIPTS BASED ON THE APP FUNCTIONALITIES
# Check for latest archive for those that are deployed as ZIP files if
# audit_settings.checkForUpdate is True
# e.g. Used for Unity EXEs

echo
echo "Checking for app archive updates..."
python3 "$NEURON_DIR/archive_update.py"

# Report status into Google Sheet

echo
echo "Starting pulse monitor (status reports)..."
nohup python3 "$NEURON_DIR/pulse.py" >/dev/null 2>&1 &

# Optional per-deployment hook to launch any auxiliary apps this exhibit
# needs, before guard.py locks down the desktop. Not required - only runs
# if launch_aux.sh actually exists (copy launch_aux.sh.sample and
# customize it, or edit launch_aux.sh directly).

if [ -f "$NEURON_DIR/launch_aux.sh" ]; then
    echo
    echo "Running launch_aux.sh..."
    bash "$NEURON_DIR/launch_aux.sh"
fi

# Run and monitor the app

echo
echo "Starting guard (app monitor / kiosk lockdown)..."
nohup python3 "$NEURON_DIR/guard.py" >/dev/null 2>&1 &

echo
echo "============================================================"
echo " Launch complete. Press Ctrl+Shift+S in the app to quit."
echo "============================================================"
