#!/usr/bin/env python3
"""
Debug script for BSE Trading Application
Starts servers and opens debug pages
"""

import subprocess
import time
import webbrowser
import requests
import sys
import os

def check_port(port):
    """Check if a port is available"""
    try:
        response = requests.get(f'http://localhost:{port}/health', timeout=2)
        return response.status_code == 200
    except:
        return False

def start_backend():
    """Start the backend server"""
    print("🔧 Starting backend server on port 3002...")
    
    # Check if already running
    if check_port(3002):
        print("✅ Backend already running on port 3002")
        return True
    
    try:
        # Start backend in background
        subprocess.Popen([sys.executable, 'server.py'], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        
        # Wait for backend to start
        for i in range(10):
            time.sleep(1)
            if check_port(3002):
                print("✅ Backend started successfully")
                return True
            print(f"   Waiting for backend... ({i+1}/10)")
        
        print("❌ Backend failed to start")
        return False
        
    except Exception as e:
        print(f"❌ Error starting backend: {e}")
        return False

def start_frontend():
    """Start the frontend server"""
    print("🌐 Starting frontend server on port 8080...")
    
    try:
        # Check if port is available
        try:
            response = requests.get('http://localhost:8080', timeout=2)
            print("✅ Frontend already running on port 8080")
            return True
        except:
            pass
        
        # Start frontend in background
        subprocess.Popen([sys.executable, 'start_frontend.py', '--port', '8080'],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
        
        # Wait for frontend to start
        for i in range(5):
            time.sleep(1)
            try:
                response = requests.get('http://localhost:8080', timeout=2)
                print("✅ Frontend started successfully")
                return True
            except:
                print(f"   Waiting for frontend... ({i+1}/5)")
        
        print("❌ Frontend failed to start")
        return False
        
    except Exception as e:
        print(f"❌ Error starting frontend: {e}")
        return False

def test_backend():
    """Test backend endpoints"""
    print("\n🧪 Testing backend endpoints...")
    
    endpoints = [
        ('Health Check', 'http://localhost:3002/health'),
        ('Stocks List', 'http://localhost:3002/api/stocks'),
        ('Single Quote', 'http://localhost:3002/api/quote/500325')
    ]
    
    for name, url in endpoints:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"   ✅ {name}: OK")
            else:
                print(f"   ⚠️  {name}: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ {name}: {str(e)}")

def open_debug_pages():
    """Open debug pages in browser"""
    print("\n🌐 Opening debug pages...")
    
    pages = [
        ('Backend Test', 'http://localhost:8080/test_backend.html'),
        ('Frontend Test', 'http://localhost:8080/test_frontend.html'),
        ('Main Application', 'http://localhost:8080/index.html')
    ]
    
    for name, url in pages:
        try:
            webbrowser.open(url)
            print(f"   🔗 Opened: {name}")
            time.sleep(1)  # Small delay between opens
        except Exception as e:
            print(f"   ❌ Failed to open {name}: {e}")

def main():
    print("🔍 BSE Trading Application - Debug Mode")
    print("=" * 50)
    
    # Start backend
    if not start_backend():
        print("\n❌ Cannot continue without backend")
        return
    
    # Start frontend
    if not start_frontend():
        print("\n❌ Cannot continue without frontend")
        return
    
    # Test backend
    test_backend()
    
    # Open debug pages
    open_debug_pages()
    
    print("\n" + "=" * 50)
    print("🎉 Debug setup complete!")
    print("\n📋 Debug URLs:")
    print("   • Backend API: http://localhost:3002")
    print("   • Frontend App: http://localhost:8080")
    print("   • Backend Test: http://localhost:8080/test_backend.html")
    print("   • Frontend Test: http://localhost:8080/test_frontend.html")
    print("\n💡 Check browser console for detailed logs")
    print("⚡ Press Ctrl+C to stop servers")
    
    try:
        # Keep script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Debug session ended")

if __name__ == "__main__":
    main()