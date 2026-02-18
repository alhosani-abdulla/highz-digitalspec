#!/usr/bin/env python3
"""
Manual GPIO Pin Control Testing Script for Spectrometer Calibration States

This script allows you to manually control the GPIO pins that set the spectrometer's
calibration state without running the full spectrometer code. Useful for testing
hardware, debugging, and development.

Usage:
    # Interactive mode
    pipenv run python src/gpio_test.py
    
    # Set state directly (decimal)
    pipenv run python src/gpio_test.py --state 5
    
    # Set state via binary
    pipenv run python src/gpio_test.py --binary 101
    
    # Run interactive mode with default state
    pipenv run python src/gpio_test.py --state 3
"""

import sys
import argparse
import time
from gpiozero import LED

# GPIO pin configuration
GPIO_PIN_0 = 21  # LSB
GPIO_PIN_1 = 20  # Middle bit
GPIO_PIN_2 = 16  # MSB

# Initialize GPIO pins
gpio_pin0 = LED(GPIO_PIN_0)
gpio_pin1 = LED(GPIO_PIN_1)
gpio_pin2 = LED(GPIO_PIN_2)

# Calibration state mapping
CALIBRATION_STATES = {
    0: "Antenna - Main Switch Powered",
    1: "Open Circuit",
    2: '6" Shorted',
    3: "Calibration State 3",
    4: "Calibration State 4",
    5: "Calibration State 5",
    6: "Calibration State 6",
    7: "Calibration State 7",
}

def set_gpio_state(state_num):
    """
    Set GPIO pins based on calibration state number (0-7).
    
    The state is encoded in 3 GPIO pins as follows:
    - Pin 21 (GPIO_PIN_0): LSB
    - Pin 20 (GPIO_PIN_1): Middle bit
    - Pin 16 (GPIO_PIN_2): MSB
    
    The internal index is calculated as: idx = 7 - state_num.
    This is because the gpio states are sent to an inverting chip. 
    """
    if state_num < 0 or state_num > 7:
        print(f"ERROR: Invalid state {state_num}. Must be 0-7.")
        return False
    
    idx = 7 - state_num
    
    # Extract bit values
    pin2 = (idx & 4) >> 2  # Bit 2
    pin1 = (idx & 2) >> 1  # Bit 1
    pin0 = idx & 1         # Bit 0
    
    # Set pins
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
    
    # Display status
    binary_str = f"{pin2}{pin1}{pin0}"
    print(f"\n✓ Set to State {state_num}: {CALIBRATION_STATES[state_num]}")
    print(f"  Internal index: {idx} (binary: {binary_str})")
    print(f"  GPIO Pins - Pin16 (MSB): {pin2}, Pin20: {pin1}, Pin21 (LSB): {pin0}")
    
    return True

def get_current_state():
    """
    Read current GPIO pin states and determine current calibration state.
    """
    pin0_state = gpio_pin0.value  # 1 if on, 0 if off
    pin1_state = gpio_pin1.value
    pin2_state = gpio_pin2.value
    
    binary_str = f"{int(pin2_state)}{int(pin1_state)}{int(pin0_state)}"
    idx = (int(pin2_state) << 2) | (int(pin1_state) << 1) | int(pin0_state)
    state_num = 7 - idx
    
    return state_num, binary_str, idx

def display_status():
    """Display current GPIO state and calibration state."""
    state, binary, idx = get_current_state()
    print(f"\n{'='*60}")
    print(f"Current Calibration State: {state}")
    print(f"Description: {CALIBRATION_STATES[state]}")
    print(f"GPIO Binary: {binary} (internal idx: {idx})")
    print(f"GPIO Pin States:")
    print(f"  Pin 21 (LSB): {'ON' if gpio_pin0.value else 'OFF'}")
    print(f"  Pin 20:       {'ON' if gpio_pin1.value else 'OFF'}")
    print(f"  Pin 16 (MSB): {'ON' if gpio_pin2.value else 'OFF'}")
    print(f"{'='*60}")

def binary_to_state(binary_str):
    """Convert binary string to calibration state number."""
    try:
        if len(binary_str) != 3:
            print(f"ERROR: Binary string must be exactly 3 bits, got '{binary_str}'")
            return None
        
        # Verify it's only 0s and 1s
        if not all(c in '01' for c in binary_str):
            print(f"ERROR: Binary string must contain only 0s and 1s, got '{binary_str}'")
            return None
        
        idx = int(binary_str, 2)
        state = 7 - idx
        return state
    except Exception as e:
        print(f"ERROR: Invalid binary format: {e}")
        return None

def interactive_mode(initial_state=None):
    """
    Run interactive mode where user can change states.
    """
    print("\n" + "="*60)
    print("GPIO Pin Control - Interactive Mode")
    print("="*60)
    print("\nAvailable Commands:")
    print("  <0-7>      - Set state using decimal (e.g., '5')")
    print("  b<binary>  - Set state using binary (e.g., 'b101')")
    print("  status     - Show current state")
    print("  list       - List all calibration states")
    print("  help       - Show this help message")
    print("  exit/quit  - Exit program (resets to state 0)")
    print("="*60)
    
    # Set initial state if provided
    if initial_state is not None:
        set_gpio_state(initial_state)
    else:
        set_gpio_state(0)
    
    display_status()
    
    try:
        while True:
            user_input = input("\nEnter command> ").strip().lower()
            
            if not user_input:
                continue
            
            if user_input in ['exit', 'quit']:
                print("\nResetting to state 0 (Antenna - Main Switch Powered)...")
                set_gpio_state(0)
                print("Exiting.")
                break
            
            elif user_input == 'status':
                display_status()
            
            elif user_input == 'list':
                print("\nAvailable Calibration States:")
                for state, description in CALIBRATION_STATES.items():
                    print(f"  {state}: {description}")
            
            elif user_input == 'help':
                print("\nAvailable Commands:")
                print("  <0-7>      - Set state using decimal (e.g., '5')")
                print("  b<binary>  - Set state using binary (e.g., 'b101')")
                print("  status     - Show current state")
                print("  list       - List all calibration states")
                print("  help       - Show this help message")
                print("  exit/quit  - Exit program (resets to state 0)")
            
            elif user_input.startswith('b'):
                # Binary input
                binary_str = user_input[1:]
                state = binary_to_state(binary_str)
                if state is not None:
                    set_gpio_state(state)
                    display_status()
            
            else:
                # Try to parse as decimal state
                try:
                    state = int(user_input)
                    if set_gpio_state(state):
                        display_status()
                except ValueError:
                    print(f"ERROR: Invalid input '{user_input}'. Type 'help' for commands.")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted. Resetting to state 0...")
        set_gpio_state(0)
        print("Exiting.")
    
    except Exception as e:
        print(f"\nERROR: {e}")
        print("Resetting to state 0 before exit...")
        try:
            set_gpio_state(0)
        except:
            pass

def main():
    parser = argparse.ArgumentParser(
        description='Manual GPIO control for spectrometer calibration states',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python gpio_test.py
  
  # Set state 5 and enter interactive mode
  python gpio_test.py --state 5
  
  # Set state via binary (101 = state 2)
  python gpio_test.py --binary 101
  
  # Set state and exit immediately
  python gpio_test.py --state 3 --exit
        """
    )
    
    parser.add_argument('--state', type=int, choices=range(8),
                        help='Initial calibration state (0-7)')
    parser.add_argument('--binary', type=str,
                        help='Set state via binary (e.g., 101 for state 2)')
    parser.add_argument('--exit', action='store_true',
                        help='Exit immediately after setting state (for scripting)')
    
    args = parser.parse_args()
    
    # Determine initial state
    initial_state = None
    
    if args.binary:
        initial_state = binary_to_state(args.binary)
        if initial_state is None:
            sys.exit(1)
    elif args.state is not None:
        initial_state = args.state
    
    # Set initial state if provided
    if initial_state is not None:
        set_gpio_state(initial_state)
        display_status()
        
        if args.exit:
            print("\nExiting with state unchanged.")
            return
    
    # Enter interactive mode
    interactive_mode(initial_state)

if __name__ == "__main__":
    main()
