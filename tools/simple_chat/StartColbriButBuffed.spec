# -*- mode: python ; coding: utf-8 -*-
# Build on Windows:
#   pyinstaller --noconfirm StartColbriButBuffed.spec
#   copy dist\StartColbriButBuffed.exe ..\..\desktop\dist\

a = Analysis(
    ['start_colbri.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='StartColbriButBuffed',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
