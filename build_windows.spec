# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Inclui os assets (sprites e ícones de interface)
datas = [
    ('assets', 'assets'),
]

a = Analysis(
    ['jogo.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'pygame',
        'pygame._sdl2',
        'pygame._sdl2.controller',
        'pygame._sdl2.audio',
        'src',
        'src.assets',
        'src.boletim',
        'src.cenario_visual',
        'src.ciclista',
        'src.comparacao',
        'src.configuracao',
        'src.gerador_assets',
        'src.jogo',
        'src.metricas',
        'src.percurso',
        'src.perigos',
        'src.som',
        'src.trafego',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', '_pytest', 'unittest'],
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
    name='DeadLane',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon='assets/ui/icone_jogo.ico',
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
