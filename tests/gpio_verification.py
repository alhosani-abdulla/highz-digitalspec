#!/usr/bin/env python3
"""
Automated GPIO State Verification Test Suite

Tests all 8 calibration states by:
1. Setting each state (0-7)
2. Verifying the expected GPIO pins are in correct state
3. Collecting pin state readings for statistics
4. Reporting results with any anomalies

This is an automated test to verify GPIO control hardware is functioning correctly.

Usage:
    pipenv run python tests/gpio_verification.py
    pipenv run python tests/gpio_verification.py --verbose
    pipenv run python tests/gpio_verification.py --repeat 3
"""

import sys
import os
import argparse
import time
import subprocess
import re
from collections import defaultdict
from datetime import datetime
from gpiozero import LED

# GPIO pin configuration (must match rcal.py)
GPIO_PIN_0 = 21  # LSB
GPIO_PIN_1 = 20  # Middle bit
GPIO_PIN_2 = 16  # MSB

GPIO_PINS = {
    21: "Pin 21 (LSB)",
    20: "Pin 20 (Mid)",
    16: "Pin 16 (MSB)",
}

# Expected pin states for each calibration state
# Format: state_num -> (pin_16_expected, pin_20_expected, pin_21_expected)
EXPECTED_STATES = {
    0: (1, 1, 1),  # idx=7, binary=111
    1: (1, 1, 0),  # idx=6, binary=110
    2: (1, 0, 1),  # idx=5, binary=101
    3: (1, 0, 0),  # idx=4, binary=100
    4: (0, 1, 1),  # idx=3, binary=011
    5: (0, 1, 0),  # idx=2, binary=010
    6: (0, 0, 1),  # idx=1, binary=001
    7: (0, 0, 0),  # idx=0, binary=000
}

CALIBRATION_NAMES = {
    0: "Antenna - Main Switch Powered",
    1: "Open Circuit",
    2: '6" Shorted',
    3: "Calibration State 3",
    4: "Calibration State 4",
    5: "Calibration State 5",
    6: "Calibration State 6",
    7: "Calibration State 7",
}

# Initialize GPIO pins
gpio_pin0 = LED(GPIO_PIN_0)
gpio_pin1 = LED(GPIO_PIN_1)
gpio_pin2 = LED(GPIO_PIN_2)

# Test results tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "errors": [],
    "stats": defaultdict(list),
}


def set_gpio_state(state_num):
    """Set GPIO pins to specified state."""
    if state_num < 0 or state_num > 7:
        raise ValueError(f"Invalid state {state_num}. Must be 0-7.")
    
    idx = 7 - state_num
    pin2 = (idx & 4) >> 2
    pin1 = (idx & 2) >> 1
    pin0 = idx & 1
    
    if pin0:
        gpio_pin0.on()
    else:
        gpio_pin0.off()
    
    if pin1:
        gpio_pin1.on()
    else:
        gpio_pin1.off()
    
    if pin2:
        gpio_pin2.on()
    else:
        gpio_pin2.off()


def read_pin_state(pin_num):
    """
    Read actual pin state using gpioget utility.
    Returns 0 or 1 representing LOW or HIGH.
    """
    try:
        # Find the chip and line number for the given pin
        result = subprocess.run(
            ["gpioinfo"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # Parse gpioinfo output to find pin mapping
        for line in result.stdout.split('\n'):
            if f'gpio{pin_num}' in line.lower() or f'pin {pin_num}' in line.lower():
                # Extract state from line like: "GPIO21 output low"
                if 'high' in line.lower():
                    return 1
                elif 'low' in line.lower():
                    return 0
        
        # Fallback: read from gpiozero
        if pin_num == 21:
            return int(gpio_pin0.value)
        elif pin_num == 20:
            return int(gpio_pin1.value)
        elif pin_num == 16:
            return int(gpio_pin2.value)
        
        return None
    except Exception as e:
        print(f"WARNING: Failed to read pin {pin_num}: {e}")
        return None


def verify_state(state_num, verbose=False):
    """
    Verify that GPIO pins match expected state.
    Returns True if all pins are correct, False otherwise.
    """
    expected = EXPECTED_STATES[state_num]
    actual = [
        int(gpio_pin2.value),
        int(gpio_pin1.value),
        int(gpio_pin0.value),
    ]
    
    # Try to read actual pin states
    pin_values = {}
    for pin_num in [16, 20, 21]:
        state = read_pin_state(pin_num)
        if state is not None:
            pin_values[pin_num] = state
    
    # Use gpiozero values as fallback
    if not pin_values:
        pin_values = {
            16: int(gpio_pin2.value),
            20: int(gpio_pin1.value),
            21: int(gpio_pin0.value),
        }
    
    # Record for statistics
    for pin_num, value in pin_values.items():
        test_results["stats"][f"pin_{pin_num}"].append(value)
    
    # Verify against expected
    expected_dict = {16: expected[0], 20: expected[1], 21: expected[2]}
    
    is_correct = all(
        pin_values[pin] == expected_dict[pin]
        for pin in [16, 20, 21]
    )
    
    if verbose or not is_correct:
        print(f"\n  State {state_num}: {CALIBRATION_NAMES[state_num]}")
        print(f"    Expected: Pin16={expected[0]}, Pin20={expected[1]}, Pin21={expected[2]}")
        print(f"    Actual:   Pin16={pin_values[16]}, Pin20={pin_values[20]}, Pin21={pin_values[21]}")
        
        if is_correct:
            print(f"    ✓ PASS")
        else:
            print(f"    ✗ FAIL")
            for pin in [16, 20, 21]:
                if pin_values[pin] != expected_dict[pin]:
                    print(f"      - Pin {pin}: expected {expected_dict[pin]}, got {pin_values[pin]}")
    
    return is_correct


def run_test_suite(verbose=False, repeat=1):
    """Run automated GPIO test for all states."""
    print("="*70)
    print("GPIO State Verification Test Suite")
    print("="*70)
    print(f"Testing {8 * repeat} total state transitions ({repeat} pass(es) of 8 states)")
    print(f"Verbose mode: {verbose}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-"*70)
    
    for pass_num in range(repeat):
        if repeat > 1:
            print(f"\n--- Pass {pass_num + 1}/{repeat} ---")
        
        for state in range(8):
            try:
                # Set the state
                set_gpio_state(state)
                
                # Small delay to allow hardware to settle
                time.sleep(0.1)
                
                # Verify the state
                if verify_state(state, verbose):
                    test_results["passed"] += 1
                else:
                    test_results["failed"] += 1
                    test_results["errors"].append(f"State {state} verification failed")
            
            except Exception as e:
                print(f"  ERROR testing state {state}: {e}")
                test_results["failed"] += 1
                test_results["errors"].append(f"State {state}: {str(e)}")
    
    # Final reset to state 0
    try:
        set_gpio_state(0)
    except:
        pass
    
    return test_results


def print_statistics():
    """Print test statistics and pin voltage analysis."""
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)
    
    total = test_results["passed"] + test_results["failed"]
    pass_rate = (test_results["passed"] / total * 100) if total > 0 else 0
    
    print(f"\nTest Statistics:")
    print(f"  Total Tests:    {total}")
    print(f"  Passed:         {test_results['passed']} ({pass_rate:.1f}%)")
    print(f"  Failed:         {test_results['failed']}")
    
    if test_results["errors"]:
        print(f"\nErrors:")
        for error in test_results["errors"]:
            print(f"  - {error}")
    
    # Pin statistics
    print(f"\nPin State Statistics:")
    for pin in [16, 20, 21]:
        key = f"pin_{pin}"
        if key in test_results["stats"] and test_results["stats"][key]:
            readings = test_results["stats"][key]
            high_count = sum(readings)
            low_count = len(readings) - high_count
            high_pct = (high_count / len(readings) * 100) if readings else 0
            
            print(f"  Pin {pin}:")
            print(f"    HIGH: {high_count} times ({high_pct:.1f}%)")
            print(f"    LOW:  {low_count} times ({100-high_pct:.1f}%)")
    
    if test_results["passed"] == total:
        print(f"\n✓ ALL TESTS PASSED")
        return 0
    else:
        print(f"\n✗ SOME TESTS FAILED")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Automated GPIO state verification test suite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test run (all 8 states once)
  python tests/gpio_verification.py
  
  # Verbose output showing each state
  python tests/gpio_verification.py --verbose
  
  # Run multiple passes for statistical analysis
  python tests/gpio_verification.py --repeat 5
  
  # Both verbose and multiple passes
  python tests/gpio_verification.py --verbose --repeat 3
        """
    )
    
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show detailed output for each state')
    parser.add_argument('-r', '--repeat', type=int, default=1,
                        help='Number of times to repeat the full test suite (default: 1)')
    
    args = parser.parse_args()
    
    try:
        # Run the test suite
        run_test_suite(verbose=args.verbose, repeat=args.repeat)
        
        # Print results
        exit_code = print_statistics()
        
        print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        sys.exit(exit_code)
    
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        try:
            set_gpio_state(0)
        except:
            pass
        sys.exit(1)
    
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        try:
            set_gpio_state(0)
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
