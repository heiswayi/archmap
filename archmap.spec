# PyInstaller spec — builds a single-file `archmap` binary.
# Build: pyinstaller archmap.spec   (run on each target OS; PyInstaller does not cross-compile)
from PyInstaller.utils.hooks import collect_data_files

# Pulls in templates/template.html (and any other package data) cross-platform,
# so we avoid OS-specific --add-data path separators.
datas = collect_data_files("archmap")

a = Analysis(
    ["pyinstaller_entry.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
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
    name="archmap",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
