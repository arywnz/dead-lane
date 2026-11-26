"""Gerador procedural de sprites e ícones PNG de alta fidelidade para Dead Lane.

Gera os assets visuais na pasta `assets/`, respeitando estritamente
as dimensões físicas e as hitboxes de colisão do jogo:
- Ciclista: base central 24x52 (canvas 32x56 com sombras suaves)
- Carro estacionado: 56x100
- Porta aberta: 68x24
- Carros em movimento: 56x104 (5 variações de modelo/cor)
- Ônibus urbano: 78x220
- Ícones de aviso: perigo de porta, ponto cego, alerta periférico e sinalizações
"""

from __future__ import annotations

import math
from pathlib import Path
import pygame

# Cores do jogo para coerência visual
FUNDO_ESCURO = (18, 29, 27)
ASFALTO = (36, 44, 45)
VERDE_DESTAQUE = (216, 249, 117)
AMARELO_AVISO = (255, 207, 112)
VERMELHO_PERIGO = (255, 120, 111)
LUZ_FREIO = (255, 69, 58)
AZUL_ONIBUS = (43, 108, 176)
AZUL_ONIBUS_TETO = (59, 130, 196)

CORES_CARROS = (
    ((127, 151, 158), (156, 179, 186)),  # Slate
    ((73, 111, 138), (95, 136, 166)),    # Navy
    ((142, 136, 111), (169, 162, 134)),  # Bronze
    ((79, 120, 109), (101, 148, 136)),   # Forest
    ((134, 75, 84), (161, 95, 105)),     # Crimson
)


def _obter_pasta_assets() -> Path:
    base = Path(__file__).resolve().parent.parent / "assets"
    (base / "sprites").mkdir(parents=True, exist_ok=True)
    (base / "ui").mkdir(parents=True, exist_ok=True)
    return base


def gerar_sprite_ciclista(freando: bool = False) -> pygame.Surface:
    """Gera o sprite top-down do ciclista (32x56), centralizado para a hitbox 24x52."""
    surf = pygame.Surface((32, 56), pygame.SRCALPHA)
    cx, cy = 16, 28

    # Sombra projetada suave no solo
    pygame.draw.ellipse(surf, (10, 16, 15, 110), (cx - 10, cy - 22, 20, 46))

    # Pneu traseiro
    pygame.draw.rect(surf, (15, 18, 18), (cx - 2, cy + 8, 4, 16), border_radius=2)
    pygame.draw.line(surf, (180, 190, 190), (cx, cy + 9), (cx, cy + 22), 1)

    # Pneu dianteiro
    pygame.draw.rect(surf, (15, 18, 18), (cx - 2, cy - 24, 4, 16), border_radius=2)
    pygame.draw.line(surf, (180, 190, 190), (cx, cy - 23), (cx, cy - 10), 1)

    # Quadro da bicicleta (tubo superior e garfo)
    pygame.draw.line(surf, (40, 55, 50), (cx, cy + 12), (cx, cy - 16), 3)
    pygame.draw.circle(surf, (60, 80, 75), (cx, cy + 4), 3)

    # Guidão com manoplas e manetes
    pygame.draw.line(surf, (50, 60, 60), (cx - 11, cy - 12), (cx + 11, cy - 12), 4)
    pygame.draw.rect(surf, (20, 25, 25), (cx - 12, cy - 14, 4, 5), border_radius=1)
    pygame.draw.rect(surf, (20, 25, 25), (cx + 8, cy - 14, 4, 5), border_radius=1)
    # Manetes de freio
    pygame.draw.line(surf, (180, 190, 195), (cx - 10, cy - 14), (cx - 6, cy - 16), 1)
    pygame.draw.line(surf, (180, 190, 195), (cx + 10, cy - 14), (cx + 6, cy - 16), 1)

    # Selim (banco da bike)
    pygame.draw.polygon(surf, (25, 30, 30), [(cx, cy + 2), (cx - 4, cy + 10), (cx + 4, cy + 10)])

    # Braços do ciclista estendidos até o guidão
    cor_braco = (80, 110, 95)
    pygame.draw.line(surf, cor_braco, (cx - 7, cy - 3), (cx - 10, cy - 12), 3)
    pygame.draw.line(surf, cor_braco, (cx + 7, cy - 3), (cx + 10, cy - 12), 3)

    # Luvas
    pygame.draw.circle(surf, (30, 35, 35), (cx - 10, cy - 12), 2)
    pygame.draw.circle(surf, (30, 35, 35), (cx + 10, cy - 12), 2)

    # Tronco do ciclista (camisa esportiva de alta visibilidade com faixa refletiva)
    pygame.draw.ellipse(surf, VERDE_DESTAQUE, (cx - 8, cy - 7, 16, 17))
    pygame.draw.ellipse(surf, (180, 220, 85), (cx - 6, cy - 6, 12, 14))
    # Faixa refletiva transversal nas costas
    pygame.draw.line(surf, (245, 255, 230), (cx - 6, cy - 1), (cx + 6, cy - 1), 2)

    # Capacete aerodinâmico visto de cima (com visor e entradas de ar)
    pygame.draw.ellipse(surf, (240, 245, 235), (cx - 5, cy - 13, 10, 13))
    pygame.draw.ellipse(surf, (50, 70, 65), (cx - 3, cy - 11, 6, 8))
    # Visor/ponta aerodinâmica
    pygame.draw.polygon(surf, (30, 40, 40), [(cx, cy - 15), (cx - 3, cy - 12), (cx + 3, cy - 12)])

    # Luz traseira de segurança (freio ativo ou refletor)
    if freando:
        # Halo de luz brilhante de frenagem
        pygame.draw.circle(surf, (255, 69, 58, 70), (cx, cy + 16), 8)
        pygame.draw.circle(surf, LUZ_FREIO, (cx, cy + 16), 4)
        pygame.draw.circle(surf, (255, 230, 230), (cx, cy + 16), 2)
    else:
        # Refletor traseiro vermelho passivo
        pygame.draw.rect(surf, (180, 40, 40), (cx - 2, cy + 14, 4, 3), border_radius=1)

    return surf


def gerar_sprite_carro_estacionado(aviso_ativo: bool = False) -> pygame.Surface:
    """Gera o sprite do carro estacionado na baia (56x100)."""
    surf = pygame.Surface((56, 100), pygame.SRCALPHA)
    rect = pygame.Rect(0, 0, 56, 100)

    # Sombra da carroceria
    pygame.draw.rect(surf, (10, 15, 15, 120), rect.move(2, 2), border_radius=10)

    # Carroceria principal (Sedan Grafite Metálico)
    cor_corpo = (76, 98, 104)
    cor_teto = (98, 125, 133)
    cor_detalhe = (55, 72, 76)
    pygame.draw.rect(surf, cor_corpo, rect, border_radius=10)
    pygame.draw.rect(surf, cor_detalhe, rect, width=2, border_radius=10)

    # Para-brisa dianteiro com gradiente/reflexo
    pygame.draw.rect(surf, (20, 32, 35), (7, 18, 42, 20), border_radius=5)
    pygame.draw.line(surf, (90, 130, 140), (10, 34), (46, 22), 2)  # Reflexo de vidro

    # Vidro traseiro
    pygame.draw.rect(surf, (20, 32, 35), (9, 74, 38, 12), border_radius=4)

    # Vidros laterais
    pygame.draw.rect(surf, (22, 34, 37), (5, 38, 4, 34), border_radius=2)
    pygame.draw.rect(surf, (22, 34, 37), (47, 38, 4, 34), border_radius=2)

    # Teto solar / contorno do teto
    pygame.draw.rect(surf, cor_teto, (9, 39, 38, 33), border_radius=5)
    pygame.draw.rect(surf, (45, 60, 65), (13, 44, 30, 22), border_radius=3)

    # Retrovisores aerodinâmicos
    pygame.draw.rect(surf, cor_corpo, (0, 24, 6, 8), border_radius=2)
    pygame.draw.rect(surf, cor_corpo, (50, 24, 6, 8), border_radius=2)

    # Faróis dianteiros (lentes transparentes)
    pygame.draw.rect(surf, (250, 245, 210), (6, 3, 11, 4), border_radius=2)
    pygame.draw.rect(surf, (250, 245, 210), (39, 3, 11, 4), border_radius=2)

    # Lanternas traseiras
    pygame.draw.rect(surf, (130, 35, 40), (6, 93, 12, 4), border_radius=2)
    pygame.draw.rect(surf, (130, 35, 40), (38, 93, 12, 4), border_radius=2)

    # Linhas de portas
    pygame.draw.line(surf, cor_detalhe, (6, 48), (50, 48), 1)
    pygame.draw.line(surf, cor_detalhe, (6, 72), (50, 72), 1)

    # Se estiver em fase de aviso (prestes a abrir a porta esquerda):
    if aviso_ativo:
        # Pisca-alerta âmbar aceso no retrovisor esquerdo e lanterna traseira esquerda
        pygame.draw.circle(surf, (255, 207, 112, 100), (3, 28), 7)
        pygame.draw.rect(surf, AMARELO_AVISO, (0, 25, 6, 6), border_radius=2)

        pygame.draw.circle(surf, (255, 207, 112, 80), (12, 95), 6)
        pygame.draw.rect(surf, AMARELO_AVISO, (6, 93, 12, 4), border_radius=2)

        # Silhueta da cabeça do motorista no interior preparando para desembarcar
        pygame.draw.circle(surf, (15, 22, 24), (17, 36), 6)
        pygame.draw.circle(surf, (40, 55, 60), (18, 35), 4)

    return surf


def gerar_sprite_porta_aberta() -> pygame.Surface:
    """Gera o sprite da porta aberta (68x24), que se projeta do carro para a esquerda."""
    surf = pygame.Surface((68, 24), pygame.SRCALPHA)

    # A porta se ancora na lateral do carro (lado direito do sprite, x=68) e abre para a esquerda (x=0).
    # Desenho top-down de uma porta aberta a ~75 graus:
    # Dobradiça reforçada em x=65..68, y=10..16
    pygame.draw.rect(surf, (40, 50, 52), (64, 8, 4, 8), border_radius=2)

    # Corpo metálico da porta estendendo-se em diagonal / linha estruturada
    # Linha principal da porta com espessura realista
    pontos_porta = [(66, 12), (6, 4), (5, 12), (64, 18)]
    pygame.draw.polygon(surf, (76, 98, 104), pontos_porta)
    pygame.draw.polygon(surf, (55, 72, 76), pontos_porta, 1)

    # Painel interno da porta (acabamento e puxador interno)
    pontos_painel = [(62, 13), (12, 6), (11, 11), (61, 16)]
    pygame.draw.polygon(surf, (45, 58, 62), pontos_painel)

    # Puxador cromado interno
    pygame.draw.line(surf, (200, 210, 215), (32, 10), (44, 12), 2)

    # Vidro da janela ligeiramente saliente com tom esverdeado/azulado
    pygame.draw.line(surf, (120, 170, 180, 180), (60, 9), (14, 4), 2)

    # Refletor vermelho de segurança na ponta da porta (visível para quem vem atrás!)
    pygame.draw.rect(surf, VERMELHO_PERIGO, (2, 4, 5, 8), border_radius=2)
    pygame.draw.rect(surf, (255, 255, 255), (3, 6, 2, 4), border_radius=1)

    # Contorno de destaque em vermelho para leitura rápida de hitbox em alta velocidade
    pygame.draw.lines(surf, (255, 120, 111, 200), False, [(66, 12), (4, 4), (3, 14), (64, 18)], 2)

    return surf


def gerar_sprite_aviso_zona_porta() -> pygame.Surface:
    """Gera a projeção da área de perigo da porta (68x24) com hachura e alerta."""
    surf = pygame.Surface((68, 24), pygame.SRCALPHA)

    # Fundo suave translúcido
    pygame.draw.rect(surf, (255, 207, 112, 38), (0, 0, 68, 24), border_radius=4)

    # Listras diagonais de perigo amarelo/preto
    passo = 12
    for offset in range(-24, 68 + 24, passo):
        pygame.draw.line(surf, (255, 207, 112, 90), (offset, 0), (offset - 14, 24), 3)

    # Borda tracejada
    for x in range(0, 68, 8):
        pygame.draw.line(surf, AMARELO_AVISO, (x, 0), (min(x + 4, 68), 0), 2)
        pygame.draw.line(surf, AMARELO_AVISO, (x, 23), (min(x + 4, 68), 23), 2)

    pygame.draw.line(surf, AMARELO_AVISO, (0, 0), (0, 24), 2)
    return surf


def gerar_sprite_carro_trafego(variante: int, freando: bool = False) -> pygame.Surface:
    """Gera o sprite de carro em movimento (56x104) para cada variante de cor."""
    surf = pygame.Surface((56, 104), pygame.SRCALPHA)
    rect = pygame.Rect(0, 0, 56, 104)

    cor_corpo, cor_teto = CORES_CARROS[variante % len(CORES_CARROS)]

    # Sombra
    pygame.draw.rect(surf, (10, 14, 14, 110), rect.move(2, 3), border_radius=12)

    # Carroceria
    pygame.draw.rect(surf, cor_corpo, rect, border_radius=12)
    cor_borda = (max(0, cor_corpo[0] - 30), max(0, cor_corpo[1] - 30), max(0, cor_corpo[2] - 30))
    pygame.draw.rect(surf, cor_borda, rect, width=2, border_radius=12)

    # Para-brisa dianteiro
    pygame.draw.rect(surf, (20, 32, 34), (7, 20, 42, 21), border_radius=5)
    pygame.draw.line(surf, (120, 160, 170), (10, 38), (46, 24), 2)  # Reflexo

    # Vidro traseiro
    pygame.draw.rect(surf, (20, 32, 34), (9, 80, 38, 12), border_radius=4)

    # Vidros laterais estreitos
    pygame.draw.rect(surf, (24, 36, 38), (5, 41, 4, 39), border_radius=2)
    pygame.draw.rect(surf, (24, 36, 38), (47, 41, 4, 39), border_radius=2)

    # Teto
    pygame.draw.rect(surf, cor_teto, (9, 43, 38, 34), border_radius=6)

    # Linhas de estilo no teto (teto solar ou frisos)
    if variante % 2 == 0:
        pygame.draw.rect(surf, (30, 42, 45), (14, 48, 28, 20), border_radius=3)
    else:
        pygame.draw.line(surf, cor_borda, (16, 45), (16, 74), 2)
        pygame.draw.line(surf, cor_borda, (40, 45), (40, 74), 2)

    # Retrovisores laterais
    pygame.draw.rect(surf, cor_corpo, (0, 26, 5, 8), border_radius=2)
    pygame.draw.rect(surf, cor_corpo, (51, 26, 5, 8), border_radius=2)

    # Faróis dianteiros com feixes visíveis
    pygame.draw.rect(surf, (254, 250, 215), (7, 2, 11, 4), border_radius=2)
    pygame.draw.rect(surf, (254, 250, 215), (38, 2, 11, 4), border_radius=2)

    # Lanternas traseiras
    if freando:
        # Luzes de freio super iluminadas com halo
        pygame.draw.circle(surf, (255, 69, 58, 90), (13, 98), 8)
        pygame.draw.circle(surf, (255, 69, 58, 90), (43, 98), 8)
        pygame.draw.rect(surf, LUZ_FREIO, (7, 96, 13, 5), border_radius=2)
        pygame.draw.rect(surf, LUZ_FREIO, (36, 96, 13, 5), border_radius=2)
        pygame.draw.rect(surf, (255, 230, 230), (10, 97, 7, 3), border_radius=1)
        pygame.draw.rect(surf, (255, 230, 230), (39, 97, 7, 3), border_radius=1)
    else:
        pygame.draw.rect(surf, (130, 40, 45), (7, 97, 12, 4), border_radius=2)
        pygame.draw.rect(surf, (130, 40, 45), (37, 97, 12, 4), border_radius=2)

    return surf


def gerar_sprite_onibus(seta_direita: bool = False, freando: bool = False) -> pygame.Surface:
    """Gera o sprite do ônibus de transporte público (78x220)."""
    surf = pygame.Surface((78, 220), pygame.SRCALPHA)
    rect = pygame.Rect(0, 0, 78, 220)

    # Sombra
    pygame.draw.rect(surf, (10, 14, 14, 110), rect.move(3, 4), border_radius=14)

    # Carroceria principal azul metropolitano
    pygame.draw.rect(surf, AZUL_ONIBUS, rect, border_radius=14)
    pygame.draw.rect(surf, (24, 62, 105), rect, width=2, border_radius=14)

    # Retrovisores dianteiros salientes e longos
    pygame.draw.rect(surf, (31, 79, 130), (0, 12, 6, 12), border_radius=2)
    pygame.draw.rect(surf, (31, 79, 130), (72, 12, 6, 12), border_radius=2)
    pygame.draw.line(surf, (200, 215, 230), (1, 14), (1, 22), 1)
    pygame.draw.line(surf, (200, 215, 230), (76, 14), (76, 22), 1)

    # Para-brisa panorâmico dianteiro curvado
    pygame.draw.rect(surf, (18, 31, 38), (7, 9, 64, 24), border_radius=6)
    # Palhetas do limpador de para-brisa
    pygame.draw.line(surf, (60, 75, 80), (18, 30), (32, 16), 2)
    pygame.draw.line(surf, (60, 75, 80), (46, 30), (60, 16), 2)
    # Letreiro eletrônico de itinerário ("CENTRO")
    pygame.draw.rect(surf, (10, 15, 12), (18, 12, 42, 6), border_radius=2)
    pygame.draw.rect(surf, (255, 180, 50), (22, 14, 34, 2))  # LEDs laranjas

    # Vidro traseiro
    pygame.draw.rect(surf, (18, 31, 38), (12, 203, 54, 10), border_radius=3)

    # Vidros das janelas laterais contínuas (faixa preta elegante)
    pygame.draw.rect(surf, (15, 25, 30), (4, 38, 5, 160), border_radius=2)
    pygame.draw.rect(surf, (15, 25, 30), (69, 38, 5, 160), border_radius=2)

    # Teto central
    pygame.draw.rect(surf, AZUL_ONIBUS_TETO, (10, 40, 58, 158), border_radius=8)

    # Frisos e vincos longitudinais do teto
    pygame.draw.line(surf, (45, 95, 145), (16, 44), (16, 192), 2)
    pygame.draw.line(surf, (45, 95, 145), (62, 44), (62, 192), 2)

    # Unidades de ar-condicionado no teto (dianteira e traseira)
    for offset_y in (60, 122):
        ac_rect = pygame.Rect(18, offset_y, 42, 28)
        pygame.draw.rect(surf, (207, 226, 243), ac_rect, border_radius=5)
        pygame.draw.rect(surf, (143, 178, 212), ac_rect, width=1, border_radius=5)
        # Grelhas de ventilação
        for gy in range(offset_y + 5, offset_y + 24, 4):
            pygame.draw.line(surf, (120, 155, 190), (ac_rect.left + 5, gy), (ac_rect.right - 5, gy), 1)

    # Alçapões de emergência no teto
    pygame.draw.rect(surf, (37, 87, 141), (25, 170, 28, 18), border_radius=4)
    pygame.draw.rect(surf, (200, 50, 50), (37, 177, 4, 4), border_radius=1)  # Válvula vermelha

    # Faróis dianteiros duplos
    pygame.draw.rect(surf, (254, 250, 215), (8, 2, 14, 5), border_radius=2)
    pygame.draw.rect(surf, (254, 250, 215), (56, 2, 14, 5), border_radius=2)

    # Lanternas traseiras e luzes de freio
    cor_lanterna = LUZ_FREIO if freando else (138, 50, 53)
    pygame.draw.rect(surf, cor_lanterna, (8, 214, 16, 4), border_radius=2)
    pygame.draw.rect(surf, cor_lanterna, (54, 214, 16, 4), border_radius=2)
    if freando:
        pygame.draw.rect(surf, (255, 230, 230), (12, 214, 8, 3), border_radius=1)
        pygame.draw.rect(surf, (255, 230, 230), (58, 214, 8, 3), border_radius=1)

    # Setas piscantes no lado direito para indicar conversão/fechamento à direita
    if seta_direita:
        # Seta dianteira direita
        pygame.draw.rect(surf, AMARELO_AVISO, (72, 18, 6, 16), border_radius=2)
        # Seta intermediária lateral direita
        pygame.draw.rect(surf, AMARELO_AVISO, (72, 105, 6, 12), border_radius=2)
        # Seta traseira direita
        pygame.draw.rect(surf, AMARELO_AVISO, (72, 192, 6, 16), border_radius=2)
        # Halos
        pygame.draw.circle(surf, (255, 207, 112, 120), (75, 26), 9)
        pygame.draw.circle(surf, (255, 207, 112, 120), (75, 200), 9)

    return surf


def gerar_icones_aviso() -> dict[str, pygame.Surface]:
    """Gera ícones vetoriais em PNG para HUD, avisos e tela de instruções."""
    icones = {}

    # 1. Ícone Alerta Triângulo (36x36)
    s_tri = pygame.Surface((36, 36), pygame.SRCALPHA)
    pts = [(18, 3), (34, 32), (2, 32)]
    pygame.draw.polygon(s_tri, (15, 20, 20), pts)
    pygame.draw.polygon(s_tri, AMARELO_AVISO, pts, 3)
    # Exclamação
    pygame.draw.line(s_tri, AMARELO_AVISO, (18, 12), (18, 22), 3)
    pygame.draw.circle(s_tri, AMARELO_AVISO, (18, 27), 2)
    icones["icone_alerta"] = s_tri

    # 2. Ícone Perigo de Porta (48x48)
    s_porta = pygame.Surface((48, 48), pygame.SRCALPHA)
    # Círculo de fundo
    pygame.draw.circle(s_porta, (35, 45, 42), (24, 24), 22)
    pygame.draw.circle(s_porta, AMARELO_AVISO, (24, 24), 22, 2)
    # Carro simplificado à direita
    pygame.draw.rect(s_porta, (120, 150, 155), (28, 12, 12, 24), border_radius=3)
    # Porta se abrindo para a esquerda em alerta
    pygame.draw.line(s_porta, VERMELHO_PERIGO, (28, 18), (12, 24), 4)
    # Exclamação ou raio de perigo
    pygame.draw.line(s_porta, AMARELO_AVISO, (18, 10), (18, 16), 2)
    pygame.draw.circle(s_porta, AMARELO_AVISO, (18, 19), 1)
    icones["icone_porta"] = s_porta

    # 3. Ícone Ponto Cego Angles Morts (48x48)
    s_cego = pygame.Surface((48, 48), pygame.SRCALPHA)
    pygame.draw.circle(s_cego, (35, 45, 42), (24, 24), 22)
    pygame.draw.circle(s_cego, VERMELHO_PERIGO, (24, 24), 22, 2)
    # Ônibus simplificado
    pygame.draw.rect(s_cego, AZUL_ONIBUS, (12, 10, 16, 28), border_radius=3)
    # Zona de ponto cego hachurada à direita
    pygame.draw.rect(s_cego, (255, 120, 111, 100), (28, 16, 14, 18), border_radius=2)
    for off in range(-10, 24, 6):
        pygame.draw.line(s_cego, VERMELHO_PERIGO, (28 + off, 16), (28 + off - 6, 34), 2)
    # Ciclista em risco
    pygame.draw.circle(s_cego, VERDE_DESTAQUE, (34, 25), 3)
    icones["icone_ponto_cego"] = s_cego

    # 4. Ícone Alerta Periférico de Borda (48x48)
    s_borda = pygame.Surface((48, 48), pygame.SRCALPHA)
    pygame.draw.rect(s_borda, (25, 35, 32), (4, 4, 40, 40), border_radius=6)
    pygame.draw.rect(s_borda, VERMELHO_PERIGO, (4, 4, 40, 40), width=4, border_radius=6)
    # Ponto central
    pygame.draw.circle(s_borda, VERDE_DESTAQUE, (24, 24), 5)
    # Setas de perigo apontando para as bordas
    pygame.draw.line(s_borda, AMARELO_AVISO, (12, 24), (6, 24), 2)
    pygame.draw.line(s_borda, AMARELO_AVISO, (36, 24), (42, 24), 2)
    pygame.draw.line(s_borda, AMARELO_AVISO, (24, 12), (24, 6), 2)
    pygame.draw.line(s_borda, AMARELO_AVISO, (24, 36), (24, 42), 2)
    icones["icone_alerta_borda"] = s_borda

    # 5. Ícone Sharrow (ciclorrota na via) (32x32)
    s_sharrow = pygame.Surface((32, 32), pygame.SRCALPHA)
    # Dois chevrons brancos/esverdeados
    for dy in (4, 14):
        pygame.draw.lines(
            s_sharrow,
            (210, 235, 220, 180),
            False,
            [(6, dy + 8), (16, dy), (26, dy + 8)],
            3,
        )
    icones["icone_sharrow"] = s_sharrow

    # 6. Ícone oficial do jogo (256x256) — Placa viária escura com ciclista e zona de perigo
    s_jogo = pygame.Surface((256, 256), pygame.SRCALPHA)
    cor_borda_icone = (56, 189, 248)  # Ciano viário (#38bdf8)
    pontos_placa = [
        (36, 16), (220, 16), (240, 36), (240, 220),
        (220, 240), (36, 240), (16, 220), (16, 36),
    ]
    pygame.draw.polygon(s_jogo, (9, 11, 15), pontos_placa)
    pygame.draw.polygon(s_jogo, cor_borda_icone, pontos_placa, width=10)

    # Faixa de asfalto interna e faixa de risco à direita ("Dead Lane")
    pygame.draw.rect(s_jogo, (24, 28, 36), (42, 38, 172, 180), border_radius=8)
    pygame.draw.rect(s_jogo, (64, 28, 34), (154, 42, 56, 172), border_radius=4)
    pygame.draw.line(s_jogo, (248, 113, 113), (154, 42), (154, 214), 5)
    # Hachura diagonal contida na zona de perigo
    for hy in range(54, 196, 26):
        pygame.draw.line(s_jogo, (251, 191, 36), (162, hy + 16), (204, hy), 5)

    # Tracejado central da faixa segura
    for ty in (48, 106, 164):
        pygame.draw.rect(s_jogo, (100, 112, 132), (102, ty, 6, 34), border_radius=2)

    # Silhueta da bicicleta vista de cima na faixa segura (x=82)
    pygame.draw.rect(s_jogo, (244, 246, 249), (77, 82, 10, 86), border_radius=5)  # quadro/rodas
    pygame.draw.line(s_jogo, (244, 246, 249), (54, 106), (110, 106), 8)  # guidão
    pygame.draw.rect(s_jogo, cor_borda_icone, (65, 118, 34, 42), border_radius=12)  # ciclista
    pygame.draw.circle(s_jogo, (244, 246, 249), (82, 116), 14)  # capacete

    # Seta de direção (sharrow) no topo esquerdo
    pygame.draw.lines(s_jogo, cor_borda_icone, False, [(62, 66), (82, 48), (102, 66)], 6)

    icones["icone_jogo"] = s_jogo

    return icones


def _salvar_ico_multiresolucao(surf: pygame.Surface, caminho_ico: Path) -> None:
    """Salva um arquivo .ico válido com PNGs embutidos (16, 32, 48 e 256 px)."""
    import io
    import struct

    tamanhos = (16, 32, 48, 256)
    imagens_png: list[tuple[int, bytes]] = []
    for tam in tamanhos:
        redim = pygame.transform.smoothscale(surf, (tam, tam))
        buf = io.BytesIO()
        pygame.image.save(redim, buf, "PNG")
        imagens_png.append((tam, buf.getvalue()))

    cabecalho = struct.pack("<HHH", 0, 1, len(imagens_png))
    offset = 6 + 16 * len(imagens_png)
    entradas = bytearray()
    dados = bytearray()
    for tam, png_bytes in imagens_png:
        dim = 0 if tam >= 256 else tam
        entradas.extend(struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png_bytes), offset))
        dados.extend(png_bytes)
        offset += len(png_bytes)

    caminho_ico.write_bytes(cabecalho + entradas + dados)


def gerar_todos_os_assets() -> Path:
    """Gera e salva todos os sprites e ícones PNG necessários."""
    pygame.init()
    pasta_base = _obter_pasta_assets()
    pasta_sprites = pasta_base / "sprites"
    pasta_ui = pasta_base / "ui"

    # Salva sprites do ciclista
    pygame.image.save(gerar_sprite_ciclista(freando=False), str(pasta_sprites / "ciclista.png"))
    pygame.image.save(gerar_sprite_ciclista(freando=True), str(pasta_sprites / "ciclista_freando.png"))

    # Carro estacionado e porta
    pygame.image.save(gerar_sprite_carro_estacionado(aviso_ativo=False), str(pasta_sprites / "carro_estacionado.png"))
    pygame.image.save(gerar_sprite_carro_estacionado(aviso_ativo=True), str(pasta_sprites / "carro_estacionado_aviso.png"))
    pygame.image.save(gerar_sprite_porta_aberta(), str(pasta_sprites / "porta_aberta.png"))
    pygame.image.save(gerar_sprite_aviso_zona_porta(), str(pasta_sprites / "porta_aviso_zona.png"))

    # Carros em movimento
    for i in range(len(CORES_CARROS)):
        pygame.image.save(gerar_sprite_carro_trafego(i, freando=False), str(pasta_sprites / f"carro_{i}.png"))
        pygame.image.save(gerar_sprite_carro_trafego(i, freando=True), str(pasta_sprites / f"carro_{i}_freando.png"))

    # Ônibus
    pygame.image.save(gerar_sprite_onibus(seta_direita=False, freando=False), str(pasta_sprites / "onibus.png"))
    pygame.image.save(gerar_sprite_onibus(seta_direita=True, freando=False), str(pasta_sprites / "onibus_seta.png"))
    pygame.image.save(gerar_sprite_onibus(seta_direita=False, freando=True), str(pasta_sprites / "onibus_freando.png"))
    pygame.image.save(gerar_sprite_onibus(seta_direita=True, freando=True), str(pasta_sprites / "onibus_seta_freando.png"))

    # Ícones de UI e avisos
    icones = gerar_icones_aviso()
    for nome, surf in icones.items():
        pygame.image.save(surf, str(pasta_ui / f"{nome}.png"))
    _salvar_ico_multiresolucao(icones["icone_jogo"], pasta_ui / "icone_jogo.ico")

    return pasta_base


if __name__ == "__main__":
    caminho = gerar_todos_os_assets()
    print(f"Todos os assets foram gerados com sucesso em: {caminho}")
