#!/usr/bin/env python3
"""
FHIR4DS Wheel Package Builder

This script builds a wheel package for the FHIR4DS library.
It handles the complete build process including dependency checking,
cleaning previous builds, and creating a distributable wheel.

Usage:
    python build_wheel.py
    # or
    uv run build_wheel.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def run_command(cmd: list, description: str = None):
    """Run a command and handle errors."""
    if description:
        print(f"🔧 {description}")
    
    print(f"   Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd, 
            check=True, 
            capture_output=True, 
            text=True,
            cwd=Path.cwd()
        )
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running command: {' '.join(cmd)}")
        print(f"   Exit code: {e.returncode}")
        if e.stdout:
            print(f"   Stdout: {e.stdout}")
        if e.stderr:
            print(f"   Stderr: {e.stderr}")
        sys.exit(1)


def check_pyproject_toml():
    """Check if pyproject.toml needs updates for FHIR4DS structure."""
    print("📋 Checking pyproject.toml configuration...")
    
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print("❌ pyproject.toml not found!")
        sys.exit(1)
    
    content = pyproject_path.read_text()
    
    # Check if it references the old structure
    if "sql_on_fhir" in content and "fhir4ds" not in content:
        print("⚠️  WARNING: pyproject.toml appears to reference old 'sql_on_fhir' structure")
        print("   The current package structure uses 'fhir4ds'")
        print("   You may need to update pyproject.toml before building")
        
        # Show what needs to be updated
        print("\n   Suggested updates:")
        print("   - Change package name from 'sql-on-fhir-view-runner' to 'fhir4ds'")
        print("   - Update [tool.hatch.build.targets.wheel] packages to ['fhir4ds']")
        print("   - Update CLI script reference if needed")
        
        response = input("\n   Continue with current pyproject.toml? (y/N): ")
        if response.lower() != 'y':
            print("   Exiting. Please update pyproject.toml first.")
            sys.exit(1)
    
    print("✅ pyproject.toml check complete")


def clean_build_artifacts():
    """Clean previous build artifacts."""
    print("🧹 Cleaning previous build artifacts...")
    
    artifacts = [
        "build/",
        "dist/",
        "*.egg-info",
        "__pycache__",
        ".pytest_cache",
        "*.pyc",
        "*.pyo"
    ]
    
    for pattern in artifacts:
        if "*" in pattern:
            # Handle glob patterns
            import glob
            for path in glob.glob(pattern, recursive=True):
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                    print(f"   Removed directory: {path}")
                elif os.path.isfile(path):
                    os.remove(path)
                    print(f"   Removed file: {path}")
        else:
            # Handle direct paths
            if os.path.exists(pattern):
                if os.path.isdir(pattern):
                    shutil.rmtree(pattern, ignore_errors=True)
                    print(f"   Removed directory: {pattern}")
                elif os.path.isfile(pattern):
                    os.remove(pattern)
                    print(f"   Removed file: {pattern}")
    
    print("✅ Cleanup complete")


def check_dependencies():
    """Check if build dependencies are available."""
    print("📦 Checking build dependencies...")
    
    required_packages = ["build", "wheel"]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package} is available")
        except ImportError:
            print(f"   ⚠️  {package} not found, installing...")
            run_command(
                [sys.executable, "-m", "pip", "install", package],
                f"Installing {package}"
            )
    
    print("✅ Dependencies check complete")


def validate_package_structure():
    """Validate that the package structure is correct."""
    print("🔍 Validating package structure...")
    
    # Check for main package directory
    package_dirs = ["fhir4ds", "sql_on_fhir"]
    found_package = None
    
    for pkg_dir in package_dirs:
        if Path(pkg_dir).exists() and Path(pkg_dir, "__init__.py").exists():
            found_package = pkg_dir
            print(f"   ✅ Found package directory: {pkg_dir}")
            break
    
    if not found_package:
        print(f"   ❌ No valid package directory found! Expected one of: {package_dirs}")
        sys.exit(1)
    
    # Check for critical files
    critical_files = [
        "pyproject.toml",
        "README.md",
        f"{found_package}/__init__.py"
    ]
    
    for file_path in critical_files:
        if Path(file_path).exists():
            print(f"   ✅ Found: {file_path}")
        else:
            print(f"   ❌ Missing: {file_path}")
            sys.exit(1)
    
    print("✅ Package structure validation complete")


def build_wheel():
    """Build the wheel package."""
    print("🏗️  Building wheel package...")
    
    # Use python -m build for modern Python packaging
    build_cmd = [sys.executable, "-m", "build", "--wheel", "--outdir", "dist/"]
    
    run_command(build_cmd, "Building wheel with python -m build")
    
    print("✅ Wheel build complete")


def show_build_results():
    """Show the results of the build."""
    print("📊 Build Results:")
    
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("   ❌ No dist/ directory found!")
        return
    
    wheel_files = list(dist_dir.glob("*.whl"))
    tar_files = list(dist_dir.glob("*.tar.gz"))
    
    if wheel_files:
        print("   🎯 Wheel files created:")
        for wheel_file in wheel_files:
            size = wheel_file.stat().st_size
            print(f"      📦 {wheel_file.name} ({size:,} bytes)")
    
    if tar_files:
        print("   📄 Source distribution files:")
        for tar_file in tar_files:
            size = tar_file.stat().st_size
            print(f"      📦 {tar_file.name} ({size:,} bytes)")
    
    if not wheel_files and not tar_files:
        print("   ❌ No package files found in dist/")
        return
    
    print("\n💡 Installation commands:")
    if wheel_files:
        print(f"   pip install dist/{wheel_files[0].name}")
        print(f"   # or")
        print(f"   pip install {wheel_files[0]}")


def main():
    """Main build function."""
    print("🚀 FHIR4DS Wheel Package Builder")
    print("=" * 50)
    
    try:
        # Step 1: Validate project structure
        validate_package_structure()
        
        # Step 2: Check pyproject.toml
        check_pyproject_toml()
        
        # Step 3: Clean previous builds
        clean_build_artifacts()
        
        # Step 4: Check dependencies
        check_dependencies()
        
        # Step 5: Build the wheel
        build_wheel()
        
        # Step 6: Show results
        show_build_results()
        
        print("\n🎉 Build completed successfully!")
        print("\nNext steps:")
        print("1. Test the wheel: pip install dist/*.whl")
        print("2. Upload to PyPI: twine upload dist/*")
        
    except KeyboardInterrupt:
        print("\n❌ Build interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Build failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()