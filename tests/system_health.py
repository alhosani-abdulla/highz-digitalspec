#!/usr/bin/env python3
"""
System Health Diagnostic Tool

Provides comprehensive system diagnostics including:
- CPU temperature and thermal zones
- RAM usage and availability
- Storage status
- Supply voltage and throttling
- System uptime and load averages
- Overall health status report

Usage:
    pipenv run python tests/system_health.py [--verbose] [--repeat N]
"""

import sys
import os
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict

try:
    import psutil
except ImportError:
    print("Error: psutil module not found. Install with: pipenv install psutil")
    sys.exit(1)


class SystemHealthMonitor:
    """Monitor and report system health metrics."""

    # Temperature thresholds (Celsius)
    TEMP_THRESHOLDS = {
        "critical": 85,
        "warning": 75,
        "healthy": 0,
    }

    # RAM usage thresholds (percentage)
    RAM_THRESHOLDS = {
        "critical": 95,
        "warning": 80,
        "healthy": 0,
    }

    # Storage usage thresholds (percentage)
    STORAGE_THRESHOLDS = {
        "critical": 95,
        "warning": 80,
        "healthy": 0,
    }

    def __init__(self):
        """Initialize the system health monitor."""
        self.metrics = defaultdict(dict)
        self.timestamp = datetime.now().isoformat()

    def get_cpu_temperature(self):
        """Get CPU temperature using vcgencmd."""
        try:
            result = subprocess.run(
                ["/usr/bin/vcgencmd", "measure_temp"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # Output format: "temp=XX.X'C"
            output = result.stdout.strip()
            if output.startswith("temp="):
                temp_str = output.split("=")[1].replace("'C", "")
                return float(temp_str)
        except Exception as e:
            print(f"Warning: Could not read CPU temperature: {e}", file=sys.stderr)
        return None

    def get_thermal_zones(self):
        """Get all thermal zone temperatures."""
        thermal_zones = {}
        thermal_path = Path("/sys/class/thermal")

        try:
            for zone_dir in sorted(thermal_path.glob("thermal_zone*")):
                zone_name = zone_dir.name
                temp_file = zone_dir / "temp"
                type_file = zone_dir / "type"

                if temp_file.exists() and type_file.exists():
                    with open(type_file) as f:
                        zone_type = f.read().strip()
                    with open(temp_file) as f:
                        # Temperatures are in millidegrees Celsius
                        temp_millidegrees = int(f.read().strip())
                        temp_celsius = temp_millidegrees / 1000.0

                    thermal_zones[zone_name] = {
                        "type": zone_type,
                        "temperature": temp_celsius,
                    }
        except Exception as e:
            print(f"Warning: Could not read thermal zones: {e}", file=sys.stderr)

        return thermal_zones

    def get_supply_voltage(self):
        """Get supply voltage using vcgencmd (returns core voltage regulator output)."""
        try:
            # On Raspberry Pi, we can read internal voltage regulators
            # sdram rails are typically around 1.1V and more stable
            result = subprocess.run(
                ["/usr/bin/vcgencmd", "measure_volts", "sdram_c"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # Output format: "volt=X.XXV"
            output = result.stdout.strip()
            if output.startswith("volt="):
                volt_str = output.split("=")[1].replace("V", "")
                voltage = float(volt_str)
                return voltage
        except Exception as e:
            print(f"Warning: Could not read supply voltage: {e}", file=sys.stderr)
        return None

    def get_throttling_status(self):
        """Get throttling status from vcgencmd."""
        throttling_info = {
            "undervolted": False,
            "capped": False,
            "throttled": False,
            "has_soft_templimit": False,
        }
        try:
            result = subprocess.run(
                ["/usr/bin/vcgencmd", "get_throttled"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # Output format: "throttled=0xXXXXX"
            output = result.stdout.strip()
            if output.startswith("throttled="):
                hex_str = output.split("=")[1]
                throttle_value = int(hex_str, 16)

                # Bit flags:
                # 0x00001: Undervolted
                # 0x00002: Capped
                # 0x00004: Throttled
                # 0x00008: Soft temperature limit active
                throttling_info["undervolted"] = bool(throttle_value & 0x00001)
                throttling_info["capped"] = bool(throttle_value & 0x00002)
                throttling_info["throttled"] = bool(throttle_value & 0x00004)
                throttling_info["has_soft_templimit"] = bool(throttle_value & 0x00008)
        except Exception as e:
            print(f"Warning: Could not read throttling status: {e}", file=sys.stderr)

        return throttling_info

    def get_ram_usage(self):
        """Get RAM usage statistics."""
        try:
            virtual_memory = psutil.virtual_memory()
            return {
                "total": virtual_memory.total,
                "used": virtual_memory.used,
                "available": virtual_memory.available,
                "percent": virtual_memory.percent,
                "free": virtual_memory.free,
            }
        except Exception as e:
            print(f"Warning: Could not read RAM usage: {e}", file=sys.stderr)
        return None

    def get_storage_usage(self, path="/"):
        """Get storage usage for a given path."""
        try:
            disk_usage = psutil.disk_usage(path)
            return {
                "total": disk_usage.total,
                "used": disk_usage.used,
                "free": disk_usage.free,
                "percent": disk_usage.percent,
            }
        except Exception as e:
            print(f"Warning: Could not read storage usage: {e}", file=sys.stderr)
        return None

    def get_system_info(self):
        """Get general system information."""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            uptime_hours = uptime_seconds / 3600
            uptime_days = uptime_hours / 24

            load_avg = os.getloadavg()

            return {
                "hostname": subprocess.run(
                    ["hostname"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                ).stdout.strip(),
                "uptime_seconds": uptime_seconds,
                "uptime_formatted": f"{int(uptime_days)}d {int(uptime_hours % 24)}h",
                "load_average": {
                    "1min": load_avg[0],
                    "5min": load_avg[1],
                    "15min": load_avg[2],
                },
                "cpu_count": psutil.cpu_count(logical=False),
                "cpu_count_logical": psutil.cpu_count(logical=True),
            }
        except Exception as e:
            print(f"Warning: Could not read system info: {e}", file=sys.stderr)
        return {}

    def _get_status_icon(self, status):
        """Return icon for status."""
        icons = {
            "healthy": "✓",
            "warning": "⚠",
            "critical": "✗",
        }
        return icons.get(status, "?")

    def _get_status_color(self, status):
        """Return ANSI color code for status."""
        colors = {
            "healthy": "\033[92m",  # Green
            "warning": "\033[93m",  # Yellow
            "critical": "\033[91m",  # Red
            "reset": "\033[0m",
        }
        return colors.get(status, "")

    def _determine_status(self, value, thresholds):
        """Determine health status based on value and thresholds."""
        if value >= thresholds["critical"]:
            return "critical"
        elif value >= thresholds["warning"]:
            return "warning"
        else:
            return "healthy"

    def format_bytes(self, bytes_val):
        """Convert bytes to human-readable format."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_val < 1024:
                return f"{bytes_val:.1f}{unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f}PB"

    def collect_metrics(self):
        """Collect all system health metrics."""
        print("Collecting system health metrics...", file=sys.stderr)

        # System information
        self.metrics["system"] = self.get_system_info()

        # CPU Temperature
        cpu_temp = self.get_cpu_temperature()
        if cpu_temp is not None:
            self.metrics["cpu_temperature"] = {
                "value": cpu_temp,
                "unit": "°C",
                "status": self._determine_status(
                    cpu_temp, self.TEMP_THRESHOLDS
                ),
            }

        # Thermal Zones
        thermal_zones = self.get_thermal_zones()
        if thermal_zones:
            self.metrics["thermal_zones"] = {}
            for zone_name, zone_data in thermal_zones.items():
                temp = zone_data["temperature"]
                self.metrics["thermal_zones"][zone_name] = {
                    "type": zone_data["type"],
                    "temperature": temp,
                    "unit": "°C",
                    "status": self._determine_status(
                        temp, self.TEMP_THRESHOLDS
                    ),
                }

        # Supply Voltage
        voltage = self.get_supply_voltage()
        if voltage is not None:
            # SDRAM voltage thresholds: 1.1V nominal, warn if < 1.05V
            status = "healthy"
            if voltage < 1.0:
                status = "critical"
            elif voltage < 1.05:
                status = "warning"
            self.metrics["supply_voltage"] = {
                "value": voltage,
                "unit": "V",
                "rail": "SDRAM",
                "status": status,
            }

        # Throttling Status
        throttling = self.get_throttling_status()
        throttling_active = any(
            throttling[key] for key in throttling if key != "has_soft_templimit"
        )
        self.metrics["throttling"] = {
            "active": throttling_active,
            "status": "critical" if throttling_active else "healthy",
            "details": throttling,
        }

        # RAM Usage
        ram = self.get_ram_usage()
        if ram is not None:
            self.metrics["ram"] = {
                "total": ram["total"],
                "used": ram["used"],
                "available": ram["available"],
                "percent": ram["percent"],
                "status": self._determine_status(
                    ram["percent"], self.RAM_THRESHOLDS
                ),
            }

        # Storage Usage
        storage = self.get_storage_usage()
        if storage is not None:
            self.metrics["storage"] = {
                "total": storage["total"],
                "used": storage["used"],
                "free": storage["free"],
                "percent": storage["percent"],
                "status": self._determine_status(
                    storage["percent"], self.STORAGE_THRESHOLDS
                ),
            }

        self.timestamp = datetime.now().isoformat()

    def get_overall_status(self):
        """Determine overall system status."""
        statuses = []
        for key, value in self.metrics.items():
            if isinstance(value, dict) and "status" in value:
                statuses.append(value["status"])
            elif key == "thermal_zones":
                for zone_data in value.values():
                    if "status" in zone_data:
                        statuses.append(zone_data["status"])

        if "critical" in statuses:
            return "critical"
        elif "warning" in statuses:
            return "warning"
        else:
            return "healthy"

    def print_report(self, verbose=False):
        """Print formatted health report."""
        print("\n" + "=" * 70)
        print("SYSTEM HEALTH DIAGNOSTIC REPORT")
        print("=" * 70)
        print(f"Timestamp: {self.timestamp}\n")

        # Overall status
        overall_status = self.get_overall_status()
        status_icon = self._get_status_icon(overall_status)
        status_color = self._get_status_color(overall_status)
        print(
            f"{status_color}Overall Status: {status_icon} {overall_status.upper()}{self._get_status_color('reset')}\n"
        )

        # System Information
        if self.metrics.get("system"):
            print("SYSTEM INFORMATION")
            print("-" * 70)
            sys_info = self.metrics["system"]
            if "hostname" in sys_info:
                print(f"  Hostname:        {sys_info['hostname']}")
            if "cpu_count" in sys_info:
                print(f"  CPU Cores:       {sys_info['cpu_count']} physical, {sys_info['cpu_count_logical']} logical")
            if "uptime_formatted" in sys_info:
                print(f"  Uptime:          {sys_info['uptime_formatted']}")
            if "load_average" in sys_info:
                load = sys_info["load_average"]
                print(f"  Load Average:    {load['1min']:.2f} (1min) {load['5min']:.2f} (5min) {load['15min']:.2f} (15min)")
            print()

        # CPU Temperature
        if "cpu_temperature" in self.metrics:
            cpu = self.metrics["cpu_temperature"]
            icon = self._get_status_icon(cpu["status"])
            color = self._get_status_color(cpu["status"])
            print("CPU TEMPERATURE")
            print("-" * 70)
            print(
                f"  {color}{icon} {cpu['value']:.1f}{cpu['unit']}{self._get_status_color('reset')} (Limits: Warning 75°C, Critical 85°C)"
            )
            print()

        # Thermal Zones
        if "thermal_zones" in self.metrics and self.metrics["thermal_zones"]:
            print("THERMAL ZONES")
            print("-" * 70)
            for zone_name, zone in self.metrics["thermal_zones"].items():
                icon = self._get_status_icon(zone["status"])
                color = self._get_status_color(zone["status"])
                print(
                    f"  {color}{icon} {zone_name} ({zone['type']}): {zone['temperature']:.1f}{zone['unit']}{self._get_status_color('reset')}"
                )
            print()

        # Supply Voltage
        if "supply_voltage" in self.metrics:
            volt = self.metrics["supply_voltage"]
            icon = self._get_status_icon(volt["status"])
            color = self._get_status_color(volt["status"])
            print("POWER SUPPLY")
            print("-" * 70)
            print(
                f"  {color}{icon} {volt['rail']} Voltage: {volt['value']:.2f}{volt['unit']}{self._get_status_color('reset')}"
            )
            print(f"    (Nominal: 1.1V, Limits: Warning 1.05V, Critical 1.0V)")
            print()

        # Throttling Status
        if "throttling" in self.metrics:
            throttle = self.metrics["throttling"]
            icon = self._get_status_icon(throttle["status"])
            color = self._get_status_color(throttle["status"])
            print("THROTTLING STATUS")
            print("-" * 70)
            if throttle["active"]:
                print(f"  {color}{icon} Throttling ACTIVE{self._get_status_color('reset')}")
                details = throttle["details"]
                if details["undervolted"]:
                    print(f"    - Undervolted detected")
                if details["capped"]:
                    print(f"    - Frequency capped")
                if details["throttled"]:
                    print(f"    - Throttled due to temperature")
                if details["has_soft_templimit"]:
                    print(f"    - Soft temperature limit active")
            else:
                print(f"  {color}{icon} No throttling{self._get_status_color('reset')}")
            print()

        # RAM Usage
        if "ram" in self.metrics:
            ram = self.metrics["ram"]
            icon = self._get_status_icon(ram["status"])
            color = self._get_status_color(ram["status"])
            print("MEMORY USAGE")
            print("-" * 70)
            print(
                f"  {color}{icon} {ram['percent']:.1f}% used{self._get_status_color('reset')}"
            )
            print(
                f"    Used:      {self.format_bytes(ram['used'])} / {self.format_bytes(ram['total'])}"
            )
            print(f"    Available: {self.format_bytes(ram['available'])}")
            print(
                f"    (Limits: Warning 80%, Critical 95%)"
            )
            print()

        # Storage Usage
        if "storage" in self.metrics:
            storage = self.metrics["storage"]
            icon = self._get_status_icon(storage["status"])
            color = self._get_status_color(storage["status"])
            print("STORAGE USAGE")
            print("-" * 70)
            print(
                f"  {color}{icon} {storage['percent']:.1f}% used{self._get_status_color('reset')}"
            )
            print(
                f"    Used: {self.format_bytes(storage['used'])} / {self.format_bytes(storage['total'])}"
            )
            print(f"    Free: {self.format_bytes(storage['free'])}")
            print(
                f"    (Limits: Warning 80%, Critical 95%)"
            )
            print()

        # Recommendations
        overall_status = self.get_overall_status()
        if overall_status != "healthy":
            print("RECOMMENDATIONS")
            print("-" * 70)
            if "cpu_temperature" in self.metrics and self.metrics["cpu_temperature"]["status"] != "healthy":
                cpu_status = self.metrics["cpu_temperature"]["status"]
                if cpu_status == "critical":
                    print("  ⚠ CPU temperature is CRITICAL - check cooling and reduce workload")
                else:
                    print("  ⚠ CPU temperature is elevated - monitor cooling system")

            if "supply_voltage" in self.metrics and self.metrics["supply_voltage"]["status"] != "healthy":
                volt_status = self.metrics["supply_voltage"]["status"]
                if volt_status == "critical":
                    print("  ⚠ Supply voltage is LOW - check power supply integrity")
                else:
                    print("  ⚠ Supply voltage is slightly low - monitor power supply")

            if "throttling" in self.metrics and self.metrics["throttling"]["active"]:
                print("  ⚠ System is throttling - check thermal conditions and power supply")

            if "ram" in self.metrics and self.metrics["ram"]["status"] != "healthy":
                print("  ⚠ High memory usage - consider stopping non-essential processes")

            if "storage" in self.metrics and self.metrics["storage"]["status"] != "healthy":
                print("  ⚠ Storage usage high - consider freeing disk space")

            print()

        print("=" * 70)


def main():
    """Main entry point."""
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="System Health Diagnostic Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--repeat",
        "-r",
        type=int,
        default=1,
        help="Run diagnostic N times with 1 second delay between runs (default: 1)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output metrics as JSON",
    )

    args = parser.parse_args()

    monitor = SystemHealthMonitor()

    try:
        for i in range(args.repeat):
            monitor.collect_metrics()

            if args.json:
                print(json.dumps(monitor.metrics, indent=2, default=str))
            else:
                monitor.print_report(verbose=args.verbose)

            if i < args.repeat - 1:
                time.sleep(1)

    except KeyboardInterrupt:
        print("\nDiagnostic interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error during diagnostic: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
