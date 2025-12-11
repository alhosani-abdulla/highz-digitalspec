# RFSoC Hostname Configuration

This guide explains how to configure the RFSoC with a hostname so it can be discovered automatically by the Python discovery function.

## Why Set a Hostname?

By default, the code connects to the RFSoC using a hardcoded IPv4 link-local address: `169.254.2.181`. This can fail if:
- The FPGA doesn't get the expected link-local address
- Network conditions change
- The device is on a different network

With a hostname, the Python code can:
1. Try hostname resolution first (most reliable)
2. Fall back to hardcoded IP if needed
3. Try IPv6 link-local discovery as last resort

## Setup Steps

### Option 1: SSH into RFSoC (Recommended)

1. **Connect RFSoC to Pi via ethernet**

2. **SSH into the RFSoC:**
   ```bash
   ssh root@169.254.2.181
   ```
   Default password: `root`

3. **Run the hostname configuration:**
   ```bash
   bash < <(curl -s https://raw.githubusercontent.com/alhosani-abdulla/highz-digitalspec/main/scripts/rfsoc_set_hostname.sh)
   ```
   
   Or manually on the RFSoC:
   ```bash
   echo "rfsoc" > /etc/hostname
   echo "127.0.0.1 rfsoc" >> /etc/hosts
   hostname rfsoc
   ```

4. **Verify:**
   ```bash
   hostname
   ```

### Option 2: Serial Connection

If SSH is not available, use a serial/USB console connection to the RFSoC and run the same commands.

### Option 3: Manual PetaLinux Configuration

If the RFSoC is running PetaLinux, you can also set hostname through the system configuration:

1. Connect to the RFSoC
2. Edit `/etc/hostname`:
   ```bash
   echo "rfsoc" > /etc/hostname
   ```

## Verify Setup

From the Pi, test hostname resolution:

```bash
ping rfsoc
```

Or from the spectrometer script, it will automatically use the hostname:

```bash
cd /home/peterson/highz-digitalspec
pipenv run python src/run_spectrometer.py
```

The discovery function will print:
```
✓ Resolved hostname 'rfsoc' to 169.254.2.181
✓ FPGA responsive at 169.254.2.181
```

## Python Discovery Priority

The discovery function tries in this order:

1. **Hostname resolution** - `rfsoc` → IP address
2. **Hardcoded IPv4** - `169.254.2.181` with connectivity test
3. **IPv6 link-local discovery** - Scan for link-local addresses

If hostname is configured, it will be found first, which is the most reliable method.

## Troubleshooting

If hostname is not resolving:

1. **Verify hostname on RFSoC:**
   ```bash
   ssh root@169.254.2.181
   hostname
   ```

2. **Check /etc/hosts:**
   ```bash
   ssh root@169.254.2.181
   cat /etc/hosts
   ```

3. **Test mDNS (if available):**
   ```bash
   # From Pi:
   avahi-resolve-address 169.254.2.181
   ```

4. **Force update:**
   ```bash
   ssh root@169.254.2.181
   hostname rfsoc
   ```
