#!/usr/bin/env python3
"""
RFSoC 4x2 Diagnostic Tool - Check for attenuation and gain settings

This script connects to your RFSoC and inspects all available registers,
looking for attenuation, gain, or other RF control settings.

Usage:
    pipenv run python tools/rfsoc_diagnostic.py --fpga 169.254.2.181
"""

import argparse
import sys
import struct
from datetime import datetime

try:
    import casperfpga
except ImportError:
    print("ERROR: casperfpga not installed. Install with: pipenv install casperfpga")
    sys.exit(1)

# Common register names that might control attenuation/gain
POTENTIAL_ATTEN_REGS = [
    'atten', 'attenuator', 'atten_control', 'atten_val',
    'gain', 'rx_gain', 'tx_gain', 'rfdc_gain',
    'dac_scale', 'adc_scale', 'scale',
    'analog_gain', 'digital_gain',
    'rf_control', 'rf_switch', 'switch_control',
    'rf_mode', 'mode_control',
]

def connect_fpga(fpga_ip):
    """Connect to FPGA and handle errors gracefully."""
    print(f"\n{'='*70}")
    print(f"Connecting to RFSoC at {fpga_ip}...")
    print(f"{'='*70}\n")
    
    try:
        fpga = casperfpga.CasperFpga(fpga_ip)
        
        if not fpga.is_connected():
            print(f"ERROR: Could not connect to {fpga_ip}")
            print("Check that:")
            print("  1. RFSoC is powered on")
            print("  2. Ethernet cable is connected")
            print("  3. FPGA has the correct bitstream loaded")
            return None
        
        print(f"✓ Connected to RFSoC")
        try:
            version = fpga.read_uint('version')
            print(f"  Bitstream version: {version}")
        except:
            print(f"  (No version register available)")
        return fpga
        
    except Exception as e:
        print(f"ERROR: Connection failed: {e}")
        return None

def list_all_registers(fpga):
    """List all available registers on the FPGA."""
    print(f"\n{'='*70}")
    print("ALL AVAILABLE REGISTERS/BRAMS")
    print(f"{'='*70}\n")
    
    try:
        devices = fpga.listdev()
        
        if not devices:
            print("No devices found!")
            return devices
        
        print(f"Found {len(devices)} register(s):\n")
        
        for i, dev in enumerate(devices, 1):
            print(f"{i:3d}. {dev}")
        
        return devices
        
    except Exception as e:
        print(f"ERROR listing devices: {e}")
        return []

def check_suspected_attenuators(fpga, devices):
    """Check for potential attenuation/gain registers."""
    print(f"\n{'='*70}")
    print("SUSPECTED ATTENUATION/GAIN REGISTERS")
    print(f"{'='*70}\n")
    
    found = []
    
    for reg_name in POTENTIAL_ATTEN_REGS:
        # Check exact match
        if reg_name in devices:
            found.append(reg_name)
        # Check case-insensitive partial match
        else:
            for dev in devices:
                if reg_name.lower() in dev.lower():
                    found.append(dev)
                    break
    
    if not found:
        print("No obvious attenuation/gain registers found.\n")
        return []
    
    print(f"Found {len(found)} potential register(s):\n")
    
    for reg in found:
        try:
            value = fpga.read_uint(reg)
            print(f"  {reg:30s} = 0x{value:08x} ({value:10d})")
        except Exception as e:
            print(f"  {reg:30s} = [ERROR: {e}]")
    
    return found

def read_rfdc_status(fpga):
    """Try to read RFDC (RF Data Converter) status."""
    print(f"\n{'='*70}")
    print("RFDC (RF DATA CONVERTER) STATUS")
    print(f"{'='*70}\n")
    
    try:
        # Try common RFDC register names
        rfdc_regs = ['rfdc_status', 'rfdc_control', 'rfdc_adc_status', 'rfdc_dac_status']
        
        for reg in rfdc_regs:
            try:
                value = fpga.read_uint(reg)
                print(f"  {reg:30s} = 0x{value:08x}")
            except:
                pass
        
        # Try to get ADC status via get_adc_status if available
        try:
            if hasattr(fpga, 'get_adc_status'):
                for i in range(4):  # RFSoC 4x2 has 4 ADCs
                    try:
                        status = fpga.get_adc_status(i)
                        print(f"\n  ADC{i} Status: {status}")
                    except:
                        pass
        except:
            pass
            
    except Exception as e:
        print(f"  Could not read RFDC status: {e}")

def read_all_uint_registers(fpga, devices):
    """Try to read all registers as unsigned integers."""
    print(f"\n{'='*70}")
    print("ALL REGISTERS (as UINT32)")
    print(f"{'='*70}\n")
    
    print(f"{'Register Name':40s} | {'Hex Value':10s} | {'Decimal':12s}\n")
    print("-" * 70)
    
    for dev in devices:
        try:
            # Try reading as uint32
            value = fpga.read_uint(dev)
            print(f"{dev:40s} | 0x{value:08x}   | {value:12d}")
        except Exception as e:
            # Try other formats
            try:
                value = fpga.read_int(dev)
                print(f"{dev:40s} | 0x{value:08x}   | {value:12d} (int)")
            except:
                print(f"{dev:40s} | [ERROR reading]")

def check_adc_dac_scaling(fpga, devices):
    """Check for ADC/DAC scaling registers."""
    print(f"\n{'='*70}")
    print("ADC/DAC SCALING ANALYSIS")
    print(f"{'='*70}\n")
    
    scaling_regs = [reg for reg in devices if 'scale' in reg.lower() or 'gain' in reg.lower()]
    
    if scaling_regs:
        print("Scaling/Gain registers found:")
        for reg in scaling_regs:
            try:
                value = fpga.read_uint(reg)
                # Try to interpret as fixed-point (18-bit by default)
                if value & 0x20000:  # Check sign bit for 18-bit
                    value_signed = value - (1 << 18)
                else:
                    value_signed = value
                
                db_value = 20 * np.log10(abs(value_signed) / 65536.0) if value_signed != 0 else -np.inf
                print(f"  {reg:35s} = 0x{value:08x} ({value_signed:8d}) ≈ {db_value:6.2f} dB")
            except Exception as e:
                print(f"  {reg:35s} = [ERROR]")
    else:
        print("No scaling/gain registers found.\n")

def main():
    parser = argparse.ArgumentParser(
        description='RFSoC 4x2 Diagnostic - Find attenuation/gain issues',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pipenv run python tools/rfsoc_diagnostic.py --fpga 169.254.2.181
  pipenv run python tools/rfsoc_diagnostic.py --fpga 192.168.1.100
        """
    )
    
    parser.add_argument('--fpga', type=str, default='169.254.2.181',
                        help='FPGA IP address (default: 169.254.2.181)')
    
    args = parser.parse_args()
    
    # Connect to FPGA
    fpga = connect_fpga(args.fpga)
    if not fpga:
        sys.exit(1)
    
    # List all registers
    devices = list_all_registers(fpga)
    
    if not devices:
        print("No registers found on FPGA!")
        sys.exit(1)
    
    # Check for suspected attenuation registers
    suspected = check_suspected_attenuators(fpga, devices)
    
    # Read RFDC status
    read_rfdc_status(fpga)
    
    # Check ADC/DAC scaling
    try:
        import numpy as np
        check_adc_dac_scaling(fpga, devices)
    except ImportError:
        pass
    
    # Read all registers
    print("\n")
    read_all_uint_registers(fpga, devices)
    
    print(f"\n{'='*70}")
    print("DIAGNOSTIC COMPLETE")
    print(f"{'='*70}\n")
    
    print("NEXT STEPS:")
    print("1. Look for registers that might have unexpected values (0 or very low)")
    print("2. Compare 'Hex Value' with expected defaults from your CASPER design")
    print("3. Check CASPER design documentation for register meanings")
    print("4. Look for 15dB worth of attenuation: 10^(-15/20) ≈ 0.178 in linear scale")
    print()

if __name__ == "__main__":
    main()
