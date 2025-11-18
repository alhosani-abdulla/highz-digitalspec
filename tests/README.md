# Spectrometer Test Suite Overview

## Test Tools Summary

Your spectrometer control system now includes a comprehensive test suite for validating hardware connectivity, system health, and functionality. All tests are automated and provide detailed diagnostics.

## Available Tests

### 1. RFSoC Connection Test (`rfsoc_connection_test.py`)

**Purpose**: Validate FPGA connectivity and casperfpga library integration

**Tests**:
- ✓ Network connectivity (ping to 169.254.2.181)
- ✓ TCP socket connectivity (port 7147)
- ✓ casperfpga KATCP protocol connection
- ✓ FPGA bitstream validation (blocks, registers, memory)
- ✓ ADC/RFDC availability and initialization
- ✓ Register read/write access

**Quick Start**:
```bash
# Basic test
pipenv run python tests/rfsoc_connection_test.py

# Verbose output
pipenv run python tests/rfsoc_connection_test.py --verbose

# Custom timeout and IP
pipenv run python tests/rfsoc_connection_test.py --timeout 15 --fpga 169.254.2.181
```

**Documentation**: `tests/RFSOC_CONNECTION_TEST.md`

---

### 2. GPIO Verification Test (`gpio_verification.py`)

**Purpose**: Validate GPIO calibration states and GPIO pin control

**Tests**:
- ✓ All 8 GPIO calibration states (0-7)
- ✓ Pin state verification (HIGH/LOW)
- ✓ GPIO transition timing analysis
- ✓ System health during GPIO operations
- ✓ CPU temperature monitoring
- ✓ Supply voltage monitoring

**Quick Start**:
```bash
# Basic test (all 8 states)
pipenv run python tests/gpio_verification.py

# With verbose output
pipenv run python tests/gpio_verification.py --verbose

# Multiple test runs
pipenv run python tests/gpio_verification.py --repeat 3 --timing

# Test specific states only
pipenv run python tests/gpio_verification.py --repeat 5
```

**Documentation**: `tests/GPIO_VERIFICATION.md`

---

### 3. System Health Diagnostic (`system_health.py`)

**Purpose**: Monitor system hardware metrics and overall health

**Monitors**:
- ✓ CPU temperature and thermal zones
- ✓ SDRAM voltage rail
- ✓ Throttling status (undervolting, capping, temperature)
- ✓ RAM usage (total, used, available)
- ✓ Storage usage (disk space)
- ✓ System uptime and load averages

**Quick Start**:
```bash
# Quick health report
pipenv run python tests/system_health.py

# Verbose mode
pipenv run python tests/system_health.py --verbose

# Continuous monitoring (5 measurements)
pipenv run python tests/system_health.py --repeat 5

# JSON output for automation
pipenv run python tests/system_health.py --json
```

**Documentation**: `tests/SYSTEM_HEALTH.md`

---

## Test Workflow Recommendations

### Pre-Measurement Checklist

```bash
# 1. Check system health
echo "=== System Health ==="
pipenv run python tests/system_health.py

# 2. Verify RFSoC connectivity
echo "=== RFSoC Connection ==="
pipenv run python tests/rfsoc_connection_test.py

# 3. Validate GPIO controls
echo "=== GPIO Verification ==="
pipenv run python tests/gpio_verification.py --repeat 2

# 4. Ready for measurement
echo "=== Ready to start spectrometer ==="
pipenv run python src/run_spectrometer.py
```

### Quick Daily Validation (under 2 minutes)

```bash
# Fast network-only check
ping -c 1 -W 2 169.254.2.181 && echo "✓ Network OK"

# System health snapshot
pipenv run python tests/system_health.py | grep "Overall Status"

# GPIO quick test
pipenv run python tests/gpio_verification.py 2>&1 | tail -3
```

### Continuous Monitoring

```bash
# Monitor system health every minute
watch -n 60 'pipenv run python tests/system_health.py'

# Log health metrics
while true; do
  pipenv run python tests/system_health.py --json >> health_log.jsonl
  sleep 300  # Every 5 minutes
done
```

### Troubleshooting Failed Tests

Each test provides detailed diagnostic recommendations:

```bash
# RFSoC not responding?
pipenv run python tests/rfsoc_connection_test.py --verbose

# System overheating?
pipenv run python tests/system_health.py

# GPIO not working?
pipenv run python tests/gpio_verification.py --verbose
```

## Test Status Reference

### Health Status Codes

All tests use consistent status indicators:

| Icon | Status | Meaning |
|------|--------|---------|
| ✓ | PASS | Test successful |
| ✗ | FAIL | Test failed |
| ⚠ | WARNING | Issue detected but test continued |
| ○ | SKIP | Test skipped (prerequisite failed) |
| ○ | ERROR | Unrecoverable error |

### Color Coding

- 🟢 **Green (HEALTHY)**: All metrics within normal range
- 🟡 **Yellow (WARNING)**: One or more metrics in warning range
- 🔴 **Red (CRITICAL)**: One or more metrics at critical levels

## Exit Codes

All tests follow standard exit codes:

```
0   = All tests passed
1   = One or more tests failed
130 = User interrupted (Ctrl+C)
```

Can be used in scripts:

```bash
if pipenv run python tests/rfsoc_connection_test.py; then
    echo "FPGA ready"
    pipenv run python src/run_spectrometer.py
else
    echo "FPGA not ready"
    exit 1
fi
```

## Manual Testing Tools

For manual hardware control (not automated testing):

- `tools/gpio_test.py` - Interactive GPIO control script
- See `tools/GPIO_TESTING.md` for manual testing procedures

## Running All Tests

```bash
# Run all tests sequentially
#!/bin/bash
set -e  # Exit on first failure

echo "Starting complete test suite..."
pipenv run python tests/system_health.py
pipenv run python tests/rfsoc_connection_test.py
pipenv run python tests/gpio_verification.py

echo "All tests passed!"
```

## Test Dependencies

All tests use Python packages already in Pipfile:

```
Required:
  - casperfpga (for RFSoC connection test)
  - psutil (for system health test)
  - numpy (optional, for extended analysis)

System utilities:
  - ping (for network tests)
  - hostname, df, free (for system diagnostics)
  - vcgencmd (Raspberry Pi only, for temperature)
```

## Performance Baseline

Typical test execution times:

| Test | Time | Notes |
|------|------|-------|
| GPIO Verification | 2-3 seconds | Per cycle, scales with --repeat |
| System Health | <1 second | Basic report |
| RFSoC Connection | 10-30 seconds | Depends on FPGA responsiveness |

## Integration with CI/CD

Tests can be integrated into automated workflows:

```bash
# GitHub Actions example
- name: Run system health check
  run: pipenv run python tests/system_health.py

- name: Verify RFSoC connection
  run: pipenv run python tests/rfsoc_connection_test.py

- name: Run GPIO verification
  run: pipenv run python tests/gpio_verification.py --repeat 3
```

## Troubleshooting Test Issues

### Test times out
- Increase timeout: `--timeout 20` (RFSoC test)
- Check network: `ping -c 1 169.254.2.181`
- Check RFSoC: Connect to serial console

### Test crashes
- Enable verbose: `--verbose`
- Check dependencies: `pipenv install --sync`
- Review recent changes: `git log --oneline -5`

### Inconsistent results
- Run with multiple iterations: `--repeat 5`
- Check system load: `top` or `system_health.py`
- Check for thermal throttling

## Related Documentation

- `src/run_spectrometer.py` - Main spectrometer control code
- `tools/gpio_test.py` - Manual GPIO control tool
- `NETWORK_CONFIGURATION.md` - Network setup
- `README.md` - Project overview

## Future Test Enhancements

Planned additions to test suite:

- [ ] Bitstream upload and programming test
- [ ] ADC clock configuration validation
- [ ] Memory stress testing
- [ ] Data acquisition validation
- [ ] Real-time performance monitoring
- [ ] Historical trend analysis
- [ ] Automated performance baselines

## Support

For issues with tests:

1. Run with `--verbose` flag for detailed output
2. Check test documentation in `tests/` directory
3. Review error recommendations provided by test
4. Check system logs: `dmesg`, `journalctl`
5. Connect to RFSoC serial console for firmware diagnostics

---

**Last Updated**: November 18, 2025
**Test Suite Version**: 1.0
