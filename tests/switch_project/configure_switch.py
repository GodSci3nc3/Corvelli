#!/usr/bin/env python3
"""
Switch Configuration Project - Office Network Setup
====================================================

This script performs a complete configuration of a Cisco switch for a small
office network environment. It demonstrates the AIConsole system's ability
to execute multi-step network configurations automatically.

Author: AIConsole Team
Date: December 2025
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BACKEND_URL = "http://localhost:3000"
SWITCH_NAME = "SW-Office-Main"

# Project configuration steps
PROJECT_STEPS = [
    {
        "number": 1,
        "name": "Hostname and Banner",
        "description": "Set switch hostname and security banner",
        "prompt": f"Configure hostname {SWITCH_NAME} and banner with message 'Authorized Access Only'"
    },
    {
        "number": 2,
        "name": "Create VLANs",
        "description": "Create 4 VLANs for network segmentation",
        "prompt": "Create VLAN 10 named Employees, VLAN 20 named Guests, VLAN 30 named Servers, and VLAN 99 named Management"
    },
    {
        "number": 3,
        "name": "Management IP",
        "description": "Configure management IP address",
        "prompt": "Configure IP address 192.168.99.1 with mask 255.255.255.0 on VLAN 99 interface"
    },
    {
        "number": 4,
        "name": "Assign Ports to VLAN 10",
        "description": "Configure employee VLAN ports",
        "prompt": "Configure ports gi0/1 to gi0/10 as access ports in VLAN 10"
    },
    {
        "number": 5,
        "name": "Assign Ports to VLAN 20",
        "description": "Configure guest VLAN ports",
        "prompt": "Configure ports gi0/11 to gi0/15 as access ports in VLAN 20"
    },
    {
        "number": 6,
        "name": "Port Security",
        "description": "Enable port security on critical ports",
        "prompt": "Enable port-security on interface gi0/1 with maximum 2 MAC addresses and violation mode shutdown"
    },
    {
        "number": 7,
        "name": "Save Configuration",
        "description": "Save configuration to NVRAM",
        "prompt": "Save the running configuration to startup configuration"
    }
]

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def execute_configuration_step(step):
    """Execute a single configuration step"""
    print(f"\n{'='*70}")
    print(f"STEP {step['number']}: {step['name']}")
    print(f"{'='*70}")
    print(f"Description: {step['description']}")
    print(f"\nPrompt: {step['prompt']}")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/comando",
            json={
                "mensaje": step['prompt'],
                "execute": True
            },
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Show generated commands
            commands = result.get('respuesta', '')
            print(f"\nGenerated commands:")
            for line in commands.split('\n'):
                if line.strip():
                    print(f"  {line}")
            
            # Check execution results
            if result.get('executed'):
                device_responses = result.get('device_responses', [])
                errors_found = []
                
                for cmd_result in device_responses:
                    response_text = cmd_result.get('response', '')
                    if any(err in response_text for err in ['Invalid', 'Error', 'Incomplete', '%']):
                        errors_found.append(cmd_result.get('command', ''))
                
                if errors_found:
                    print(f"\n⚠ ERRORS detected in {len(errors_found)} command(s)")
                    for cmd in errors_found:
                        print(f"  - {cmd}")
                    return False
                else:
                    print(f"\n✓ Step completed successfully")
                    return True
            else:
                print(f"\n✗ Execution failed")
                return False
        else:
            print(f"\n✗ Server error: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n✗ Connection error: {e}")
        return False

def main():
    """Main execution function"""
    print_header("SWITCH CONFIGURATION PROJECT: OFFICE NETWORK")
    
    print(f"\nProject: Complete office switch configuration")
    print(f"Objective: Configure a production-ready switch with security and VLANs")
    print(f"Switch: {SWITCH_NAME}")
    print(f"Total steps: {len(PROJECT_STEPS)}")
    
    print(f"\nConfiguration steps:")
    for step in PROJECT_STEPS:
        print(f"   {step['number']}. {step['name']}")
    
    input("\nPress ENTER to start configuration...")
    
    # Execute each step
    start_time = datetime.now()
    results = []
    
    for step in PROJECT_STEPS:
        success = execute_configuration_step(step)
        results.append({
            'step': step['number'],
            'name': step['name'],
            'success': success
        })
        
        if not success:
            print(f"\n⚠ WARNING: Step {step['number']} failed")
            retry = input("Continue with next step? (y/n): ")
            if retry.lower() != 'y':
                print("\nConfiguration aborted by user")
                break
        
        # Brief pause between steps
        if step['number'] < len(PROJECT_STEPS):
            time.sleep(1)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Final summary
    print_header("CONFIGURATION SUMMARY")
    print(f"\nExecution time: {duration:.1f} seconds")
    print(f"Total steps: {len(PROJECT_STEPS)}")
    
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n" + "="*70)
        print("PROJECT COMPLETED SUCCESSFULLY!")
        print("="*70)
        print("\nYour switch now has:")
        print("   ✓ Configured hostname and banner")
        print("   ✓ 4 VLANs for network segmentation")
        print("   ✓ Management IP address")
        print("   ✓ 15 ports assigned to VLANs")
        print("   ✓ Port security enabled")
        print("   ✓ Configuration saved to NVRAM")
    elif successful > 0:
        print("\n" + "="*70)
        print("PROJECT PARTIALLY COMPLETED")
        print("="*70)
        print(f"\n{successful} of {len(PROJECT_STEPS)} steps completed successfully")
        print("\nFailed steps:")
        for r in results:
            if not r['success']:
                print(f"   ✗ Step {r['step']}: {r['name']}")
    else:
        print("\n" + "="*70)
        print("PROJECT FAILED")
        print("="*70)
        print("\nNo steps completed successfully")
        print("Check backend logs and switch connectivity")
    
    print("\n" + "=" * 70)
    print("Configuration project finished")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled by user")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
