#!/usr/bin/env python3
"""
Main test runner for Discord Todo Bot

This script runs all test suites from the tests directory.
"""

import sys
import os
import time

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_unit_tests():
    """Run unit tests"""
    print("🧪 Running Unit Tests")
    print("=" * 50)
    
    try:
        from tests.test_todo_bot import run_tests
        return run_tests()
    except Exception as e:
        print(f"❌ Unit test error: {e}")
        return False

def run_integration_tests():
    """Run integration tests"""
    print("\n🔧 Running Integration Tests")
    print("=" * 50)
    
    try:
        from tests.test_integration import run_integration_tests
        return run_integration_tests()
    except Exception as e:
        print(f"❌ Integration test error: {e}")
        return False

def run_comprehensive_tests():
    """Run comprehensive tests"""
    print("\n🔍 Running Comprehensive Tests")
    print("=" * 50)
    
    try:
        from tests.test_comprehensive import run_comprehensive_tests
        return run_comprehensive_tests()
    except Exception as e:
        print(f"❌ Comprehensive test error: {e}")
        return False

def main():
    """Run all test suites"""
    print("🚀 Discord Todo Bot - Master Test Suite")
    print("=" * 70)
    
    start_time = time.time()
    
    # Run all test suites
    unit_success = run_unit_tests()
    integration_success = run_integration_tests()
    comprehensive_success = run_comprehensive_tests()
    
    # Calculate total time
    total_time = time.time() - start_time
    
    # Print final summary
    print(f"\n{'='*70}")
    print("📊 MASTER TEST SUMMARY")
    print(f"{'='*70}")
    print(f"Unit Tests: {'✅ PASSED' if unit_success else '❌ FAILED'}")
    print(f"Integration Tests: {'✅ PASSED' if integration_success else '❌ FAILED'}")
    print(f"Comprehensive Tests: {'✅ PASSED' if comprehensive_success else '❌ FAILED'}")
    print(f"Total Time: {total_time:.2f} seconds")
    
    all_passed = unit_success and integration_success and comprehensive_success
    
    if all_passed:
        print("\n🎉 ALL TEST SUITES PASSED!")
        print("✅ Server downtime recovery: VERIFIED")
        print("✅ Guild isolation: VERIFIED")
        print("✅ Scalability (100 users): VERIFIED")
        print("✅ Edge cases: VERIFIED")
        print("✅ Data persistence: VERIFIED")
        print("\n🚀 Your Discord Todo Bot is ready for production deployment!")
        return 0
    else:
        print("\n⚠️  SOME TEST SUITES FAILED!")
        print("Please fix the failing tests before deployment.")
        return 1

if __name__ == "__main__":
    exit(main()) 