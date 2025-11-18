# Ethernet Network Configuration for RFSoC Link-Local Communication

## Quick Reference

**File:** `/home/peterson/highz-digitalspec/NETWORK_CONFIGURATION.md`

**Purpose:** Document the NetworkManager configuration for persistent link-local Ethernet connectivity to the RFSoC FPGA.

## Current Configuration

The Raspberry Pi's eth0 interface is configured to automatically assign a link-local IPv4 address compatible with the RFSoC's network:

| Setting | Value | Purpose |
|---------|-------|---------|
| Connection Name | `eth0` | NetworkManager profile name |
| Interface | `eth0` | Ethernet interface |
| IPv4 Method | `manual` | Use static IP instead of DHCP |
| IPv4 Address | `169.254.1.1/16` | Link-local address compatible with RFSoC |
| Autoconnect | `yes` | Automatically activate on boot |
| Autoconnect Priority | `100` | High priority for connection ordering |

## Active Configuration Commands

View the current configuration:
```bash
nmcli connection show eth0
```

View just the network settings:
```bash
nmcli connection show eth0 | grep -E "ipv4|autoconnect"
```

Check the actual IPv4 address assigned:
```bash
ip addr show eth0
```

## Verifying Connectivity

Test RFSoC reachability:
```bash
ping -c 2 169.254.2.181
```

Test FPGA connection:
```bash
cd ~/highz-digitalspec
pipenv run python -c "import casperfpga; fpga = casperfpga.CasperFpga('169.254.2.181', timeout=10); print('FPGA Connected!')"
```

Run the spectrometer:
```bash
TakeSpecs  # Uses the alias configured in scripts/highz_alias.sh
# Or:
cd ~/highz-digitalspec && pipenv run python src/run_spectrometer.py --state 0
```

## Modifying the Configuration

### Change IPv4 Address
```bash
sudo nmcli connection modify eth0 ipv4.addresses 169.254.2.1/16
sudo nmcli connection reload
```

### Disable Autoconnect
```bash
sudo nmcli connection modify eth0 connection.autoconnect no
sudo nmcli connection reload
```

### Switch Back to DHCP
```bash
sudo nmcli connection modify eth0 ipv4.method auto
sudo nmcli connection reload
```

### View Full Configuration Details
```bash
nmcli connection show eth0
```

## Manual/Temporary Configuration (One-Session Only)

If you need to quickly configure eth0 without modifying NetworkManager:
```bash
sudo ip addr add 169.254.1.1/16 dev eth0
```

**Note:** This does NOT persist across reboots. Use the NetworkManager configuration above for permanent settings.

## Troubleshooting

### eth0 Shows Only IPv6 Address
Indicates that the NetworkManager configuration is not active. Reload it:
```bash
sudo nmcli connection up eth0
sleep 2
ip addr show eth0
```

### Cannot Ping RFSoC
1. Check eth0 has the IPv4 address:
   ```bash
   ip addr show eth0 | grep "inet "
   ```
   Should show: `inet 169.254.1.1/16`

2. Check RFSoC is powered and reachable via serial console (see main README)

3. If recently modified, reload NetworkManager:
   ```bash
   sudo nmcli connection reload
   sudo nmcli connection up eth0
   ```

### FPGA Connection Error
```
ConnectionError: Could not connect to host 169.254.2.181
```

This usually means eth0 doesn't have the IPv4 address. Run:
```bash
sudo nmcli connection reload
sudo nmcli connection up eth0
```

## Background: Why Link-Local Addressing?

The RFSoC FPGA boots with a link-local IPv4 address (169.254.2.181) when:
- No DHCP server is present on the network
- The board hasn't been pre-configured with a static IP
- It's directly connected to another device (isolated link)

The Raspberry Pi must also have a compatible link-local address in the same /16 subnet (169.254.0.0/16) to communicate. This is why eth0 is configured as 169.254.1.1/16.

## NetworkManager File Location

The connection profile is stored at:
```
/etc/NetworkManager/system-connections/eth0.nmconnection
```

You can view or edit it directly (requires root):
```bash
sudo cat /etc/NetworkManager/system-connections/eth0.nmconnection
```

But **use the `nmcli` commands above** instead of editing directly, as NetworkManager handles format validation and permission management.

## Related Documentation

- Main README: `/home/peterson/highz-digitalspec/README.md` - See "Troubleshooting" section
- FPGA Troubleshooting: Serial console connection guide in main README
- Spectrometer Usage: See main README "Usage" section

## Contact & Debugging

If you encounter issues:
1. Check the troubleshooting section above
2. Review the main README troubleshooting section
3. Verify RFSoC is booted (use serial console)
4. Ensure both devices have compatible link-local addresses in 169.254.0.0/16 subnet
