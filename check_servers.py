#!/usr/bin/env python3
"""
Quick server status checker for BSE Trading Application
"""

import requests
import json
import time

def check_server(name, url, timeout=5):
    """Check if a server is responding"""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            print(f"✅ {name}: Running (Status: {response.status_code})")
            return True
        else:
            print(f"⚠️  {name}: Responding but with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ {name}: Not responding (Connection refused)")
        return False
    except requests.exceptions.Timeout:
        print(f"⏰ {name}: Timeout (Server may be starting)")
        return False
    except Exception as e:
        print(f"❌ {name}: Error - {str(e)}")
        return False

def check_api_endpoint(name, url, timeout=5):
    """Check a specific API endpoint"""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {name}: Working")
            return True
        else:
            print(f"⚠️  {name}: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {name}: {str(e)}")
        return False

def main():
    print("🔍 BSE Trading Application - Server Status Check")
    print("=" * 50)
    
    # Check backend server
    print("\n📡 Backend Server (Port 3002):")
    backend_health = check_server("Health Check", "http://localhost:3002/health")
    
    if backend_health:
        print("\n📊 Backend API Endpoints:")
        check_api_endpoint("Stocks List", "http://localhost:3002/api/stocks")
        check_api_endpoint("Single Quote", "http://localhost:3002/api/quote/500325")
        check_api_endpoint("Detailed Health", "http://localhost:3002/health/detailed")
    
    # Check frontend server
    print("\n🌐 Frontend Server (Port 8080):")
    frontend_running = check_server("Frontend", "http://localhost:8080")
    
    if frontend_running:
        check_server("Test Page", "http://localhost:8080/test_backend.html")
    
    print("\n" + "=" * 50)
    
    if backend_health and frontend_running:
        print("🎉 All servers are running successfully!")
        print("\n🚀 Access your application:")
        print("   • Main App: http://localhost:8080")
        print("   • Backend Test: http://localhost:8080/test_backend.html")
        print("   • API Health: http://localhost:3002/health")
    else:
        print("⚠️  Some servers are not responding.")
        print("\n💡 Troubleshooting:")
        print("   • Make sure both servers are started")
        print("   • Check if ports 3002 and 8080 are available")
        print("   • Run: python server.py (for backend)")
        print("   • Run: python start_frontend.py (for frontend)")

if __name__ == "__main__":
    main()