#!/usr/bin/env python3
"""
Quick RFDC Register Modifier - Test Attenuation Fixes

This tool lets you quickly test different RFDC values to see if changing them
affects the measured spectrum power level.

USAGE:
    # Check current value
    pipenv run python tools/rfdc_quick_test.py --fpga 169.254.2.181 --action get
    
    # Try different gain values
    pipenv run python tools/rfdc_quick_test.py --fpga 169.254.2.181 --action set --value 0x020500FF
    
    # Interactive mode - test multiple values
    pipenv run python tools/rfdc_quick_test.py --fpga 169.254.2.181 --action interactive

WARNINGS:
    - This modifies hardware registers in real-time
    - Can cause unexpected spectrum changes
    - Make sure to note original value before testing
    - Test with low-power inputs first
    - Stop data acquisition before making major changes
"""

import sys
import time
try:
    import casperfpga
except ImportError:
    print("ERROR: casperfpga not installed")
    sys.exit(1)

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
        print(f"ERROR: {e}")
        return None

def action_get(fpga):
    """Get current RFDC value."""
    try:
        val = fpga.read_uint('rfdc')
        print(f"\nCurrent RFDC value: 0x{val:08x}\n")
        
        # Decode it
        byte3 = (val >> 24) & 0xFF
        byte2 = (val >> 16) & 0xFF
        byte1 = (val >> 8) & 0xFF
        byte0 = val & 0xFF
        
        print(f"  Byte breakdown:")
        print(f"    Byte 3 (bits 31-24): 0x{byte3:02x}")
        print(f"    Byte 2 (bits 23-16): 0x{byte2:02x}")
        print(f"    Byte 1 (bits 15-8):  0x{byte1:02x}")
        print(f"    Byte 0 (bits 7-0):   0x{byte0:02x}\n")
        
        return val
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def action_set(fpga, value):
    """Set RFDC to a specific value."""
    try:
        current = fpga.read_uint('rfdc')
        print(f"\n⚠ RFDC MODIFICATION")
        print(f"  Current value: 0x{current:08x}")
        print(f"  Target value:  0x{value:08x}")
        
        # Show what changes
        diff = current ^ value
        changed_bytes = []
        for i in range(4):
            byte_diff = (diff >> (i*8)) & 0xFF
            if byte_diff:
                old_byte = (current >> (i*8)) & 0xFF
                new_byte = (value >> (i*8)) & 0xFF
                changed_bytes.append(f"Byte{i}: 0x{old_byte:02x}→0x{new_byte:02x}")
        
        print(f"  Changes: {', '.join(changed_bytes)}\n")
        
        # Confirm
        response = input("Continue? (yes/no): ").strip().lower()
        if response != 'yes':
            print("Cancelled.")
            return current
        
        # Write it
        fpga.write_uint('rfdc', value)
        time.sleep(0.5)
        
        # Read back to verify
        new_val = fpga.read_uint('rfdc')
        if new_val == value:
            print(f"✓ Successfully set RFDC to 0x{new_val:08x}\n")
            return new_val
        else:
            print(f"✗ WARNING: Write failed!")
            print(f"  Expected: 0x{value:08x}")
            print(f"  Got:      0x{new_val:08x}\n")
            return new_val
    
    except Exception as e:
        print(f"ERROR: {e}\n")
        return None

def action_test_sequence(fpga):
    """Test a sequence of predefined RFDC values."""
    try:
        print("\n" + "="*70)
        print("RFDC TEST SEQUENCE")
        print("="*70 + "\n")
        
        original = fpga.read_uint('rfdc')
        print(f"Original value: 0x{original:08x}\n")
        
        # Test values focusing on bytes that might be gain
        test_values = [
            (original,            "Original (baseline)"),
            (original | 0x0000FF00, "Try: Enable all bits in byte1"),
            (original | 0x000000FF, "Try: Enable all bits in byte0"),
            (original | 0x0000FFFF, "Try: Enable all bits in bytes 0-1"),
            ((original & 0xFF0000FF) | 0x0000FF00, "Try: Set byte1 to 0xFF"),
            ((original & 0xFFFF00FF) | 0x00FF0000, "Try: Set byte2 to 0xFF"),
        ]
        
        for val, desc in test_values:
            print(f"\n{desc}")
            print(f"  Value: 0x{val:08x}")
            
            try:
                fpga.write_uint('rfdc', val)
                time.sleep(0.2)
                read_back = fpga.read_uint('rfdc')
                
                if read_back == val:
                    print(f"  ✓ Written successfully")
                else:
                    print(f"  ✗ Read back different: 0x{read_back:08x}")
            except Exception as e:
                print(f"  ✗ Error: {e}")
            
            response = input("  Continue to next? (yes/no): ").strip().lower()
            if response != 'yes':
                break
        
        # Restore original
        print(f"\nRestoring original value: 0x{original:08x}")
        fpga.write_uint('rfdc', original)
        time.sleep(0.2)
        if fpga.read_uint('rfdc') == original:
            print("✓ Original value restored\n")
        else:
            print("✗ WARNING: Could not restore original value!\n")
    
    except Exception as e:
        print(f"ERROR: {e}\n")

def action_interactive(fpga):
    """Interactive mode - manually enter and test values."""
    print("\n" + "="*70)
    print("INTERACTIVE RFDC MODIFIER")
    print("="*70 + "\n")
    
    original = fpga.read_uint('rfdc')
    print(f"Original: 0x{original:08x}\n")
    
    try:
        while True:
            try:
                user_input = input("Enter value (hex, e.g. 0x02050000) or 'quit': ").strip().lower()
                
                if user_input == 'quit':
                    print("Exiting.")
                    break
                
                if user_input == 'reset':
                    fpga.write_uint('rfdc', original)
                    print(f"Reset to original: 0x{original:08x}\n")
                    continue
                
                if user_input == 'status':
                    val = fpga.read_uint('rfdc')
                    print(f"Current: 0x{val:08x}\n")
                    continue
                
                # Parse hex value
                try:
                    value = int(user_input, 16)
                except ValueError:
                    print("Invalid hex format. Use format: 0xXXXXXXXX\n")
                    continue
                
                # Set it
                action_set(fpga, value)
                
                print("\nMeasure spectrum to check if attenuation changed!")
                print("Commands: 'quit', 'reset', 'status', or enter new hex value\n")
            
            except KeyboardInterrupt:
                print("\n\nCancelled.")
                break
        
        # Restore original on exit
        print(f"\nRestoring original: 0x{original:08x}")
        fpga.write_uint('rfdc', original)
        if fpga.read_uint('rfdc') == original:
            print("✓ Original restored")
        else:
            print("✗ WARNING: Could not restore!")
    
    except Exception as e:
        print(f"ERROR: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Quick RFDC register tester',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get current value
  pipenv run python tools/rfdc_quick_test.py --fpga 169.254.2.181 --action get
  
  # Set to specific value
  pipenv run python tools/rfdc_quick_test.py --fpga 169.254.2.181 --action set --value 0x020500FF
  
  # Interactive testing
  pipenv run python tools/rfdc_quick_test.py --fpga 169.254.2.181 --action interactive
  
  # Test predefined sequence
  pipenv run python tools/rfdc_quick_test.py --fpga 169.254.2.181 --action test
        """
    )
    
    parser.add_argument('--fpga', type=str, default='169.254.2.181',
                        help='FPGA IP address')
    parser.add_argument('--action', type=str, default='get',
                        choices=['get', 'set', 'test', 'interactive'],
                        help='Action to perform')
    parser.add_argument('--value', type=lambda x: int(x, 16),
                        help='Value to set (hex format, e.g. 0x02050000)')
    
    args = parser.parse_args()
    
    fpga = connect_fpga(args.fpga)
    if not fpga:
        sys.exit(1)
    
    if args.action == 'get':
        action_get(fpga)
    elif args.action == 'set':
        if args.value is None:
            print("ERROR: --value required for 'set' action")
            sys.exit(1)
        action_set(fpga, args.value)
    elif args.action == 'test':
        action_test_sequence(fpga)
    elif args.action == 'interactive':
        action_interactive(fpga)

if __name__ == "__main__":
    main()
