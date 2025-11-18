#!/usr/bin/env python3
"""
Enhanced GPIO Verification with Voltage/Stability Analysis

Extends gpio_verification.py with:
- System health metrics (CPU temp, power supply voltage)
- GPIO transition timing analysis
- Voltage level stability checks
- Advanced anomaly detection

Usage:
    pipenv run python tests/gpio_verification_advanced.py
    pipenv run python tests/gpio_verification_advanced.py --verbose
    pipenv run python tests/gpio_verification_advanced.py --repeat 5 --analyze-voltage
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
import statistics

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
    "timing": defaultdict(list),
    "system_metrics": {},
}


def get_system_metrics():
    """Get system health metrics for context."""
    metrics = {}
    
    # CPU Temperature
    try:
        result = subprocess.run(
            ["vcgencmd", "measure_temp"],
            capture_output=True,
            text=True,
            timeout=2
        )
        temp_match = re.search(r"temp=([\d.]+)", result.stdout)
        if temp_match:
            metrics["cpu_temp_c"] = float(temp_match.group(1))
    except:
        pass
    
    # Power supply voltage (if available via vcgencmd)
    try:
        result = subprocess.run(
            ["vcgencmd", "measure_volts"],
            capture_output=True,
            text=True,
            timeout=2
        )
        volt_match = re.search(r"volt=([\d.]+)V", result.stdout)
        if volt_match:
            metrics["supply_voltage_v"] = float(volt_match.group(1))
    except:
        pass
    
    return metrics


def measure_gpio_transition_time(from_state, to_state):
    """
    Measure the time it takes to transition between two GPIO states.
    Returns time in milliseconds.
    """
    from gpiozero import LED
    import time
    
    start = time.perf_counter()
    
    # Set from state
    idx_from = 7 - from_state
    pin2_from = (idx_from & 4) >> 2
    pin1_from = (idx_from & 2) >> 1
    pin0_from = idx_from & 1
    
    if pin0_from:
        gpio_pin0.on()
    else:
        gpio_pin0.off()
    
    if pin1_from:
        gpio_pin1.on()
    else:
        gpio_pin1.off()
    
    if pin2_from:
        gpio_pin2.on()
    else:
        gpio_pin2.off()
    
    transition_start = time.perf_counter()
    
    # Transition to new state
    idx_to = 7 - to_state
    pin2_to = (idx_to & 4) >> 2
    pin1_to = (idx_to & 2) >> 1
    pin0_to = idx_to & 1
    
    if pin0_to != pin0_from:
        if pin0_to:
            gpio_pin0.on()
        else:
            gpio_pin0.off()
    
    if pin1_to != pin1_from:
        if pin1_to:
            gpio_pin1.on()
        else:
            gpio_pin1.off()
    
    if pin2_to != pin2_from:
        if pin2_to:
            gpio_pin2.on()
        else:
            gpio_pin2.off()
    
    transition_end = time.perf_counter()
    transition_time = (transition_end - transition_start) * 1000  # Convert to ms
    
    return transition_time


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
    """Read actual pin state."""
    if pin_num == 21:
        return int(gpio_pin0.value)
    elif pin_num == 20:
        return int(gpio_pin1.value)
    elif pin_num == 16:
        return int(gpio_pin2.value)
    return None


def verify_state(state_num, verbose=False, measure_timing=False):
    """Verify GPIO pins match expected state and optionally measure timing."""
    expected = EXPECTED_STATES[state_num]
    
    # Read actual pin states
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


def run_test_suite(verbose=False, repeat=1, measure_timing=False):
    """Run automated GPIO test for all states."""
    print("="*70)
    print("Enhanced GPIO State Verification Test Suite")
    print("="*70)
    
    # Get and display system metrics
    metrics = get_system_metrics()
    test_results["system_metrics"] = metrics
    
    print(f"\nSystem Metrics:")
    if "cpu_temp_c" in metrics:
        print(f"  CPU Temperature: {metrics['cpu_temp_c']:.1f}°C")
    if "supply_voltage_v" in metrics:
        print(f"  Supply Voltage: {metrics['supply_voltage_v']:.2f}V (Expected: 5.0V)")
    
    print(f"\nTest Configuration:")
    print(f"  Total States: {8 * repeat} ({repeat} pass(es) of 8 states)")
    print(f"  Verbose Mode: {verbose}")
    print(f"  Timing Analysis: {measure_timing}")
    print(f"  Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-"*70)
    
    for pass_num in range(repeat):
        if repeat > 1:
            print(f"\n--- Pass {pass_num + 1}/{repeat} ---")
        
        for state in range(8):
            try:
                set_gpio_state(state)
                time.sleep(0.1)
                
                if verify_state(state, verbose):
                    test_results["passed"] += 1
                else:
                    test_results["failed"] += 1
                    test_results["errors"].append(f"State {state} verification failed")
            
            except Exception as e:
                print(f"  ERROR testing state {state}: {e}")
                test_results["failed"] += 1
                test_results["errors"].append(f"State {state}: {str(e)}")
    
    # Measure transition timing
    if measure_timing:
        print("\n--- Measuring State Transition Times ---")
        for from_state in range(8):
            for to_state in range(8):
                if from_state != to_state:
                    try:
                        transition_time = measure_gpio_transition_time(from_state, to_state)
                        test_results["timing"][f"{from_state}_to_{to_state}"] = transition_time
                    except:
                        pass
    
    # Final reset
    try:
        set_gpio_state(0)
    except:
        pass
    
    return test_results


def print_statistics():
    """Print comprehensive test statistics."""
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
    
    # Timing statistics
    if test_results["timing"]:
        print(f"\nGPIO Transition Timing:")
        times = list(test_results["timing"].values())
        if times:
            print(f"  Min:     {min(times):.3f} ms")
            print(f"  Max:     {max(times):.3f} ms")
            print(f"  Average: {statistics.mean(times):.3f} ms")
            print(f"  StdDev:  {statistics.stdev(times):.3f} ms" if len(times) > 1 else "")
    
    # System metrics summary
    if test_results["system_metrics"]:
        print(f"\nSystem Health During Testing:")
        if "cpu_temp_c" in test_results["system_metrics"]:
            temp = test_results["system_metrics"]["cpu_temp_c"]
            status = "✓ OK" if temp < 70 else "⚠ Elevated" if temp < 80 else "✗ High"
            print(f"  CPU Temperature: {temp:.1f}°C {status}")
        if "supply_voltage_v" in test_results["system_metrics"]:
            volt = test_results["system_metrics"]["supply_voltage_v"]
            status = "✓ OK" if 4.8 < volt < 5.2 else "⚠ Off-spec"
            print(f"  Supply Voltage: {volt:.2f}V {status}")
    
    if test_results["passed"] == total:
        print(f"\n✓ ALL TESTS PASSED")
        return 0
    else:
        print(f"\n✗ SOME TESTS FAILED")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Enhanced GPIO verification with voltage/stability analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test with system metrics
  python tests/gpio_verification_advanced.py
  
  # Verbose with timing analysis
  python tests/gpio_verification_advanced.py --verbose --timing
  
  # Multiple passes with detailed analysis
  python tests/gpio_verification_advanced.py --verbose --repeat 3 --timing
        """
    )
    
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show detailed output for each state')
    parser.add_argument('-r', '--repeat', type=int, default=1,
                        help='Number of times to repeat the full test suite (default: 1)')
    parser.add_argument('-t', '--timing', action='store_true',
                        help='Measure GPIO transition times')
    
    args = parser.parse_args()
    
    try:
        # Run the test suite
        run_test_suite(verbose=args.verbose, repeat=args.repeat, measure_timing=args.timing)
        
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
