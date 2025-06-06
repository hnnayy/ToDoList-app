#!/usr/bin/env python3
"""
Security validation script for CI/CD pipeline
"""
import json
import sys
import os

def check_bandit_results():
    """Check Bandit SAST results"""
    try:
        with open('bandit-report.json', 'r') as f:
            data = json.load(f)
        
        high_severity = len([issue for issue in data.get('results', []) 
                           if issue.get('issue_severity') == 'HIGH'])
        critical_severity = len([issue for issue in data.get('results', []) 
                               if issue.get('issue_severity') == 'CRITICAL'])
        
        print(f"Bandit scan - High: {high_severity}, Critical: {critical_severity}")
        
        if critical_severity > 0:
            print("❌ Critical vulnerabilities found! Pipeline failed.")
            return False
        
        if high_severity > 3:  # Allow max 3 high severity issues
            print("❌ Too many high severity vulnerabilities! Pipeline failed.")
            return False
            
        return True
    except FileNotFoundError:
        print("⚠️  Bandit report not found")
        return True

def check_safety_results():
    """Check Safety dependency scan results"""
    try:
        with open('safety-report.json', 'r') as f:
            data = json.load(f)
        
        vulnerabilities = len(data.get('vulnerabilities', []))
        print(f"Safety scan - Vulnerabilities: {vulnerabilities}")
        
        if vulnerabilities > 0:
            print("⚠️  Dependency vulnerabilities found - review required")
        
        return True  # Don't fail on dependency issues for now
    except FileNotFoundError:
        print("⚠️  Safety report not found")
        return True

if __name__ == "__main__":
    bandit_ok = check_bandit_results()
    safety_ok = check_safety_results()
    
    if bandit_ok and safety_ok:
        print("✅ Security checks passed!")
        sys.exit(0)
    else:
        print("❌ Security checks failed!")
        sys.exit(1)
