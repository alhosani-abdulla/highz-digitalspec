# =======================
# Imports
# =======================
import argparse
import subprocess
import time
import os
import struct
from datetime import datetime, timezone

# Third-party imports
import numpy as np
import casperfpga
import rcal

from .vars import *
from .fpga_helper import initialize_fpga

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

########################################################################
# Main function to take spectra in a loop, switching states and saving data
def main(Antenna_no=ANTENNA):
    global acc_n, cycle_count, sub_dir_count, current_parent_dir, current_sub_dir_path, run_directory

    # Initialize global variables
    cycle_count = 0
    sub_dir_count = 0
    current_parent_dir = None  # name of the current parent directory
    current_sub_dir_path = None  # Path to the current subdirectory

    # Initialize FPGA and ADC
    fpga, adc = initialize_fpga()

    # Initial GPIO/Switch state
    rcal.gpio_switch(1, SWITCH_DELAY)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='high-z digital spectrometer')
    parser.add_argument('--state', default=None, type=int,
                        help='switch state (0-10)')
    parser.add_argument('--run_directory', default=None,
                        help='parent directory name for this observing run')
    args = parser.parse_args()
    print(args, flush=True)
    input_state = args.state
    run_directory = args.run_directory

    # Main data acquisition loop
    while True:
        # Check if storage device is mounted
        wait_for_storage('/media/peterson/INDURANCE')

        acc_n = fpga.read_uint('acc_cnt')

        if input_state is not None:
            rcal.gpio_switch(input_state, SWITCH_DELAY)
            for n in range(100):  # collect 100 spectra in the specified state
                data, name = save_all_data(fpga, switch_value=input_state)
            print(
                f'Completed data collection for state {input_state}. Exiting.')
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
                    data, name = save_all_data(fpga, switch_value=s)

            # Observing with the Antenna - collecting ant_acc_n spectras
            state = 0
            rcal.gpio_switch(state, SWITCH_DELAY)
            for cnt in range(ANT_ACC_N):
                data, name = save_all_data(fpga, switch_value=state)

        # Increment the cycle count after one full calibration + observation cycle
        cycle_count += 1

def get_vacc_data(fpga):
	"""
	Read accumulated vector data from FPGA and interleave channels.
	
	Parameters:
		fpga: FPGA object for reading data
		
	Returns:
		tuple: (interleaved_spectrum, accumulation_count)
	"""
	half_nfft = NFFT // 2
	samples_per_channel = half_nfft // NCHANNELS
	channel_data = np.zeros((NCHANNELS, samples_per_channel))

	start_time = time.time()
	for channel_idx in range(NCHANNELS):
		raw_bytes = fpga.read('q{:d}'.format(channel_idx + 1), samples_per_channel * 8, 0)
		channel_data[channel_idx, :] = struct.unpack('>{:d}Q'.format(samples_per_channel), raw_bytes)

	interleaved_spectrum = []
	for sample_idx in range(samples_per_channel):
		for channel_idx in range(NCHANNELS):
			interleaved_spectrum.append(channel_data[channel_idx, sample_idx])
	
	print(f'data read time: {time.time() - start_time}')

	return interleaved_spectrum, fpga.read_uint('acc_cnt')

def write_filename(state, acc_n):
    basename = str(datetime.fromtimestamp(time.time(), tz=timezone.utc).strftime(
        '%Y%m%d_%H%M%S') + f'_antenna{ANTENNA}_state{state}')

    return f"{basename}_{acc_n}" if SAVE_EACH_ACC else basename


def sum_spectrum(spectrum):
    return np.array([sum(x) for x in zip(*spectrum)], dtype=np.float64)


def save_data(dataDict, filename):
    """
    Save data into the appropriate directory.
    """
    global current_parent_dir, sub_dir_count, current_sub_dir_path, cycle_count, run_directory

    # Skip saving if SAVE_DATA is False
    if not SAVE_DATA:
        print(f"Data saving disabled. Would have saved: {filename}")
        return

    # Wait for storage to be mounted
    wait_for_storage('/media/peterson/INDURANCE')

    dirnames = next(os.walk(BASE_PATH))[1]
    dirname = dirnames[-1]

    # Determine the parent directory for this run
    if run_directory is not None:
        # Use run_directory as the parent directory for this run
        parent_dir_name = run_directory
    else:
        parent_dir_name = filename.split('_')[0]

    parent_dir_path = os.path.join(BASE_PATH, dirname, parent_dir_name)
    # Create the parent directory if it doesn't exist
    if parent_dir_name not in os.listdir(os.path.join(BASE_PATH, dirname)):
        os.mkdir(parent_dir_path)

    # Create a new subdirectory only after completing a cycle
    if cycle_count >= 1 or current_sub_dir_path is None:
        current_parent_dir = parent_dir_name
        current_sub_dir_path, sub_dir_count = get_sub_directory(
            parent_dir_path, sub_dir_count)
        cycle_count = 0  # Reset cycle count after creating a new subdirectory

    # Save the file in the appropriate directory
    file_path = os.path.join(current_sub_dir_path, f"{filename}.npy")
    np.save(file_path, dataDict, allow_pickle='False')
    print(f"Data saved to {file_path}")


def save_all_data(fpga, switch_value):
    global acc_n
    t_1 = time.time()
    # save volt + temp data
    # dataDict = volt_therm_lib.get_temp_volt_data()
    dataDict = {}
    dataDict["switch state"] = switch_value
    t_2 = time.time()
    if SAVE_EACH_ACC:
        # Save each individual accumulation
        acc_n = print_acc_cnt(fpga, acc_n)
        t_3 = time.time()
        s, cnt = get_vacc_data(fpga)
        t_4 = time.time()
        dataDict["spectrum"] = s
        filename = write_filename(switch_value, cnt)
        t_5 = time.time()
        if SAVE_DATA:
            save_data(dataDict, filename)

    else:
        spectra = {}
        while len(spectra) < 3:
            acc_n = print_acc_cnt(fpga, acc_n)
            s, cnt = get_vacc_data(fpga)
            spectra[cnt] = s

        spectra_list = [spectra[key] for key in spectra.keys()]

        # separating corrupt spectra from clean ones:
        # clean_spectra, corrupt_spectra = detect_periodic_noise(spectra_list)

        dataDict["spectrum"] = sum_spectrum(spectra_list)
        # dataDict["nspectra"] = len(clean_spectra)
        filename = write_filename(switch_value, 'average',)
        if SAVE_DATA:
            save_data(dataDict, filename)

        print(dataDict.keys())
        print(switch_value)
        print(dataDict["switch state"])
        # print("Number of Clean Spectra:" + dataDict["nspectra"])
    t_6 = time.time()

    # print(f'save_all_data: {t_2-t_1}, {t_3-t_2}, {t_4-t_3}, {t_5-t_4}, {t_6-t_5}')
    print(f'save_all_data: {t_2-t_1}, {t_6-t_2}')

    return dataDict, filename


def get_sub_directory(parent_dir_path, sub_dir_count):
    """
    Handles directory creation and naming for observing runs.

    Parameters:
                    base_path (str): Parent directory path where subdirectories are stored.
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
