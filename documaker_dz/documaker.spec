# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for DocuMaker DZ (Windows single-file GUI executable, no console window)."""

from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH)

datas = [
    (str(ROOT / "localization" / "*.json"), "localization"),
    (str(ROOT / "assets" / "icon.ico"), "assets"),
    (str(ROOT / "assets" / "icon.png"), "assets"),
]

# Bundle ffmpeg.exe & ffprobe.exe automatically if placed in documaker_dz/bin/
bin_dir = ROOT / "bin"
if (bin_dir / "ffmpeg.exe").exists():
    datas.append((str(bin_dir / "ffmpeg.exe"), "bin"))
if (bin_dir / "ffprobe.exe").exists():
    datas.append((str(bin_dir / "ffprobe.exe"), "bin"))

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT.parent)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "edge_tts",
        "httpx",
        "cryptography.fernet",
        "PySide6.QtMultimedia",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "torch",
        "PIL.ImageTk",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="DocuMakerDZ",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Mandatory: no terminal window
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "icon.ico"),
)
