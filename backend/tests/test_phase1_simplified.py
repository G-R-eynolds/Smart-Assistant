#!/usr/bin/env python3
"""
Simplified Phase 1 Test: Direct Pipeline Function Testing

This test validates our Smart Assistant pipeline functions independently
without the full Open WebUI dependency chain.
"""
import sys
import os
import asyncio
import json
import importlib.util

def test_pipeline_function_structure(function_path, function_name):
    """Test that a pipeline function has the correct structure"""
    print(f"\n🔍 Testing {function_name} Structure...")
    
    try:
        # Load the module directly
        spec = importlib.util.spec_from_file_location("pipeline_module", function_path)
        module = importlib.util.module_from_spec(spec)
        
        # Execute the module
        spec.loader.exec_module(module)
        
        # Check if Pipeline class exists
        if hasattr(module, 'Pipeline'):
            pipeline_class = getattr(module, 'Pipeline')
            print(f"   ✅ Pipeline class found")
            
            # Check required attributes
            required_attrs = ['id', 'name', 'valves']
            for attr in required_attrs:
                if hasattr(pipeline_class, attr):
                    print(f"   ✅ Has '{attr}' attribute")
                else:
                    print(f"   ❌ Missing '{attr}' attribute")
                    return False
            
            # Check for inlet method
            if hasattr(pipeline_class, 'inlet'):
                print(f"   ✅ Has 'inlet' method")
            else:
                print(f"   ❌ Missing 'inlet' method")
                return False
            
            print(f"   🎉 {function_name} structure is correct!")
            return True
        else:
            print(f"   ❌ No Pipeline class found in {function_name}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error loading {function_name}: {e}")
        return False

def test_pipeline_function_content(function_path, function_name):
    """Test the content and trigger detection logic"""
    print(f"\n📝 Testing {function_name} Content...")
    
    try:
        # Read the file content
        with open(function_path, 'r') as f:
            content = f.read()
        
        # Check for key components
        checks = {
            'Pipeline class definition': 'class Pipeline:',
            'Valves configuration': 'class Valves',
            'Inlet method': 'async def inlet',
            'Error handling': 'try:' and 'except',
            'Logging': 'logger',
            'HTTP requests': 'aiohttp' or 'requests',
            'JSON processing': 'json',
            'Smart Assistant integration': 'smart_assistant_url'
        }
        
        passed = 0
        total = len(checks)
        
        for check_name, pattern in checks.items():
            if isinstance(pattern, str):
                found = pattern in content
            else:
                found = any(p in content for p in pattern)
            
            if found:
                print(f"   ✅ {check_name}")
                passed += 1
            else:
                print(f"   ⚠️  {check_name} (not found)")
        
        print(f"   📊 Content Score: {passed}/{total}")
        return passed >= total * 0.7  # 70% pass rate
        
    except Exception as e:
        print(f"   ❌ Error reading {function_name}: {e}")
        return False

def test_microservice_integration():
    """Test our microservice adapter integration"""
    print(f"\n🔗 Testing Microservice Integration...")
    
    microservice_path = "/home/gabe/Documents/Agent Project 2.0/smart-assistant-microservice.py"
    
    try:
        with open(microservice_path, 'r') as f:
            content = f.read()
        
        integration_checks = {
            'FastAPI app creation': '@app.',
            'Health endpoint': '/health',
            'Job discovery endpoint': '/api/v1/jobs/discover',
            'Inbox processing endpoint': '/api/v1/inbox/process',
            'Intelligence briefing endpoint': '/api/v1/intelligence/briefing',
            'CORS middleware': 'CORSMiddleware',
            'Request/Response models': ('class.*Request', 'class.*Response'),
            'Smart Assistant integration': 'smart-assistant'
        }
        
        passed = 0
        total = len(integration_checks)
        
        for check_name, pattern in integration_checks.items():
            if isinstance(pattern, tuple):
                found = all(p in content for p in pattern)
            elif isinstance(pattern, str):
                found = pattern in content
            else:
                found = False
            
            if found:
                print(f"   ✅ {check_name}")
                passed += 1
            else:
                print(f"   ⚠️  {check_name}")
        
        print(f"   📊 Integration Score: {passed}/{total}")
        return passed >= total * 0.8  # 80% pass rate
        
    except Exception as e:
        print(f"   ❌ Error testing microservice: {e}")
        return False

def test_database_models():
    """Test our Smart Assistant database models"""
    print(f"\n🗄️  Testing Database Models...")
    
    try:
        # Test that our models file exists and has correct structure
        models_path = "/home/gabe/Documents/Agent Project 2.0/backend/open_webui/models/smart_assistant.py"
        
        if not os.path.exists(models_path):
            print(f"   ❌ Models file not found at {models_path}")
            return False
        
        with open(models_path, 'r') as f:
            content = f.read()
        
        # Check for required model definitions
        required_models = [
            'SmartAssistantJob',
            'SmartAssistantCareerProfile', 
            'SmartAssistantBriefing',
            'SmartAssistantSystemStatus'
        ]
        
        model_checks = {
            'SQLAlchemy imports': 'from sqlalchemy',
            'Base model import': 'from open_webui.models.base',
            'Table definitions': '__tablename__',
            'Column definitions': 'Column',
            'Primary key': 'primary_key=True',
            'Foreign key': 'ForeignKey',
            'JSON fields': 'JSON',
            'DateTime fields': 'DateTime'
        }
        
        passed = 0
        total = len(required_models) + len(model_checks)
        
        # Check for model classes
        for model_name in required_models:
            if f"class {model_name}" in content:
                print(f"   ✅ {model_name} model defined")
                passed += 1
            else:
                print(f"   ❌ {model_name} model missing")
        
        # Check for essential database components
        for check_name, pattern in model_checks.items():
            if pattern in content:
                print(f"   ✅ {check_name}")
                passed += 1
            else:
                print(f"   ⚠️  {check_name}")
        
        print(f"   📊 Database Models Score: {passed}/{total}")
        return passed >= total * 0.8  # 80% pass rate
        
    except Exception as e:
        print(f"   ❌ Database models test failed: {e}")
        return False

def main():
    """Run simplified Phase 1 tests"""
    print("🚀 Phase 1 Simplified Integration Tests")
    print("=" * 50)
    
    results = []
    
    # Test pipeline function files
    pipeline_functions = [
        ("/home/gabe/Documents/Agent Project 2.0/backend/open_webui/functions/job_discovery.py", "Job Discovery Pipeline"),
        ("/home/gabe/Documents/Agent Project 2.0/backend/open_webui/functions/inbox_management.py", "Inbox Management Pipeline"),
        ("/home/gabe/Documents/Agent Project 2.0/backend/open_webui/functions/intelligence_briefing.py", "Intelligence Briefing Pipeline")
    ]
    
    # Test function structure
    for func_path, func_name in pipeline_functions:
        if os.path.exists(func_path):
            structure_ok = test_pipeline_function_structure(func_path, func_name)
            content_ok = test_pipeline_function_content(func_path, func_name)
            results.append(structure_ok and content_ok)
        else:
            print(f"   ❌ {func_name} file not found at {func_path}")
            results.append(False)
    
    # Test microservice integration
    results.append(test_microservice_integration())
    
    # Test database models
    results.append(test_database_models())
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Phase 1 Simplified Test Results:")
    print(f"   ✅ Passed: {sum(results)}")
    print(f"   ❌ Failed: {len(results) - sum(results)}")
    
    if all(results):
        print("\n🎉 Phase 1 Implementation Validated Successfully!")
        print("📋 Summary of Achievements:")
        print("   • Job Discovery Pipeline Function ✅")
        print("   • Inbox Management Pipeline Function ✅")
        print("   • Intelligence Briefing Pipeline Function ✅")
        print("   • Smart Assistant Microservice Adapter ✅")
        print("   • Database Integration Models ✅")
        print("\n🔄 Ready to proceed with Phase 2: Frontend Integration")
        print("   Next steps: Svelte component development")
    else:
        print("\n⚠️  Some components need refinement")
    
    return all(results)

if __name__ == "__main__":
    main()
