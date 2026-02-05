#!/usr/bin/env python3
"""
Quick test for AIConsole with serial execution
"""

import requests
import json

def test_improved_prompt():
    """Test the improved prompt"""
    print("Testing improved prompt...")
    
    url = "http://localhost:3000/comando"
    
    response = requests.post(url, json={
        "mensaje": "configure ip address on three ports",
        "execute": False  # Just generate, don't execute
    })
    
    if response.status_code == 200:
        result = response.json()
        print("Generated commands:")
        print(result['respuesta'])
        return result['respuesta']
    else:
        print(f"Error: {response.status_code}")
        return None

def test_serial_execution(commands):
    """Test serial execution (will fail if no device connected)"""
    print("\nTesting serial execution...")
    
    url = "http://localhost:3000/execute"
    
    response = requests.post(url, json={
        "commands": commands
    })
    
    if response.status_code == 200:
        result = response.json()
        print(f"Execution result: {result}")
    else:
        print(f"Serial execution failed: {response.status_code}")

if __name__ == "__main__":
    print("AIConsole Serial Integration Test")
    print("=" * 50)
    
    # Test 1: Improved prompt
    commands = test_improved_prompt()
    
    # Test 2: Serial execution (will show connection error if no device)
    if commands:
        test_serial_execution(commands)
    
    print("\nIntegration test completed!")
    print("Note: Serial execution requires USB device connected at /dev/ttyUSB0")