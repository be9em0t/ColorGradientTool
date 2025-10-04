# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_submodules

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
    a.binaries,
    a.datas,
    [],
    name='ColorGradientTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    icon=os.path.join(base_dir, 'resources', 'ColorGradientTool_icon.png')
)