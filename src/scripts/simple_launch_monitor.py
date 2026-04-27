#!/usr/bin/env python3
"""
Simple tool to monitor and manage launchd services
"""

import subprocess
import json
import sys
import time
from pathlib import Path

def get_launch_services():
    """Get all launch services information"""
    services = []
    
    # Get user agents
    try:
        result = subprocess.run(['launchctl', 'list'], 
                              capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        for line in lines:
            parts = line.split()
            if len(parts) >= 3:
                pid, status, label = parts[0], parts[1], parts[2]
                services.append({
                    'label': label,
                    'pid': pid,
                    'status': status,
                    'type': 'user'
                })
    except:
        pass
    
    # Get launch agents info
    try:
        agents_dir = Path.home() / 'Library' / 'LaunchAgents'
        for plist_file in agents_dir.glob('*.plist'):
            services.append({
                'label': plist_file.stem,
                'path': str(plist_file),
                'type': 'user_agent',
                'status': 'loaded' if any(s['label'] == plist_file.stem for s in services) else 'unloaded'
            })
    except:
        pass
    
    return services

def get_project_hub_status():
    """Get specific info about our project"""
    services = get_launch_services()
    project_hub = next((s for s in services if 'macosgithubprojects' in s.get('label', '')), None)
    return project_hub

def main():
    print("🚀 Project Hub Launch Status Monitor")
    print("=" * 50)
    
    # Get Project Hub status
    project_hub = get_project_hub_status()
    
    if project_hub:
        print(f"\n📱 Project Hub Status:")
        print(f"   Label: {project_hub.get('label', 'N/A')}")
        print(f"   Status: {project_hub.get('status', 'N/A')}")
        print(f"   PID: {project_hub.get('pid', 'N/A')}")
        print(f"   Type: {project_hub.get('type', 'N/A')}")
        
        if project_hub.get('status') == 'Error':
            print("   ❌ Error detected!")
            print("   🔍 Check logs:")
            print("      tail -f /tmp/macosgithubprojects.stderr")
    else:
        print("\n📱 Project Hub Status:")
        print("   ❌ Not found in active services")
        print("   📂 Check installation:")
        print("      ls ~/Library/LaunchAgents/ | grep macosgithubprojects")
    
    print("\n📋 All Launch Services:")
    print("-" * 30)
    services = get_launch_services()
    for service in services[:10]:  # Show first 10
        label = service.get('label', 'N/A')
        status = service.get('status', 'N/A')
        if 'macosgithubprojects' in label:
            print(f"🚨 {label}: {status}")
        else:
            print(f"   {label}: {status}")

if __name__ == "__main__":
    main()