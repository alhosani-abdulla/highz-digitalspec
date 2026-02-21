#!/usr/bin/env python3
"""
Advanced RFSoC RFDC Diagnostic - Test Gain Control Hypotheses

This script tests various hypotheses about what controls the 15dB attenuation:
1. QMC (Quadrature Mixer Correction) gain settings
2. ADC/DAC tile gain settings
3. RFDC register bit patterns
4. Fine mixer scale settings

Usage:
    pipenv run python tools/rfsoc_diagnostic_advanced.py --fpga 169.254.2.181 --test all
"""

import sys
import argparse

try:
    import casperfpga
except ImportError:
    print("ERROR: casperfpga not installed")
    sys.exit(1)

def connect_fpga(fpga_ip):
    """Connect to FPGA."""
    print(f"\nConnecting to RFSoC at {fpga_ip}...")
    try:
        fpga = casperfpga.CasperFpga(fpga_ip)
        if fpga.is_connected():
            print("✓ Connected")
            return fpga
        else:
            print("ERROR: Could not connect")
            return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def test_qmc_settings(fpga):
    """
    Test QMC (Quadrature Mixer Correction) settings for ADCs.
    These control gain and phase correction for I/Q mixers.
    """
    print(f"\n{'='*70}")
    print("TEST 1: QMC (Quadrature Mixer Correction) Settings")
    print(f"{'='*70}\n")
    
    print("QMC settings control gain and phase correction for I/Q data paths.")
    print("This might be where your 15dB of attenuation is set!\n")
    
    adc = fpga.adcs['rfdc']
    
    # Try to get QMC settings for each tile and slice
    for tile in range(4):
        for block in range(2):  # 2 blocks per tile
            try:
                # Try getting QMC settings (if method exists)
                if hasattr(adc, 'get_qmc_settings'):
                    settings = adc.get_qmc_settings(tile, block, adc.ADC_TILE)
                    print(f"  ADC Tile {tile}, Block {block}:")
                    if isinstance(settings, dict):
                        for key, val in settings.items():
                            print(f"    {key}: {val}")
                    else:
                        print(f"    {settings}")
                else:
                    print(f"  ADC Tile {tile}, Block {block}: get_qmc_settings method not available")
                    break
            except Exception as e:
                # Expected - not all blocks may have settings
                pass

def test_fine_mixer_settings(fpga):
    """
    Test fine mixer scale settings which control gain for fine frequency mixing.
    """
    print(f"\n{'='*70}")
    print("TEST 2: Fine Mixer Scale Settings")
    print(f"{'='*70}\n")
    
    print("Fine mixer scale affects gain: 0=Auto, 1=1.0x, 2=0.7x\n")
    
    adc = fpga.adcs['rfdc']
    
    for tile in range(4):
        for block in range(2):
            try:
                if hasattr(adc, 'get_mixer_scale'):
                    scale = adc.get_mixer_scale(tile, block, adc.ADC_TILE)
                    print(f"  ADC Tile {tile}, Block {block}: Mixer Scale = {scale}")
                    
                    # Explain what 0.7 means in dB
                    if scale == 2:  # 0.7x
                        db_atten = 20 * np.log10(0.7)
                        print(f"    ^ 0.7x = {db_atten:.2f} dB attenuation")
            except:
                pass

def test_coarse_mixer_freq(fpga):
    """
    Test coarse mixer frequency and settings.
    """
    print(f"\n{'='*70}")
    print("TEST 3: Coarse Mixer Frequency Settings")
    print(f"{'='*70}\n")
    
    print("Coarse mixer can affect the signal path and potentially gain\n")
    
    adc = fpga.adcs['rfdc']
    
    for tile in range(4):
        for block in range(2):
            try:
                if hasattr(adc, 'get_mixer_freq'):
                    freq = adc.get_mixer_freq(tile, block, adc.ADC_TILE)
                    print(f"  ADC Tile {tile}, Block {block}:")
                    if isinstance(freq, dict):
                        for key, val in freq.items():
                            print(f"    {key}: {val}")
                    else:
                        print(f"    Frequency: {freq}")
            except:
                pass

def test_tile_decimation(fpga):
    """
    Test ADC tile decimation factor which can affect gain.
    """
    print(f"\n{'='*70}")
    print("TEST 4: Tile Decimation Settings")
    print(f"{'='*70}\n")
    
    print("Decimation factor can affect gain through scaling\n")
    
    adc = fpga.adcs['rfdc']
    
    for tile in range(4):
        try:
            if hasattr(adc, 'get_decim'):
                decim = adc.get_decim(tile, adc.ADC_TILE)
                print(f"  ADC Tile {tile}: Decimation = {decim}")
                # 15dB attenuation = 10^(-15/20) ≈ 0.178 or 10^(-15/20) ≈ 1/5.62
                # Decimation of 1, 2, 4, 8, 16... wouldn't directly give 15dB
        except:
            pass

def test_adc_tile_defaults(fpga):
    """
    Show default ADC tile configuration.
    """
    print(f"\n{'='*70}")
    print("TEST 5: ADC Tile Status and Configuration")
    print(f"{'='*70}\n")
    
    adc = fpga.adcs['rfdc']
    
    try:
        status = adc.status()
        print("ADC/DAC Tile Status:")
        for tile, info in status.items():
            print(f"  {tile}: {info}")
    except Exception as e:
        print(f"ERROR getting status: {e}")

def test_rfdc_register_analysis(fpga):
    """
    Analyze the RFDC register in detail.
    """
    print(f"\n{'='*70}")
    print("TEST 6: RFDC Register Deep Analysis")
    print(f"{'='*70}\n")
    
    try:
        value = fpga.read_uint('rfdc')
        print(f"RFDC Register: 0x{value:08x}")
        
        # Try to map to known RFDC offsets
        print("\nAnalyzing as Xilinx RFDC offsets:")
        print(f"  Byte 3 (0x{(value >> 24) & 0xFF:02x}): Tile 0/1 control")
        print(f"  Byte 2 (0x{(value >> 16) & 0xFF:02x}): Tile 2/3 control")
        print(f"  Byte 1 (0x{(value >>  8) & 0xFF:02x}): ADC gain or control")
        print(f"  Byte 0 (0x{value & 0xFF:02x}): DAC gain or control")
        
        # Check specific bit patterns that might indicate scaling
        print("\nLooking for scaling patterns:")
        
        # 15dB attenuation = 0x1999 or similar in some scaling formats
        # 0.178 in Q16 fixed point = 11666 = 0x2D92
        # -15dB = -0.178 in linear scale
        
        # Try fractions that equal 15dB
        import math
        atten_linear = 10**(-15/20)  # ≈ 0.1778
        atten_q16 = int(atten_linear * 65536)
        
        print(f"  15dB attenuation in linear: {atten_linear:.4f}")
        print(f"  15dB in Q16 fixed-point: 0x{atten_q16:04x} ({atten_q16})")
        print(f"  Current RFDC bytes: 0x{(value >> 8) & 0xFFFF:04x}")
        
        if ((value >> 8) & 0xFFFF) == atten_q16:
            print("  ✓ POTENTIAL MATCH! Gain register might be in bytes 1-2!")
        
    except Exception as e:
        print(f"ERROR: {e}")

def list_available_adc_methods(fpga):
    """
    List all available methods on the ADC object.
    """
    print(f"\n{'='*70}")
    print("Available ADC Methods (for future debugging)")
    print(f"{'='*70}\n")
    
    adc = fpga.adcs['rfdc']
    
    methods = [m for m in dir(adc) if not m.startswith('_') and callable(getattr(adc, m))]
    
    # Filter for potentially useful ones
    interesting = [m for m in methods if any(x in m.lower() for x in 
                                             ['gain', 'scale', 'mixer', 'qmc', 'atten', 'coeff', 'cali', 'thresh'])]
    
    print("Methods that might control gain/attenuation:")
    for method in sorted(interesting):
        print(f"  - {method}")

def main():
    parser = argparse.ArgumentParser(
        description='Advanced RFSoC diagnostic to find attenuation source',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pipenv run python tools/rfsoc_diagnostic_advanced.py --fpga 169.254.2.181 --test all
  pipenv run python tools/rfsoc_diagnostic_advanced.py --fpga 169.254.2.181 --test qmc
        """
    )
    
    parser.add_argument('--fpga', type=str, default='169.254.2.181',
                        help='FPGA IP address')
    parser.add_argument('--test', type=str, default='all',
                        choices=['all', 'qmc', 'mixer', 'decimation', 'rfdc', 'methods'],
                        help='Which tests to run')
    
    args = parser.parse_args()
    
    # Connect
    fpga = connect_fpga(args.fpga)
    if not fpga:
        sys.exit(1)
    
    # Run tests
    if args.test in ['all', 'qmc']:
        test_qmc_settings(fpga)
    
    if args.test in ['all', 'mixer']:
        test_fine_mixer_settings(fpga)
        test_coarse_mixer_freq(fpga)
    
    if args.test in ['all', 'decimation']:
        test_tile_decimation(fpga)
    
    if args.test in ['all', 'rfdc']:
        test_rfdc_register_analysis(fpga)
        test_adc_tile_defaults(fpga)
    
    if args.test in ['all', 'methods']:
        list_available_adc_methods(fpga)

if __name__ == "__main__":
    main()
