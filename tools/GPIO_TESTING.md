# GPIO Testing Script

## Overview

`gpio_test.py` is a standalone utility for manually testing and controlling the GPIO pins that set the spectrometer's calibration state. This is useful for:

- **Hardware Testing**: Verify GPIO pins are functioning correctly
- **Development**: Test calibration states without running full spectrometer code
- **Debugging**: Isolate GPIO control issues from FPGA communication issues
- **System Integration**: Test hardware state changes independently

## Quick Start

### Interactive Mode (Default)
```bash
pipenv run python tools/gpio_test.py
```

### Set State Before Entering Interactive Mode
```bash
# Using decimal (0-7)
pipenv run python tools/gpio_test.py --state 5

# Using binary (3-bit format)
pipenv run python tools/gpio_test.py --binary 101
```

### Set State and Exit Immediately
```bash
# Useful for scripting or one-shot tests
pipenv run python tools/gpio_test.py --state 3 --exit
```

## Calibration States

| State | Description | Use Case |
|-------|-------------|----------|
| 0 | Antenna - Main Switch Powered | Default/Antenna observation |
| 1 | Open Circuit | Calibration reference |
| 2 | 6" Shorted | Calibration reference |
| 3-7 | Calibration States 3-7 | Reserved/Other calibration |

## Interactive Commands

Once the script is running, you can use these commands:

| Command | Example | Description |
|---------|---------|-------------|
| Decimal | `5` | Set to state 5 |
| Binary | `b101` | Set state via binary (3-bit) |
| `status` | `status` | Show current GPIO state |
| `list` | `list` | List all calibration states |
| `help` | `help` | Show help message |
| `exit`/`quit` | `exit` | Exit and reset to state 0 |

## Understanding GPIO Pin Mapping

The spectrometer uses 3 GPIO pins to represent 8 calibration states (3 bits):

```
Pin 16 (GPIO22) = MSB (Bit 2)
Pin 20 (GPIO20) = Middle (Bit 1)  
Pin 21 (GPIO21) = LSB (Bit 0)
```

Internal conversion:
```
internal_index = 7 - state_number
```

### Example Conversions

| State | Internal Idx | Binary | GPIO Pins (16,20,21) |
|-------|--------------|--------|----------------------|
| 0     | 7            | 111    | ON, ON, ON           |
| 1     | 6            | 110    | ON, ON, OFF          |
| 2     | 5            | 101    | ON, OFF, ON          |
| 3     | 4            | 100    | ON, OFF, OFF         |
| 4     | 3            | 011    | OFF, ON, ON          |
| 5     | 2            | 010    | OFF, ON, OFF         |
| 6     | 1            | 001    | OFF, OFF, ON         |
| 7     | 0            | 000    | OFF, OFF, OFF        |

## Example Usage Session

```bash
$ pipenv run python src/gpio_test.py

============================================================
GPIO Pin Control - Interactive Mode
============================================================

Available Commands:
  <0-7>      - Set state using decimal (e.g., '5')
  b<binary>  - Set state using binary (e.g., 'b101')
  status     - Show current state
  list       - List all calibration states
  help       - Show this help message
  exit/quit  - Exit program (resets to state 0)
============================================================

✓ Set to State 0: Antenna - Main Switch Powered
  Internal index: 7 (binary: 111)
  GPIO Pins - Pin16 (MSB): 1, Pin20: 1, Pin21 (LSB): 1

============================================================
Current Calibration State: 0
Description: Antenna - Main Switch Powered
GPIO Binary: 111 (internal idx: 7)
GPIO Pin States:
  Pin 21 (LSB): ON
  Pin 20:       ON
  Pin 16 (MSB): ON
============================================================

Enter command> 2

✓ Set to State 2: 6" Shorted
  Internal index: 5 (binary: 101)
  GPIO Pins - Pin16 (MSB): 1, Pin20: 0, Pin21 (LSB): 1

============================================================
Current Calibration State: 2
Description: 6" Shorted
GPIO Binary: 101 (internal idx: 5)
GPIO Pin States:
  Pin 21 (LSB): ON
  Pin 20:       OFF
  Pin 16 (MSB): ON
============================================================

Enter command> status

============================================================
Current Calibration State: 2
Description: 6" Shorted
GPIO Binary: 101 (internal idx: 5)
GPIO Pin States:
  Pin 21 (LSB): ON
  Pin 20:       OFF
  Pin 16 (MSB): ON
============================================================

Enter command> b000

✓ Set to State 7: Calibration State 7
  Internal index: 0 (binary: 000)
  GPIO Pins - Pin16 (MSB): 0, Pin20: 0, Pin21 (LSB): 0

============================================================
Current Calibration State: 7
Description: Calibration State 7
GPIO Binary: 000 (internal idx: 0)
GPIO Pin States:
  Pin 21 (LSB): OFF
  Pin 20:       OFF
  Pin 16 (MSB): OFF
============================================================

Enter command> exit

Resetting to state 0 (Antenna - Main Switch Powered)...

✓ Set to State 0: Antenna - Main Switch Powered
  Internal index: 7 (binary: 111)
  GPIO Pins - Pin16 (MSB): 1, Pin20: 1, Pin21 (LSB): 1

Exiting.
```

## Scripting Examples

### Test all states quickly
```bash
for state in {0..7}; do
  echo "Testing state $state..."
  pipenv run python tools/gpio_test.py --state $state --exit
  sleep 1
done
```

### Set state for observation session
```bash
# Set to antenna state before starting full spectrometer
pipenv run python tools/gpio_test.py --state 0 --exit

# Then run spectrometer
pipenv run python src/run_spectrometer.py
```

### Test binary state conversion
```bash
# Test all binary values
for binary in 000 001 010 011 100 101 110 111; do
  echo "Testing binary $binary..."
  pipenv run python tools/gpio_test.py --binary $binary --exit
  sleep 1
done
```

## Troubleshooting

### GPIO Permission Error
```
Error: gpiozero.GPIOFactory: Cannot run without GPIO support
```

Solution: Add user to gpio group:
```bash
sudo usermod -a -G gpio $USER
# Log out and back in for changes to take effect
```

### Pins Not Responding
1. Verify pins are connected to your GPIO header
2. Check pins with manual test:
   ```bash
   sudo gpioinfo
   ```
3. Test with simpler GPIO tool first:
   ```bash
   gpiod_set -c 0 -l 21 1
   ```

### Binary Conversion Confusion
Remember: internal_index = 7 - state
- State 0 → idx 7 → binary 111
- State 7 → idx 0 → binary 000

Use `status` command to verify current pin states.

## Related Files

- **Main script**: `src/rcal.py` - Original calibration control (used by `run_spectrometer.py`)
- **Spectrometer**: `src/run_spectrometer.py` - Full spectrometer that uses GPIO control
- **Network config**: See `NETWORK_CONFIGURATION.md` for hardware setup

## Notes

- The script automatically resets to state 0 (Antenna) on exit
- Changes take effect immediately
- All GPIO operations require GPIO group membership (or sudo)
- The script is safe to run repeatedly - GPIO pins have debouncing built in
