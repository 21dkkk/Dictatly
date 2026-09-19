# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None
ROOT = Path.cwd()

datas = [
    (str(ROOT / 'resources'), 'resources'),
]
binaries = []
hiddenimports = [
    'PySide6.QtSvg',
    'PySide6.QtSvgWidgets',
    'win32gui',
    'win32con',
    'win32process',
    'win32api',
    'win32event',
    'win32com.client',
]

# Collect all dynamic libraries, data files, and submodules for key packages
for pkg in ['ctranslate2', 'faster_whisper', 'sounddevice', 'onnxruntime']:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as e:
        print(f"[Warning] Could not collect all for {pkg}: {e}")

# Collect NVIDIA CUDA & cuDNN DLLs if present in site-packages
site_packages = Path(sys.prefix) / 'Lib' / 'site-packages'
nvidia_dir = site_packages / 'nvidia'
if nvidia_dir.exists():
    for dll_path in nvidia_dir.glob('**/*.dll'):
        binaries.append((str(dll_path), '.'))

a = Analysis(
    ['main.py'],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'unittest', 'pytest', 'IPython'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Dictatly',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'resources' / 'app_icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Dictatly',
)
