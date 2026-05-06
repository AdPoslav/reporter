# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Reporter
# Build with:  pyinstaller reporter.spec --clean --noconfirm

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates',       'templates'),
        ('static',          'static'),
        ('export_template', 'export_template'),
    ],
    hiddenimports=[
        'xlrd',
        'xlwt',
        'xlutils',
        'xlutils.copy',
        'xlutils.filter',
        'msoffcrypto',
        'olefile',
        'flask',
        'jinja2',
        'jinja2.ext',
        'werkzeug',
        'werkzeug.serving',
        'werkzeug.routing',
        'click',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'PIL'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Reporter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # no black terminal window
    disable_windowed_traceback=False,
    icon=None,              # optional: set to 'reporter.ico' if you have one
)
