# GPIO Verification Test Suite

## Overview

`gpio_verification.py` is a comprehensive automated GPIO test that verifies spectrometer calibration state control with system health monitoring and timing analysis.

**What it tests:**
- All 8 calibration states (0-7) and GPIO pin state transitions
- Pin logic levels and timing precision
- System stability (CPU temperature, supply voltage)
- GPIO transition speed and consistency

**Perfect for:**
- Pre-flight hardware checks before data collection
- Regression testing after system changes
- Debugging GPIO control issues
- Statistical validation of GPIO stability

## Quick Start

### Basic Verification (All 8 states, 1 pass)
```bash
pipenv run python tests/gpio_verification.py
```

### Verbose Output (See each state result)
```bash
pipenv run python tests/gpio_verification.py --verbose
```

### With Transition Timing (Measure GPIO speed)
```bash
pipenv run python tests/gpio_verification.py --timing
```

### Multiple Passes (Statistical analysis)
```bash
pipenv run python tests/gpio_verification.py --repeat 5
```

### Combined Options
```bash
pipenv run python tests/gpio_verification.py --verbose --repeat 3 --timing
```

## Expected GPIO Pin States

The test verifies each calibration state maps to the correct GPIO pins:

```
Pin 16 (GPIO 16) = MSB (Bit 2)
Pin 20 (GPIO 20) = Middle (Bit 1)
Pin 21 (GPIO 21) = LSB (Bit 0)

Internal formula: idx = 7 - state_number
```

| State | Description | Pin16 | Pin20 | Pin21 | Binary |
|-------|-------------|-------|-------|-------|--------|
| 0 | Antenna | 1 | 1 | 1 | 111 |
| 1 | Open Circuit | 1 | 1 | 0 | 110 |
| 2 | 6" Shorted | 1 | 0 | 1 | 101 |
| 3 | Cal State 3 | 1 | 0 | 0 | 100 |
| 4 | Cal State 4 | 0 | 1 | 1 | 011 |
| 5 | Cal State 5 | 0 | 1 | 0 | 010 |
| 6 | Cal State 6 | 0 | 0 | 1 | 001 |
| 7 | Cal State 7 | 0 | 0 | 0 | 000 |

## Example Output

### Basic Run
```
======================================================================
Enhanced GPIO State Verification Test Suite
======================================================================

System Metrics:
  CPU Temperature: 51.1°C
  Supply Voltage: 5.00V

Test Configuration:
  Total States: 8 (1 pass(es) of 8 states)
  Verbose Mode: False
  Timing Analysis: False
  Start time: 2025-11-18 11:47:28

======================================================================
TEST RESULTS SUMMARY
======================================================================

Test Statistics:
  Total Tests:    8
  Passed:         8 (100.0%)
  Failed:         0

Pin State Statistics:
  Pin 16:
    HIGH: 4 times (50.0%)
    LOW:  4 times (50.0%)
  Pin 20:
    HIGH: 4 times (50.0%)
    LOW:  4 times (50.0%)
  Pin 21:
    HIGH: 4 times (50.0%)
    LOW:  4 times (50.0%)

System Health During Testing:
  CPU Temperature: 51.1°C ✓ OK
  Supply Voltage: 5.00V ✓ OK

✓ ALL TESTS PASSED
```

### With Timing Analysis (`--timing` flag)
```
GPIO Transition Timing:
  Min:     0.014 ms
  Max:     0.037 ms
  Average: 0.022 ms
  StdDev:  0.008 ms
```

### Verbose Run (`--verbose` flag)
```
  State 0: Antenna - Main Switch Powered
    Expected: Pin16=1, Pin20=1, Pin21=1
    Actual:   Pin16=1, Pin20=1, Pin21=1
    ✓ PASS

  State 1: Open Circuit
    Expected: Pin16=1, Pin20=1, Pin21=0
    Actual:   Pin16=1, Pin20=1, Pin21=0
    ✓ PASS

[... all states shown ...]
```

## Understanding Results

### Pin State Statistics

For a working GPIO system with 8 states (3 bits):
- Each pin should be HIGH ~50% of the time
- Each pin should be LOW ~50% of the time

**Anomalies to investigate:**
- Pins always HIGH or always LOW → Stuck pin
- >60% HIGH or LOW → Bias in specific states
- Inconsistent across passes → Timing/electrical issues

### Transition Timing

GPIO state changes should be **very fast** (<1 ms):
- Typical: 0.01-0.05 ms
- If >1 ms: Possible GPIO driver issue
- If inconsistent: Possible system load or electrical noise

### System Health

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| CPU Temp | <70°C | 70-80°C | >80°C |
| Supply Voltage | 4.8-5.2V | ±0.2V drift | <4.6V or >5.4V |

## Command-Line Options

```
usage: gpio_verification.py [-h] [-v] [-r REPEAT] [-t]

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Show detailed output for each state
  -r REPEAT, --repeat REPEAT
                        Number of times to repeat full test suite (default: 1)
  -t, --timing          Measure GPIO transition times
```

## Troubleshooting

### GPIO Permission Error
```bash
sudo usermod -a -G gpio $USER
# Log out and back in for changes to take effect
```

### Test Fails on Specific States
- Check GPIO wiring for that pin
- Verify gpiozero can access the pin:
  ```bash
  pipenv run python -c "from gpiozero import LED; led = LED(16); led.on(); print('Pin working')"
  ```

### Inconsistent Timing
- Close other processes to reduce system load
- Check for electromagnetic interference near GPIO cables
- Run multiple passes (`--repeat`) to identify patterns

### All Tests Fail
- Verify GPIO pins connected to RPi GPIO header
- Check gpiozero/pigpio driver is available
- Try with `sudo` for full GPIO access
- Check if another process is using the pins

## Integration Examples

### Pre-Flight Check Script
```bash
#!/bin/bash
# Verify GPIO before running spectrometer
if ! pipenv run python tests/gpio_verification.py --repeat 3; then
    echo "GPIO verification failed! Do not proceed."
    exit 1
fi
echo "GPIO healthy. Ready to collect data."
./scripts/launcher.sh
```

### Automated Daily Test
```bash
# Add to crontab
0 6 * * * cd /home/peterson/highz-digitalspec && pipenv run python tests/gpio_verification.py >> /var/log/gpio_test.log 2>&1
```

### CI/CD Integration
```yaml
# Example GitHub Actions
- name: Verify GPIO
  run: pipenv run python tests/gpio_verification.py --verbose --repeat 5
```

## Performance

- **Single pass (8 states):** ~1 second
- **10 passes:** ~10 seconds
- **With timing:** +0-1 second (negligible)
- **Test is non-blocking** for rest of system

## Exit Codes

- `0` - All tests passed
- `1` - Tests failed or error occurred

## Related Files

- **Manual tool**: `tools/gpio_test.py` - Interactive GPIO control
- **GPIO driver**: `src/rcal.py` - Production GPIO code
- **Spectrometer**: `src/run_spectrometer.py` - Uses GPIO control
- **Network**: See `NETWORK_CONFIGURATION.md` for pin connections

## Dependencies

- `gpiozero` (included in pipenv)
- `vcgencmd` (system utility, usually available on RPi)
- GPIO access (requires user in gpio group or sudo)

## Technical Details

**What the test verifies:**
1. Sets each GPIO state (0-7)
2. Reads actual pin levels using gpiozero
3. Compares actual vs expected
4. Collects statistics across all states
5. Measures transition times (optional)
6. Reports system health metrics

**State calculation:**
- User specifies: state number (0-7)
- Internal calculation: `idx = 7 - state_number`
- Binary mapping: `(pin16 << 2) | (pin20 << 1) | pin21`

**System metrics:**
- CPU temperature via `vcgencmd measure_temp`
- Supply voltage via `vcgencmd measure_volts`
- Transition timing via `time.perf_counter()`
