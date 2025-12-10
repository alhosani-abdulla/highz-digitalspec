#!/bin/bash
# Launcher script for digital spectrometer
# Activates the pre-configured virtualenv and runs the spectrometer
# Designed to be called from crontab at reboot: @reboot /home/peterson/highz-digitalspec/scripts/launcher.sh

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR="$( dirname "$SCRIPT_DIR" )"

# Get the user's home directory (for virtualenv location)
# When run from sudo crontab, SUDO_USER is not set, so default to peterson
TARGET_USER="${SUDO_USER:-peterson}"
TARGET_HOME=$(eval echo "~$TARGET_USER")

# Configuration
VENV_PATH="$TARGET_HOME/.local/share/virtualenvs/highz-digitalspec-gvua5dZu"
PRIMARY_LOGDIR="/media/peterson/INDURANCE/logs"
FALLBACK_LOGDIR="$TARGET_HOME/spectrometer_logs"

# Check if INDURANCE is actually mounted (not just if directory exists)
if mountpoint -q "/media/peterson/INDURANCE" 2>/dev/null; then
    LOGDIR="$PRIMARY_LOGDIR"
else
    LOGDIR="$FALLBACK_LOGDIR"
    echo "WARNING: INDURANCE storage not mounted, using fallback: $FALLBACK_LOGDIR" >&2
fi

TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
LOGFILE="$LOGDIR/digital_spec_$TIMESTAMP.log"

# Create log directory if it doesn't exist
mkdir -p "$LOGDIR" 2>/dev/null || {
    echo "ERROR: Could not create log directory: $LOGDIR" >&2
    exit 1
}

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGFILE"
}

# Start logging
log_message "========================================="
log_message "Starting Digital Spectrometer"
log_message "========================================="

# Change to repository directory
cd "$REPO_DIR" || {
    log_message "ERROR: Failed to change to repository directory: $REPO_DIR"
    exit 1
}

# Activate the virtualenv
if [ ! -d "$VENV_PATH" ]; then
    log_message "ERROR: virtualenv not found at: $VENV_PATH"
    exit 1
fi

source "$VENV_PATH/bin/activate"
log_message "Activated virtualenv: $VENV_PATH"
log_message "Python version: $(python --version 2>&1)"
log_message "Python path: $(which python)"

# Run the spectrometer control software
log_message "Starting spectrometer control software..."
log_message "Output will be logged to: $LOGFILE"
log_message "-----------------------------------------"

# Run the Python script with unbuffered output
python -u src/run_spectrometer.py >> "$LOGFILE" 2>&1
EXIT_CODE=$?

# Log completion status
log_message "-----------------------------------------"
if [ $EXIT_CODE -eq 0 ]; then
    log_message "Spectrometer exited successfully (code: $EXIT_CODE)"
else
    log_message "ERROR: Spectrometer exited with error code: $EXIT_CODE"
fi
log_message "========================================="

exit $EXIT_CODE
