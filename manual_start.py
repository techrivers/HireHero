#!/usr/bin/env python3
"""
Manual start script to test the application
"""

import sys
import os
import subprocess
import time

def start_application():
    """Start the application manually."""
    print("🚀 Manual Application Startup")
    print("=" * 40)
    
    # Change to project directory
    project_dir = "/Users/sanaalishah/Desktop/AI-projects/cv-matcher-agent"
    os.chdir(project_dir)
    print(f"📁 Changed to directory: {project_dir}")
    
    # Check if Docker is running
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"🐳 Docker version: {result.stdout.strip()}")
        else:
            print("❌ Docker not available")
            return
    except FileNotFoundError:
        print("❌ Docker not found")
        return
    
    # Try to start with docker-compose
    print("\n🔨 Building and starting containers...")
    try:
        # Build and start
        build_process = subprocess.Popen(
            ["docker-compose", "up", "--build"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor output for a few seconds
        start_time = time.time()
        while time.time() - start_time < 30:
            line = build_process.stdout.readline()
            if line:
                print(f"   {line.strip()}")
                
                # Look for success indicators
                if "listening on" in line.lower() or "server started" in line.lower():
                    print("✅ Server appears to be starting...")
                    break
                    
                if "error" in line.lower() and "failed" in line.lower():
                    print("❌ Build error detected")
                    break
            else:
                time.sleep(0.1)
        
        print("\n🎯 Application startup initiated!")
        print("   Backend should be at: http://localhost:9000")
        print("   Frontend should be at: http://localhost:3000")
        
    except Exception as e:
        print(f"❌ Error starting application: {e}")

if __name__ == "__main__":
    start_application()