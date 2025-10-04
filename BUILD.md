# ColorGradientTool - Build & Distribution Guide

This guide explains how to build ColorGradientTool as a standalone executable for macOS and Windows.

## Prerequisites

1. **Python 3.9+** (tested with Python 3.13)
2. **Required packages** (install via `pip install -r requirements.txt`):
   - PySide6 >= 6.5.0
   - coloraide >= 3.0.0
   - PyInstaller (for building executables)

## Quick Build

### Using the Build Script (Recommended)

```bash
# Make sure you're in the project directory
cd /path/to/ColorGradientTool

# Run the build script
./build.sh
```

The script will automatically detect your platform and build the appropriate executable.

### Manual Build

#### macOS
```bash
pyinstaller macos.spec --clean --noconfirm
```
Output: `dist/ColorGradientTool.app`

#### Windows
```bash
pyinstaller windows.spec --clean --noconfirm
```
Output: `dist/ColorGradientTool.exe`

## Build Files

- **`macos.spec`** - PyInstaller specification for macOS (.app bundle)
- **`windows.spec`** - PyInstaller specification for Windows (.exe)
- **`build.sh`** - Cross-platform build script

## Spec File Details

### macOS Features
- Creates a proper .app bundle
- Includes application icon and resources
- Sets proper app metadata (bundle identifier, version)
- **Always targets arm64 architecture (Apple Silicon)**
- No code signing (for development/testing)
- **Settings stored in `~/Library/Application Support/ColorGradientTool/`**

### Windows Features
- Creates a single executable file
- Includes application icon and resources
- Console-less application (GUI only)
- Optimized for Windows 10/11

### Included Resources
Both builds automatically include:
- `ColorGradient.ini` (settings file)
- `resources/ColorGradientTool_icon.png` (app icon)
- `images/color_colors_themes_icon.png` (UI resources)

## Build Output

### macOS
- **Location**: `dist/ColorGradientTool.app`
- **Size**: ~100MB
- **Run**: Double-click or `open dist/ColorGradientTool.app`

### Windows
- **Location**: `dist/ColorGradientTool.exe`
- **Size**: ~80-100MB
- **Run**: Double-click `ColorGradientTool.exe`

## Settings Location

The application stores its settings in different locations depending on how it's run:

### Development Mode (running main.py directly)
- **Location**: `./ColorGradient.ini` (same directory as main.py)
- **Behavior**: Settings are stored in the project directory

### Packaged Application
#### macOS
- **Location**: `~/Library/Application Support/ColorGradientTool/ColorGradient.ini`
- **Behavior**: Settings are copied from the app bundle on first run, then persist in user directory

#### Windows
- **Location**: `%APPDATA%\ColorGradientTool\ColorGradient.ini`
- **Behavior**: Settings are stored in user's AppData directory

## Troubleshooting

### Common Issues

1. **Missing dependencies**
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

2. **Code signing issues on macOS**
   - The spec file is configured without code signing for development
   - For distribution, update `codesign_identity` in `macos.spec`

3. **Large file size**
   - This is normal for PySide6 applications
   - The builds include the entire Qt framework and Python runtime

4. **Import errors**
   - Check that all hidden imports are included in the spec files
   - Add missing modules to the `hiddenimports` list

### Build Directories

- **`build/`** - Temporary build files (can be deleted)
- **`dist/`** - Final executable output
- **`*.spec`** - PyInstaller configuration files

## Distribution

### macOS
1. Test the .app bundle on the target system
2. For wider distribution, consider:
   - Code signing with Apple Developer certificate
   - Notarization for Gatekeeper compatibility
   - Creating a DMG installer

### Windows
1. Test the .exe on target Windows versions
2. For wider distribution, consider:
   - Code signing with a certificate
   - Creating an installer (NSIS, Inno Setup, etc.)
   - Antivirus false positive mitigation

## Development Notes

- The spec files are optimized for the current project structure
- Resource paths are relative to the project directory
- Hidden imports include all necessary PySide6 and coloraide modules
- Excluded modules (tkinter, matplotlib, etc.) reduce file size

### Git Workflow
- **Tracked**: Source code, spec files, build scripts, documentation
- **Ignored**: Build artifacts (`build/`, `dist/`), Python cache, temporary files
- The `.gitignore` is configured to properly handle PyInstaller builds
- Spec files (`.spec`) are tracked since they contain important build configuration

## Version Information

- PyInstaller: 6.16.0+
- Python: 3.13.x
- PySide6: 6.5.0+
- coloraide: 3.0.0+

For questions or issues, refer to the main project documentation.