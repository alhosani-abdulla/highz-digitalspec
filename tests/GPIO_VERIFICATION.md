# GPIO Automated Verification Tests

## Overview

`gpio_verification.py` is an automated test suite that systematically verifies GPIO pin control functionality. It:

- Sets each calibration state (0-7) and verifies pins change to expected states
- Reads actual GPIO pin logic levels to confirm hardware is responding
- Collects statistics on pin state transitions
- Reports detailed results with pass/fail status
- Auto-resets to state 0 on exit

Perfect for:
- **Hardware Commissioning**: Verify GPIO control is working after setup
- **Regression Testing**: Run before/after system changes
- **Debugging**: Identify which states have GPIO issues
- **Statistical Analysis**: See if pins are consistent across multiple runs

## Quick Start

### Basic Test (All 8 states once)
```bash
pipenv run python tests/gpio_verification.py
```

### Verbose Output (See each state result)
```bash
pipenv run python tests/gpio_verification.py --verbose
```

### Multiple Passes (For statistical confidence)
```bash
pipenv run python tests/gpio_verification.py --repeat 5
```

### Combined Options
```bash
pipenv run python tests/gpio_verification.py --verbose --repeat 3
```

## How It Works

### Test Sequence

For each calibration state (0-7):
1. **Set State**: Configure GPIO pins using gpiozero
2. **Wait**: Allow 100ms for hardware to settle
3. **Read State**: Query actual pin levels using `gpioinfo` or gpiozero fallback
4. **Verify**: Compare actual vs expected pin states
5. **Record**: Track pin values for statistics
6. **Report**: Print pass/fail result (verbose mode only)

### Expected Pin States

The test uses the same GPIO mapping as `rcal.py`:

```
Pin 16 (GPIO 16) = MSB (Bit 2)
Pin 20 (GPIO 20) = Middle (Bit 1)
Pin 21 (GPIO 21) = LSB (Bit 0)

Internal formula: idx = 7 - state_number
Binary = (pin16 << 2) | (pin20 << 1) | pin21
```

#### State Table

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
```bash
$ pipenv run python tests/gpio_verification.py

======================================================================
GPIO State Verification Test Suite
======================================================================
Testing 8 total state transitions (1 pass(es) of 8 states)
Verbose mode: False
Start time: 2025-11-18 11:45:30
----------------------------------------------------------------------

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

✓ ALL TESTS PASSED

End time: 2025-11-18 11:45:32
======================================================================
```

### Verbose Run with Multiple Passes
```bash
$ pipenv run python tests/gpio_verification.py --verbose --repeat 2

======================================================================
GPIO State Verification Test Suite
======================================================================
Testing 16 total state transitions (2 pass(es) of 8 states)
Verbose mode: True
Start time: 2025-11-18 11:46:00
----------------------------------------------------------------------

--- Pass 1/2 ---

  State 0: Antenna - Main Switch Powered
    Expected: Pin16=1, Pin20=1, Pin21=1
    Actual:   Pin16=1, Pin20=1, Pin21=1
    ✓ PASS

  State 1: Open Circuit
    Expected: Pin16=1, Pin20=1, Pin21=0
    Actual:   Pin16=1, Pin20=1, Pin21=0
    ✓ PASS

[... all states shown ...]

--- Pass 2/2 ---
[... all states shown again ...]

======================================================================
TEST RESULTS SUMMARY
======================================================================

Test Statistics:
  Total Tests:    16
  Passed:         16 (100.0%)
  Failed:         0

Pin State Statistics:
  Pin 16:
    HIGH: 8 times (50.0%)
    LOW:  8 times (50.0%)
  Pin 20:
    HIGH: 8 times (50.0%)
    LOW:  8 times (50.0%)
  Pin 21:
    HIGH: 8 times (50.0%)
    LOW:  8 times (50.0%)

✓ ALL TESTS PASSED

End time: 2025-11-18 11:46:04
======================================================================
```

### Failed Test Example
```bash
  State 2: 6" Shorted
    Expected: Pin16=1, Pin20=0, Pin21=1
    Actual:   Pin16=1, Pin20=1, Pin21=1
    ✗ FAIL
      - Pin 20: expected 0, got 1
```

## Understanding the Results

### Pin State Statistics

For a perfectly working GPIO system with 8 states (3 bits):
- Each pin should be HIGH about 50% of the time (4 out of 8 states)
- Each pin should be LOW about 50% of the time (4 out of 8 states)

**Anomalies to watch for:**
- A pin that's always HIGH or always LOW → May be stuck
- Pins with >60% HIGH or LOW → May indicate bias or issue with specific states
- Inconsistent results across multiple passes → May indicate timing or electrical issues

### Pass Rates

| Pass Rate | Status | Action |
|-----------|--------|--------|
| 100% | ✓ OK | GPIO control is working correctly |
| 75-99% | ⚠ Marginal | Some states fail occasionally - investigate |
| <75% | ✗ Failed | Multiple states failing - check GPIO wiring/driver |

## Troubleshooting

### Error: "GPIO Permission Denied"
```bash
sudo usermod -a -G gpio $USER
# Log out and back in
```

### All Tests Failing
1. Check GPIO pins are connected to header
2. Verify `gpiozero` or `pigpio` driver is available
3. Check if pins are in use by another process:
   ```bash
   gpioinfo | grep -E "GPIO (16|20|21)"
   ```

### Intermittent Failures
1. Increase delay between state changes (modify script)
2. Check power supply voltage stability
3. Look for electromagnetic interference near GPIO cables
4. Try multiple passes with `--repeat` to see pattern

### Pin Reads Don't Match gpiozero Values
- `gpioinfo` tool may not be available or permissions restricted
- Script falls back to gpiozero values
- Run with `sudo` if available to get more accurate readings

## Integration with CI/CD

### Run as Pre-Flight Check
```bash
#!/bin/bash
# Run GPIO verification before spectrometer operation
pipenv run python tests/gpio_verification.py --repeat 3
if [ $? -ne 0 ]; then
    echo "GPIO verification failed! Do not proceed with data collection."
    exit 1
fi
echo "GPIO verification passed. Ready to run spectrometer."
```

### Automated Test in Cron
```bash
# Test GPIO daily and log results
0 6 * * * cd /home/peterson/highz-digitalspec && pipenv run python tests/gpio_verification.py >> /var/log/gpio_test.log 2>&1
```

## Comparison with Manual Tool

| Aspect | `gpio_test.py` (Manual) | `gpio_verification.py` (Auto) |
|--------|------------------------|-------------------------------|
| Purpose | Manual testing/control | Automated verification |
| User Input | Interactive commands | None (automated) |
| Reporting | Status display | Pass/fail + statistics |
| Use Case | Development/debugging | Testing/validation |
| Exit Behavior | User-controlled | Auto-resets to state 0 |

## Advanced Usage

### Custom Test Script Wrapper
```bash
#!/bin/bash
# Run comprehensive GPIO test suite

echo "GPIO Verification Test Suite"
echo "============================"

# Quick baseline test
echo -e "\n1. Quick baseline (1 pass)..."
pipenv run python tests/gpio_verification.py

# Statistical analysis (10 passes)
echo -e "\n2. Statistical analysis (10 passes)..."
pipenv run python tests/gpio_verification.py --repeat 10 --verbose

# Log results
echo -e "\nTest completed at $(date)" >> gpio_test_results.log
```

## Performance Notes

- Each state transition takes ~100ms (configurable)
- Single pass (8 states): ~1 second
- 10 passes: ~10 seconds
- Test is non-blocking for system

## Related Files

- **Manual tool**: `tools/gpio_test.py` - Interactive GPIO control
- **GPIO driver**: `src/rcal.py` - Production GPIO control code
- **Spectrometer**: `src/run_spectrometer.py` - Uses GPIO control
- **Hardware config**: See `NETWORK_CONFIGURATION.md` for pin connections

## Dependencies

- `gpiozero` - GPIO control (already in pipenv)
- `gpioinfo` - GPIO state reading (system utility, may not be available)
- Linux GPIO sysfs or pigpio daemon - For GPIO access

## Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed or error occurred
- `Ctrl+C` - Test interrupted (returns to state 0)
