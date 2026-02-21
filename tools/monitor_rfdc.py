#!/usr/bin/env python3
"""
Monitor RFSoC behavior during spectrometer acquisition

This monitors all registers while data is being acquired to see
if any values change that might indicate attenuation control.

Usage:
    # In one terminal, start taking spectra:
    pipenv run TakeSpecs &
    
    # In another terminal, run this monitor:
    pipenv run python tools/monitor_rfdc.py --fpga 169.254.2.181 --interval 0.5
"""

import argparse
import sys
import time
from datetime import datetime

try:
    import casperfpga
except ImportError:
    print("ERROR: casperfpga not installed")
    sys.exit(1)

def monitor_registers(fpga_ip, interval=0.5, duration=60):
    """Monitor register values over time."""
    
    print(f"\n{'='*70}")
    print(f"RFSoC REGISTER MONITOR")
    print(f"{'='*70}\n")
    print(f"Connecting to {fpga_ip}...")
    
    try:
        fpga = casperfpga.CasperFpga(fpga_ip)
        if not fpga.is_connected():
            print("ERROR: Could not connect")
            return
    except Exception as e:
        print(f"ERROR: {e}")
        return
    
    print("✓ Connected")
    print(f"\nMonitoring for {duration} seconds at {interval}s intervals...")
    print(f"Press Ctrl+C to stop\n")
    
    # Key registers to watch
    watch_regs = ['rfdc', 'acc_cnt', 'sync_cnt', 'q1', 'q2', 'q3', 'q4']
    
    print(f"{'Time':12s} | ", end="")
    for reg in watch_regs:
        print(f"{reg:12s} | ", end="")
    print()
    print("-" * (12 + len(watch_regs) * 14 + 4))
    
    start_time = time.time()
    prev_values = {}
    
    try:
        while time.time() - start_time < duration:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"{timestamp} | ", end="")
            
            for reg in watch_regs:
                try:
                    value = fpga.read_uint(reg)
                    
                    # Highlight if value changed
                    if reg in prev_values and prev_values[reg] != value:
                        print(f"*0x{value:08x}* | ", end="")
                    else:
                        print(f" 0x{value:08x}  | ", end="")
                    
                    prev_values[reg] = value
                except:
                    print(f"{'ERR':12s} | ", end="")
            
            print()
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped")
    
    print(f"\n{'='*70}")
    print("Values with * changed since last read")
    print(f"{'='*70}\n")

def main():
    parser = argparse.ArgumentParser(
        description='Monitor RFSoC registers during acquisition',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor for 60 seconds (default)
  pipenv run python tools/monitor_rfdc.py --fpga 169.254.2.181
  
  # Monitor for 5 minutes at 1-second intervals
  pipenv run python tools/monitor_rfdc.py --fpga 169.254.2.181 --duration 300 --interval 1.0
        """
    )
    
    parser.add_argument('--fpga', type=str, default='169.254.2.181',
                        help='FPGA IP address')
    parser.add_argument('--interval', type=float, default=0.5,
                        help='Monitoring interval in seconds')
    parser.add_argument('--duration', type=int, default=60,
                        help='Duration to monitor in seconds')
    
    args = parser.parse_args()
    
    monitor_registers(args.fpga, args.interval, args.duration)

if __name__ == "__main__":
    main()
