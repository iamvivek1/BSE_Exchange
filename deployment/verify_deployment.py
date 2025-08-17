#!/usr/bin/env python3
"""
Post-deployment verification script for BSE Data Optimization system.
Runs comprehensive tests to ensure deployment is successful.
"""

import requests
import json
import time
import sys
from typing import Dict, List, Any


class DeploymentVerifier:
    """Deployment verification test suite"""
    
    def __init__(self):
        self.backend_url = "http://localhost:5000"
        self.frontend_url = "http://localhost:8080"
        self.monitoring_url = "http://localhost:8081"
        self.test_symbols = ["500325", "500209", "532540"]
        self.results = []
    
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if message:
            print(f"    {message}")
        
        self.results.append({
            "test": test_name,
            "success": success,
            "message": message
        })
    
    def test_backend_health(self) -> bool:
        """Test backend health endpoint"""
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                message = f"Status: {data.get('status', 'unknown')}"
            else:
                message = f"HTTP {response.status_code}"
            
            self.log_test("Backend Health Check", success, message)
            return success
            
        except Exception as e:
            self.log_test("Backend Health Check", False, str(e))
            return False
    
    def test_stock_api_endpoints(self) -> bool:
        """Test stock API endpoints"""
        tests_passed = 0
        total_tests = 3
        
        # Test individual stock quote
        try:
            symbol = self.test_symbols[0]
            response = requests.get(f"{self.backend_url}/api/stock/{symbol}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "symbol" in data and "current_price" in data:
                    tests_passed += 1
                    self.log_test("Individual Stock Quote API", True, f"Symbol: {data['symbol']}")
                else:
                    self.log_test("Individual Stock Quote API", False, "Invalid response format")
            else:
                self.log_test("Individual Stock Quote API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Individual Stock Quote API", False, str(e))
        
        # Test batch stock quotes
        try:
            symbols = ",".join(self.test_symbols)
            response = requests.get(f"{self.backend_url}/api/stocks/batch?symbols={symbols}", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    tests_passed += 1
                    self.log_test("Batch Stock Quotes API", True, f"Retrieved {len(data)} quotes")
                else:
                    self.log_test("Batch Stock Quotes API", False, "Empty or invalid response")
            else:
                self.log_test("Batch Stock Quotes API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Batch Stock Quotes API", False, str(e))
        
        # Test market status
        try:
            response = requests.get(f"{self.backend_url}/api/market/status", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "status" in data:
                    tests_passed += 1
                    self.log_test("Market Status API", True, f"Status: {data['status']}")
                else:
                    self.log_test("Market Status API", False, "Invalid response format")
            else:
                self.log_test("Market Status API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Market Status API", False, str(e))
        
        return tests_passed == total_tests
    
    def test_frontend_accessibility(self) -> bool:
        """Test frontend accessibility"""
        try:
            response = requests.get(self.frontend_url, timeout=10)
            success = response.status_code == 200 and "BSE" in response.text
            
            message = "Frontend loaded successfully" if success else f"HTTP {response.status_code}"
            self.log_test("Frontend Accessibility", success, message)
            return success
            
        except Exception as e:
            self.log_test("Frontend Accessibility", False, str(e))
            return False
    
    def test_websocket_connectivity(self) -> bool:
        """Test WebSocket connectivity (basic check)"""
        try:
            # Check if WebSocket endpoint is available
            response = requests.get(f"{self.backend_url}/socket.io/", timeout=10)
            success = response.status_code in [200, 400]  # 400 is expected for HTTP request to WebSocket
            
            message = "WebSocket endpoint available" if success else f"HTTP {response.status_code}"
            self.log_test("WebSocket Connectivity", success, message)
            return success
            
        except Exception as e:
            self.log_test("WebSocket Connectivity", False, str(e))
            return False
    
    def test_cache_functionality(self) -> bool:
        """Test cache functionality through API response times"""
        try:
            symbol = self.test_symbols[0]
            
            # First request (cache miss)
            start_time = time.time()
            response1 = requests.get(f"{self.backend_url}/api/stock/{symbol}", timeout=10)
            first_request_time = time.time() - start_time
            
            # Second request (should be cached)
            start_time = time.time()
            response2 = requests.get(f"{self.backend_url}/api/stock/{symbol}", timeout=10)
            second_request_time = time.time() - start_time
            
            if response1.status_code == 200 and response2.status_code == 200:
                # Cache is working if second request is significantly faster
                cache_working = second_request_time < first_request_time * 0.8
                
                message = f"First: {first_request_time:.3f}s, Second: {second_request_time:.3f}s"
                self.log_test("Cache Functionality", cache_working, message)
                return cache_working
            else:
                self.log_test("Cache Functionality", False, "API requests failed")
                return False
                
        except Exception as e:
            self.log_test("Cache Functionality", False, str(e))
            return False
    
    def test_monitoring_dashboard(self) -> bool:
        """Test monitoring dashboard"""
        try:
            response = requests.get(f"{self.monitoring_url}/api/health", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                message = f"Status: {data.get('status', 'unknown')}"
            else:
                message = f"HTTP {response.status_code}"
            
            self.log_test("Monitoring Dashboard", success, message)
            return success
            
        except Exception as e:
            self.log_test("Monitoring Dashboard", False, str(e))
            return False
    
    def test_performance_benchmarks(self) -> bool:
        """Test basic performance benchmarks"""
        try:
            symbol = self.test_symbols[0]
            response_times = []
            
            # Make 10 requests and measure response times
            for _ in range(10):
                start_time = time.time()
                response = requests.get(f"{self.backend_url}/api/stock/{symbol}", timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    response_times.append(response_time)
                else:
                    self.log_test("Performance Benchmarks", False, f"Request failed: HTTP {response.status_code}")
                    return False
            
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)
                
                # Performance targets: avg < 500ms, max < 1000ms
                performance_ok = avg_response_time < 0.5 and max_response_time < 1.0
                
                message = f"Avg: {avg_response_time:.3f}s, Max: {max_response_time:.3f}s"
                self.log_test("Performance Benchmarks", performance_ok, message)
                return performance_ok
            else:
                self.log_test("Performance Benchmarks", False, "No successful requests")
                return False
                
        except Exception as e:
            self.log_test("Performance Benchmarks", False, str(e))
            return False
    
    def run_all_tests(self) -> bool:
        """Run all verification tests"""
        print("BSE Data Optimization - Deployment Verification")
        print("=" * 50)
        
        tests = [
            self.test_backend_health,
            self.test_stock_api_endpoints,
            self.test_frontend_accessibility,
            self.test_websocket_connectivity,
            self.test_cache_functionality,
            self.test_monitoring_dashboard,
            self.test_performance_benchmarks
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test in tests:
            if test():
                passed_tests += 1
            time.sleep(1)  # Brief pause between tests
        
        print("\n" + "=" * 50)
        print(f"VERIFICATION SUMMARY: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("✅ DEPLOYMENT VERIFICATION SUCCESSFUL")
            return True
        else:
            print("❌ DEPLOYMENT VERIFICATION FAILED")
            print("\nFailed tests:")
            for result in self.results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
            return False


def main():
    """Main verification function"""
    verifier = DeploymentVerifier()
    
    # Wait for services to be fully ready
    print("Waiting for services to be ready...")
    time.sleep(10)
    
    # Run verification tests
    success = verifier.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()