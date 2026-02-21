#!/usr/bin/env python3
"""
RFSoC 15dB Attenuation Diagnostic Summary and Troubleshooting Guide

What we know so far:
- Your RFSoC has an 'rfdc' register: 0x02050000
- The 15dB attenuation is isolated to the RFSoC (not software/calibration)
- There are no explicit gain/attenuation registers in the design
- The attenuation is likely in the RFDC (RF Data Converter) tile configuration

Hypothesis: The 15dB attenuation could be from:
1. QMC (Quadrature Mixer Correction) gain settings - controls I/Q gain
2. Fine mixer scale factor (0.7x = -3dB, multiple cascaded stages could add up)
3. ADC tile digital gain settings
4. FPGA bitstream design difference (v26.fpg might have different scaling than v25.fpg)

Usage:
    pipenv run python tools/test_attenuation_hypothesis.py --test monitor
"""

import sys
import time
try:
    import casperfpga
    import numpy as np
except ImportError as e:
    print(f"ERROR: Missing module: {e}")
    sys.exit(1)

def connect_fpga(fpga_ip):
    """Connect to FPGA."""
    try:
        fpga = casperfpga.CasperFpga(fpga_ip)
        if fpga.is_connected():
            return fpga
        else:
            return None
    except:
        return None

def test_1_rfdc_register_change(fpga):
    """
    Test Hypothesis 1: Does RFDC register control gain?
    
    Monitor the rfdc register while acquiring data to see if it changes.
    If it does, those changes might indicate gain switching.
    """
    print("\n" + "="*70)
    print("TEST 1: Monitor RFDC Register for Changes During Acquisition")
    print("="*70 + "\n")
    
    print("This test monitors the 'rfdc' register for 30 seconds while")
    print("the spectrometer is acquiring data (if running).\n")
    
    try:
        initial_val = fpga.read_uint('rfdc')
        print(f"Initial RFDC value: 0x{initial_val:08x}\n")
        
        values_seen = {initial_val: 1}
        print("Monitoring for changes (press Ctrl+C to stop):\n")
        
        start = time.time()
        while time.time() - start < 30:
            try:
                val = fpga.read_uint('rfdc')
                if val not in values_seen:
                    values_seen[val] = 0
                    print(f"  ✓ NEW VALUE: 0x{val:08x} (was 0x{list(values_seen.keys())[-2]:08x})")
                values_seen[val] += 1
                time.sleep(0.5)
            except:
                pass
        
        print(f"\nValues seen ({len(values_seen)} unique):")
        for val, count in sorted(values_seen.items()):
            print(f"  0x{val:08x}: seen {count} times")
        
        if len(values_seen) == 1:
            print("\n⚠ RFDC register did NOT change")
            print("  This suggests the gain/attenuation is set at initialization")
            print("  and not dynamically adjusted during acquisition.")
        else:
            print("\n✓ RFDC register CHANGED")
            print("  This suggests gain is being dynamically controlled!")
        
    except Exception as e:
        print(f"ERROR: {e}")

def test_2_bitstream_comparison(fpga):
    """
    Test Hypothesis 2: Is it a bitstream design issue?
    
    Compare v26.fpg with v25.fpg to see what changed.
    """
    print("\n" + "="*70)
    print("TEST 2: Bitstream Comparison (v25 vs v26)")
    print("="*70 + "\n")
    
    print("To compare bitstreams, we need to analyze the CASPER design files.")
    print("Since the .fpg files are binary, we would need the .vhd/.v source files.\n")
    
    print("Without the design source, here's what to look for:")
    print("  1. Check if QMC gain correction was changed")
    print("  2. Check if ADC tile prescaling was modified")
    print("  3. Check if fine mixer scale factor changed")
    print("  4. Compare register initialization values\n")
    
    print("Action items:")
    print("  - Ask the lab workstation team for v26 CASPER design source")
    print("  - Or: Boot v25.fpg and compare RFDC register value with v26")
    print("  - Or: Check git history if designs are version controlled")

def test_3_dac_loopback_test(fpga):
    """
    Test Hypothesis 3: Generate known signal and measure to isolate attenuation source.
    
    This would require DAC output connected to ADC input for loopback testing.
    """
    print("\n" + "="*70)
    print("TEST 3: Loopback Test (Requires DAC->ADC Connection)")
    print("="*70 + "\n")
    
    print("Recommended loopback configuration:")
    print("  1. Connect DAC0_OUT to ADC0_IN with known attenuation cable")
    print("     (e.g., 10dB or 20dB attenuator)")
    print("  2. Generate known RF tone from DAC")
    print("  3. Measure received power level in ADC spectrum")
    print("  4. Compare measured attenuation with expected\n")
    
    print("This would tell you:")
    print("  - If attenuation is in digital path (register/FPGA)")
    print("  - If attenuation is in analog path (RF circuits)")
    print("  - Exact frequency-dependent behavior")

def test_4_register_dump_comparison(fpga):
    """
    Dump all registers for comparison with a known-good state.
    """
    print("\n" + "="*70)
    print("TEST 4: Full Register Dump for Comparison")
    print("="*70 + "\n")
    
    try:
        print("Current register values:\n")
        devices = fpga.listdev()
        
        for dev in sorted(devices):
            try:
                val = fpga.read_uint(dev)
                print(f"  {dev:40s} = 0x{val:08x} ({val:10d})")
            except:
                pass
        
        print("\n\nTo use this for comparison:")
        print("  1. Boot v25.fpg on same RFSoC")
        print("  2. Run: pipenv run python tools/register_dump.py > v25_registers.txt")
        print("  3. Run: pipenv run python tools/register_dump.py > v26_registers.txt")
        print("  4. Compare: diff v25_registers.txt v26_registers.txt")
        print("  5. Look for registers that differ between v25 and v26")
        
    except Exception as e:
        print(f"ERROR: {e}")

def test_5_quick_fixes_to_try(fpga):
    """
    Suggest quick fixes that might work if specific register controls gain.
    """
    print("\n" + "="*70)
    print("TEST 5: Potential Quick Fixes")
    print("="*70 + "\n")
    
    print("If the attenuation is in the 'rfdc' register, try these modifications:\n")
    
    try:
        current = fpga.read_uint('rfdc')
        print(f"Current RFDC value: 0x{current:08x}\n")
        
        print("Hypothesis: Bytes 1-2 might control ADC gain\n")
        
        # Try different values
        test_values = [
            (current | 0x0000FFFF, "Enable all gain bits"),
            (current & 0xFFFF00FF, "Disable all gain bits"),
            (current | 0x00FF0000, "Try 0x00FF0000"),
            (0x02050101, "Try minimal gain change"),
            (0x020500FF, "Try 0x020500FF"),
        ]
        
        print("⚠ WARNING: These are HYPOTHETICAL fixes. Test carefully!\n")
        print("To test a change, run:")
        print("  1. Start spectrum acquisition: pipenv run TakeSpecs &")
        print("  2. In another terminal:")
        print("     cd /home/peterson/highz-digitalspec")
        print("     pipenv run python3 -c \"")
        print("       import casperfpga")
        print("       fpga = casperfpga.CasperFpga('169.254.2.181')")
        print("       fpga.write_uint('rfdc', 0x020500FF)  # Try new value")
        print("       print('RFDC set to:', hex(fpga.read_uint('rfdc')))")
        print("     \"")
        print("  3. Check if spectrum amplitude changed\n")
        
        print("Test values to try:")
        for val, desc in test_values:
            change = (val ^ current)
            byte_changes = [
                f"Byte3: 0x{(change>>24)&0xFF:02x}",
                f"Byte2: 0x{(change>>16)&0xFF:02x}",
                f"Byte1: 0x{(change>>8)&0xFF:02x}",
                f"Byte0: 0x{change&0xFF:02x}",
            ]
            changed = [b for b in byte_changes if '0x00' not in b]
            print(f"\n  {desc}")
            print(f"    Value: 0x{val:08x}")
            print(f"    Changes: {', '.join(changed) if changed else 'None'}")
        
    except Exception as e:
        print(f"ERROR: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Test hypotheses about RFSoC 15dB attenuation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pipenv run python tools/test_attenuation_hypothesis.py --test monitor
  pipenv run python tools/test_attenuation_hypothesis.py --test all
        """
    )
    
    parser.add_argument('--fpga', type=str, default='169.254.2.181',
                        help='FPGA IP address')
    parser.add_argument('--test', type=str, default='all',
                        choices=['monitor', 'bitstream', 'loopback', 'dump', 'fixes', 'all'],
                        help='Which test to run')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("RFSoC 15dB Attenuation Troubleshooting")
    print("="*70)
    
    fpga = connect_fpga(args.fpga)
    if not fpga:
        print(f"ERROR: Could not connect to {args.fpga}")
        sys.exit(1)
    
    if args.test in ['monitor', 'all']:
        test_1_rfdc_register_change(fpga)
    
    if args.test in ['bitstream', 'all']:
        test_2_bitstream_comparison(fpga)
    
    if args.test in ['loopback', 'all']:
        test_3_dac_loopback_test(fpga)
    
    if args.test in ['dump', 'all']:
        test_4_register_dump_comparison(fpga)
    
    if args.test in ['fixes', 'all']:
        test_5_quick_fixes_to_try(fpga)
    
    print("\n" + "="*70)
    print("Troubleshooting Complete")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
