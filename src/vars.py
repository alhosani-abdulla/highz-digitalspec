# This file contains global variables and configuration settings 
# for the spectrometer acquisition.
# It is imported by other modules to access these shared settings.
import os

# Path to the FPGA configuration file (update as needed)
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(script_dir, '../'))

# Update the subfolder and filename as needed:
CONFIG_PATH = os.path.join(repo_root, 'fpga_config', '03-11-2025', 'v26.fpg')
BASE_PATH = '/media/peterson'  # Path to external storage for data

# Acquisition and instrument parameters
# FPGA IP address (link local address when connected via ethernet)
FPGA_IP = '169.254.2.181'

# Default antenna identifier (update as needed)
ANTENNA = '4'

# FFT parameters
ACC_LENGTH = 8750 * 2        # Accumulation length (see notes below)
NCHANNELS = 4                # Number of channels
NFFT = 32768                 # FFT length

# Calibration and observation parameters
CAL_ACC_N = 10                # Number of spectra per calibration state per cycle
ANT_ACC_N = 10               # Number of spectra for antenna state per cycle
FB_N = 7                      # Number of spectra for filter bank calibration
SAVE_EACH_ACC = False         # True: save each accumulation, False: sum accumulations
SAVE_DATA = True              # True: save data to disk, False: run without saving

# The time in seconds for one accumulation. Skips one accumulation when switching states.
SWITCH_DELAY = ACC_LENGTH * 3 / 100000