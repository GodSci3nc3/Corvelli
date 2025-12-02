#!/usr/bin/env python3
"""
Quick integration test for AIConsole with local Ollama
Tests the complete pipeline: Frontend -> Backend -> Ollama -> Response
"""

import requests
import json
import time

def test_backend():
    """Test backend API directly"""
    print("Testing backend API...")
    
    url = "http://localhost:3000/comando"
    test_commands = [
        "configure ip address on interface",
        "show running configuration",
        "create vlan 10"
    ]
    
    for cmd in test_commands:
        print(f"\nTesting: {cmd}")
        try:
            response = requests.post(url, 
                json={"mensaje": cmd}, 
                timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"SUCCESS: {result['respuesta']}")
            else:
                print(f"ERROR: {response.status_code}")
                
        except Exception as e:
            print(f"ERROR: {e}")
        
        time.sleep(2)  # Wait between requests

if __name__ == "__main__":
    print("AIConsole Integration Test")
    print("=" * 40)
    test_backend()
    print("\nTest completed!")