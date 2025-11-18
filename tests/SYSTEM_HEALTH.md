# System Health Diagnostic Tool

## Overview

The `system_health.py` tool provides comprehensive system diagnostics and health monitoring for the spectrometer control system. It monitors critical hardware metrics and generates health status reports with recommendations for any anomalies detected.

## Features

### Monitored Metrics

1. **CPU Temperature**
   - Current CPU temperature
   - Thresholds: Warning 75°C, Critical 85°C
   - Color-coded output with status icons

2. **Thermal Zones**
   - All available thermal sensor readings
   - Includes sensor type information
   - Individual status for each zone

3. **Power Supply (Voltage)**
   - SDRAM voltage rail monitoring (1.1V nominal)
   - Thresholds: Warning 1.05V, Critical 1.0V
   - Indicates power supply health

4. **Throttling Status**
   - Detects if system is throttling due to:
     - Undervolting
     - Frequency capping
     - Temperature limits
     - Soft temperature limits
   - Shows detailed throttling reasons if active

5. **Memory Usage**
   - Total, used, and available RAM
   - Percentage utilization
   - Thresholds: Warning 80%, Critical 95%
   - Human-readable byte formatting

6. **Storage Usage**
   - Total, used, and free disk space
   - Percentage utilization
   - Thresholds: Warning 80%, Critical 95%
   - Monitored path: root filesystem (/)

7. **System Information**
   - Hostname
   - CPU core count (physical and logical)
   - System uptime
   - Load averages (1min, 5min, 15min)

### Health Status Indicators

Status levels are color-coded:
- **✓ HEALTHY (Green)**: All metrics within normal limits
- **⚠ WARNING (Yellow)**: One or more metrics in warning range
- **✗ CRITICAL (Red)**: One or more metrics at critical levels

## Installation

The tool requires `psutil` for system metrics collection:

```bash
# Install psutil in the spectrometer environment
pipenv install psutil
```

## Usage

### Basic Diagnostic Report

```bash
pipenv run python tests/system_health.py
```

Output displays formatted health report with all metrics and overall status.

### Verbose Output

```bash
pipenv run python tests/system_health.py --verbose
```

Enables additional diagnostic details (future expansion for detailed logging).

### Multiple Runs with Interval

```bash
pipenv run python tests/system_health.py --repeat 5
```

Runs diagnostic 5 times with 1-second delays between runs. Useful for:
- Monitoring temperature trends
- Detecting intermittent throttling
- Observing load changes

### JSON Output

```bash
pipenv run python tests/system_health.py --json
```

Outputs raw metrics in JSON format for:
- Machine parsing
- Integration with monitoring systems
- Data logging and archival

Example JSON output:
```json
{
  "system": {
    "hostname": "highz-rpi-1",
    "uptime_seconds": 3507.9,
    "cpu_count": 4,
    "load_average": {"1min": 0.17, "5min": 0.30, "15min": 0.29}
  },
  "cpu_temperature": {"value": 50.1, "unit": "°C", "status": "healthy"},
  "ram": {"total": 3981172736, "used": 2489663488, "percent": 62.5, "status": "healthy"},
  "storage": {"total": 251286482944, "used": 10870882304, "percent": 4.3, "status": "healthy"}
}
```

### Combined Options

```bash
# Verbose output with multiple runs
pipenv run python tests/system_health.py --verbose --repeat 3

# JSON output with 10 consecutive measurements
pipenv run python tests/system_health.py --json --repeat 10
```

## Output Examples

### Healthy System

```
======================================================================
SYSTEM HEALTH DIAGNOSTIC REPORT
======================================================================
Timestamp: 2025-11-18T12:04:04.727382

Overall Status: ✓ HEALTHY

SYSTEM INFORMATION
----------------------------------------------------------------------
  Hostname:        highz-rpi-1
  CPU Cores:       4 physical, 4 logical
  Uptime:          0d 0h
  Load Average:    0.24 (1min) 0.32 (5min) 0.29 (15min)

CPU TEMPERATURE
----------------------------------------------------------------------
  ✓ 51.1°C (Limits: Warning 75°C, Critical 85°C)

THERMAL ZONES
----------------------------------------------------------------------
  ✓ thermal_zone0 (cpu-thermal): 51.1°C

POWER SUPPLY
----------------------------------------------------------------------
  ✓ SDRAM Voltage: 1.10V
    (Nominal: 1.1V, Limits: Warning 1.05V, Critical 1.0V)

THROTTLING STATUS
----------------------------------------------------------------------
  ✓ No throttling

MEMORY USAGE
----------------------------------------------------------------------
  ✓ 62.2% used
    Used:      2.3GB / 3.7GB
    Available: 1.4GB
    (Limits: Warning 80%, Critical 95%)

STORAGE USAGE
----------------------------------------------------------------------
  ✓ 4.5% used
    Used: 10.1GB / 234.0GB
    Free: 214.3GB
    (Limits: Warning 80%, Critical 95%)

======================================================================
```

### System with Warnings

If a system shows warnings or critical issues, recommendations appear at the end:

```
RECOMMENDATIONS
----------------------------------------------------------------------
  ⚠ CPU temperature is elevated - monitor cooling system
  ⚠ High memory usage - consider stopping non-essential processes
```

## Threshold Reference

### Temperature Thresholds
| Level | CPU Temp | Thermal Zone |
|-------|----------|--------------|
| Healthy | < 75°C | < 75°C |
| Warning | 75-85°C | 75-85°C |
| Critical | > 85°C | > 85°C |

### Voltage Thresholds (SDRAM Rail)
| Level | Voltage |
|-------|---------|
| Healthy | ≥ 1.05V |
| Warning | 1.0-1.05V |
| Critical | < 1.0V |

### Memory/Storage Thresholds
| Level | Usage |
|-------|-------|
| Healthy | < 80% |
| Warning | 80-95% |
| Critical | > 95% |

## Interpreting Results

### High Temperature
- **Cause**: Excessive CPU load, inadequate cooling
- **Action**: Reduce workload, check cooling solution, ensure proper ventilation
- **Critical**: If sustained above 85°C, system will throttle

### Throttling Active
- **Undervolted**: Power supply issue, need stable 5V
- **Capped**: CPU frequency reduced, usually due to temperature or power
- **Throttled**: Triggered by high temperature, reduce load
- **Soft limit**: Soft temperature limit active, monitor thermal conditions

### High Memory Usage
- **Action**: Monitor for memory leaks in spectrometer code
- **Critical**: If > 95%, system may become unstable or crash
- **Solution**: Stop non-essential processes, increase available memory

### High Storage Usage
- **Action**: Check /home/peterson/Data/ for old measurements
- **Critical**: Filesystem performance degrades with < 5% free space
- **Solution**: Archive or delete old data files

### Low Supply Voltage
- **Cause**: Weak power supply, cable resistance, high load
- **Action**: Check power supply rating and cable integrity
- **Critical**: Can cause undervolting and throttling

## Integration Examples

### Running Before Spectrometer Acquisition

```bash
# Check system health before starting measurements
pipenv run python tests/system_health.py

# If CRITICAL or WARNING is shown, investigate before proceeding
pipenv run python src/run_spectrometer.py
```

### Monitoring Long-Running Measurements

```bash
# Run health check in background while spectrometer operates
while true; do
  pipenv run python tests/system_health.py
  sleep 60
done &

# Start spectrometer measurement
pipenv run python src/run_spectrometer.py
```

### Data Logging

```bash
# Log health metrics every minute
while true; do
  echo "=== $(date) ===" >> system_health.log
  pipenv run python tests/system_health.py --json >> system_health.log
  sleep 60
done &
```

### Automated Alerts

```bash
# Run periodic health checks and alert if critical
#!/bin/bash
while true; do
  output=$(pipenv run python tests/system_health.py 2>&1)
  if echo "$output" | grep -q "CRITICAL"; then
    echo "ALERT: System health CRITICAL!" | mail -s "RPi Health Alert" user@example.com
  fi
  sleep 300  # Check every 5 minutes
done
```

## Troubleshooting

### "Error: psutil module not found"
```bash
pipenv install psutil
pipenv lock
```

### "vcgencmd not found"
Only available on Raspberry Pi. On other systems, temperature will be skipped gracefully.

### Voltage reading seems wrong
- SDRAM voltage (1.1V nominal) is an internal rail, not the 5V supply
- 5V supply voltage isn't directly readable via vcgencmd
- If SDRAM voltage is healthy, 5V supply is likely OK
- Check power supply with multimeter if issues suspected

### Very high uptime shows "0d 0h"
- Occurs on fresh boot
- Uptime calculation corrects after system has been running
- Not an error condition

## System Requirements

- Python 3.7+
- psutil module (installed via pipenv)
- vcgencmd (on Raspberry Pi)
- Linux with thermal zone support in /sys/class/thermal/

## Files

- **Source**: `tests/system_health.py`
- **Documentation**: `tests/SYSTEM_HEALTH.md` (this file)
- **Related**: `tests/gpio_verification.py` (includes basic system monitoring)
- **Related**: `tests/GPIO_VERIFICATION.md` (GPIO test documentation)

## Version History

### v1.0 (Current)
- Comprehensive system health monitoring
- Temperature, voltage, throttling detection
- RAM and storage usage tracking
- System uptime and load averages
- Color-coded status indicators
- JSON output support
- Repeat measurement capability
- Recommendations for anomalies

## Future Enhancements

- Historical trend tracking
- Alert thresholds configuration
- Email/SMS notification support
- Graphical trend visualization
- Integration with syslog
- Performance baseline comparison
