# Switch Configuration Project

## Overview

This project demonstrates the AIConsole system's ability to perform complete, multi-step network configurations on real Cisco switches. It applies a production-ready configuration suitable for a small office environment.

## What This Project Does

The script executes **7 automated configuration steps** that transform a factory-default switch into a fully configured network device:

### Configuration Steps

1. **Basic Settings**
   - Sets hostname to `SW-Office-Main`
   - Configures security banner: "Authorized Access Only"

2. **VLAN Creation**
   - VLAN 10: Employees (for staff workstations)
   - VLAN 20: Guests (for visitor access)
   - VLAN 30: Servers (for infrastructure)
   - VLAN 99: Management (for switch administration)

3. **Management Access**
   - Assigns IP 192.168.99.1/24 to VLAN 99
   - Enables remote management capability

4. **Employee Port Assignment**
   - Configures ports GigabitEthernet 0/1-10
   - Assigns to VLAN 10 (Employees)
   - Sets to access mode

5. **Guest Port Assignment**
   - Configures ports GigabitEthernet 0/11-15
   - Assigns to VLAN 20 (Guests)
   - Sets to access mode

6. **Port Security**
   - Enables security on GigabitEthernet 0/1
   - Limits to 2 MAC addresses
   - Sets violation action to shutdown

7. **Configuration Persistence**
   - Saves running-config to startup-config
   - Ensures configuration survives reboots

## Why This Matters

### Network Segmentation
VLANs separate network traffic, improving:
- **Security**: Employees can't access server VLAN
- **Performance**: Broadcast domains are isolated
- **Management**: Easier troubleshooting and policy enforcement

### Port Security
Prevents unauthorized devices from connecting:
- Detects MAC address changes
- Automatically disables compromised ports
- Protects against MAC flooding attacks

### Management Access
Dedicated management VLAN provides:
- Isolated administrative access
- Predictable IP addressing
- Secure network management

## Technical Details

### Protocol Used
- Serial communication over USB (9600 baud)
- Direct Cisco IOS command execution
- Real-time error detection

### AI Integration
- Natural language prompts converted to Cisco IOS commands
- Context-aware command generation
- Automatic mode detection (User/Privileged/Config)

### Error Handling
- Detects invalid commands
- Reports incomplete commands
- Allows user intervention on failures
- Provides detailed error messages

## File Structure

```
tests/switch_project/
├── configure_switch.py    # Main configuration script
└── README.md             # This documentation
```

## Prerequisites

1. **Hardware**
   - Cisco switch connected via USB serial cable
   - Device path: `/dev/ttyUSB0`
   - Switch must be accessible (no password or empty password)

2. **Software**
   - AIConsole backend running on port 3000
   - Python 3.x with `requests` module
   - Serial communication configured

3. **Network**
   - Backend server accessible at `http://localhost:3000`
   - No rate limiting on AI models (or use rule-based fallback)

## Execution

### Step 1: Verify Prerequisites

Check that the backend is running:
```bash
ps aux | grep "node.*server.js"
```

If not running, start it:
```bash
cd /home/arthur/Escritorio/AIConsole/backend
node server.js &
```

### Step 2: Run the Configuration Script

```bash
cd /home/arthur/Escritorio/AIConsole/tests/switch_project
python3 configure_switch.py
```

### Step 3: Monitor Progress

The script will:
1. Display all planned configurations
2. Wait for your confirmation (press ENTER)
3. Execute each step sequentially
4. Show generated commands for each step
5. Display switch responses
6. Report success/failure for each step
7. Provide final statistics

### Step 4: Review Results

At the end, you'll see:
- Total execution time
- Number of successful steps
- Number of failed steps
- Overall success rate

## Expected Output

```
======================================================================
  SWITCH CONFIGURATION PROJECT: OFFICE NETWORK
======================================================================

Project: Complete switch configuration for small office network
Objective: Configure VLANs, security, and management access
Switch: SW-Office-Main
Total steps: 7

Configurations to be applied:
   - Hostname and security banner
   - 4 VLANs (Employees, Guests, Servers, Management)
   - Management IP address (192.168.99.1)
   - 15 ports assigned to VLANs
   - Port security on critical ports
   - Save configuration to NVRAM

Press ENTER to start configuration...

[STEP 1/7] Configure basic switch settings
----------------------------------------------------------------------
Prompt: Configure hostname to SW-Office-Main and set banner...
Sending to switch...

Generated commands:
    configure terminal
    hostname SW-Office-Main
    banner motd # Authorized Access Only #
    end

Executed on switch: YES
Status: SUCCESS - No errors detected

Step 1 completed successfully

[... continues for all 7 steps ...]

======================================================================
  CONFIGURATION SUMMARY
======================================================================

Total time: 45.3 seconds
Successful steps: 7/7
Failed steps: 0/7
Success rate: 100.0%

PROJECT COMPLETED SUCCESSFULLY!

Your switch now has:
   + Configured hostname
   + 4 VLANs for network segmentation
   + Management IP address
   + 15 ports assigned to VLANs
   + Port security enabled
   + Configuration saved to NVRAM
```

## Troubleshooting

### Script hangs or times out
- Check that switch is connected and powered on
- Verify serial cable is properly connected
- Ensure backend server is responding

### Commands fail with "Invalid input"
- Switch may not support certain commands (Layer 2 vs Layer 3)
- Check Cisco IOS version compatibility
- Review switch model capabilities

### AI rate limiting errors
- System will fall back to rule-based command generation
- Wait 60 seconds between runs if using free AI tier
- Consider upgrading to paid AI models for unlimited access

### Configuration not saved
- Ensure step 7 completes successfully
- Manually save with: `copy running-config startup-config`
- Check NVRAM space with: `show flash:`

## Reverting Configuration

To restore factory defaults:

```cisco
enable
erase startup-config
reload
```

**WARNING**: This will erase all configurations. The switch will reboot.

## Customization

Edit `configure_switch.py` to modify:

- **Hostname**: Change `SWITCH_NAME` variable
- **VLANs**: Modify VLAN numbers and names in step 2
- **IP Address**: Update management IP in step 3
- **Port Ranges**: Adjust interface ranges in steps 4-5
- **Security Settings**: Modify port-security parameters in step 6

## Learning Outcomes

After running this project, you will understand:

1. **VLAN Configuration**: How to create and assign VLANs
2. **Port Assignment**: How to configure switch ports for specific VLANs
3. **Security Features**: How port-security protects network access
4. **Management Access**: How to configure switch management interfaces
5. **Configuration Persistence**: How to save configurations permanently
6. **Automation**: How AI can automate complex network configurations

## Next Steps

Consider extending this project by:

- Adding trunk ports for inter-VLAN routing
- Configuring Spanning Tree Protocol (STP)
- Setting up SSH access for remote management
- Implementing access control lists (ACLs)
- Configuring DHCP snooping for security
- Adding logging and monitoring

## Support

For issues or questions:
- Check backend logs: `/tmp/server.log`
- Review switch console output
- Verify serial connection with: `screen /dev/ttyUSB0 9600`
- Ensure Python dependencies are installed

## License

This project is part of the AIConsole system.
