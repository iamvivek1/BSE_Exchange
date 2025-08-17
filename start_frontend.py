#!/usr/bin/env python3
"""
Simple HTTP server to serve the BSE frontend files
"""

import http.server
import socketserver
import os
import webbrowser
import threading
import time

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def start_server(port=8080):
    """Start the frontend server"""
    
    # Change to the directory containing the HTML files
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    handler = CustomHTTPRequestHandler
    
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"🚀 BSE Frontend Server starting on port {port}")
            print(f"📱 Frontend URL: http://localhost:{port}")
            print(f"🔗 Backend API: http://localhost:3002")
            print(f"📊 Open http://localhost:{port} in your browser")
            print("\n🎯 Features Available:")
            print("   ✅ Real-time stock data")
            print("   ✅ Performance optimizations")
            print("   ✅ Loading states & connection status")
            print("   ✅ Client-side validation")
            print("   ✅ Error handling & recovery")
            print("   ✅ Smooth animations & charts")
            print("\n⚡ Press Ctrl+C to stop the server\n")
            
            # Auto-open browser after a short delay
            def open_browser():
                time.sleep(2)
                try:
                    webbrowser.open(f'http://localhost:{port}')
                    print(f"🌐 Browser opened automatically")
                except:
                    print("💡 Please manually open http://localhost:{port} in your browser")
            
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 Frontend server stopped")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {port} is already in use")
            print(f"💡 Try a different port: python start_frontend.py --port 8081")
        else:
            print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    import sys
    
    port = 8080
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if "--port" in sys.argv:
            try:
                port_index = sys.argv.index("--port") + 1
                port = int(sys.argv[port_index])
            except (ValueError, IndexError):
                print("❌ Invalid port number")
                sys.exit(1)
        elif "--help" in sys.argv or "-h" in sys.argv:
            print("BSE Frontend Server")
            print("Usage: python start_frontend.py [--port PORT]")
            print("Default port: 8080")
            sys.exit(0)
    
    start_server(port)