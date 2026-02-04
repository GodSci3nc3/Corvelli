from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
import uvicorn
import threading
from ssh_executor import SSHExecutor
from serial_executor import SerialExecutor

app = FastAPI(title="Corvelli Connection Server")

# CORS for Node.js backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connection storage (thread-safe)
connections: Dict[str, object] = {}
connection_lock = threading.Lock()

# Request models
class ConnectRequest(BaseModel):
    connection_id: str
    connection_type: str  # "ssh" or "serial"
    host: Optional[str] = None
    port: Optional[int] = 22
    username: Optional[str] = None
    password: Optional[str] = None
    serial_port: Optional[str] = "/dev/ttyUSB0"
    baudrate: Optional[int] = 9600

class ExecuteRequest(BaseModel):
    connection_id: str
    command: str

class DisconnectRequest(BaseModel):
    connection_id: str

# Endpoints
@app.post("/connect")
async def connect(req: ConnectRequest):
    """Establish persistent connection"""
    with connection_lock:
        # Close existing connection if any
        if req.connection_id in connections:
            try:
                old_conn = connections[req.connection_id]
                if hasattr(old_conn, 'close'):
                    old_conn.close()
            except:
                pass
        
        try:
            if req.connection_type.lower() == "ssh":
                executor = SSHExecutor(
                    host=req.host,
                    port=req.port,
                    username=req.username,
                    password=req.password,
                    timeout=30
                )
                
                if not executor.connect():
                    return {
                        "success": False,
                        "error": executor.last_error or "Connection failed"
                    }
                
                connections[req.connection_id] = executor
                
                return {
                    "success": True,
                    "message": f"Connected to {req.host} via SSH",
                    "connection_type": "ssh",
                    "mode": executor.current_mode
                }
            
            elif req.connection_type.lower() == "serial":
                executor = SerialExecutor(
                    port=req.serial_port,
                    baudrate=req.baudrate,
                    password=req.password or ""
                )
                
                if not executor.connect():
                    return {
                        "success": False,
                        "error": "Serial connection failed"
                    }
                
                connections[req.connection_id] = executor
                
                return {
                    "success": True,
                    "message": f"Connected to {req.serial_port}",
                    "connection_type": "serial"
                }
            
            else:
                raise HTTPException(status_code=400, detail="Invalid connection type")
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

@app.post("/execute")
async def execute_command(req: ExecuteRequest):
    """Execute command on persistent connection"""
    with connection_lock:
        if req.connection_id not in connections:
            return {
                "success": False,
                "error": "Not connected. Please connect first."
            }
        
        executor = connections[req.connection_id]
        
        try:
            if isinstance(executor, SSHExecutor):
                output = executor.execute_commands(req.command)
                
                # Extract text from response
                if isinstance(output, dict) and "results" in output:
                    text_output = "\n".join([r.get("response", "") for r in output["results"]])
                else:
                    text_output = str(output)
                
                return {
                    "success": True,
                    "output": text_output,
                    "mode": executor.current_mode
                }
            
            elif isinstance(executor, SerialExecutor):
                output = executor.execute_commands(req.command)
                
                # Extract text from response
                if isinstance(output, dict) and output.get("success") and "results" in output:
                    text_output = "\n".join([r.get("response", "") for r in output["results"]])
                elif isinstance(output, dict) and "error" in output:
                    return {
                        "success": False,
                        "error": output["error"]
                    }
                else:
                    text_output = str(output)
                
                return {
                    "success": True,
                    "output": text_output
                }
            
            else:
                return {
                    "success": False,
                    "error": "Invalid executor type"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

@app.post("/disconnect")
async def disconnect(req: DisconnectRequest):
    """Close persistent connection"""
    with connection_lock:
        if req.connection_id in connections:
            try:
                executor = connections[req.connection_id]
                
                if isinstance(executor, SSHExecutor):
                    executor.close()
                elif isinstance(executor, SerialExecutor):
                    executor.close_connection()
                
                del connections[req.connection_id]
                
                return {
                    "success": True,
                    "message": "Connection closed"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }
        
        return {
            "success": True,
            "message": "No active connection"
        }

@app.get("/status/{connection_id}")
async def get_status(connection_id: str):
    """Check connection status"""
    with connection_lock:
        if connection_id in connections:
            executor = connections[connection_id]
            
            if isinstance(executor, SSHExecutor):
                return {
                    "connected": executor.authenticated,
                    "type": "ssh",
                    "mode": executor.current_mode
                }
            elif isinstance(executor, SerialExecutor):
                return {
                    "connected": executor.authenticated,
                    "type": "serial"
                }
        
        return {
            "connected": False
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
