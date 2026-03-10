"""
Corvelli Connection Server
Manages persistent SSH and Serial connections
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
import paramiko
import serial
import time
import uvicorn

app = FastAPI()

# Store active connections
connections: Dict[str, any] = {}


class ConnectionRequest(BaseModel):
    connection_id: str
    connection_type: str  # 'ssh' or 'serial'
    host: Optional[str] = None
    port: Optional[int] = 22
    username: Optional[str] = None
    password: Optional[str] = None
    serial_port: Optional[str] = '/dev/ttyUSB0'
    baudrate: Optional[int] = 9600


class ExecuteRequest(BaseModel):
    connection_id: str
    command: str


class DisconnectRequest(BaseModel):
    connection_id: str


def clean_output(output: str) -> str:
    """Remove terminal control characters"""
    import re
    # Remove ANSI escape codes
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    cleaned = ansi_escape.sub('', output)
    return cleaned.strip()


@app.post("/connect")
async def connect(req: ConnectionRequest):
    """Establish SSH or Serial connection"""
    try:
        if req.connection_type == 'ssh':
            # SSH Connection
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            client.connect(
                hostname=req.host,
                port=req.port,
                username=req.username,
                password=req.password,
                timeout=10,
                look_for_keys=False,
                allow_agent=False
            )
            
            # Create interactive shell
            shell = client.invoke_shell()
            time.sleep(1)
            
            # Read initial output
            shell.recv(4096).decode('utf-8', errors='ignore')
            
            connections[req.connection_id] = {
                'type': 'ssh',
                'client': client,
                'shell': shell
            }
            
            return {
                "success": True,
                "message": f"Connected to {req.host} via SSH"
            }
            
        elif req.connection_type == 'serial':
            # Serial Connection
            print(f"[Serial Debug] Connecting to {req.serial_port} at {req.baudrate} baud")
            
            ser = serial.Serial(
                port=req.serial_port,
                baudrate=req.baudrate,
                timeout=2,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            print(f"[Serial Debug] Serial port opened: {ser.is_open}")
            
            # Wait for connection to stabilize
            time.sleep(1)
            
            # Check if there's any initial data
            initial_waiting = ser.in_waiting
            print(f"[Serial Debug] Initial buffer: {initial_waiting} bytes")
            
            if initial_waiting > 0:
                initial_data = ser.read(initial_waiting).decode('utf-8', errors='ignore')
                print(f"[Serial Debug] Initial data: {repr(initial_data[:100])}")
            
            # Send a few newlines to get a prompt
            ser.write(b'\r\n')
            time.sleep(0.5)
            
            prompt_waiting = ser.in_waiting
            print(f"[Serial Debug] After newline, buffer: {prompt_waiting} bytes")
            
            if prompt_waiting > 0:
                prompt_data = ser.read(prompt_waiting).decode('utf-8', errors='ignore')
                print(f"[Serial Debug] Prompt data: {repr(prompt_data[:100])}")
            
            connections[req.connection_id] = {
                'type': 'serial',
                'serial': ser
            }
            
            return {
                "success": True,
                "message": f"Connected to {req.serial_port}"
            }
        else:
            raise HTTPException(status_code=400, detail="Invalid connection type")
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/execute")
async def execute(req: ExecuteRequest):
    """Execute command on connected device"""
    try:
        if req.connection_id not in connections:
            return {
                "success": False,
                "error": "Connection not found. Please connect first."
            }
        
        conn = connections[req.connection_id]
        
        if conn['type'] == 'ssh':
            shell = conn['shell']
            
            # Send command
            shell.send(req.command + '\n')
            
            # Read output dynamically
            output = ""
            max_wait = 10  # Maximum 10 seconds
            idle_timeout = 0.5  # 500ms of no data = command complete
            start_time = time.time()
            last_data_time = start_time
            
            while time.time() - start_time < max_wait:
                if shell.recv_ready():
                    chunk = shell.recv(4096).decode('utf-8', errors='ignore')
                    output += chunk
                    last_data_time = time.time()
                    
                    # Get last line to check for interactive prompts
                    lines = output.strip().split('\n')
                    last_line = lines[-1] if lines else ""
                    
                    # Check for interactive prompts (waiting for user input)
                    # Examples: "How many bits [512]: ", "[yes/no]: ", "Password: "
                    if any(last_line.rstrip().endswith(marker) for marker in [':', ']:']) and \
                       not any(marker in last_line for marker in ['#', '>']):
                        # Interactive prompt detected - return immediately
                        print(f"[Interactive] Detected interactive prompt: {repr(last_line[-50:])}")
                        time.sleep(0.3)  # Small wait to ensure prompt is complete
                        if not shell.recv_ready():
                            break
                    
                    # Check if we've received a regular prompt (command complete)
                    if any(marker in output[-100:] for marker in ['#', '>', 'Switch', 'Router']):
                        # Wait a bit more to ensure nothing else coming
                        time.sleep(0.2)
                        if not shell.recv_ready():
                            break
                else:
                    # No data waiting - check if we've been idle long enough
                    if output and (time.time() - last_data_time) > idle_timeout:
                        break
                    time.sleep(0.05)
            
            # Read any remaining data
            while shell.recv_ready():
                output += shell.recv(4096).decode('utf-8', errors='ignore')
                time.sleep(0.05)
            
            return {
                "success": True,
                "output": clean_output(output) if output else "No response from device"
            }
            
        elif conn['type'] == 'serial':
            ser = conn['serial']
            
            print(f"[Serial Debug] Executing command: {req.command}")
            print(f"[Serial Debug] Buffer before clear: {ser.in_waiting} bytes")
            
            # Clear any pending data first
            ser.reset_input_buffer()
            
            # Send command
            command_bytes = (req.command + '\r\n').encode()
            print(f"[Serial Debug] Sending: {command_bytes}")
            ser.write(command_bytes)
            ser.flush()  # Ensure data is sent
            
            # Read output dynamically until we detect prompt
            output = ""
            max_wait = 10  # Maximum 10 seconds total
            idle_timeout = 0.5  # 500ms of no data = command complete
            start_time = time.time()
            last_data_time = start_time
            chunks_received = 0
            
            while time.time() - start_time < max_wait:
                waiting = ser.in_waiting
                if waiting:
                    chunk = ser.read(waiting).decode('utf-8', errors='ignore')
                    output += chunk
                    chunks_received += 1
                    last_data_time = time.time()
                    print(f"[Serial Debug] Chunk {chunks_received}: {len(chunk)} bytes, total: {len(output)} bytes")
                    
                    # Get last line to check for interactive prompts
                    lines = output.strip().split('\n')
                    last_line = lines[-1] if lines else ""
                    
                    # Check for interactive prompts (waiting for user input)
                    # Examples: "How many bits [512]: ", "[yes/no]: ", "Password: "
                    if any(last_line.rstrip().endswith(marker) for marker in [':', ']:']) and \
                       not any(marker in last_line for marker in ['#', '>']):
                        # Interactive prompt detected - return immediately
                        print(f"[Serial Debug] Interactive prompt detected: {repr(last_line[-50:])}")
                        time.sleep(0.3)  # Small wait to ensure prompt is complete
                        if not ser.in_waiting:
                            print(f"[Serial Debug] Interactive prompt complete")
                            break
                    
                    # Check if we've received a regular prompt (command complete)
                    if any(marker in output[-100:] for marker in ['#', '>']):
                        # Wait a bit more to ensure nothing else coming
                        time.sleep(0.2)
                        if not ser.in_waiting:
                            print(f"[Serial Debug] Prompt detected, command complete")
                            break
                else:
                    # No data waiting - check if we've been idle long enough
                    elapsed = time.time() - start_time
                    if output and (time.time() - last_data_time) > idle_timeout:
                        print(f"[Serial Debug] Idle timeout reached after {elapsed:.2f}s")
                        break
                    time.sleep(0.05)
            
            # Read any remaining data
            if ser.in_waiting:
                remaining = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                output += remaining
                print(f"[Serial Debug] Read {len(remaining)} remaining bytes")
            
            elapsed_total = time.time() - start_time
            print(f"[Serial Debug] Total time: {elapsed_total:.2f}s, chunks: {chunks_received}, output length: {len(output)} bytes")
            
            if not output:
                print(f"[Serial Debug] WARNING: No data received from device")
            
            return {
                "success": True,
                "output": clean_output(output) if output else "No response from device"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/disconnect")
async def disconnect(req: DisconnectRequest):
    """Close connection"""
    try:
        if req.connection_id in connections:
            conn = connections[req.connection_id]
            
            if conn['type'] == 'ssh':
                conn['shell'].close()
                conn['client'].close()
            elif conn['type'] == 'serial':
                conn['serial'].close()
            
            del connections[req.connection_id]
        
        return {
            "success": True,
            "message": "Disconnected"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "ok",
        "active_connections": len(connections)
    }


if __name__ == "__main__":
    print("Corvelli Connection Server starting on port 5000...")
    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")
