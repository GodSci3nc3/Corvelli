#!/usr/bin/env python3
"""
Quick serial connection test
"""
import sys
sys.path.append('/home/arthur/Escritorio/AIConsole/backend')
from serial_executor import SerialExecutor

print("Testing serial connection to switch...")
print("=" * 50)

executor = SerialExecutor()

if executor.connect():
    print("Connection established!")
    
    # Test with simple command
    print("\nSending 'enable'...")
    response = executor.send_command("enable")
    print(f"Response: [{response}]")
    
    print("\nSending empty enter...")
    response = executor.send_command("")
    print(f"Response: [{response}]")
    
    print("\nSending 'show version'...")
    response = executor.send_command("show version")
    print(f"Response: [{response}]")
    
    executor.connection.close()
    print("\nConnection closed")
else:
    print("Failed to connect!")
    print("Check:")
    print("1. Is switch powered on?")
    print("2. Is USB cable connected?")
    print("3. Is /dev/ttyUSB0 the correct port?")
    print("4. Try: ls -la /dev/ttyUSB*")