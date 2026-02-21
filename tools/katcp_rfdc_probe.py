#!/usr/bin/env python3
"""
Direct KATCP Command Diagnostic for RFSoC

Since the ADCs aren't registered in casperfpga, we'll probe available KATCP commands
that might control attenuation/gain on the RFDC.

Usage:
    pipenv run python tools/katcp_rfdc_probe.py --fpga 169.254.2.181
"""

import sys
try:
    import casperfpga
except ImportError:
    print("ERROR: casperfpga not installed")
    sys.exit(1)

def connect_fpga(fpga_ip):
    """Connect to FPGA."""
    print(f"\nConnecting to {fpga_ip}...")
    try:
        fpga = casperfpga.CasperFpga(fpga_ip)
        if fpga.is_connected():
            print("✓ Connected\n")
            return fpga
        else:
            print("ERROR: Could not connect")
            return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def probe_katcp_commands(fpga):
    """
    Try common KATCP commands that might exist on the RFSoC.
    """
    print(f"{'='*70}")
    print("Probing KATCP Commands for Gain/Attenuation Control")
    print(f"{'='*70}\n")
    
    # Common KATCP commands on RFDC devices
    commands_to_try = [
        # Status and info
        ('?help', []),
        ('?list-bof', []),
        
        # RFDC-specific
        ('?rfdc-status', []),
        ('?rfdc-adc-scale', []),
        ('?rfdc-adc-gain', []),
        ('?rfdc-dac-scale', []),
        ('?rfdc-dac-gain', []),
        ('?rfdc-qmc-gain', []),
        ('?rfdc-qmc', []),
        
        # Gain/Scale variants
        ('?adc-gain', []),
        ('?dac-gain', []),
        ('?adc-scale', []),
        ('?dac-scale', []),
        ('?get-gain', []),
        ('?set-gain', []),
        
        # Tile control
        ('?rfdc-tile-status', []),
        ('?rfdc-get-fab-clk-freq', [0, 'adc']),
    ]
    
    t = fpga.transport
    
    for cmd_name, cmd_args in commands_to_try:
        try:
            # Strip the ? for the actual request
            request_name = cmd_name[1:] if cmd_name.startswith('?') else cmd_name
            
            # Make the request with minimal timeout
            if cmd_args:
                reply, informs = t.katcprequest(
                    name=request_name,
                    request_timeout=2,
                    request_args=cmd_args
                )
            else:
                reply, informs = t.katcprequest(
                    name=request_name,
                    request_timeout=2
                )
            
            print(f"✓ {cmd_name}")
            print(f"  Reply: {reply}")
            if informs:
                for i, inform in enumerate(informs[:3]):  # Show first 3 informs
                    args_str = str(inform.arguments)[:80]
                    print(f"  Inform {i}: {args_str}")
                if len(informs) > 3:
                    print(f"  ... and {len(informs) - 3} more informs")
            print()
            
        except Exception as e:
            # This is expected for non-existent commands
            error_str = str(e)[:60]
            # Only print if it's not a "fail" error (which is expected)
            if 'timeout' in error_str.lower():
                print(f"✗ {cmd_name}: TIMEOUT")
            elif 'fail' not in error_str.lower() and 'unknown' not in error_str.lower():
                print(f"✗ {cmd_name}: {error_str}")

def probe_qmc_by_tile(fpga):
    """
    Try to query QMC settings for each ADC tile.
    """
    print(f"\n{'='*70}")
    print("Probing QMC Settings by Tile")
    print(f"{'='*70}\n")
    
    t = fpga.transport
    
    # Try different QMC-related commands
    qmc_commands = [
        'rfdc-qmc-gain',
        'rfdc-get-qmc',
        'rfdc-qmc-coeff',
        'rfdc-get-mixer-scale',
        'get-mixer-scale',
    ]
    
    for tile in range(4):
        for block in range(2):
            for cmd in qmc_commands:
                try:
                    reply, informs = t.katcprequest(
                        name=cmd,
                        request_timeout=1,
                        request_args=[tile, block, 'adc']
                    )
                    print(f"✓ {cmd} tile={tile} block={block} adc")
                    for inform in informs:
                        print(f"  {inform.arguments}")
                except:
                    pass

def probe_register_values(fpga):
    """
    Directly read all available registers looking for ones that might be gain.
    """
    print(f"\n{'='*70}")
    print("Direct Register Probing")
    print(f"{'='*70}\n")
    
    devices = fpga.listdev()
    
    print(f"Available registers/BRAMs: {len(devices)}\n")
    
    # Look for anything gain-related
    gain_keywords = ['gain', 'scale', 'atten', 'coeff', 'mixer', 'qmc']
    
    potential_gain_regs = []
    for dev in devices:
        for keyword in gain_keywords:
            if keyword in dev.lower():
                potential_gain_regs.append(dev)
                break
    
    if potential_gain_regs:
        print(f"Registers with '{' | '.join(gain_keywords)}':\n")
        for reg in potential_gain_regs:
            try:
                val = fpga.read_uint(reg)
                print(f"  {reg:40s} = 0x{val:08x}")
            except Exception as e:
                print(f"  {reg:40s} = ERROR: {e}")
    else:
        print("No registers found with gain/scale/attenuation keywords")
        print("\nAll registers:")
        for dev in devices:
            try:
                val = fpga.read_uint(dev)
                print(f"  {dev:40s} = 0x{val:08x}")
            except:
                print(f"  {dev:40s} = [unreadable]")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Probe KATCP commands and registers for gain control'
    )
    parser.add_argument('--fpga', type=str, default='169.254.2.181',
                        help='FPGA IP address')
    
    args = parser.parse_args()
    
    fpga = connect_fpga(args.fpga)
    if not fpga:
        sys.exit(1)
    
    probe_katcp_commands(fpga)
    probe_register_values(fpga)
    probe_qmc_by_tile(fpga)
    
    print(f"\n{'='*70}")
    print("Probing Complete")
    print(f"{'='*70}\n")
    
    print("NEXT STEPS:")
    print("1. Look for any commands above marked with ✓ that seem related to gain/attenuation")
    print("2. Check if the RFDC register changes when gain settings are modified")
    print("3. Compare register values between your old setup (if available) and this one")
    print("4. Search the CASPER design files for QMC or gain control code")
    print()

if __name__ == "__main__":
    main()
