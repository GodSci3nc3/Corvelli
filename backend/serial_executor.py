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
            time.sleep(0.5)
            
            for _ in range(2):
                self.connection.write(b'\r\n')
                time.sleep(0.1)
            
            time.sleep(0.5)
            initial_output = ""
            if self.connection.in_waiting:
                initial_output = self.connection.read(self.connection.in_waiting).decode('utf-8', errors='ignore')
            
            if 'Password:' in initial_output or 'password:' in initial_output:
                self.connection.write(f"{self.password}\r\n".encode('utf-8'))
                time.sleep(0.3)
                
                if self.connection.in_waiting:
                    auth_response = self.connection.read(self.connection.in_waiting).decode('utf-8', errors='ignore')
                    
                    if '>' in auth_response or '#' in auth_response:
                        self.authenticated = True
                        
                        self.connection.write(b"enable\r\n")
                        time.sleep(0.3)
                        if self.connection.in_waiting:
                            enable_response = self.connection.read(self.connection.in_waiting).decode('utf-8', errors='ignore')
                            
                            if 'Password:' in enable_response:
                                self.connection.write(f"{self.password}\r\n".encode('utf-8'))
                                time.sleep(0.3)
                                if self.connection.in_waiting:
                                    self.connection.read(self.connection.in_waiting)
            else:
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
            
            self.connection.write(b"\r\n")
            time.sleep(0.2)
            
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
            
            # Read response with dynamic timing - wait only as needed
            response = ""
            max_wait = 3  # Max 3 seconds (reduced from 5)
            idle_threshold = 0.3  # Consider complete after 300ms of no data
            start_time = time.time()
            last_data_time = start_time
            
            while time.time() - start_time < max_wait:
                if self.connection.in_waiting:
                    data = self.connection.read(self.connection.in_waiting)
                    response += data.decode('utf-8', errors='ignore')
                    last_data_time = time.time()
                    
                    # Check if output seems complete (ends with prompt)
                    if any(marker in response[-50:] for marker in ['#', '>', 'Switch', 'Router']):
                        # Wait just a bit more to ensure nothing else coming
                        time.sleep(0.1)
                        if not self.connection.in_waiting:
                            break
                else:
                    # No data waiting - check if we've been idle long enough
                    if response and (time.time() - last_data_time) > idle_threshold:
                        break
                    time.sleep(0.05)  # Small sleep to avoid CPU spinning
            
            return response.strip() if response else "No response from device"
        except Exception as e:
            return f"Command error: {e}"
    
    def execute_commands(self, commands_string, keep_alive=False):
        """Execute multiple commands from string"""
        if not self.connection or not self.authenticated:
            if not self.connect():
                return {"success": False, "error": "Failed to connect"}
        
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
            if not keep_alive and self.connection:
                self.connection.close()
                self.authenticated = False

    def close_connection(self):
        """Close the serial connection"""
        if self.connection:
            try:
                self.connection.close()
                self.authenticated = False
                return {"success": True, "message": "Connection closed"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": True, "message": "No active connection"}

def main():
    """Main function for CLI usage"""
    if len(sys.argv) < 2:
        print("Usage: python serial_executor.py '<commands>' [keep_alive]")
        sys.exit(1)
    
    commands = sys.argv[1]
    keep_alive = len(sys.argv) > 2 and sys.argv[2].lower() == 'true'
    executor = SerialExecutor()
    result = executor.execute_commands(commands, keep_alive=keep_alive)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()