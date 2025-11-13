#!/bin/bash
# Unified launcher script for digital spectrometer
# This script sets up the environment and runs the spectrometer control software
# Designed to be called from crontab at reboot: @reboot /home/peterson/highz-digitalspec/launcher.sh

# Configuration
REPO_DIR="/home/peterson/highz-digitalspec"
LOGDIR="/home/peterson/logs"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
LOGFILE="$LOGDIR/digital_spec_$TIMESTAMP.log"

# Create log directory if it doesn't exist
mkdir -p "$LOGDIR"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGFILE"
}

# Start logging
log_message "========================================="
log_message "Starting Digital Spectrometer"
log_message "========================================="

# Load pyenv if not already loaded
export PYENV_ROOT="$HOME/.pyenv"
if [ -d "$PYENV_ROOT/bin" ]; then
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init - bash)"
    log_message "Loaded pyenv"
fi

# Change to repository directory
cd "$REPO_DIR" || {
    log_message "ERROR: Failed to change to repository directory: $REPO_DIR"
    exit 1
}
log_message "Changed to repository directory: $REPO_DIR"

# Verify Python version
PYTHON_VERSION=$(python --version 2>&1)
log_message "Python version: $PYTHON_VERSION"

# Run the spectrometer using pipenv
log_message "Starting spectrometer control software..."
log_message "Output will be logged to: $LOGFILE"
log_message "-----------------------------------------"

# Run the Python script with pipenv and capture all output
pipenv run python src/run_spectrometer.py >> "$LOGFILE" 2>&1
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
