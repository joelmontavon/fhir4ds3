#!/bin/bash
# FHIR4DS Build Script
# Simple script to build wheel packages for FHIR4DS

set -e  # Exit on any error

echo "🚀 FHIR4DS Build Script"
echo "======================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}🔧 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_error "pyproject.toml not found! Are you in the right directory?"
    exit 1
fi

# Check if fhir4ds package exists
if [ ! -d "fhir4ds" ]; then
    print_error "fhir4ds package directory not found!"
    exit 1
fi

print_success "Found FHIR4DS project structure"

# Clean previous builds
print_status "Cleaning previous build artifacts..."
rm -rf build/
rm -rf dist/
rm -rf *.egg-info/
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
print_success "Cleanup complete"

# Check Python version
print_status "Checking Python version..."
python_version=$(python --version 2>&1)
print_success "Using $python_version"

# Check if build dependencies are available
print_status "Checking build dependencies..."

# Check for build module
if ! python -c "import build" 2>/dev/null; then
    print_warning "build module not found, installing..."
    pip install build
fi

# Check for wheel module
if ! python -c "import wheel" 2>/dev/null; then
    print_warning "wheel module not found, installing..."
    pip install wheel
fi

print_success "Build dependencies ready"

# Check if FHIR4DS can be imported
print_status "Validating package structure..."
if python -c "import fhir4ds; print(f'FHIR4DS version: {fhir4ds.__version__}')" 2>/dev/null; then
    print_success "Package structure valid"
else
    print_warning "Could not import fhir4ds, but continuing with build..."
fi

# Build the wheel
print_status "Building wheel package..."
python -m build --wheel --outdir dist/

if [ $? -eq 0 ]; then
    print_success "Wheel build completed successfully"
else
    print_error "Wheel build failed"
    exit 1
fi

# Show results
print_status "Build Results:"
if [ -d "dist" ]; then
    echo ""
    echo "📦 Generated packages:"
    for file in dist/*; do
        if [ -f "$file" ]; then
            size=$(stat --format="%s" "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null || echo "unknown")
            echo "   $(basename "$file") (${size} bytes)"
        fi
    done
    
    echo ""
    echo "💡 Installation commands:"
    wheel_file=$(ls dist/*.whl 2>/dev/null | head -1)
    if [ -n "$wheel_file" ]; then
        echo "   pip install $wheel_file"
        echo "   # or"
        echo "   pip install dist/*.whl"
    fi
    
    echo ""
    echo "🚀 Upload commands (optional):"
    echo "   # Test PyPI:"
    echo "   twine upload --repository testpypi dist/*"
    echo "   # Production PyPI:"
    echo "   twine upload dist/*"
    
else
    print_error "No dist directory found"
    exit 1
fi

print_success "Build script completed successfully!"

echo ""
echo "🎉 FHIR4DS wheel package is ready!"
echo ""
echo "Next steps:"
echo "1. Test installation: pip install dist/*.whl"
echo "2. Run tests: make test or python -m pytest"
echo "3. Upload to PyPI: twine upload dist/*"