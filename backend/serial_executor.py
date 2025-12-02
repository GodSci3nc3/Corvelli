#!/usr/bin/env python3
"""
Serial communication module for AIConsole
Handles USB serial connection to network devices
"""

import serial
import time
import sys
import json

class SerialExecutor:
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600, timeout=3, password=''):
        """Initialize serial connection parameters"""
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.password = password
        self.connection = None
        self.authenticated = False
    
    def connect(self):
        """Establish serial connection and authenticate"""
        try:
            self.connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            time.sleep(2)
            
            # Send multiple enters to wake up device
            for _ in range(3):
                self.connection.write(b'\r\n')
                time.sleep(0.3)
            
            # Wait for initial output
            time.sleep(2)
            initial_output = ""
            if self.connection.in_waiting:
                initial_output = self.connection.read(self.connection.in_waiting).decode('utf-8', errors='ignore')
            
            # Check if password is required
            if 'Password:' in initial_output or 'password:' in initial_output:
                # Send password (empty string + Enter)
                self.connection.write(f"{self.password}\r\n".encode('utf-8'))
                time.sleep(1)
                
                # Read response
                if self.connection.in_waiting:
                    auth_response = self.connection.read(self.connection.in_waiting).decode('utf-8', errors='ignore')
                    
                    # Check if we got to a prompt
                    if '>' in auth_response or '#' in auth_response:
                        self.authenticated = True
                        
                        # Try to enter privileged mode
                        self.connection.write(b"enable\r\n")
                        time.sleep(1)
                        if self.connection.in_waiting:
                            enable_response = self.connection.read(self.connection.in_waiting).decode('utf-8', errors='ignore')
                            
                            # If it asks for password again, send empty
                            if 'Password:' in enable_response:
                                self.connection.write(f"{self.password}\r\n".encode('utf-8'))
                                time.sleep(1)
                                if self.connection.in_waiting:
                                    self.connection.read(self.connection.in_waiting)
            else:
                # No password required, try to get to prompt
                self.authenticated = True
            
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def get_current_prompt(self):
        """Get the current prompt from the switch (e.g., Switch>, Switch#, Switch(config)#)"""
        if not self.connection:
            return "Switch>"
        
        try:
            # Clear buffer
            self.connection.reset_input_buffer()
            
            # Send enter to get prompt
            self.connection.write(b"\r\n")
            time.sleep(0.5)
            
            # Read response
            response = ""
            if self.connection.in_waiting:
                response = self.connection.read(self.connection.in_waiting).decode('utf-8', errors='ignore')
            
            # Extract the last line which should be the prompt
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            if lines:
                last_line = lines[-1]
                # Return the prompt (e.g., "Switch>", "Switch#", "Switch(config)#")
                return last_line
            
            return "Switch>"
        except:
            return "Switch>"
    
    def send_command(self, command):
        """Send single command and get response"""
        if not self.connection:
            return "No connection established"
        
        try:
            # Clear input buffer
            self.connection.reset_input_buffer()
            
            # Send command with \r\n (carriage return + line feed)
            self.connection.write(f"{command}\r\n".encode('utf-8'))
            
            # Wait longer for response
            time.sleep(2)
            
            # Read response with longer timeout
            response = ""
            max_wait = 5  # Wait up to 5 seconds
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                if self.connection.in_waiting:
                    data = self.connection.read(self.connection.in_waiting)
                    response += data.decode('utf-8', errors='ignore')
                    time.sleep(0.2)
                    
                    # If we got some response, wait a bit more for complete output
                    if response and time.time() - start_time > 1:
                        # Check if output seems complete (ends with prompt or similar)
                        if any(marker in response for marker in ['#', '>', 'Switch', 'Router']):
                            break
                else:
                    time.sleep(0.1)
            
            return response.strip() if response else "No response from device"
        except Exception as e:
            return f"Command error: {e}"
    
    def execute_commands(self, commands_string):
        """Execute multiple commands from string"""
        if not self.connect():
            return {"success": False, "error": "Failed to connect"}
        
        commands = [cmd.strip() for cmd in commands_string.split('\n') if cmd.strip()]
        results = []
        
        try:
            # Get current prompt state
            current_prompt = self.get_current_prompt()
            
            # Execute commands as-is, without forcing any mode
            for command in commands:
                response = self.send_command(command)
                results.append({
                    "command": command,
                    "response": response
                })
                time.sleep(0.5)
            
            return {
                "success": True, 
                "results": results,
                "initial_prompt": current_prompt
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
        
        finally:
            if self.connection:
                self.connection.close()

def main():
    """Main function for CLI usage"""
    if len(sys.argv) < 2:
        print("Usage: python serial_executor.py '<commands>'")
        sys.exit(1)
    
    commands = sys.argv[1]
    executor = SerialExecutor()
    result = executor.execute_commands(commands)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()