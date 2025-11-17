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

### FPGA/RFSoC Connection Troubleshooting

#### Finding the RFSoC IP Address via Serial Console

If the FPGA is not responding to its expected IP address, you can access it directly via serial connection:

**Prerequisites:**
- USB-to-Serial adapter (typically /dev/ttyUSB0 or /dev/ttyUSB1)
- `minicom` or similar serial terminal software
- Physical access to the RFSoC board

**Steps:**

1. **Install minicom** (if needed):
   ```bash
   sudo apt-get install minicom
   ```

2. **Identify the serial port**:
   ```bash
   ls /dev/ttyUSB*
   ```
   Usually `/dev/ttyUSB0` or `/dev/ttyUSB1`

3. **Connect to the RFSoC via serial**:
   ```bash
   minicom -D /dev/ttyUSB1 -b 115200
   ```
   
   Parameters:
   - `-D /dev/ttyUSB1`: Serial port
   - `-b 115200`: Baud rate (8 data bits, 1 stop bit, no parity by default)

4. **Once connected**, press Enter to see the boot messages and access the shell:
   - You should see the Linux kernel boot output
   - Eventually get a login prompt
   - **RFSoC Linux Shell Credentials:**
     - Username: `casper`
     - Password: `casper`

5. **Find the IP address**:
   ```bash
   ifconfig
   ```
   or
   ```bash
   ip addr
   ```
   
   Look for the Ethernet interface (usually `eth0` or `enp0s...`). Common IP address ranges:
   - **Link-local** (auto-assigned): `169.254.x.x` - indicates no DHCP server
   - **Static/DHCP**: Check if an IP is assigned in the expected subnet

6. **Exit minicom**: Press `Ctrl+A` then `X` to exit

**Example session:**
```
Connected to minicom. Press Ctrl+A Z for help

[Linux boot messages...]

root@rfsoc:~# ifconfig
eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST> mtu 1500
      inet 169.254.2.181  netmask 255.255.0.0
      inet6 fe80::xxx:xxx:xxx  prefixlen 64  scopeid 0x20<link>
      ...

root@rfsoc:~# exit
```

#### Connecting to Link-Local IP Address

If the RFSoC has a link-local address (169.254.x.x), you need to:

1. **Configure your Raspberry Pi's Ethernet interface** with a compatible link-local address:
   ```bash
   sudo ifconfig eth0 169.254.1.1 netmask 255.255.0.0
   ```

2. **Verify connectivity**:
   ```bash
   ping 169.254.2.181
   ```

3. **Test FPGA connection** (once you have Python environment set up):
   ```bash
   pipenv run python -c "import casperfpga; fpga = casperfpga.CasperFpga('169.254.2.181', timeout=10); print('Connected!')"
   ```

#### ADC Status Parsing Error

**Error message:**
```
ValueError: not enough values to unpack (expected 2, got 1)
```

**Cause:** The casperfpga library's RFDC parser expects ADC status in format `ADC0: Enabled 1 State 15 PLL 1` but the RFSoC firmware returns `ADC0: Enabled 1, State: 15 PLL: 1` (with colons and commas).

**Solution:** This is already fixed in the current version. The `get_adc_status()` function in `run_spectrometer.py` handles both formats correctly by parsing the raw KATCP response with regex pattern matching.

**If you upgrade casperfpga**, re-apply the fix by ensuring `get_adc_status()` is used instead of `adc.status()`.

### Python Import Errors
If you get import errors, ensure you're running within the pipenv environment:
```bash
pipenv run python your_script.py
```

### FPGA Connection Issues
- Verify FPGA IP address matches `FPGA_IP` in configuration
- Check Ethernet connection (should be direct connection for link-local addressing)
- Ensure FPGA is powered and programmed with correct bitstream
- Use serial console (see above) to verify RFSoC boot and IP configuration

### GPIO Permission Issues
Add user to gpio group:
```bash
sudo usermod -a -G gpio $USER
```
Log out and back in for changes to take effect.

### X11 Forwarding Issues (Remote Plotting/Visualization)

**Error message:**
```
Unexpected error: no display name and no $DISPLAY environment variable
```

**Cause:** X11 forwarding not properly configured for SSH connection.

**Solution:**

1. **On your Mac**: Start XQuartz before SSH'ing:
   ```bash
   open -a XQuartz
   ```

2. **Connect to RPi with X11 forwarding enabled**:
   ```bash
   ssh -Y peterson@<rpi-hostname>
   ```
   
   The `-Y` flag enables trusted X11 forwarding (recommended for local networks).

3. **Verify DISPLAY is set**:
   ```bash
   echo $DISPLAY
   # Should show something like: localhost:10.0
   ```

4. **Now run visualization tools**:
   ```bash
   ViewSpecs  # Real-time spectrum viewer
   ```

**Persistent configuration (optional):**
Add to `~/.ssh/config` on your Mac to remember these settings:
```
Host highz-rpi-1
    HostName <hostname-or-ip>
    User peterson
    ForwardX11 yes
    ForwardX11Trusted yes
```

Then simply: `ssh highz-rpi-1`

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
