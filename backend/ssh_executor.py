#!/usr/bin/env python3
"""
SSH communication module for AIConsole
Handles SSH connection to network devices (Cisco, etc)
"""

import paramiko
import time
import sys
import json
import socket

class SSHExecutor:
    def __init__(self, host='192.168.1.10', port=22, username='admin', password='admin123', timeout=10):
        """Initialize SSH connection parameters"""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.client = None
        self.shell = None
        self.authenticated = False
    
    def connect(self):
        """Establish SSH connection and authenticate"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                look_for_keys=False,
                allow_agent=False
            )
            
            self.shell = self.client.invoke_shell()
            time.sleep(1)
            
            if self.shell.recv_ready():
                self.shell.recv(4096)
            
            self.authenticated = True
            return True
            
        except paramiko.AuthenticationException:
            print(f"Authentication failed for {self.username}@{self.host}")
            return False
        except paramiko.SSHException as e:
            print(f"SSH error: {e}")
            return False
        except socket.timeout:
            print(f"Connection timeout to {self.host}:{self.port}")
            return False
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def get_current_prompt(self):
        """Get the current prompt from the device"""
        if not self.shell:
            return "Switch>"
        
        try:
            self.shell.send("\n")
            time.sleep(0.5)
            
            response = ""
            if self.shell.recv_ready():
                response = self.shell.recv(4096).decode('utf-8', errors='ignore')
            
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            if lines:
                return lines[-1]
            
            return "Switch>"
        except:
            return "Switch>"
    
    def send_command(self, command):
        """Send single command and get response"""
        if not self.shell:
            return "No connection established"
        
        try:
            if self.shell.recv_ready():
                self.shell.recv(4096)
            
            self.shell.send(f"{command}\n")
            
            response = ""
            max_wait = 3
            idle_threshold = 0.3
            start_time = time.time()
            last_data_time = start_time
            
            while time.time() - start_time < max_wait:
                if self.shell.recv_ready():
                    data = self.shell.recv(4096)
                    response += data.decode('utf-8', errors='ignore')
                    last_data_time = time.time()
                    
                    if any(marker in response[-50:] for marker in ['#', '>', 'Switch', 'Router']):
                        time.sleep(0.1)
                        if not self.shell.recv_ready():
                            break
                else:
                    if response and (time.time() - last_data_time) > idle_threshold:
                        break
                    time.sleep(0.05)
            
            return response.strip() if response else "No response from device"
        except Exception as e:
            return f"Command error: {e}"
    
    def execute_commands(self, commands_string):
        """Execute multiple commands from string"""
        if not self.connect():
            return {"success": False, "error": "Failed to connect via SSH"}
        
        commands = [cmd.strip() for cmd in commands_string.split('\n') if cmd.strip()]
        results = []
        
        try:
            current_prompt = self.get_current_prompt()
            
            for command in commands:
                response = self.send_command(command)
                results.append({
                    "command": command,
                    "response": response
                })
                time.sleep(0.1)
            
            return {
                "success": True,
                "results": results,
                "initial_prompt": current_prompt
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
        
        finally:
            if self.client:
                self.client.close()

def main():
    """Main function for CLI usage"""
    if len(sys.argv) < 5:
        print("Usage: python ssh_executor.py '<commands>' <host> <username> <password>")
        sys.exit(1)
    
    commands = sys.argv[1]
    host = sys.argv[2]
    username = sys.argv[3]
    password = sys.argv[4]
    
    executor = SSHExecutor(host=host, username=username, password=password)
    result = executor.execute_commands(commands)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
