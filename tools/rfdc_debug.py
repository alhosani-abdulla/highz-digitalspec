#!/usr/bin/env python3
"""
RFSoC RFDC Register Decoder and Adjuster

Decodes the RFDC (RF Data Converter) register which controls:
- ADC/DAC enable/disable
- Gain/attenuation settings
- Power states

Usage:
    pipenv run python tools/rfdc_debug.py --fpga 169.254.2.181 --read
    pipenv run python tools/rfdc_debug.py --fpga 169.254.2.181 --set 0x02050001
"""

import argparse
import sys
try:
    import casperfpga
except ImportError:
    print("ERROR: casperfpga not installed")
    sys.exit(1)

def decode_rfdc_register(value):
    """
    Decode RFDC register value.
    
    RFDC register format (typically):
    Bits 31-24: ADC Tile Power State
    Bits 23-16: DAC Tile Power State
    Bits 15-8:  ADC Gain/Attenuation Control
    Bits 7-0:   DAC Gain/Attenuation Control
    
    Or it might be used for:
    - Tile enable/disable
    - Power control
    - Gain control
    
    This is design-specific!
    """
    
    print(f"\nRFDC Register Value: 0x{value:08x} ({value})")
    print(f"Binary: {bin(value)[2:].zfill(32)}")
    print()
    
    # Break into bytes
    byte3 = (value >> 24) & 0xFF  # MSB
    byte2 = (value >> 16) & 0xFF
    byte1 = (value >> 8) & 0xFF
    byte0 = value & 0xFF          # LSB
    
    print(f"Byte breakdown:")
    print(f"  Byte 3 (bits 31-24): 0x{byte3:02x} ({byte3:8b}) - Likely ADC/DAC tile power or control")
    print(f"  Byte 2 (bits 23-16): 0x{byte2:02x} ({byte2:8b}) - Likely ADC/DAC tile power or control")
    print(f"  Byte 1 (bits 15-8):  0x{byte1:02x} ({byte1:8b}) - Likely ADC/DAC gain control")
    print(f"  Byte 0 (bits 7-0):   0x{byte0:02x} ({byte0:8b}) - Likely DAC gain control")
    print()
    
    # Check bit patterns
    print("Bit Analysis:")
    if byte3 & 0x02:
        print("  ✓ Bit 25 (ADC tile power?) set")
    if byte2 & 0x05:
        print(f"  ✓ Bits 20,22 (DAC control?) = {(byte2 & 0x05):02b}")
    
    # Check if this looks like attenuation
    print("\n⚠ IMPORTANT: This register format is DESIGN-SPECIFIC!")
    print("You need to check your CASPER design documentation for:")
    print("  - What each field controls")
    print("  - What values correspond to gain vs attenuation")
    print("  - How to modify for 15dB of attenuation adjustment")

def connect_fpga(fpga_ip):
    """Connect to FPGA."""
    try:
        fpga = casperfpga.CasperFpga(fpga_ip)
        if fpga.is_connected():
            return fpga
        else:
            print(f"ERROR: Could not connect to {fpga_ip}")
            return None
    except Exception as e:
        print(f"ERROR: Connection failed: {e}")
        return None

def read_rfdc(fpga):
    """Read current RFDC register."""
    try:
        value = fpga.read_uint('rfdc')
        print(f"\n{'='*70}")
        print(f"RFDC REGISTER READ")
        print(f"{'='*70}")
        decode_rfdc_register(value)
        return value
    except Exception as e:
        print(f"ERROR reading rfdc: {e}")
        return None

def set_rfdc(fpga, value):
    """Set RFDC register to new value."""
    try:
        print(f"\n{'='*70}")
        print(f"RFDC REGISTER SET")
        print(f"{'='*70}")
        
        print(f"\nCurrent value:")
        current = fpga.read_uint('rfdc')
        decode_rfdc_register(current)
        
        print(f"\nSetting to: 0x{value:08x}")
        fpga.write_uint('rfdc', value)
        
        # Read back to verify
        new_value = fpga.read_uint('rfdc')
        decode_rfdc_register(new_value)
        
        if new_value == value:
            print(f"\n✓ Successfully set RFDC register")
        else:
            print(f"\n✗ WARNING: Register read back different value!")
            print(f"  Expected: 0x{value:08x}")
            print(f"  Got:      0x{new_value:08x}")
        
        return new_value
    except Exception as e:
        print(f"ERROR setting rfdc: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(
        description='Decode and modify RFDC register on RFSoC',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Read current RFDC value
  pipenv run python tools/rfdc_debug.py --fpga 169.254.2.181 --read
  
  # Modify RFDC register
  pipenv run python tools/rfdc_debug.py --fpga 169.254.2.181 --set 0x02050001
  
  # Decode a specific value without connecting
  pipenv run python tools/rfdc_debug.py --decode 0x02050000
        """
    )
    
    parser.add_argument('--fpga', type=str, default='169.254.2.181',
                        help='FPGA IP address')
    parser.add_argument('--read', action='store_true',
                        help='Read and display current RFDC value')
    parser.add_argument('--set', type=lambda x: int(x, 16),
                        help='Set RFDC to this hex value (e.g., 0x02050000)')
    parser.add_argument('--decode', type=lambda x: int(x, 16),
                        help='Decode a hex value without connecting to FPGA')
    
    args = parser.parse_args()
    
    # If decode-only mode
    if args.decode is not None:
        print(f"\n{'='*70}")
        print(f"RFDC REGISTER DECODE")
        print(f"{'='*70}")
        decode_rfdc_register(args.decode)
        return
    
    # Connect to FPGA
    fpga = connect_fpga(args.fpga)
    if not fpga:
        sys.exit(1)
    
    if args.read:
        read_rfdc(fpga)
    elif args.set is not None:
        set_rfdc(fpga, args.set)
    else:
        # Default to read
        read_rfdc(fpga)

if __name__ == "__main__":
    main()
