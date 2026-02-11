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
            ser = serial.Serial(
                port=req.serial_port,
                baudrate=req.baudrate,
                timeout=2
            )
            
            # Wait for connection
            time.sleep(1)
            ser.read_all()  # Clear buffer
            
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
            time.sleep(2)
            
            # Read output
            output = ""
            while shell.recv_ready():
                chunk = shell.recv(4096).decode('utf-8', errors='ignore')
                output += chunk
                time.sleep(0.1)
            
            return {
                "success": True,
                "output": clean_output(output)
            }
            
        elif conn['type'] == 'serial':
            ser = conn['serial']
            
            # Send command
            ser.write((req.command + '\r\n').encode())
            time.sleep(2)
            
            # Read output
            output = ser.read_all().decode('utf-8', errors='ignore')
            
            return {
                "success": True,
                "output": clean_output(output)
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
