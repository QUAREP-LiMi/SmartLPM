# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['SmartLPM.py'],
    pathex=[],
    binaries=[],    
    datas=[        
        ('C:/ProgramData/SmartLPM/Config', 'Config'),
        ('Resource\*', 'Resource'),
        ('TLPM_64.dll', '.'),
        ('Resource\icon350x350.ico', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# Collect icon file
icon_file = 'icon350x350.ico'

pyz = PYZ(a.pure)

binaries = [
    ('src\TLPM_64.dll','_internal\TLPM_64.dll'),
]


exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SmartLPM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SmartLPM',
)
