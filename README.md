# highz-digitalspec

Digital spectrometer control software for the HighZ-EXP 21-cm cosmological signal detection experiment.

## Overview

This repository contains the Python control software for operating the CASPER-based digital spectrometer used in the High-Z instrument. The spectrometer is built on an RFSoC FPGA platform and is designed for detecting the 21-cm signal from the Cosmic Dawn era.

## System Requirements

- **Hardware**: Raspberry Pi (tested on RPi 4)
- **OS**: Debian-based Linux (Raspberry Pi OS)
- **Python**: 3.8.19 (managed via pyenv)
- **FPGA**: CASPER RFSoC with Ethernet connectivity

## Environment Setup

This project uses:
- **pyenv** - Python version management
- **pipenv** - Virtual environment and dependency management

### Initial Setup (One-time)

#### 1. Install Build Dependencies

```bash
sudo apt-get update && sudo apt-get install -y \
  make build-essential libssl-dev zlib1g-dev libbz2-dev \
  libreadline-dev libsqlite3-dev wget curl llvm \
  libncurses-dev openssl bzip2 xz-utils tk-dev \
  libgdbm-dev tcl-dev libxml2-dev libxmlsec1-dev \
  libffi-dev liblzma-dev git
```

#### 2. Install pyenv

```bash
curl https://pyenv.run | bash
```

Add to `~/.bashrc`:
```bash
# Pyenv configuration
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"
eval "$(pyenv virtualenv-init -)"
```

Reload shell:
```bash
source ~/.bashrc
```

#### 3. Install Python 3.8.19

```bash
pyenv install 3.8.19
```

**Note**: This will compile Python from source and may take 10-20 minutes on a Raspberry Pi.

#### 4. Install pipenv

```bash
sudo apt install pipenv
```

### Project Setup

#### Clone and Setup Environment

```bash
# Clone the repository
git clone https://github.com/alhosani-abdulla/highz-digitalspec.git
cd highz-digitalspec

# Python 3.8.19 will be automatically used (via .python-version file)

# Install dependencies
pipenv install
```

The `Pipfile.lock` ensures that all dependencies (including sub-dependencies) are installed at exactly the same versions used during development.

#### Viewing Dependencies

```bash
# View dependency tree
pipenv graph

# List all installed packages
pipenv run pip list

# Export to requirements.txt format (if needed)
pipenv run pip freeze > requirements.txt
```

## Usage

### Activate Virtual Environment

```bash
# Option 1: Spawn a shell within the virtualenv
pipenv shell

# Option 2: Run commands directly
pipenv run python src/run_spectrometer.py
```

### Running the Spectrometer

#### Manual Execution
```bash
pipenv run python src/run_spectrometer.py --antenna 1
```

#### Using the Launcher Script
The `launcher.sh` script handles environment setup and logging:
```bash
./scripts/launcher.sh
```

Logs are saved to `/home/peterson/logs/digital_spec_YYYY-MM-DD_HH-MM-SS.log`

#### Automatic Start on Boot
To run the spectrometer automatically at system startup, add to crontab:
```bash
crontab -e
```

Add this line:
```
@reboot /home/peterson/highz-digitalspec/scripts/launcher.sh
```

The launcher script will:
- Load pyenv and activate the correct Python version
- Use pipenv to run the spectrometer in the virtual environment
- Log all output with timestamps
- Handle errors gracefully

### Configuration

Edit the configuration parameters in `src/run_spectrometer.py`:
- `FPGA_IP`: IP address of the RFSoC FPGA
- `CONFIG_PATH`: Path to the FPGA configuration file (.fpg)
- `BASE_PATH`: External storage path for data

## Repository Structure

```
highz-digitalspec/
├── src/                    # Python source code
│   ├── run_spectrometer.py # Main spectrometer control script
│   └── rcal.py            # Calibration control via GPIO
├── scripts/               # System scripts
│   ├── launcher.sh       # Unified launcher script (for manual/crontab use)
│   ├── mount_highz.sh    # External storage mount
│   ├── unmount_highz.sh  # External storage unmount
│   └── README.md         # Scripts documentation
├── fpga_config/          # FPGA bitstream files (.fpg)
│   └── [dated folders]   # Organized by configuration date
├── Pipfile               # Direct dependencies
├── Pipfile.lock          # Locked dependency versions (all packages)
├── .python-version       # Python version (3.8.19)
└── README.md            # This file
```

## Dependencies

### Direct Dependencies
- `numpy` - Numerical computing
- `casperfpga` - CASPER FPGA communication library (from GitHub)
- `gpiozero` - Raspberry Pi GPIO control
- `python-utils` - Utility functions

All sub-dependencies are automatically managed by pipenv and locked in `Pipfile.lock`.

### Hardware Dependencies
- GPIO pins (21, 20, 16) for calibration state control
- Ethernet connection to FPGA (typically link-local 169.254.x.x)

## Related Repositories

- **[Highz-EXP](https://github.com/alhosani-abdulla/Highz-EXP)** - Original combined repository
- **[adf4351-controller](https://github.com/alhosani-abdulla/adf4351-controller)** - Local Oscillator controller
- **[highz-filterbank](https://github.com/alhosani-abdulla/highz-filterbank)** - Multi-channel filterbank spectrometer

## Troubleshooting

### Python Import Errors
If you get import errors, ensure you're running within the pipenv environment:
```bash
pipenv run python your_script.py
```

### FPGA Connection Issues
- Verify FPGA IP address matches `FPGA_IP` in configuration
- Check Ethernet connection (should be direct connection for link-local addressing)
- Ensure FPGA is powered and programmed with correct bitstream

### GPIO Permission Issues
Add user to gpio group:
```bash
sudo usermod -a -G gpio $USER
```
Log out and back in for changes to take effect.

## Development

### Adding New Dependencies

```bash
# Add a new package
pipenv install package-name

# Add a development dependency
pipenv install --dev package-name

# Update Pipfile.lock
pipenv lock
```

### Python Version Note

This project requires Python 3.8 due to the `casperfpga` package compatibility. Python 3.8 reached end-of-life in October 2024, but remains necessary for FPGA communication. The environment is isolated via pyenv/pipenv to prevent conflicts with system Python.

## License

MIT

## Contributors

High-Z Team
