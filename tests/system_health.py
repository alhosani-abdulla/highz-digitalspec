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

import sys, time, json

try:
    import psutil
except ImportError:
    print("Error: psutil module not found. Install with: pipenv install psutil")
    sys.exit(1)

from src.sys_monitor import SystemHealthMonitor

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
