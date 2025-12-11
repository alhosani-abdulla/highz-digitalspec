# =======================
# Imports
# =======================
import os
import time
import struct
import argparse
import re
import subprocess
import socket
from datetime import datetime, timezone

# Third-party imports
import numpy as np
import casperfpga
import rcal

# =======================
# CONFIGURATION
# =======================

# Paths and hardware configuration
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(script_dir, '../'))
# Update the subfolder and filename as needed:
CONFIG_PATH = os.path.join(repo_root, 'fpga_config', '03-11-2025', 'v26.fpg')
BASE_PATH = '/media/peterson'  # Path to external storage for data

# Acquisition and instrument parameters
FPGA_IP = '169.254.2.181'    # FPGA IP address (link local address when connected via ethernet)
ANTENNA = '1'                # Antenna identifier

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

# =======================
# End CONFIGURATION
# =======================

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

# Helper function to work around casperfpga RFDC status parsing bug
def get_adc_status(adc):
  """
  Get ADC status with workaround for casperfpga parsing bug.
  The RFSoC firmware returns format like "ADC0: Enabled 1, State: 15 PLL: 1"
  but casperfpga expects "ADC0: Enabled 1 State 15 PLL 1" (no colons in values).
  
  This function parses the response correctly and returns a formatted string.
  """
  import re
  
  try:
    # Get raw katcp transport and make request directly
    t = adc.parent.transport
    reply, informs = t.katcprequest(name='rfdc-status', request_timeout=t._timeout)
    
    status_str = "ADC/DAC Status:\n"
    
    for inform in informs:
      if inform.arguments:
        arg_str = inform.arguments[0].decode()
        # Parse: "ADC0: Enabled 1, State: 15 PLL: 1"
        info = arg_str.split(': ', 1)
        tile = info[0]
        
        if len(info) > 1:
          # Use regex to extract all key-value pairs
          rest = info[1]
          pattern = r'(\w+):\s*(\d+)|(\w+)\s+(\d+)'
          values = {}
          
          for match in re.finditer(pattern, rest):
            if match.group(1):  # "key: value" format
              k, v = match.group(1), match.group(2)
            else:  # "key value" format
              k, v = match.group(3), match.group(4)
            values[k] = int(v)
          
          # Format nicely
          value_str = ', '.join([f'{k}: {v}' for k, v in values.items()])
          status_str += f"  {tile}: {value_str}\n"
    
    return status_str
    
  except Exception as e:
    return f"Could not read ADC status: {e}\n"

def discover_fpga_address(hardcoded_ip=FPGA_IP, hostname_hint='rfsoc', timeout=5):
  """
  Discover FPGA address using multiple methods with fallbacks.
  
  Tries in order:
    1. Hostname hints ('rfsoc', 'localhost.localdomain', etc.)
    2. Hardcoded IPv4 address with connectivity test
    3. IPv6 link-local address discovery
  
  Parameters:
    hardcoded_ip (str): Fallback IPv4 address (default: FPGA_IP config)
    hostname_hint (str): Primary hostname to try resolving (e.g., 'rfsoc', 'localhost.localdomain')
    timeout (int): Timeout in seconds for connection attempts
    
  Returns:
    str: Working IP address for FPGA, or None if all methods fail
  """
  
  # Build list of hostnames to try
  hostnames_to_try = []
  if hostname_hint:
    hostnames_to_try.append(hostname_hint)
  # Always try common RFSoC hostnames
  hostnames_to_try.extend(['rfsoc', 'localhost.localdomain', 'localhost'])
  
  # Remove duplicates while preserving order
  hostnames_to_try = list(dict.fromkeys(hostnames_to_try))
  
  # Method 1: Try hostname resolution
  for hostname in hostnames_to_try:
    try:
      resolved_ip = socket.gethostbyname(hostname)
      print(f"✓ Resolved hostname '{hostname}' to {resolved_ip}")
      
      # Quick connectivity test
      try:
        socket.create_connection((resolved_ip, 7147), timeout=timeout)  # KATCP default port
        print(f"✓ FPGA responsive at {resolved_ip}")
        return resolved_ip
      except (socket.timeout, ConnectionRefusedError, OSError):
        print(f"✗ {resolved_ip} not responding on KATCP port")
    except socket.gaierror:
      print(f"✗ Could not resolve hostname '{hostname}'")
  
  # Method 2: Try hardcoded IPv4 address
  print(f"Attempting hardcoded IPv4 address: {hardcoded_ip}")
  try:
    socket.create_connection((hardcoded_ip, 7147), timeout=timeout)
    print(f"✓ FPGA responsive at {hardcoded_ip}")
    return hardcoded_ip
  except (socket.timeout, ConnectionRefusedError, OSError) as e:
    print(f"✗ Could not connect to {hardcoded_ip}: {e}")
  
  # Method 3: Try to find IPv6 link-local address via neighbor discovery
  print("Attempting to discover IPv6 link-local address...")
  try:
    # Get list of network interfaces
    result = subprocess.run(
      ['ip', 'link', 'show'],
      capture_output=True,
      text=True,
      timeout=timeout
    )
    
    # Extract interface names (skip lo)
    interfaces = re.findall(r'^(\d+):\s+(\S+):', result.stdout, re.MULTILINE)
    interfaces = [iface for _, iface in interfaces if iface != 'lo' and not iface.startswith('docker')]
    
    if interfaces:
      # Try to discover IPv6 neighbors on each interface
      for iface in interfaces:
        try:
          # Use ping with IPv6 link-local all-nodes multicast to trigger neighbor discovery
          subprocess.run(
            ['ping', '-6', '-c', '1', 'ff02::1%' + iface],
            capture_output=True,
            timeout=2
          )
          
          # Now query the neighbor table
          result = subprocess.run(
            ['ip', 'neigh', 'show'],
            capture_output=True,
            text=True,
            timeout=timeout
          )
          
          # Look for fe80:: addresses
          ipv6_pattern = r'(fe80::[a-f0-9:]+)\s+dev\s+' + iface
          matches = re.findall(ipv6_pattern, result.stdout)
          
          for ipv6_addr in matches:
            # For link-local, must include interface scope
            addr_with_scope = ipv6_addr + '%' + iface
            print(f"  Trying IPv6 link-local: {addr_with_scope}")
            try:
              socket.create_connection((ipv6_addr, 7147, 0, iface), timeout=timeout)
              print(f"✓ FPGA responsive at {ipv6_addr}")
              return ipv6_addr
            except (socket.timeout, ConnectionRefusedError, OSError, TypeError):
              # TypeError occurs if socket doesn't support interface scope this way
              continue
        except Exception:
          continue
  except Exception as e:
    print(f"✗ IPv6 discovery failed: {e}")
  
  return None

def initialize_fpga():
  """
  Initialize the FPGA and ADC, program the bitstream, and set up clocks.
  Returns the fpga and adc objects.
  """
  print(datetime.fromtimestamp(time.time(), tz=timezone.utc))
  rcal.gpio_switch(0, 2)
  
  # Discover FPGA address with retries
  max_retries = 5
  retry_delay = 5  # seconds
  fpga_addr = None
  
  for attempt in range(max_retries):
    print(f"\n=== FPGA Connection Attempt {attempt + 1}/{max_retries} ===")
    fpga_addr = discover_fpga_address()
    
    if fpga_addr:
      print(f"✓ Found FPGA at {fpga_addr}")
      break
    
    if attempt < max_retries - 1:
      print(f"✗ FPGA not found. Retrying in {retry_delay} seconds...")
      time.sleep(retry_delay)
  
  if not fpga_addr:
    print("✗ Failed to discover FPGA after all attempts")
    print("Please check:")
    print("  - FPGA is powered on and connected via ethernet")
    print("  - Network connection is active")
    print("  - Firewall is not blocking KATCP port 7147")
    time.sleep(180)
    os.system('sudo reboot')
  
  try:
    print(f'Running Script ...')
    # Connect to the FPGA using discovered address
    fpga = casperfpga.CasperFpga(fpga_addr)
    fpga.upload_to_ram_and_program(CONFIG_PATH)

    adc = fpga.adcs['rfdc']
    adc.init()
    # Use workaround function to read ADC status instead of adc.status()
    print(get_adc_status(adc))

    c = adc.show_clk_files()
    adc.progpll('lmk', c[1])
    adc.progpll('lmx', c[0])

  except Exception as e:
    print(f'An error occurred during FPGA initialization: {e}')
    time.sleep(180)
    os.system('sudo reboot')

  time.sleep(15)  # Let clocks adjust

  # Set accumulation length
  fpga.write_int('acc_len', ACC_LENGTH)
  print('Initialization complete. Taking data...')
  return fpga, adc

def main():
  global acc_n, cycle_count, sub_dir_count, current_parent_dir, current_sub_dir_path, run_directory

  # Initialize global variables
  cycle_count = 0
  sub_dir_count = 0
  current_parent_dir = None # name of the current parent directory
  current_sub_dir_path = None  # Path to the current subdirectory

  # Initialize FPGA and ADC
  fpga, adc = initialize_fpga()

  # Initial GPIO/Switch state
  rcal.gpio_switch(1,SWITCH_DELAY)
  
  # Parse command line arguments
  parser = argparse.ArgumentParser(description='high-z digital spectrometer')
  parser.add_argument('--state', default=None, type=int, help='switch state (0-10)')
  parser.add_argument('--run_directory', default=None, help='parent directory name for this observing run')
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
      for n in range(100): #collect 100 spectra in the specified state
        data, name = save_all_data(fpga, switch_value=input_state)
      print(f'Completed data collection for state {input_state}. Exiting.')
      break
    else:
      #Digital Spectrometer Calibaration Sweep.
      for s in range(1,8): # Calibration states 1-7
        spectra_n = CAL_ACC_N
        if s == 2: # switching to 6" shorted
          rcal.gpio_switch(s, SWITCH_DELAY)
          spectra_n = CAL_ACC_N + FB_N  # extra spectra for filter bank calibration
        else:
          rcal.gpio_switch(s, SWITCH_DELAY) # Switching Calibration States
        
        for n in range(spectra_n):
          data, name = save_all_data(fpga, switch_value=s)

      #Observing with the Antenna - collecting ant_acc_n spectras 
      state = 0
      rcal.gpio_switch(state, SWITCH_DELAY)
      for cnt in range(ANT_ACC_N):
        data, name = save_all_data(fpga, switch_value=state)

    # Increment the cycle count after one full calibration + observation cycle
    cycle_count += 1

def print_acc_cnt(fpga, last_acc_n):
  acc_n = fpga.read_uint('acc_cnt')
  if acc_n > last_acc_n: 
    last_acc_n = acc_n

  c = 1
  while acc_n == last_acc_n:
    acc_n = fpga.read_uint('acc_cnt')
    c += 1
  
  #c = 0
  #start_time = time.time()
  while False:
    current_cnt = fpga.read_uint('acc_cnt')
    current_time = time.time()
    c += 1
    if current_cnt > acc_n:
      increment_time = current_time - start_time
      print(f'Time for increment: {increment_time} seconds {c}')
    
      start_time = current_time
      acc_n = current_cnt
      c = 0
  print(acc_n, c)
  return acc_n
  
def get_vacc_data(fpga):
  half_nfft = NFFT//2
  chunk = half_nfft//NCHANNELS
  raw = np.zeros((NCHANNELS, chunk))
  
  start_time = time.time()
  for i in range(NCHANNELS):
    q = fpga.read('q{:d}'.format(i+1), chunk * 8, 0)
    raw[i,:] = struct.unpack('>{:d}Q'.format(chunk), q)

  interleave_q = []
  for i in range(chunk):
    for j in range(NCHANNELS):
      interleave_q.append(raw[j,i])
  print(f'data read time: {time.time() - start_time}')

  return interleave_q, fpga.read_uint('acc_cnt')

def write_filename(state, acc_n):
  basename = str(datetime.fromtimestamp(time.time(), tz=timezone.utc).strftime('%Y%m%d_%H%M%S') + f'_antenna{ANTENNA}_state{state}')
  
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
    current_sub_dir_path, sub_dir_count = get_sub_directory(parent_dir_path, sub_dir_count)
    cycle_count = 0  # Reset cycle count after creating a new subdirectory

  # Save the file in the appropriate directory
  file_path = os.path.join(current_sub_dir_path, f"{filename}.npy")
  np.save(file_path, dataDict, allow_pickle='False')
  print(f"Data saved to {file_path}")

def save_all_data(fpga, switch_value):
  global acc_n
  t_1 = time.time()
  #save volt + temp data
  #dataDict = volt_therm_lib.get_temp_volt_data()
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
    
    #separating corrupt spectra from clean ones:
    #clean_spectra, corrupt_spectra = detect_periodic_noise(spectra_list)
    
    dataDict["spectrum"] = sum_spectrum(spectra_list)
    #dataDict["nspectra"] = len(clean_spectra)
    filename = write_filename(switch_value, 'average',)
    if SAVE_DATA:
      save_data(dataDict, filename)

    print(dataDict.keys())
    print(switch_value)
    print(dataDict["switch state"])
    #print("Number of Clean Spectra:" + dataDict["nspectra"])
  t_6 = time.time()

  #print(f'save_all_data: {t_2-t_1}, {t_3-t_2}, {t_4-t_3}, {t_5-t_4}, {t_6-t_5}')
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
