# =======================
# Imports
# =======================
import argparse
import subprocess
import time
import os
from datetime import datetime, timezone

# Third-party imports
import numpy as np
import rcal

from .vars import * 
from .fpga_helper import initialize_fpga, get_acc_cnt, get_vacc_data

sum_spectrum = lambda spectrum: np.array([sum(x) for x in zip(*spectrum)], dtype=np.float64)

def is_storage_mounted(mount_path):
    """
    Check if storage device is actually mounted (not just if directory exists).

    Parameters:
            mount_path (str): Path to check (e.g., '/media/peterson/INDURANCE')

    Returns:
            bool: True if mounted, False if not mounted
    """
    try:
        result = subprocess.run(
            ['mountpoint', '-q', mount_path],
            capture_output=True,
            timeout=2
        )
        return result.returncode == 0
    except Exception:
        # Fallback: check if directory has contents (less reliable)
        try:
            return len(next(os.walk(mount_path))[1]) > 0
        except:
            return False

def wait_for_storage(mount_path, check_interval=5):
    """
    Wait for storage device to be mounted.

    Parameters:
            mount_path (str): Path to wait for
            check_interval (int): Seconds between checks
    """
    while not is_storage_mounted(mount_path):
        print(f'Storage {mount_path} not mounted. Waiting for drive...')
        time.sleep(check_interval)
  
def write_filename(state, acc_no):
    """Generate a filename based on the current timestamp, antenna state, and accumulation number."""
    basename = str(datetime.fromtimestamp(time.time(), tz=timezone.utc).strftime(
        '%Y%m%d_%H%M%S') + f'_antenna{ANTENNA}_state{state}')

    return f"{basename}_{acc_no}" if SAVE_EACH_ACC else basename

########################################################################
# Main function to take spectra in a loop, switching states and saving data
def main(Antenna_no):
    global cycle_count

    # Initialize global variables
    cycle_count = 0
    sub_dir_count = 0
    
    # Initialize FPGA and ADC
    fpga, adc = initialize_fpga()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='high-z digital spectrometer')
    parser.add_argument('--state', default=None, type=int,
                        help='switch state (0-10)')
    parser.add_argument('--run_dir', default=None,
                        help='parent directory name for this observing run')
    args = parser.parse_args()
    print(f"Command line arguments: {args}")
    
    input_state = args.state
    run_dir = args.run_dir

    # Main data acquisition loop
    while True:
        # Check if storage device is mounted
        wait_for_storage('/media/peterson/INDURANCE')

        acc_n = fpga.read_uint('acc_cnt')

        if input_state is not None:
            rcal.gpio_switch(input_state, SWITCH_DELAY)
            for n in range(100):  # collect 100 spectra in the specified state
                _, _, sub_dir_count, acc_n = save_all_data(fpga, switch_value=input_state, sub_dir_count=sub_dir_count,
                        last_acc_n=acc_n, run_dir=run_dir)
            print(f'Completed data collection for state {input_state}. Exiting.')
            break
        else:
            # Digital Spectrometer Calibaration Sweep.
            for s in range(1, 8):  # Calibration states 1-7
                spectra_n = CAL_ACC_N
                if s == 2:  # switching to 6" shorted
                    rcal.gpio_switch(s, SWITCH_DELAY)
                    spectra_n = CAL_ACC_N + FB_N  # extra spectra for filter bank calibration
                else:
                    # Switching Calibration States
                    rcal.gpio_switch(s, SWITCH_DELAY)

                for n in range(spectra_n):
                    _, _, sub_dir_count, acc_n = save_all_data(fpga, switch_value=s, sub_dir_count=sub_dir_count,
                            last_acc_n=acc_n, run_dir=run_dir)

            # Observing with the Antenna - collecting ant_acc_n spectras
            state = 0
            rcal.gpio_switch(state, SWITCH_DELAY)
            for cnt in range(ANT_ACC_N):
                _, _, sub_dir_count, acc_n = save_all_data(fpga, switch_value=state, sub_dir_count=sub_dir_count,
                        last_acc_n=acc_n, run_dir=run_dir)

        # Increment the cycle count after one full calibration + observation cycle
        cycle_count += 1

def save_data(dataDict, filename, sub_dir_count, run_dir=None) -> int:
    """Save data into the appropriate directory.
    
    Returns:
        int: Updated subdirectory count if a new subdirectory was created, otherwise the same count.
    """
    # Skip saving if SAVE_DATA is False
    if not SAVE_DATA:
        print(f"Data saving disabled. Would have saved: {filename}")
        return sub_dir_count

    # Wait for storage to be mounted
    wait_for_storage('/media/peterson/INDURANCE')

    # Get the latest directory in the base path
    dirnames = next(os.walk(BASE_PATH))[1]
    dirname = dirnames[-1]

    # Create parent directory for data if it doesn't exist
    parent_dir_name = run_dir if run_dir is not None else filename.split('_')[0]
    parent_dir_path = os.path.join(BASE_PATH, dirname, parent_dir_name)

    if not os.path.exists(parent_dir_path):
        os.mkdir(parent_dir_path)

    # Create a new subdirectory only after completing a cycle
    if cycle_count >= 1 or current_sub_dir_path is None:
        current_sub_dir_path, sub_dir_count = get_sub_directory(
            parent_dir_path, sub_dir_count)
        cycle_count = 0  # Reset cycle count after creating a new subdirectory

    # Save the file in the appropriate directory
    file_path = os.path.join(current_sub_dir_path, f"{filename}.npy")
    np.save(file_path, dataDict, allow_pickle='False')
    print(f"Data saved to {file_path}")
    return sub_dir_count

def save_all_data(fpga, switch_value, last_acc_n, sub_dir_count, run_dir):
    """Collect data from the FPGA, save it, and return the data dictionary and filename.
    
    Parameters:
        fpga: FPGA object to read from
        switch_value: The current state of the GPIO switch
        last_acc_n: The last known accumulation count to wait for new data
        sub_dir_count: Counter for subdirectory numbers
        run_dir: Parent directory name for this observing run (optional)
    """
    t_1 = time.time()
    # save volt + temp data
    # dataDict = volt_therm_lib.get_temp_volt_data()
    dataDict = {}
    dataDict["switch state"] = switch_value
    t_2 = time.time()
    if SAVE_EACH_ACC:
        # Save each individual accumulation
        acc_n = get_acc_cnt(fpga, last_acc_n)
        last_acc_n = acc_n

        s, cnt = get_vacc_data(fpga)
        dataDict["spectrum"] = s
        filename = write_filename(switch_value, cnt)
        if SAVE_DATA:
            sub_dir_count = save_data(dataDict, filename, sub_dir_count, run_dir)

    else:
        spectra = {}
        while len(spectra) < 3:
            acc_n = get_acc_cnt(fpga, acc_n)
            last_acc_n = acc_n
            
            s, cnt = get_vacc_data(fpga)
            spectra[cnt] = s

        spectra_list = [spectra[key] for key in spectra.keys()]

        # separating corrupt spectra from clean ones:
        # clean_spectra, corrupt_spectra = detect_periodic_noise(spectra_list)

        dataDict["spectrum"] = sum_spectrum(spectra_list)
        # dataDict["nspectra"] = len(clean_spectra)
        filename = write_filename(switch_value, 'average')
        if SAVE_DATA:
            sub_dir_count = save_data(dataDict, filename, sub_dir_count, run_dir)
        
        print(f"Saved averaged spectrum for switch state {switch_value} with accumulation count {cnt}.")
        print(dataDict["switch state"])
        # print("Number of Clean Spectra:" + dataDict["nspectra"])
    t_6 = time.time()

    # print(f'save_all_data: {t_2-t_1}, {t_3-t_2}, {t_4-t_3}, {t_5-t_4}, {t_6-t_5}')
    print(f'save_all_data: {t_2-t_1}, {t_6-t_2}')

    return dataDict, filename, sub_dir_count, last_acc_n

def get_sub_directory(parent_dir_path, sub_dir_count):
    """
    Handles directory creation and naming for observing runs.

    Parameters:
        parent_dir_path (str): Parent directory path where subdirectories are stored.
        sub_dir_count (int): Counter for subdirectory numbers.

    Returns:
        str: Path to the subdirectory for the current data chunk.
    """

    # Determine the unique subdirectory name
    sub_dir_name = f"{datetime.fromtimestamp(time.time(), tz=timezone.utc).strftime('%H%M%S')}"
    sub_dir_path = os.path.join(parent_dir_path, sub_dir_name)

    # Create subdirectory if it doesn't exist
    if not os.path.exists(sub_dir_path):
        os.makedirs(sub_dir_path)
        sub_dir_count += 1

    return sub_dir_path, sub_dir_count

########################################################################


if __name__ == "__main__":
    main()
