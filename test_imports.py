#!/usr/bin/env python3
"""
Test script to identify import issues in refactored code.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_import(module_name, description):
    """Test importing a module."""
    try:
        __import__(module_name)
        print(f"✅ {description}: Import OK")
        return True
    except Exception as e:
        print(f"❌ {description}: Import failed - {e}")
        return False

def main():
    """Run all import tests."""
    print("🧪 Testing Refactored Code Imports\n")
    
    results = []
    
    # Test shared modules
    results.append(test_import("shared.db", "Shared DB"))
    results.append(test_import("shared.auth", "Shared Auth"))
    results.append(test_import("shared.logging", "Shared Logging"))
    results.append(test_import("shared.middleware", "Shared Middleware"))
    
    # Test payment domain
    results.append(test_import("apps.payments.models", "Payment Models"))
    results.append(test_import("apps.payments.services.payment_service", "Payment Service"))
    results.append(test_import("apps.payments.services.webhook_service", "Webhook Service"))
    results.append(test_import("apps.payments.providers.telebirr", "Telebirr Provider"))
    results.append(test_import("apps.payments.api.routers", "Payment API"))
    
    # Test music domain (from temp directory)
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'temp_music_domain'))
    results.append(test_import("models", "Music Models"))
    results.append(test_import("services", "Music Services"))
    results.append(test_import("api", "Music API"))
    
    print(f"\n📊 Results: {sum(results)}/{len(results)} imports successful")
    
    if not all(results):
        print("\n🔧 Issues found that need fixing:")
        print("1. Fix circular import dependencies")
        print("2. Correct import paths")
        print("3. Resolve missing dependencies")
        return False
    
    print("\n🎉 All imports successful!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
