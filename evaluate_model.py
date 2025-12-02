#!/usr/bin/env python3
"""
Model evaluation system for Cisco command generation
Tests accuracy of AI model against expected outputs
"""

import requests
import json
from difflib import SequenceMatcher

# Test cases: input -> expected output
TEST_CASES = [
    {
        "input": "configure ip address on interface gigabitethernet 0/1",
        "expected": [
            "interface gigabitethernet0/1",
            "ip address",
            "no shutdown"
        ]
    },
    {
        "input": "create vlan 10 named sales",
        "expected": [
            "vlan 10",
            "name sales"
        ]
    },
    {
        "input": "show running configuration",
        "expected": [
            "show running-config"
        ]
    },
    {
        "input": "configure three ports with ip addresses",
        "expected": [
            "interface",
            "ip address",
            "interface",
            "ip address",
            "interface",
            "ip address"
        ]
    },
    {
        "input": "enable port security on interface",
        "expected": [
            "interface",
            "switchport mode access",
            "switchport port-security"
        ]
    },
    {
        "input": "set hostname to Router1",
        "expected": [
            "hostname Router1"
        ]
    },
    {
        "input": "configure ospf routing",
        "expected": [
            "router ospf"
        ]
    },
    {
        "input": "disable interface gigabitethernet 0/2",
        "expected": [
            "interface gigabitethernet0/2",
            "shutdown"
        ]
    }
]

def similarity_score(generated, expected_keywords):
    """Calculate how well generated output matches expected keywords"""
    generated_lower = generated.lower()
    
    # Check how many expected keywords are present
    matches = sum(1 for keyword in expected_keywords if keyword.lower() in generated_lower)
    total = len(expected_keywords)
    
    return (matches / total) * 100 if total > 0 else 0

def evaluate_model():
    """Run all test cases and calculate accuracy"""
    print("=" * 70)
    print("CISCO COMMAND GENERATOR - MODEL EVALUATION")
    print("=" * 70)
    
    results = []
    total_score = 0
    
    for i, test in enumerate(TEST_CASES, 1):
        print(f"\nTest {i}/{len(TEST_CASES)}")
        print(f"Input: {test['input']}")
        
        try:
            # Call the API
            response = requests.post(
                'http://localhost:3000/comando',
                json={"mensaje": test['input'], "execute": False},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                generated = result.get('respuesta', '')
                
                print(f"Generated:\n{generated}")
                print(f"Expected keywords: {test['expected']}")
                
                # Calculate score
                score = similarity_score(generated, test['expected'])
                results.append({
                    "test": i,
                    "score": score,
                    "generated": generated
                })
                total_score += score
                
                print(f"Score: {score:.1f}%")
                
                if score >= 80:
                    print("Status: PASS")
                elif score >= 50:
                    print("Status: PARTIAL")
                else:
                    print("Status: FAIL")
            else:
                print(f"Error: HTTP {response.status_code}")
                results.append({"test": i, "score": 0, "error": "HTTP error"})
                
        except Exception as e:
            print(f"Error: {e}")
            results.append({"test": i, "score": 0, "error": str(e)})
    
    # Summary
    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    
    avg_score = total_score / len(TEST_CASES)
    passed = sum(1 for r in results if r.get('score', 0) >= 80)
    partial = sum(1 for r in results if 50 <= r.get('score', 0) < 80)
    failed = sum(1 for r in results if r.get('score', 0) < 50)
    
    print(f"Total tests: {len(TEST_CASES)}")
    print(f"Passed (>=80%): {passed}")
    print(f"Partial (50-79%): {partial}")
    print(f"Failed (<50%): {failed}")
    print(f"\nAverage accuracy: {avg_score:.1f}%")
    
    if avg_score >= 80:
        print("Model status: EXCELLENT")
    elif avg_score >= 60:
        print("Model status: GOOD")
    elif avg_score >= 40:
        print("Model status: NEEDS IMPROVEMENT")
    else:
        print("Model status: POOR")
    
    # Save results
    with open('evaluation_results.json', 'w') as f:
        json.dump({
            "average_score": avg_score,
            "passed": passed,
            "partial": partial,
            "failed": failed,
            "details": results
        }, f, indent=2)
    
    print("\nResults saved to: evaluation_results.json")
    print("=" * 70)

if __name__ == "__main__":
    print("\nStarting model evaluation...")
    print("Make sure backend is running on port 3000\n")
    
    try:
        evaluate_model()
    except KeyboardInterrupt:
        print("\nEvaluation interrupted by user")
    except Exception as e:
        print(f"\nFatal error: {e}")
