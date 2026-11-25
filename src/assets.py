"""Gerenciador e cache de assets visuais (sprites, ícones e texturas)."""

from pathlib import Path
import pygame

from src.gerador_assets import gerar_todos_os_assets

_SPRITES_CACHE: dict[str, pygame.Surface] = {}
_ICONES_CACHE: dict[str, pygame.Surface] = {}
_PASTA_ASSETS = Path(__file__).resolve().parent.parent / "assets"


def _garantir_existencia_assets() -> None:
    """Verifica se os arquivos PNG existem e, se não existirem, gera-os automaticamente."""
    pasta_sprites = _PASTA_ASSETS / "sprites"
    arquivo_teste = pasta_sprites / "ciclista.png"
    if not arquivo_teste.exists():
        gerar_todos_os_assets()


def carregar_sprite(nome: str) -> pygame.Surface:
    """Carrega ou retorna do cache um sprite da pasta assets/sprites/."""
    if nome in _SPRITES_CACHE:
        return _SPRITES_CACHE[nome]

    _garantir_existencia_assets()
    caminho = _PASTA_ASSETS / "sprites" / f"{nome}.png"
    if not caminho.exists():
        # Fallback de emergência caso algum arquivo específico falte
        gerar_todos_os_assets()

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
    caminho = _PASTA_ASSETS / "ui" / f"{nome}.png"
    if not caminho.exists():
        gerar_todos_os_assets()

    surf = pygame.image.load(str(caminho))
    if pygame.display.get_init() and pygame.display.get_surface() is not None:
        surf = surf.convert_alpha()
    _ICONES_CACHE[nome] = surf
    return surf
