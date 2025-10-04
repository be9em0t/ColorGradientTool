#!/bin/bash
# Build script for ColorGradientTool
# Run this script from the project directory

set -e  # Exit on any error

echo "🔧 Building ColorGradientTool..."

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Please run this script from the project directory."
    exit 1
fi

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "❌ Error: PyInstaller not found. Please install it with: pip install pyinstaller"
    exit 1
fi

# Determine platform
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macOS"
    SPEC_FILE="macos.spec"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    PLATFORM="Windows"
    SPEC_FILE="windows.spec"
else
    echo "❌ Error: Unsupported platform: $OSTYPE"
    exit 1
fi

echo "🏗️  Building for $PLATFORM using $SPEC_FILE..."

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/

# Run PyInstaller
echo "⚙️  Running PyInstaller..."
pyinstaller "$SPEC_FILE" --clean --noconfirm

# Check if build was successful
if [[ "$PLATFORM" == "macOS" ]]; then
    if [ -d "dist/ColorGradientTool.app" ]; then
        echo "✅ Build successful! Application created at: dist/ColorGradientTool.app"
        echo "📱 To run: open dist/ColorGradientTool.app"
        
        # Show size
        SIZE=$(du -sh dist/ColorGradientTool.app | cut -f1)
        echo "📦 App size: $SIZE"
    else
        echo "❌ Build failed: Application not found in dist/"
        exit 1
    fi
elif [[ "$PLATFORM" == "Windows" ]]; then
    if [ -f "dist/ColorGradientTool.exe" ]; then
        echo "✅ Build successful! Executable created at: dist/ColorGradientTool.exe"
        echo "📱 To run: dist/ColorGradientTool.exe"
        
        # Show size (if du is available on Windows)
        if command -v du &> /dev/null; then
            SIZE=$(du -sh dist/ColorGradientTool.exe | cut -f1)
            echo "📦 Executable size: $SIZE"
        fi
    else
        echo "❌ Build failed: Executable not found in dist/"
        exit 1
    fi
fi

echo "🎉 Build completed successfully!"