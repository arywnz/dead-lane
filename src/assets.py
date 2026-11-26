"""Gerenciador e cache de assets visuais (sprites, ícones e texturas)."""

from __future__ import annotations

import sys
from pathlib import Path
import pygame

from src.gerador_assets import gerar_todos_os_assets

_SPRITES_CACHE: dict[str, pygame.Surface] = {}
_ICONES_CACHE: dict[str, pygame.Surface] = {}


def obter_caminho_base() -> Path:
    """Retorna o diretório base da aplicação, compatível com execução normal e PyInstaller (_MEIPASS)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def obter_pasta_assets() -> Path:
    """Retorna a pasta assets baseada no diretório raiz do projeto ou executável."""
    return obter_caminho_base() / "assets"


def _garantir_existencia_assets() -> None:
    """Verifica se os arquivos PNG existem e, se não existirem (e não estiver frozen), gera-os."""
    pasta_assets = obter_pasta_assets()
    pasta_sprites = pasta_assets / "sprites"
    arquivo_teste = pasta_sprites / "ciclista.png"
    icone_jogo = pasta_assets / "ui" / "icone_jogo.png"
    if not arquivo_teste.exists() or not icone_jogo.exists():
        # No modo empacotado (frozen), os assets já devem estar presentes via spec; se não, tenta gerar
        try:
            gerar_todos_os_assets()
        except Exception:
            pass


def carregar_sprite(nome: str) -> pygame.Surface:
    """Carrega ou retorna do cache um sprite da pasta assets/sprites/."""
    if nome in _SPRITES_CACHE:
        return _SPRITES_CACHE[nome]

    _garantir_existencia_assets()
    pasta_assets = obter_pasta_assets()
    caminho = pasta_assets / "sprites" / f"{nome}.png"
    if not caminho.exists():
        # Fallback de emergência caso algum arquivo específico falte
        try:
            gerar_todos_os_assets()
        except Exception:
            pass

    surf = pygame.image.load(str(caminho))
    if pygame.display.get_init() and pygame.display.get_surface() is not None:
        surf = surf.convert_alpha()
    _SPRITES_CACHE[nome] = surf
    return surf


def carregar_icone(nome: str) -> pygame.Surface:
    """Carrega ou retorna do cache um ícone da pasta assets/ui/."""
    if nome in _ICONES_CACHE:
        return _ICONES_CACHE[nome]

    _garantir_existencia_assets()
    pasta_assets = obter_pasta_assets()
    caminho = pasta_assets / "ui" / f"{nome}.png"
    if not caminho.exists():
        try:
            gerar_todos_os_assets()
        except Exception:
            pass

    surf = pygame.image.load(str(caminho))
    if pygame.display.get_init() and pygame.display.get_surface() is not None:
        surf = surf.convert_alpha()
    _ICONES_CACHE[nome] = surf
    return surf
