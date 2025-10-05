#!/usr/bin/env python3
"""
Demo script to showcase ModelGuard functionality
"""
import subprocess
import time
import sys
import os
import requests
import tempfile
import trimesh

def create_demo_mesh():
    """Create a demo mesh for testing"""
    # Create a simple cube
    cube = trimesh.creation.box(extents=[20, 20, 20])
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp:
        cube.export(tmp.name)
        return tmp.name

def test_api():
    """Test the API with a demo mesh"""
    print("🧪 Testing ModelGuard API...")
    
    # Create demo mesh
    mesh_file = create_demo_mesh()
    
    try:
        # Test health endpoint
        print("  📡 Checking API health...")
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("  ✅ API is healthy")
            health_data = response.json()
            print(f"     Version: {health_data.get('version', 'unknown')}")
            print(f"     Uptime: {health_data.get('uptime_seconds', 0):.1f}s")
        else:
            print("  ❌ API health check failed")
            return False
        
        # Test validation endpoint
        print("  🔍 Testing model validation...")
        with open(mesh_file, 'rb') as f:
            files = {'file': ('demo_cube.stl', f, 'application/octet-stream')}
            response = requests.post("http://localhost:8000/validate", files=files, timeout=30)
        
        if response.status_code == 200:
            report = response.json()
            print("  ✅ Model validation successful")
            print(f"     Model ID: {report.get('model_id', 'unknown')}")
            print(f"     Decision: {report.get('decision', 'unknown')}")
            print(f"     Processing time: {report.get('processing_time_ms', 0):.2f}ms")
            print(f"     Triangles: {report.get('metrics', {}).get('triangles', 0)}")
            print(f"     Vertices: {report.get('metrics', {}).get('vertices', 0)}")
            
            if report.get('errors'):
                print(f"     Errors: {len(report['errors'])}")
            if report.get('warnings'):
                print(f"     Warnings: {len(report['warnings'])}")
            
            return True
        else:
            print(f"  ❌ Validation failed: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("  ❌ Cannot connect to API. Make sure backend is running on port 8000")
        return False
    except Exception as e:
        print(f"  ❌ Test failed: {str(e)}")
        return False
    finally:
        # Clean up
        try:
            os.unlink(mesh_file)
        except OSError:
            pass

def main():
    """Main demo function"""
    print("🦷 ModelGuard Demo")
    print("=" * 50)
    
    # Check if backend is running
    print("🔍 Checking if backend is running...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            print("✅ Backend is running")
        else:
            print("❌ Backend is not responding properly")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Backend is not running. Please start it with:")
        print("   python start_backend.py")
        return
    
    # Run API tests
    if test_api():
        print("\n🎉 Demo completed successfully!")
        print("\n📋 Next steps:")
        print("   1. Open http://localhost:8501 in your browser for the UI")
        print("   2. Upload a 3D model file (STL, OBJ, PLY)")
        print("   3. View the validation results")
        print("\n📖 API documentation: http://localhost:8000/docs")
    else:
        print("\n❌ Demo failed. Check the backend logs for errors.")

if __name__ == "__main__":
    main()
