# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

# Project base directory
base_dir = os.path.abspath('.')

# Additional data files (INI, resources, images)
additional_datas = [
    (os.path.join(base_dir, 'ColorGradient.ini'), '.'),
    (os.path.join(base_dir, 'resources', 'ColorGradientTool_icon.png'), 'resources'),
    (os.path.join(base_dir, 'images', 'color_colors_themes_icon.png'), 'images')
]

a = Analysis(
    ['main.py'],
    pathex=[base_dir],
    binaries=[],
    datas=additional_datas,
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'coloraide'
    ] + collect_submodules('coloraide'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ColorGradientTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch='arm64',  # Always target arm64 for Apple Silicon
    codesign_identity=None,  # Disable code signing for now
    entitlements_file=None,
)

app = BUNDLE(
    exe,
    a.binaries,
    a.datas,
    name='ColorGradientTool.app',
    icon=os.path.join(base_dir, 'resources', 'ColorGradientTool_icon.png'),
    bundle_identifier='com.yourcompany.colorgradienttool',
    version='1.0.0',
    info_plist={
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.15',  # macOS Catalina
    }
)