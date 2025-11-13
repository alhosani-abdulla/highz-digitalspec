# Scripts Directory

This directory contains shell scripts for managing the HighZ digital spectrometer, including system initialization, file mounting, and data management.

## Scripts Overview

### `launcher.sh`
**Purpose:** Main launcher script for the digital spectrometer

**Description:**
- Runs the digital spectrometer control code (`run_spectrometer.py`) using the pipenv virtual environment
- Handles all logging with timestamped output files
- Can be executed manually or automatically at system boot via crontab
- Creates log directory if it doesn't exist

**Usage:**
```bash
./launcher.sh
```

**Log Files:**
- Timestamped logs: `/home/peterson/logs/spectrometer_YYYY-MM-DD_HH-MM-SS.log`
- Both stdout and stderr are captured in the log files

**Automated Execution:**
To run automatically at boot, add to crontab:
```bash
crontab -e
# Add the following line:
@reboot /home/peterson/highz-digitalspec/scripts/launcher.sh
```

### `mount_highz.sh`
**Purpose:** Mount Google Drive storage for HighZ experiment data

**Description:**
- Mounts the `googledrive:high-z` remote to `$HOME/HighzDrive`
- Uses rclone with optimized VFS caching for large data files
- Includes safety checks to prevent duplicate mounts
- Runs as a background daemon with comprehensive logging

**Features:**
- **VFS Cache Mode:** Full caching for optimal performance
- **Write-back:** 10-second delay for write operations
- **Cache Settings:** 24-hour max age, 3GB max size
- **Concurrent Mount Protection:** Uses file locking to prevent conflicts

**Usage:**
```bash
./mount_highz.sh
```

**Prerequisites:**
- rclone must be installed and configured
- Google Drive remote named `googledrive` must be set up in rclone config
- For encrypted configs, set `RCLONE_CONFIG_PASS` environment variable

### `unmount_highz.sh`
**Purpose:** Safely unmount the HighZ Google Drive

**Description:**
- Cleanly unmounts the Google Drive from `$HOME/HighzDrive`
- Uses `fusermount` for graceful unmounting with fallback to lazy unmount
- Includes status checking to verify mount state before attempting unmount

**Usage:**
```bash
./unmount_highz.sh
```

## Setup Instructions

### 1. Make Scripts Executable
```bash
chmod +x *.sh
```

### 2. Configure rclone (for mount scripts)
```bash
rclone config
# Follow prompts to set up Google Drive remote named "googledrive"
```

### 3. Set up Boot Script (optional)
To run `launcher.sh` automatically on system startup using crontab:

```bash
crontab -e
```

Add the following line:
```bash
@reboot /home/peterson/highz-digitalspec/scripts/launcher.sh
```

Save and exit. The spectrometer will now start automatically on boot, with all output logged to timestamped files.

## File Structure

```
scripts/
├── README.md              # This file
├── launcher.sh            # Main launcher script for the digital spectrometer
├── mount_highz.sh         # Google Drive mount script
└── unmount_highz.sh       # Google Drive unmount script
```

## Troubleshooting

### Mount Issues
- **Problem:** `rclone mount` fails with authentication error
  - **Solution:** Run `rclone config reconnect googledrive` to refresh tokens

- **Problem:** Mount point already in use
  - **Solution:** Run `./unmount_highz.sh` first, then retry mounting

### Permission Issues
- **Problem:** Scripts fail with permission denied
  - **Solution:** Ensure scripts are executable with `chmod +x *.sh`

### Log Analysis
Check log files for detailed error information:
```bash
# Recent spectrometer logs
tail -f /home/peterson/logs/spectrometer_*.log

# Most recent spectrometer log
ls -t /home/peterson/logs/spectrometer_*.log | head -1 | xargs tail -f

# Recent mount logs
tail -f ~/.local/share/rclone/rclone-mount.log
```

## Dependencies

- **Python 3.8.19:** Managed via pyenv (see main README)
- **pipenv:** For virtual environment management
- **rclone:** Required for Google Drive mounting
- **fuse:** Required for filesystem mounting
- **bash:** Required for script execution
- **crontab:** Optional, for automatic boot execution

## Notes

- The mount script uses aggressive caching settings optimized for large scientific data files
- Log rotation should be implemented for production use to prevent disk space issues
- Scripts are designed for the specific user `peterson` and paths - modify as needed for your setup