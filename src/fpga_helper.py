import socket
import struct
import subprocess
import time
import os
import re
import numpy as np
import casperfpga
from datetime import datetime, timezone

from vars import *
import rcal

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
        reply, informs = t.katcprequest(
            name='rfdc-status', request_timeout=t._timeout)

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
                    value_str = ', '.join(
                        [f'{k}: {v}' for k, v in values.items()])
                    status_str += f"  {tile}: {value_str}\n"

        return status_str

    except Exception as e:
        return f"Could not read ADC status: {e}\n"

def initialize_fpga() -> tuple:
    """
    Initialize the FPGA and ADC, gpio switch to state 0, discover FPGA address, 
    program the bitstream, and set up clocks.

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
                socket.create_connection(
                    (resolved_ip, 7147), timeout=timeout)  # KATCP default port
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
        interfaces = re.findall(r'^(\d+):\s+(\S+):',
                                result.stdout, re.MULTILINE)
        interfaces = [iface for _, iface in interfaces if iface !=
                      'lo' and not iface.startswith('docker')]

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
                            socket.create_connection(
                                (ipv6_addr, 7147, 0, iface), timeout=timeout)
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

def get_acc_cnt(fpga, last_acc_n):
    """Wait for the FPGA to update the accumulation count, indicating new data is ready.
    
    Parameters:
        fpga: FPGA object to read from
        last_acc_n: The last known accumulation count to compare against.
        
    Returns:
        tuple: (new_acc_n, loop_count) where new_acc_n is the updated accumulation count and 
        loop_count is the number of iterations performed"""
    acc_n = fpga.read_uint('acc_cnt')
    if acc_n > last_acc_n: 
        last_acc_n = acc_n

    c = 1
    while acc_n == last_acc_n:
        acc_n = fpga.read_uint('acc_cnt')
        c += 1
    
    return acc_n, c