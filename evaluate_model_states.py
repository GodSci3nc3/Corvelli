#!/usr/bin/env python3
"""
Evaluation system for AIConsole command generation
Tests AI model accuracy with different switch states
"""

import requests
import json

def calculate_similarity(generated, expected_keywords):
    """Calculate similarity score based on keyword matching"""
    generated_lower = generated.lower()
    matches = sum(1 for keyword in expected_keywords if keyword.lower() in generated_lower)
    return (matches / len(expected_keywords)) * 100 if expected_keywords else 0

def test_command(prompt, expected_keywords, switch_state="Switch>", test_num=1, total=1):
    """Test a single command generation"""
    print(f"\nTest {test_num}/{total}")
    print(f"Switch State: {switch_state}")
    print(f"Input: {prompt}")
    
    try:
        response = requests.post('http://localhost:3000/comando', 
            json={"mensaje": prompt, "execute": False},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            generated = result.get('respuesta', '')
            
            print(f"Generated:")
            print(generated)
            
            score = calculate_similarity(generated, expected_keywords)
            
            print(f"Expected keywords: {expected_keywords}")
            print(f"Score: {score}%")
            
            status = "PASS" if score >= 80 else ("PARTIAL" if score >= 50 else "FAIL")
            print(f"Status: {status}")
            
            return {
                "test": test_num,
                "switch_state": switch_state,
                "prompt": prompt,
                "score": score,
                "generated": generated,
                "status": status
            }
        else:
            print(f"Error: HTTP {response.status_code}")
            return {
                "test": test_num,
                "switch_state": switch_state,
                "prompt": prompt,
                "score": 0,
                "generated": f"Error: {response.status_code}",
                "status": "FAIL"
            }
    except Exception as e:
        print(f"Exception: {str(e)}")
        return {
            "test": test_num,
            "switch_state": switch_state,
            "prompt": prompt,
            "score": 0,
            "generated": f"Exception: {str(e)}",
            "status": "FAIL"
        }

def run_evaluation():
    """Run comprehensive evaluation with different switch states"""
    print("Starting model evaluation with switch states...")
    print("Make sure backend is running on port 3000\n")
    
    print("=" * 70)
    print("CISCO COMMAND GENERATOR - EVALUATION WITH SWITCH STATES")
    print("=" * 70)
    
    # Test cases with different switch states
    test_cases = [
        # Tests in USER MODE (Switch>)
        {
            "prompt": "configure ip address on interface gigabitethernet 0/1",
            "switch_state": "Switch>",
            "expected": ['enable', 'configure terminal', 'interface gigabitethernet0/1', 'ip address', 'no shutdown']
        },
        {
            "prompt": "create vlan 10 named sales",
            "switch_state": "Switch>",
            "expected": ['enable', 'configure terminal', 'vlan 10', 'name sales']
        },
        
        # Tests in PRIVILEGED MODE (Switch#)
        {
            "prompt": "configure ip address on interface gigabitethernet 0/1",
            "switch_state": "Switch#",
            "expected": ['configure terminal', 'interface gigabitethernet0/1', 'ip address', 'no shutdown']
        },
        {
            "prompt": "create vlan 10 named sales",
            "switch_state": "Switch#",
            "expected": ['configure terminal', 'vlan 10', 'name sales']
        },
        
        # Tests in CONFIG MODE (Switch(config)#)
        {
            "prompt": "configure ip address on interface gigabitethernet 0/1",
            "switch_state": "Switch(config)#",
            "expected": ['interface gigabitethernet0/1', 'ip address', 'no shutdown']
        },
        {
            "prompt": "create vlan 10 named sales",
            "switch_state": "Switch(config)#",
            "expected": ['vlan 10', 'name sales']
        },
        
        # Show commands (work in any mode)
        {
            "prompt": "show running configuration",
            "switch_state": "Switch>",
            "expected": ['show running-config']
        },
        {
            "prompt": "mostrar la versión del sistema",
            "switch_state": "Switch#",
            "expected": ['show version']
        },
        
        # Additional tests
        {
            "prompt": "configure three ports with ip addresses",
            "switch_state": "Switch(config)#",
            "expected": ['interface', 'ip address', 'interface', 'ip address', 'interface', 'ip address']
        },
        {
            "prompt": "enable port security on interface",
            "switch_state": "Switch(config)#",
            "expected": ['interface', 'switchport mode access', 'switchport port-security']
        },
        {
            "prompt": "set hostname to Router1",
            "switch_state": "Switch(config)#",
            "expected": ['hostname']
        },
        {
            "prompt": "disable interface gigabitethernet 0/2",
            "switch_state": "Switch(config)#",
            "expected": ['interface gigabitethernet0/2', 'shutdown']
        },
    ]
    
    total_tests = len(test_cases)
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        result = test_command(
            test_case["prompt"],
            test_case["expected"],
            test_case["switch_state"],
            i,
            total_tests
        )
        results.append(result)
    
    # Calculate summary
    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for r in results if r["score"] >= 80)
    partial = sum(1 for r in results if 50 <= r["score"] < 80)
    failed = sum(1 for r in results if r["score"] < 50)
    avg_score = sum(r["score"] for r in results) / len(results) if results else 0
    
    print(f"Total tests: {total_tests}")
    print(f"Passed (>=80%): {passed}")
    print(f"Partial (50-79%): {partial}")
    print(f"Failed (<50%): {failed}")
    print(f"\nAverage accuracy: {avg_score:.1f}%")
    
    if avg_score >= 90:
        status = "EXCELLENT"
    elif avg_score >= 70:
        status = "GOOD"
    elif avg_score >= 50:
        status = "FAIR"
    else:
        status = "POOR"
    
    print(f"Model status: {status}")
    
    # Save detailed results
    output = {
        "average_score": avg_score,
        "passed": passed,
        "partial": partial,
        "failed": failed,
        "status": status,
        "details": [
            {
                "test": r["test"],
                "switch_state": r["switch_state"],
                "prompt": r["prompt"],
                "score": r["score"],
                "generated": r["generated"],
                "status": r["status"]
            }
            for r in results
        ]
    }
    
    with open("evaluation_results_states.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to: evaluation_results_states.json")
    print("=" * 70)

if __name__ == "__main__":
    run_evaluation()
