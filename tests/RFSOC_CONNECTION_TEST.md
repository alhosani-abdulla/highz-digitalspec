# RFSoC Connection Test Documentation

## Overview

The `rfsoc_connection_test.py` tool provides comprehensive testing and diagnostics for RFSoC FPGA connectivity and casperfpga library integration. It validates the entire connection chain from network layer up through FPGA bitstream and ADC accessibility.

## Features

### Connection Layer Tests

1. **Network Connectivity**
   - Pings the RFSoC FPGA IP address (169.254.2.181)
   - Measures network latency
   - Detects link-local IPv4 connectivity

2. **Socket Connectivity**
   - Tests TCP connection to casperfpga port (7147)
   - Validates RFSoC server is responding
   - Measures connection time

3. **casperfpga Library Connection**
   - Establishes KATCP protocol connection
   - Validates transport layer
   - Retrieves connection metadata

### FPGA/Bitstream Tests

4. **Bitstream Information**
   - Lists all programmable blocks (FPGA blocks)
   - Enumerates available registers
   - Maps memory regions
   - Validates bitstream is properly loaded

5. **ADC/RFDC Tests**
   - Checks RFDC ADC availability
   - Validates ADC interface accessibility
   - Tests ADC initialization sequence
   - Retrieves ADC status information

### Access Tests

6. **Register Access**
   - Attempts register read operations
   - Validates register interface
   - Confirms communication with FPGA fabric

## Installation

The test requires casperfpga to be installed (already in Pipfile):

```bash
# Verify casperfpga is available
pipenv install casperfpga
```

## Usage

### Basic Test Run

```bash
pipenv run python tests/rfsoc_connection_test.py
```

Runs all tests sequentially and produces a summary report.

### Verbose Output

```bash
pipenv run python tests/rfsoc_connection_test.py --verbose
```

Enables detailed logging for each test step and error messages.

### Custom FPGA IP Address

```bash
pipenv run python tests/rfsoc_connection_test.py --fpga 192.168.1.100
```

Tests a different FPGA IP address (useful for non-standard configurations).

### Extended Timeout

```bash
pipenv run python tests/rfsoc_connection_test.py --timeout 15
```

Increases connection timeout from default 10s to 15s (useful over slower networks).

### Combined Options

```bash
# Complete diagnostics with extended timeout and verbose output
pipenv run python tests/rfsoc_connection_test.py --verbose --timeout 15 --fpga 169.254.2.181
```

## Output Examples

### Successful Connection

```
======================================================================
RFSoC CONNECTION TEST SUMMARY
======================================================================
FPGA IP: 169.254.2.181
Test Time: 2025-11-18T14:35:22.445201

TEST RESULTS
----------------------------------------------------------------------
✓ network_connectivity.................... PASS
  └─ Successfully reached 169.254.2.181 (latency: 2.15 ms)
✓ socket_connectivity..................... PASS
  └─ Connected successfully in 45.3 ms
✓ casperfpga_connection................... PASS
  └─ casperfpga connection successful (123.5 ms)
✓ bitstream_info.......................... PASS
  └─ Bitstream loaded: 24 blocks, 156 registers, 8 memory regions
✓ adc_availability........................ PASS
  └─ RFDC ADC found and accessible
✓ adc_initialization...................... PASS
  └─ ADC initialized successfully
✓ adc_status.............................. PASS
  └─ ADC status retrieved
✓ register_access......................... PASS
  └─ Successfully read register 'acc_len': 17500

======================================================================
Overall Status: ✓ PASSED
======================================================================
```

### Failed Connection (RFSoC Offline)

```
======================================================================
RFSoC CONNECTION TEST SUMMARY
======================================================================
FPGA IP: 169.254.2.181
Test Time: 2025-11-18T12:14:21.178057

TEST RESULTS
----------------------------------------------------------------------
✗ network_connectivity.................... FAIL
  └─ Ping to 169.254.2.181 failed
✗ socket_connectivity..................... FAIL
  └─ Connection timeout (10s)
○ casperfpga_connection................... ERROR
  └─ casperfpga error: Possible that host does not follow one of the defined casperfpga transport protocols
○ bitstream_info.......................... SKIP
  └─ FPGA not connected
[... remaining tests skipped ...]

======================================================================
Overall Status: ✗ FAILED
======================================================================

ERRORS:
----------------------------------------------------------------------
1. Network connectivity failed: Ping to 169.254.2.181 failed
2. Socket connection timed out to 169.254.2.181:7147
3. casperfpga connection failed: Possible that host does not follow one of the defined casperfpga transport protocols

RECOMMENDATIONS:
----------------------------------------------------------------------
• Check network connectivity:
  - Verify eth0 is configured: ip addr show eth0
  - Manually ping RFSoC: ping 169.254.2.181
  - Check NetworkManager connection: nmcli conn show
• RFSoC server not responding:
  - Check RFSoC is powered on and booted
  - Connect to serial console: minicom -D /dev/ttyUSB1
  - Verify bitstream is loaded on RFSoC
```

### Partial Failure (Network OK, FPGA Issue)

```
TEST RESULTS
----------------------------------------------------------------------
✓ network_connectivity.................... PASS
  └─ Successfully reached 169.254.2.181 (latency: 1.89 ms)
✓ socket_connectivity..................... PASS
  └─ Connected successfully in 32.1 ms
✓ casperfpga_connection................... PASS
  └─ casperfpga connection successful (85.2 ms)
⚠ bitstream_info.......................... WARNING
  └─ Could not query bitstream: No blocks found
⚠ adc_availability........................ WARNING
  └─ Expected 'rfdc' ADC not found. Available: ['adc0', 'adc1']
[... remaining tests skipped ...]

======================================================================
Overall Status: ⚠ PASSED WITH WARNINGS
======================================================================

WARNINGS:
----------------------------------------------------------------------
1. Bitstream query incomplete: No blocks found
2. Expected 'rfdc' ADC not found. Available: ['adc0', 'adc1']
```

## Test Sequencing

The tests are designed to fail gracefully and proceed logically:

```
1. Network Connectivity (layer 1)
   ↓ (if fails, remaining tests will timeout)
2. Socket Connectivity (layer 2)
   ↓ (if fails, casperfpga cannot connect)
3. casperfpga Connection (layer 3)
   ↓ (if fails, no FPGA access)
4-8. FPGA/ADC Tests (layer 4-5)
   ↓ (dependent on casperfpga connection)
```

Early failures cause cascading test skips to save time.

## Test Status Codes

- **✓ PASS**: Test completed successfully
- **✗ FAIL**: Test failed (unexpected condition)
- **⚠ WARNING**: Test completed with issues (data available but incomplete)
- **○ SKIP**: Test skipped (prerequisite failed)
- **○ ERROR**: Unrecoverable error in test

## Troubleshooting

### Network connectivity failed

**Problem**: Test fails to ping RFSoC

**Causes**:
- RFSoC powered off or unreachable
- Ethernet cable disconnected
- NetworkManager eth0 not configured
- Link-local IPv4 not assigned

**Solutions**:
```bash
# Check eth0 configuration
ip addr show eth0

# Verify NetworkManager connection
nmcli conn show

# Manually ping RFSoC
ping -c 1 169.254.2.181

# Restart NetworkManager if needed
sudo systemctl restart NetworkManager

# See NETWORK_CONFIGURATION.md for persistent setup
```

### Socket connectivity timeout

**Problem**: TCP connection to port 7147 times out

**Causes**:
- RFSoC server crashed or not started
- Firewall blocking port 7147
- Bitstream not loaded on RFSoC

**Solutions**:
```bash
# Connect to RFSoC serial console
minicom -D /dev/ttyUSB1

# Check if server is running (in RFSoC terminal):
ps aux | grep -i server

# Reboot RFSoC if needed
reboot

# Check firewall on RPi
sudo ufw status
```

### casperfpga connection error

**Problem**: Connection established but KATCP protocol fails

**Causes**:
- casperfpga version incompatible with RFSoC firmware
- Corrupted bitstream
- casperfpga not installed

**Solutions**:
```bash
# Reinstall casperfpga
pipenv install --force-reinstall casperfpga

# Check casperfpga version
pipenv run python -c "import casperfpga; print(casperfpga.__version__)"

# Reload bitstream on RFSoC (in RFSoC terminal):
# See RFSoC documentation for bitstream loading procedure
```

### ADC/RFDC not found

**Problem**: FPGA connected but RFDC ADC not accessible

**Causes**:
- Bitstream doesn't include RFDC block
- ADC name different in bitstream
- ADC initialization required first

**Solutions**:
- Verify bitstream includes RFDC block
- Check bitstream compilation log for errors
- Inspect RFSoC serial output during boot
- See run_spectrometer.py for ADC initialization code

### Register read failed

**Problem**: FPGA connected but register access fails

**Causes**:
- Register name doesn't exist in bitstream
- FPGA communication interrupted
- Register address out of bounds

**Solutions**:
- Run test with `--verbose` to see which register failed
- Check bitstream register definitions
- Verify test_register_access uses valid register from list

## Integration with Spectrometer

### Pre-Flight Check Before Measurement

```bash
# Run connection test before each measurement session
pipenv run python tests/rfsoc_connection_test.py

# If test passes, proceed with spectrometer
if [ $? -eq 0 ]; then
    pipenv run python src/run_spectrometer.py
else
    echo "FPGA connection failed - check diagnostics above"
fi
```

### Automated Health Monitoring

```bash
#!/bin/bash
# Monitor RFSoC connection every 5 minutes

while true; do
    echo "=== $(date) ===" >> rfsoc_health.log
    if ! pipenv run python tests/rfsoc_connection_test.py >> rfsoc_health.log 2>&1; then
        echo "ALERT: RFSoC connection lost!"
        # Optional: send alert, restart service, etc.
    fi
    sleep 300  # 5 minutes
done
```

### Quick Connection Verification

```bash
# Fast network-only check (under 3 seconds)
ping -c 1 -W 2 169.254.2.181 && echo "RFSoC reachable" || echo "RFSoC unreachable"

# Quick socket check (under 5 seconds)
timeout 5 bash -c '</dev/tcp/169.254.2.181/7147' && echo "RFSoC server responding" || echo "Server not responding"
```

## System Requirements

- Python 3.7+
- casperfpga module
- Network connectivity to RFSoC (link-local IPv4 or routable IP)
- ping, timeout commands available
- Linux/Unix environment

## Related Documentation

- `NETWORK_CONFIGURATION.md` - Network setup and troubleshooting
- `src/run_spectrometer.py` - Spectrometer initialization code
- `tests/system_health.py` - System diagnostics
- `tests/GPIO_VERIFICATION.md` - GPIO test documentation

## Version History

### v1.0 (Current)
- Comprehensive connection testing
- Network and socket layer validation
- casperfpga library integration testing
- FPGA bitstream and ADC verification
- Register access testing
- Intelligent error recommendations
- Verbose output mode
- Configurable timeout and IP address

## Future Enhancements

- Bitstream upload and programming test
- ADC clock configuration testing
- Memory read/write stress test
- Ongoing connection monitoring
- Historical connection statistics
- Performance baseline establishment
- Automated troubleshooting suggestions
