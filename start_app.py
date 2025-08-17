#!/usr/bin/env python3
"""
BSE Trading Application Startup Script
Starts both backend and frontend servers and opens the application
"""

import subprocess
import time
import webbrowser
import requests
import sys
import os
from threading import Thread

def check_backend():
    """Check if backend is running"""
    try:
        response = requests.get('http://localhost:3002/health', timeout=2)
        return response.status_code == 200
    except:
        return False

def check_frontend():
    """Check if frontend is running"""
    try:
        response = requests.get('http://localhost:8080', timeout=2)
        return response.status_code == 200
    except:
        return False

def start_backend():
    """Start backend server"""
    print("🔧 Starting backend server on port 3002...")
    
    if check_backend():
        print("✅ Backend already running")
        return True
    
    try:
        # Start backend
        subprocess.Popen([sys.executable, 'server.py'], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        
        # Wait for backend to start
        for i in range(15):
            time.sleep(1)
            if check_backend():
                print("✅ Backend started successfully")
                return True
            print(f"   Waiting... ({i+1}/15)")
        
        print("❌ Backend failed to start")
        return False
        
    except Exception as e:
        print(f"❌ Error starting backend: {e}")
        return False

def start_frontend():
    """Start frontend server"""
    print("🌐 Starting frontend server on port 8080...")
    
    if check_frontend():
        print("✅ Frontend already running")
        return True
    
    try:
        # Start frontend
        subprocess.Popen([sys.executable, 'start_frontend.py', '--port', '8080'],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
        
        # Wait for frontend to start
        for i in range(10):
            time.sleep(1)
            if check_frontend():
                print("✅ Frontend started successfully")
                return True
            print(f"   Waiting... ({i+1}/10)")
        
        print("❌ Frontend failed to start")
        return False
        
    except Exception as e:
        print(f"❌ Error starting frontend: {e}")
        return False

def test_application():
    """Test the application endpoints"""
    print("\n🧪 Testing application...")
    
    tests = [
        ('Backend Health', 'http://localhost:3002/health'),
        ('Stocks API', 'http://localhost:3002/api/stocks'),
        ('Frontend', 'http://localhost:8080'),
        ('Simple Test', 'http://localhost:8080/test_simple.html')
    ]
    
    for name, url in tests:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"   ✅ {name}: OK")
            else:
                print(f"   ⚠️  {name}: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ {name}: {str(e)}")

def open_application():
    """Open the application in browser"""
    print("\n🌐 Opening application...")
    
    urls = [
        'http://localhost:8080/test_simple.html',
        'http://localhost:8080/index.html'
    ]
    
    for url in urls:
        try:
            webbrowser.open(url)
            print(f"   🔗 Opened: {url}")
            time.sleep(1)
        except Exception as e:
            print(f"   ❌ Failed to open {url}: {e}")

def main():
    print("🚀 BSE Trading Application Startup")
    print("=" * 40)
    
    # Start backend
    if not start_backend():
        print("\n❌ Cannot start without backend")
        return False
    
    # Start frontend  
    if not start_frontend():
        print("\n❌ Cannot start without frontend")
        return False
    
    # Test application
    test_application()
    
    # Open in browser
    open_application()
    
    print("\n" + "=" * 40)
    print("🎉 Application started successfully!")
    print("\n📋 URLs:")
    print("   • Main App: http://localhost:8080")
    print("   • Simple Test: http://localhost:8080/test_simple.html")
    print("   • Backend API: http://localhost:3002")
    print("   • Backend Health: http://localhost:3002/health")
    
    print("\n💡 Tips:")
    print("   • Check browser console for any errors")
    print("   • Use F12 Developer Tools to debug")
    print("   • Backend logs are in the server.py window")
    
    print("\n⚡ Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Application stopped")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)