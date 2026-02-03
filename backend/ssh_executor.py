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
import re

class SSHExecutor:
    def __init__(self, host='192.168.1.10', port=22, username='admin', password='admin123', timeout=30):
        """Initialize SSH connection parameters"""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.client = None
        self.shell = None
        self.authenticated = False
        self.current_mode = 'unknown'
        self.last_error = None
    
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
            time.sleep(0.5)
            
            initial = self._read_until_prompt(timeout=5)
            
            if not self._has_prompt(initial):
                self.last_error = "No prompt detected after connection"
                return False
            
            if not self._ensure_privileged_mode():
                self.last_error = "Failed to enter privileged mode"
                return False
            
            self.authenticated = True
            return True
            
        except paramiko.AuthenticationException:
            self.last_error = f"Authentication failed for {self.username}@{self.host}"
            return False
        except paramiko.SSHException as e:
            self.last_error = f"SSH error: {e}"
            return False
        except socket.timeout:
            self.last_error = f"Connection timeout to {self.host}:{self.port}"
            return False
        except Exception as e:
            self.last_error = f"Connection error: {e}"
            return False
    
    def _read_until_prompt(self, timeout=5):
        """Read until we see a prompt marker"""
        buffer = ""
        start = time.time()
        
        while time.time() - start < timeout:
            if self.shell.recv_ready():
                chunk = self.shell.recv(4096).decode('utf-8', errors='ignore')
                buffer += chunk
                
                if self._has_prompt(buffer[-100:]):
                    time.sleep(0.1)
                    if self.shell.recv_ready():
                        buffer += self.shell.recv(4096).decode('utf-8', errors='ignore')
                    return buffer
            
            time.sleep(0.05)
        
        return buffer
    
    def _has_prompt(self, text):
        """Check if text contains a valid prompt"""
        patterns = [
            r'[\w-]+>',
            r'[\w-]+#',
            r'\(config[^)]*\)#'
        ]
        return any(re.search(pattern, text) for pattern in patterns)
    
    def _ensure_privileged_mode(self):
        """Ensure we're in privileged mode (#)"""
        current = self.get_current_prompt()
        
        if '>' in current and '#' not in current:
            self.shell.send("enable\n")
            response = self._read_until_prompt(timeout=3)
            
            if 'Password:' in response or 'password:' in response:
                self.shell.send(f"{self.password}\n")
                response = self._read_until_prompt(timeout=3)
            
            current = self.get_current_prompt()
            return '#' in current
        
        return True
    
    def _update_mode_from_prompt(self, prompt):
        """Update current mode based on prompt"""
        if '(config' in prompt:
            self.current_mode = 'config'
        elif '#' in prompt:
            self.current_mode = 'privileged'
        elif '>' in prompt:
            self.current_mode = 'user'
    
    def get_current_prompt(self):
        """Get the current prompt from the device"""
        if not self.shell:
            return "Switch>"
        
        try:
            self.shell.send("\n")
            time.sleep(0.2)
            
            response = ""
            if self.shell.recv_ready():
                response = self.shell.recv(4096).decode('utf-8', errors='ignore')
            
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            if lines:
                prompt = lines[-1]
                self._update_mode_from_prompt(prompt)
                return prompt
            
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
            
            response = self._read_until_prompt(timeout=5)
            
            return response.strip() if response else "No response from device"
        except Exception as e:
            return f"Command error: {e}"
    
    def execute_commands(self, commands_string, keep_alive=False):
        """Execute multiple commands from string"""
        if not self.client or not self.authenticated:
            if not self.connect():
                error_msg = self.last_error or "Failed to connect via SSH"
                return {"success": False, "error": error_msg}
        
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
            if not keep_alive and self.client:
                self.client.close()
                self.authenticated = False

    def test_connection(self):
        """Test if connection is alive and functional"""
        if not self.client or not self.authenticated:
            return {"success": False, "error": "Not connected"}
        
        try:
            self.shell.send("\n")
            response = self._read_until_prompt(timeout=2)
            
            if self._has_prompt(response):
                return {"success": True, "prompt": self.get_current_prompt()}
            else:
                return {"success": False, "error": "No prompt detected"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def close_connection(self):
        """Close the SSH connection"""
        if self.client:
            try:
                self.client.close()
                self.authenticated = False
                self.current_mode = 'unknown'
                return {"success": True, "message": "Connection closed"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": True, "message": "No active connection"}

def main():
    """Main function for CLI usage"""
    if len(sys.argv) < 5:
        print("Usage: python ssh_executor.py '<commands>' <host> <username> <password> [keep_alive]")
        sys.exit(1)
    
    commands = sys.argv[1]
    host = sys.argv[2]
    username = sys.argv[3]
    password = sys.argv[4]
    keep_alive = len(sys.argv) > 5 and sys.argv[5].lower() == 'true'
    
    executor = SSHExecutor(host=host, username=username, password=password)
    result = executor.execute_commands(commands, keep_alive=keep_alive)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
