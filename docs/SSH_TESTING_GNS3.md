# SSH Connection Testing with GNS3

## Prerequisites

1. **Install GNS3**
   - Download from https://www.gns3.com/software/download
   - Install GNS3 VM (recommended) or use local installation
   - Requires VMware Workstation/VirtualBox

2. **Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Cisco IOS Image**
   - Obtain Cisco IOSv or IOU/IOL image
   - Import to GNS3: Edit > Preferences > Dynamips > IOS Routers > New

## GNS3 Setup for SSH Testing

### Step 1: Create Network Topology

1. Open GNS3
2. Drag a Cisco router/switch to workspace
3. Drag a "Cloud" node to workspace
4. Connect router interface (e.g., Gi0/0) to Cloud

### Step 2: Configure Cloud Node

1. Right-click Cloud > Configure
2. Select your host's network adapter (e.g., Ethernet or Wi-Fi adapter)
3. This bridges GNS3 device to your host machine network

### Step 3: Start Device

1. Right-click router > Start
2. Wait for device to boot (green light)
3. Right-click router > Console

### Step 4: Configure SSH on Device

```cisco
enable
configure terminal

hostname Router1
ip domain-name lab.local

username admin privilege 15 secret admin123

crypto key generate rsa modulus 2048

line vty 0 4
 login local
 transport input ssh
 exit

interface GigabitEthernet0/0
 ip address 192.168.1.10 255.255.255.0
 no shutdown
 exit

end
write memory
```

**Important Notes:**
- Change `192.168.1.10` to match your network subnet
- If your PC is on 10.0.0.x, use 10.0.0.10
- Username: admin
- Password: admin123

### Step 5: Verify Connectivity from Host

```bash
# Ping the device
ping 192.168.1.10

# Test SSH manually
ssh admin@192.168.1.10
```

### Step 6: Test with AIConsole

1. Start backend server:
   ```bash
   cd backend
   node server.js
   ```

2. Start frontend:
   ```bash
   cd frontend
   python app.py
   ```

3. In AIConsole:
   - Select "SSH" from connection dropdown
   - Click "Conectar"
   - Enter credentials:
     - Host: 192.168.1.10
     - Username: admin
     - Password: admin123
   - Should see "CONEXION SSH ESTABLECIDA"

4. Test commands:
   - Putty Mode: `show version`
   - AI Mode: "show me the version"

## Troubleshooting

### Cannot Ping Device
- Verify Cloud is connected to correct adapter
- Check interface is "no shutdown"
- Verify IP addressing matches your subnet

### SSH Connection Refused
- Verify SSH is enabled: `show ip ssh`
- Check crypto keys: `show crypto key mypubkey rsa`
- Verify line vty: `show running-config | section line vty`

### Authentication Failed
- Double-check username/password
- Try: `show running-config | include username`
- Re-create user if needed

### Python Module Not Found
```bash
pip install paramiko
```

## Alternative: Use Switch Instead of Router

For Layer 2 switch simulation:

```cisco
enable
configure terminal

hostname Switch1
ip domain-name lab.local

username admin privilege 15 secret admin123
crypto key generate rsa modulus 2048

interface vlan 1
 ip address 192.168.1.10 255.255.255.0
 no shutdown
 exit

line vty 0 15
 login local
 transport input ssh
 exit

end
write memory
```

## Network Diagram Example

```
┌──────────────┐
│  Your PC     │
│  (Host)      │
└──────┬───────┘
       │
   [Cloud Node]
       │
       │ Gi0/0
┌──────┴───────┐
│ Cisco Router │
│ 192.168.1.10 │
│   (GNS3)     │
└──────────────┘
```

## Quick Test Script

Save as `test_ssh.py`:

```python
#!/usr/bin/env python3
import paramiko

host = "192.168.1.10"
username = "admin"
password = "admin123"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=username, password=password, timeout=10)
    
    shell = client.invoke_shell()
    shell.send("show version\n")
    
    import time
    time.sleep(2)
    
    output = shell.recv(4096).decode('utf-8')
    print(output)
    
    client.close()
    print("\nSSH connection successful!")
    
except Exception as e:
    print(f"Error: {e}")
```

Run: `python test_ssh.py`
