from dataclasses import dataclass
import math

import pygame

from src.ciclista import Ciclista
from src.configuracao import (
    ALTURA_JANELA,
    CENTRO_PISTA_X,
    CICLISTA_TELA_Y,
    COMPRIMENTO_PERCURSO_M,
    COMPRIMENTO_TRECHO_M,
    ESCALA_PISTA_PX_POR_M,
    FAIXAS_PISTA,
    LARGURA_PISTA,
    NOMES_TRECHOS,
    VELOCIDADE_MAXIMA_MPS,
)
from src.percurso import Percurso
from src.perigos import FasePontoCego, FasePorta, PerigoPontoCego, PerigoPorta
from src.trafego import TipoVeiculo, Veiculo

FUNDO = "#121d1b"
ASFALTO = "#242c2d"
BORDA_PISTA = "#465451"
CALCADA = "#2e3b37"
MARCACAO_FAIXA = "#687675"
TEXTO_PRINCIPAL = "#edf1e6"
TEXTO_SECUNDARIO = "#aebdb4"
DESTAQUE = "#d8f975"
PAINEL = "#1b2824"
AVISO = "#ffcf70"
PERIGO = "#ff786f"
LUZ_FREIO = "#ff453a"
AZUL_ONIBUS = "#2b6cb0"
AZUL_ONIBUS_TETO = "#3b82c4"

_CORES_CARROS: tuple[tuple[str, str], ...] = (
    ("#7f979e", "#9cb3ba"),
    ("#496f8a", "#5f88a6"),
    ("#8e886f", "#a9a286"),
    ("#4f786d", "#659488"),
    ("#864b54", "#a15f69"),
)


@dataclass(frozen=True)
class PaletaTrecho:
    fundo: str
    asfalto: str
    trilho_pneu: str
    calcada: str
    meio_fio: str
    bloco_urbano: str
    telhado_urbano: str
    copa_arvore: str
    copa_luz: str
    sombra_dx: int
    sombra_dy: int
    farois_ativos: bool
    rotulo_densidade: str


PALETAS_TRECHO: tuple[PaletaTrecho, ...] = (
    PaletaTrecho(
        fundo="#121d1b",
        asfalto="#242c2d",
        trilho_pneu="#202829",
        calcada="#2e3b37",
        meio_fio="#4c5d58",
        bloco_urbano="#182623",
        telhado_urbano="#1f302c",
        copa_arvore="#2b5246",
        copa_luz="#3d6e5e",
        sombra_dx=6,
        sombra_dy=4,
        farois_ativos=False,
        rotulo_densidade="Tráfego leve",
    ),
    PaletaTrecho(
        fundo="#131f1c",
        asfalto="#273031",
        trilho_pneu="#222b2c",
        calcada="#32413c",
        meio_fio="#556661",
        bloco_urbano="#1b2a26",
        telhado_urbano="#223530",
        copa_arvore="#335f50",
        copa_luz="#477e6b",
        sombra_dx=2,
        sombra_dy=3,
        farois_ativos=False,
        rotulo_densidade="Tráfego moderado",
    ),
    PaletaTrecho(
        fundo="#0f1716",
        asfalto="#1e2526",
        trilho_pneu="#192021",
        calcada="#27332f",
        meio_fio="#414e4a",
        bloco_urbano="#14201d",
        telhado_urbano="#1a2925",
        copa_arvore="#23453b",
        copa_luz="#325c4f",
        sombra_dx=-6,
        sombra_dy=5,
        farois_ativos=True,
        rotulo_densidade="Tráfego intenso",
    ),
)

_CONE_FAROL_CACHE: pygame.Surface | None = None
_HALO_POSTE_CACHE: pygame.Surface | None = None


def _cone_farol() -> pygame.Surface:
    global _CONE_FAROL_CACHE
    if _CONE_FAROL_CACHE is None:
        surf = pygame.Surface((68, 72), pygame.SRCALPHA)
        pygame.draw.polygon(surf, (254, 249, 195, 58), [(24, 72), (44, 72), (66, 0), (2, 0)])
        pygame.draw.polygon(surf, (254, 249, 195, 28), [(28, 72), (40, 72), (56, 0), (12, 0)])
        _CONE_FAROL_CACHE = surf
    return _CONE_FAROL_CACHE


def _halo_poste() -> pygame.Surface:
    global _HALO_POSTE_CACHE
    if _HALO_POSTE_CACHE is None:
        surf = pygame.Surface((84, 84), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 219, 138, 22), (42, 42), 40)
        pygame.draw.circle(surf, (255, 219, 138, 34), (42, 42), 22)
        _HALO_POSTE_CACHE = surf
    return _HALO_POSTE_CACHE


def _y_tela(distancia_ciclista_m: float, distancia_alvo_m: float) -> float:
    return CICLISTA_TELA_Y + (distancia_ciclista_m - distancia_alvo_m) * ESCALA_PISTA_PX_POR_M


def desenhar_cenario_avenida(
    tela: pygame.Surface,
    distancia_m: float,
    indice_trecho: int,
) -> None:
    paleta = PALETAS_TRECHO[min(indice_trecho, len(PALETAS_TRECHO) - 1)]
    esquerda_pista = CENTRO_PISTA_X - LARGURA_PISTA // 2
    direita_pista = esquerda_pista + LARGURA_PISTA
    largura_faixa = LARGURA_PISTA // FAIXAS_PISTA

    # Área urbana esquerda e calçada esquerda
    pygame.draw.rect(tela, paleta.fundo, (0, 0, esquerda_pista - 36, ALTURA_JANELA))
    pygame.draw.rect(tela, paleta.calcada, (esquerda_pista - 36, 0, 36, ALTURA_JANELA))

    # Baia de estacionamento e calçada direita (mantendo folga limpa até o painel em x=748)
    pygame.draw.rect(tela, "#202a2a", (direita_pista, 0, 62, ALTURA_JANELA))
    pygame.draw.rect(tela, paleta.calcada, (direita_pista + 62, 0, 24, ALTURA_JANELA))

    # Leito da avenida
    pygame.draw.rect(tela, paleta.asfalto, (esquerda_pista, 0, LARGURA_PISTA, ALTURA_JANELA))

    # Trilhos discretos de rodagem nas 3 faixas
    for faixa in range(FAIXAS_PISTA):
        cx = esquerda_pista + faixa * largura_faixa + largura_faixa // 2
        pygame.draw.rect(tela, paleta.trilho_pneu, (cx - 26, 0, 14, ALTURA_JANELA))
        pygame.draw.rect(tela, paleta.trilho_pneu, (cx + 12, 0, 14, ALTURA_JANELA))

    # Bordas contínuas e sombra do meio-fio
    pygame.draw.line(tela, paleta.meio_fio, (esquerda_pista, 0), (esquerda_pista, ALTURA_JANELA), 4)
    pygame.draw.line(tela, paleta.meio_fio, (direita_pista, 0), (direita_pista, ALTURA_JANELA), 4)
    pygame.draw.line(tela, BORDA_PISTA, (direita_pista + 62, 0), (direita_pista + 62, ALTURA_JANELA), 3)

    # Divisórias tracejadas das faixas
    espacamento_tracos = 110
    deslocamento = int(distancia_m * ESCALA_PISTA_PX_POR_M) % espacamento_tracos
    for faixa in range(1, FAIXAS_PISTA):
        faixa_x = esquerda_pista + faixa * LARGURA_PISTA // FAIXAS_PISTA
        for y in range(deslocamento - espacamento_tracos, ALTURA_JANELA, espacamento_tracos):
            pygame.draw.rect(tela, MARCACAO_FAIXA, (faixa_x - 2, y, 4, 52), border_radius=2)

    # Demarcação de vagas na baia direita
    passo_vaga = 140
    desloc_vaga = int(distancia_m * ESCALA_PISTA_PX_POR_M) % passo_vaga
    for y in range(desloc_vaga - passo_vaga, ALTURA_JANELA, passo_vaga):
        pygame.draw.line(tela, "#3d4c49", (direita_pista + 6, y), (direita_pista + 56, y), 2)

    # Símbolos de ciclorrota (sharrow) na faixa direita
    passo_sharrow = 270
    desloc_sharrow = int(distancia_m * ESCALA_PISTA_PX_POR_M) % passo_sharrow
    cx_direita = esquerda_pista + 2 * largura_faixa + largura_faixa // 2
    for y in range(desloc_sharrow - passo_sharrow, ALTURA_JANELA + 40, passo_sharrow):
        pygame.draw.lines(
            tela,
            "#3c4d4a",
            False,
            [(cx_direita - 14, y + 10), (cx_direita, y), (cx_direita + 14, y + 10)],
            3,
        )
        pygame.draw.lines(
            tela,
            "#3c4d4a",
            False,
            [(cx_direita - 14, y + 20), (cx_direita, y + 10), (cx_direita + 14, y + 20)],
            3,
        )

    # Quadras urbanas, árvores e postes à esquerda
    passo_bloco_m = 28.0
    primeiro_indice = math.floor((distancia_m - 12.0) / passo_bloco_m)
    ultimo_indice = math.ceil((distancia_m + 24.0) / passo_bloco_m)
    for idx in range(primeiro_indice, ultimo_indice + 1):
        marco_m = idx * passo_bloco_m
        y_centro = round(_y_tela(distancia_m, marco_m))
        largura_bloco = 132 if idx % 2 == 0 else 112
        altura_bloco = 180 if idx % 3 != 0 else 220
        bx = 22 if idx % 2 == 0 else 36
        bloco_rect = pygame.Rect(bx, y_centro - altura_bloco // 2, largura_bloco, altura_bloco)
        pygame.draw.rect(tela, paleta.bloco_urbano, bloco_rect, border_radius=10)
        pygame.draw.rect(tela, paleta.telhado_urbano, bloco_rect.inflate(-24, -28), border_radius=6)

        # Árvore estilizada na calçada esquerda
        arvore_x = esquerda_pista - 18
        arvore_y = y_centro - 54
        pygame.draw.circle(tela, "#0f1716", (arvore_x + paleta.sombra_dx, arvore_y + paleta.sombra_dy), 14)
        pygame.draw.circle(tela, paleta.copa_arvore, (arvore_x, arvore_y), 14)
        pygame.draw.circle(tela, paleta.copa_luz, (arvore_x - 3, arvore_y - 3), 7)

        # Poste de iluminação periódico
        if idx % 2 == 0:
            poste_x = esquerda_pista - 10
            poste_y = y_centro + 62
            if paleta.farois_ativos:
                tela.blit(_halo_poste(), (poste_x - 42, poste_y - 42))
            pygame.draw.circle(tela, "#8fa19b", (poste_x, poste_y), 4)
            pygame.draw.line(tela, "#8fa19b", (poste_x, poste_y), (poste_x + 12, poste_y), 2)

        # Abrigo de ponto de ônibus ocasional na calçada direita
        if idx % 4 == 1:
            abrigo_rect = pygame.Rect(direita_pista + 65, y_centro - 28, 16, 56)
            pygame.draw.rect(tela, "#374b54", abrigo_rect, border_radius=4)
            pygame.draw.rect(tela, "#587b8a", abrigo_rect.inflate(-6, -12), border_radius=2)


def desenhar_marcos_percurso(tela: pygame.Surface, distancia_m: float, fonte: pygame.font.Font) -> None:
    esquerda_pista = CENTRO_PISTA_X - LARGURA_PISTA // 2
    direita_pista = esquerda_pista + LARGURA_PISTA
    for numero_trecho in range(1, len(NOMES_TRECHOS) + 1):
        marco_m = numero_trecho * COMPRIMENTO_TRECHO_M
        y = round(_y_tela(distancia_m, marco_m))
        if -40 <= y < ALTURA_JANELA + 40:
            chegada = marco_m == COMPRIMENTO_PERCURSO_M
            cor = DESTAQUE if chegada else TEXTO_PRINCIPAL
            rotulo = "Chegada" if chegada else f"Checkpoint {numero_trecho}"
            legenda = fonte.render(rotulo, True, cor)
            retangulo_legenda = legenda.get_rect(midbottom=(CENTRO_PISTA_X, y - 7))
            pygame.draw.line(tela, cor, (esquerda_pista, y), (direita_pista, y), 4)
            pygame.draw.rect(tela, ASFALTO, retangulo_legenda.inflate(20, 6), border_radius=5)
            tela.blit(legenda, retangulo_legenda)


def desenhar_perigo_porta(
    tela: pygame.Surface,
    perigo: PerigoPorta,
    distancia_ciclista_m: float,
    fonte: pygame.font.Font,
) -> None:
    carro = perigo.area_carro(distancia_ciclista_m)
    retangulo_carro = pygame.Rect(round(carro.x), round(carro.y), round(carro.w), round(carro.h))
    if not tela.get_rect().colliderect(retangulo_carro):
        return

    sombra = retangulo_carro.move(4, 3)
    pygame.draw.rect(tela, "#131b1a", sombra, border_radius=10)
    pygame.draw.rect(tela, "#4c6268", retangulo_carro, border_radius=10)
    pygame.draw.rect(tela, FUNDO, retangulo_carro.inflate(-14, -35), border_radius=6)
    pygame.draw.line(tela, BORDA_PISTA, retangulo_carro.midtop, retangulo_carro.midbottom, 2)

    fase = perigo.fase
    if fase is FasePorta.AVISO:
        pygame.draw.rect(tela, AVISO, retangulo_carro, width=3, border_radius=10)
        rotulo = fonte.render("! Porta", True, AVISO)
        tela.blit(rotulo, (retangulo_carro.right - rotulo.get_width(), retangulo_carro.top - rotulo.get_height() - 6))
    elif fase is FasePorta.ABERTA:
        porta = perigo.area_porta(distancia_ciclista_m)
        retangulo_porta = pygame.Rect(round(porta.x), round(porta.y), round(porta.w), round(porta.h))
        pygame.draw.rect(tela, PERIGO, retangulo_porta, border_radius=4)
        pygame.draw.line(tela, FUNDO, retangulo_porta.midleft, retangulo_porta.midright, 2)


def desenhar_perigo_ponto_cego(
    tela: pygame.Surface,
    perigo: PerigoPontoCego,
    distancia_ciclista_m: float,
    indice_trecho: int,
    tempo_s: float,
    fonte: pygame.font.Font,
    ciclista_em_risco: bool,
) -> None:
    if perigo.onibus is None:
        return

    fase = perigo.fase
    if fase in (FasePontoCego.AVISO, FasePontoCego.ATIVO):
        zona = perigo.area_ponto_cego(distancia_ciclista_m)
        if zona is not None:
            rect = pygame.Rect(round(zona.x), round(zona.y), round(zona.w), round(zona.h))
            if tela.get_rect().colliderect(rect):
                eh_ativo = fase is FasePontoCego.ATIVO
                cor_hex = PERIGO if eh_ativo else AVISO
                cor_rgb = pygame.Color(cor_hex)
                pulso = 0.5 + 0.5 * math.sin(tempo_s * (11.0 if eh_ativo else 6.5))

                superficie = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                alfa_fundo = int((68 if eh_ativo else 42) + 22 * pulso)
                pygame.draw.rect(
                    superficie,
                    (cor_rgb.r, cor_rgb.g, cor_rgb.b, alfa_fundo),
                    (0, 0, rect.width, rect.height),
                    border_radius=10,
                )

                # Hachura diagonal para leitura acessível (inspirada em sinalização Angles Morts)
                alfa_listra = 95 if eh_ativo else 60
                passo = 22
                desloc = int(tempo_s * 36) % passo
                for offset in range(-rect.height, rect.width + rect.height, passo):
                    x1 = offset + desloc
                    pygame.draw.line(
                        superficie,
                        (cor_rgb.r, cor_rgb.g, cor_rgb.b, alfa_listra),
                        (x1, 0),
                        (x1 - rect.height * 0.45, rect.height),
                        4,
                    )

                tela.blit(superficie, rect.topleft)
                espessura = 3 if (eh_ativo or ciclista_em_risco) else 2
                pygame.draw.rect(tela, cor_hex, rect, width=espessura, border_radius=10)

                # Seta discreta indicando saída por frenagem ou recuo
                cx = rect.centerx
                cy = rect.bottom - 22
                pygame.draw.lines(
                    tela,
                    cor_hex,
                    False,
                    [(cx - 10, cy - 6), (cx, cy + 4), (cx + 10, cy - 6)],
                    3,
                )

                rotulo_texto = "! ZONA CRÍTICA" if eh_ativo else "! PONTO CEGO"
                rotulo = fonte.render(rotulo_texto, True, cor_hex)
                badge = pygame.Rect(
                    min(rect.x + 8, CENTRO_PISTA_X + LARGURA_PISTA // 2 - rotulo.get_width() - 16),
                    rect.y + 10,
                    rotulo.get_width() + 14,
                    rotulo.get_height() + 6,
                )
                pygame.draw.rect(tela, FUNDO, badge, border_radius=6)
                pygame.draw.rect(tela, cor_hex, badge, width=1, border_radius=6)
                tela.blit(rotulo, (badge.x + 7, badge.y + 3))

    desenhar_veiculo(tela, perigo.onibus, distancia_ciclista_m, indice_trecho, tempo_s)


def desenhar_veiculo(
    tela: pygame.Surface,
    veiculo: Veiculo,
    distancia_ciclista_m: float,
    indice_trecho: int,
    tempo_s: float,
) -> None:
    rect_f = veiculo.area_visual(distancia_ciclista_m)
    rect = pygame.Rect(round(rect_f.x), round(rect_f.y), round(rect_f.w), round(rect_f.h))
    if rect.bottom < -80 or rect.top > ALTURA_JANELA + 40:
        return

    paleta = PALETAS_TRECHO[min(indice_trecho, len(PALETAS_TRECHO) - 1)]

    # Sombra projetada
    sombra_surf = pygame.Surface((rect.width + 6, rect.height + 6), pygame.SRCALPHA)
    pygame.draw.rect(
        sombra_surf,
        (10, 14, 14, 110),
        (3, 3, rect.width, rect.height),
        border_radius=14 if veiculo.tipo is TipoVeiculo.ONIBUS else 12,
    )
    tela.blit(sombra_surf, (rect.x + paleta.sombra_dx - 3, rect.y + paleta.sombra_dy - 3))

    # Cones de faróis na Hora do rush
    if paleta.farois_ativos:
        cone = _cone_farol()
        tela.blit(cone, (rect.left + 8 - cone.get_width() // 2, rect.top - cone.get_height() + 4))
        tela.blit(cone, (rect.right - 8 - cone.get_width() // 2, rect.top - cone.get_height() + 4))

    if veiculo.tipo is TipoVeiculo.ONIBUS:
        _desenhar_onibus(tela, rect, veiculo, tempo_s)
    else:
        _desenhar_carro(tela, rect, veiculo)


def _desenhar_carro(tela: pygame.Surface, rect: pygame.Rect, veiculo: Veiculo) -> None:
    cor_corpo, cor_teto = _CORES_CARROS[veiculo.cor_variante % len(_CORES_CARROS)]

    # Retrovisores laterais
    pygame.draw.rect(tela, cor_corpo, (rect.left - 4, rect.top + 26, 5, 8), border_radius=2)
    pygame.draw.rect(tela, cor_corpo, (rect.right - 1, rect.top + 26, 5, 8), border_radius=2)

    # Chassi e para-brisas
    pygame.draw.rect(tela, cor_corpo, rect, border_radius=12)
    pygame.draw.rect(tela, "#142022", (rect.left + 7, rect.top + 20, rect.width - 14, 21), border_radius=5)
    pygame.draw.rect(tela, "#142022", (rect.left + 9, rect.bottom - 24, rect.width - 18, 12), border_radius=4)
    pygame.draw.rect(tela, cor_teto, (rect.left + 9, rect.top + 43, rect.width - 18, 32), border_radius=6)

    # Faróis dianteiros
    pygame.draw.rect(tela, "#f8f4cf", (rect.left + 7, rect.top + 2, 10, 4), border_radius=2)
    pygame.draw.rect(tela, "#f8f4cf", (rect.right - 17, rect.top + 2, 10, 4), border_radius=2)

    # Lanternas traseiras (iluminadas quando freando)
    cor_lanterna = LUZ_FREIO if veiculo.freando else "#7c3032"
    pygame.draw.rect(tela, cor_lanterna, (rect.left + 7, rect.bottom - 6, 12, 4), border_radius=2)
    pygame.draw.rect(tela, cor_lanterna, (rect.right - 19, rect.bottom - 6, 12, 4), border_radius=2)


def _desenhar_onibus(
    tela: pygame.Surface,
    rect: pygame.Rect,
    veiculo: Veiculo,
    tempo_s: float,
) -> None:
    # Retrovisores dianteiros salientes
    pygame.draw.rect(tela, "#1f4f82", (rect.left - 5, rect.top + 12, 6, 10), border_radius=2)
    pygame.draw.rect(tela, "#1f4f82", (rect.right - 1, rect.top + 12, 6, 10), border_radius=2)

    # Chassi principal do ônibus
    pygame.draw.rect(tela, AZUL_ONIBUS, rect, border_radius=14)
    pygame.draw.rect(tela, "#183e69", rect, width=2, border_radius=14)

    # Para-brisa panorâmico e vidro traseiro
    pygame.draw.rect(tela, "#121f26", (rect.left + 7, rect.top + 9, rect.width - 14, 22), border_radius=6)
    pygame.draw.rect(tela, "#121f26", (rect.left + 12, rect.bottom - 16, rect.width - 24, 9), border_radius=3)

    # Faixa superior e duas unidades de ar-condicionado no teto
    pygame.draw.rect(tela, AZUL_ONIBUS_TETO, (rect.left + 10, rect.top + 40, rect.width - 20, rect.height - 62), border_radius=8)
    for offset_y in (64, 126):
        ac_rect = pygame.Rect(rect.left + 19, rect.top + offset_y, rect.width - 38, 28)
        pygame.draw.rect(tela, "#cfe2f3", ac_rect, border_radius=5)
        pygame.draw.line(tela, "#8fb2d4", (ac_rect.left + 5, ac_rect.centery), (ac_rect.right - 5, ac_rect.centery), 2)

    # Alçapão de ventilação
    pygame.draw.rect(tela, "#25578d", (rect.left + 25, rect.bottom - 48, rect.width - 50, 18), border_radius=4)

    # Faróis e lanternas
    pygame.draw.rect(tela, "#f8f4cf", (rect.left + 9, rect.top + 2, 13, 4), border_radius=2)
    pygame.draw.rect(tela, "#f8f4cf", (rect.right - 22, rect.top + 2, 13, 4), border_radius=2)
    cor_lanterna = LUZ_FREIO if veiculo.freando else "#8a3235"
    pygame.draw.rect(tela, cor_lanterna, (rect.left + 9, rect.bottom - 6, 15, 4), border_radius=2)
    pygame.draw.rect(tela, cor_lanterna, (rect.right - 24, rect.bottom - 6, 15, 4), border_radius=2)

    # Seta direita piscante (para perigo de ponto cego)
    if veiculo.seta_direita_ativa and int(tempo_s * 6) % 2 == 0:
        pygame.draw.rect(tela, AVISO, (rect.right - 5, rect.top + 18, 6, 18), border_radius=2)
        pygame.draw.rect(tela, AVISO, (rect.right - 5, rect.bottom - 32, 6, 16), border_radius=2)


def desenhar_ciclista(tela: pygame.Surface, ciclista: Ciclista, freando: bool) -> None:
    x, y = round(ciclista.x), CICLISTA_TELA_Y
    pygame.draw.ellipse(tela, "#151b1a", (x - 17, y - 25, 38, 54))
    pygame.draw.rect(tela, "#101716", (x - 4, y - 26, 8, 52), border_radius=4)
    pygame.draw.line(tela, "#edf1e6", (x - 12, y - 12), (x + 12, y - 12), 4)
    pygame.draw.rect(tela, DESTAQUE, (x - 9, y - 8, 18, 25), border_radius=7)
    pygame.draw.circle(tela, TEXTO_PRINCIPAL, (x, y - 9), 7)
    if freando and ciclista.velocidade_mps > 0:
        pygame.draw.circle(tela, LUZ_FREIO, (x, y + 22), 5)


def desenhar_painel(
    tela: pygame.Surface,
    ciclista: Ciclista,
    fonte_titulo: pygame.font.Font,
    fonte_texto: pygame.font.Font,
    fonte_menor: pygame.font.Font,
    fonte_velocidade: pygame.font.Font,
    percurso: Percurso,
    mensagem_status: tuple[str, str] | None,
) -> None:
    painel = pygame.Rect(748, 72, 464, 576)
    pygame.draw.rect(tela, PAINEL, painel, border_radius=22)
    pygame.draw.rect(tela, "#2b3d37", painel, width=2, border_radius=22)

    x = painel.x + 32
    largura_util = 400
    paleta = PALETAS_TRECHO[min(percurso.indice_trecho, len(PALETAS_TRECHO) - 1)]

    tela.blit(fonte_titulo.render("Dead Lane", True, TEXTO_PRINCIPAL), (x, 96))

    # Badge de densidade do trecho
    badge_texto = fonte_menor.render(paleta.rotulo_densidade, True, DESTAQUE)
    badge_rect = pygame.Rect(x + largura_util - badge_texto.get_width() - 22, 108, badge_texto.get_width() + 22, 28)
    pygame.draw.rect(tela, "#253831", badge_rect, border_radius=8)
    tela.blit(badge_texto, (badge_rect.x + 11, badge_rect.y + 4))

    rotulo_trecho = f"Trecho {percurso.indice_trecho + 1}/{len(NOMES_TRECHOS)} · {NOMES_TRECHOS[percurso.indice_trecho]}"
    tela.blit(fonte_texto.render(rotulo_trecho, True, TEXTO_SECUNDARIO), (x, 152))

    # Velocímetro
    velocidade_exibida = f"{ciclista.velocidade_mps * 3.6:.0f}"
    rotulo = fonte_velocidade.render(velocidade_exibida, True, DESTAQUE)
    tela.blit(rotulo, (x, 184))
    tela.blit(fonte_texto.render("km/h", True, TEXTO_SECUNDARIO), (x + rotulo.get_width() + 12, 229))
    pygame.draw.rect(tela, BORDA_PISTA, (x, 272, largura_util, 6), border_radius=3)
    largura_barra_velocidade = round(largura_util * ciclista.velocidade_mps / VELOCIDADE_MAXIMA_MPS)
    if largura_barra_velocidade:
        pygame.draw.rect(tela, DESTAQUE, (x, 272, largura_barra_velocidade, 6), border_radius=3)

    # Progresso do percurso em 3 trechos
    rotulo_distancia = f"Percurso   {int(ciclista.distancia_m)} / {COMPRIMENTO_PERCURSO_M} m"
    tela.blit(fonte_texto.render(rotulo_distancia, True, TEXTO_SECUNDARIO), (x, 300))
    barra_y = 336
    pygame.draw.rect(tela, BORDA_PISTA, (x, barra_y, largura_util, 8), border_radius=4)
    largura_barra_percurso = round(largura_util * ciclista.distancia_m / COMPRIMENTO_PERCURSO_M)
    if largura_barra_percurso:
        pygame.draw.rect(tela, DESTAQUE, (x, barra_y, largura_barra_percurso, 8), border_radius=4)
    for divisoria in (1, 2):
        tick_x = x + round(largura_util * divisoria / len(NOMES_TRECHOS))
        pygame.draw.line(tela, PAINEL, (tick_x, barra_y - 1), (tick_x, barra_y + 9), 3)

    pygame.draw.line(tela, BORDA_PISTA, (x, 362), (x + largura_util, 362))

    for linha, (acao, teclas) in enumerate(
        (
            ("Acelerar", "W / ↑"),
            ("Frear", "S / ↓"),
            ("Mover para os lados", "A D / ← →"),
            ("Reiniciar", "R"),
            ("Sair", "Esc"),
        )
    ):
        y = 382 + linha * 34
        tela.blit(fonte_texto.render(acao, True, TEXTO_PRINCIPAL), (x, y))
        rotulo_tecla = fonte_texto.render(teclas, True, TEXTO_SECUNDARIO)
        tela.blit(rotulo_tecla, (x + largura_util - rotulo_tecla.get_width(), y))

    if mensagem_status is None:
        return

    mensagem, cor = mensagem_status
    card = pygame.Rect(x, 566, largura_util, 56)
    pygame.draw.rect(tela, FUNDO, card, border_radius=12)
    pygame.draw.rect(tela, cor, card, width=2, border_radius=12)
    pygame.draw.rect(tela, cor, (card.x + 2, card.y + 10, 5, card.height - 20), border_radius=2)
    texto_render = fonte_menor.render(mensagem, True, cor)
    if texto_render.get_width() > largura_util - 28:
        texto_render = pygame.transform.smoothscale(
            texto_render,
            (largura_util - 28, texto_render.get_height()),
        )
    tela.blit(texto_render, (card.x + 18, card.centery - texto_render.get_height() // 2))
