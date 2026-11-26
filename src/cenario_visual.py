from dataclasses import dataclass
import math

import pygame

from src.assets import carregar_icone, carregar_sprite
from src.ciclista import Ciclista
from src.configuracao import (
    ALCANCE_PORTA,
    ALTURA_JANELA,
    ALTURA_PORTA,
    CENTRO_PISTA_X,
    CICLISTA_TELA_Y,
    COMPRIMENTO_PERCURSO_M,
    COMPRIMENTO_TRECHO_M,
    ESCALA_PISTA_PX_POR_M,
    FAIXAS_PISTA,
    LARGURA_JANELA,
    LARGURA_PISTA,
    NOMES_TRECHOS,
    VELOCIDADE_MAXIMA_MPS,
)
from src.percurso import Percurso
from src.perigos import FasePontoCego, FasePorta, PerigoPontoCego, PerigoPorta
from src.trafego import TipoVeiculo, Veiculo

FUNDO = "#090b0f"
ASFALTO = "#181c24"
BORDA_PISTA = "#2b3240"
CALCADA = "#131720"
MARCACAO_FAIXA = "#647084"
TEXTO_PRINCIPAL = "#f4f6f9"
TEXTO_SECUNDARIO = "#9aa4b5"
DESTAQUE = "#38bdf8"
PAINEL = "#11151d"
AVISO = "#fbbf24"
PERIGO = "#f87171"
LUZ_FREIO = "#ff453a"
AZUL_ONIBUS = "#2b6cb0"
AZUL_ONIBUS_TETO = "#3b82c4"


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
        fundo="#090b0f",
        asfalto="#181c24",
        trilho_pneu="#141820",
        calcada="#131720",
        meio_fio="#2b3240",
        bloco_urbano="#0e1218",
        telhado_urbano="#141922",
        copa_arvore="#1f3a36",
        copa_luz="#2c524c",
        sombra_dx=6,
        sombra_dy=4,
        farois_ativos=False,
        rotulo_densidade="Tráfego leve",
    ),
    PaletaTrecho(
        fundo="#0b0d12",
        asfalto="#1c212b",
        trilho_pneu="#171b24",
        calcada="#161b25",
        meio_fio="#323a4a",
        bloco_urbano="#11151e",
        telhado_urbano="#181e2a",
        copa_arvore="#24423d",
        copa_luz="#325c55",
        sombra_dx=2,
        sombra_dy=3,
        farois_ativos=False,
        rotulo_densidade="Tráfego moderado",
    ),
    PaletaTrecho(
        fundo="#07080c",
        asfalto="#14171f",
        trilho_pneu="#10131a",
        calcada="#10131b",
        meio_fio="#252b38",
        bloco_urbano="#0b0e14",
        telhado_urbano="#10141c",
        copa_arvore="#192e2b",
        copa_luz="#23403c",
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
        surf = pygame.Surface((76, 86), pygame.SRCALPHA)
        for _, (y_topo, larg_topo, alfa) in enumerate(
            ((28, 36, 46), (18, 48, 32), (8, 60, 18), (0, 72, 9))
        ):
            meia_topo = larg_topo // 2
            cx = 38
            pygame.draw.polygon(
                surf,
                (254, 249, 195, alfa),
                [(cx - 6, 86), (cx + 6, 86), (cx + meia_topo, y_topo), (cx - meia_topo, y_topo)],
            )
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

    # Textura sutil de lajotas na calçada esquerda
    passo_calcada = 28
    desloc_calc = int(distancia_m * ESCALA_PISTA_PX_POR_M) % passo_calcada
    for y in range(desloc_calc - passo_calcada, ALTURA_JANELA, passo_calcada):
        pygame.draw.line(tela, (40, 52, 48), (esquerda_pista - 36, y), (esquerda_pista, y), 1)

    # Baia de estacionamento e calçada direita (mantendo folga limpa até o painel em x=748)
    pygame.draw.rect(tela, "#202a2a", (direita_pista, 0, 62, ALTURA_JANELA))
    pygame.draw.rect(tela, paleta.calcada, (direita_pista + 62, 0, 24, ALTURA_JANELA))
    for y in range(desloc_calc - passo_calcada, ALTURA_JANELA, passo_calcada):
        pygame.draw.line(tela, (40, 52, 48), (direita_pista + 62, y), (direita_pista + 86, y), 1)

    # Leito da avenida
    pygame.draw.rect(tela, paleta.asfalto, (esquerda_pista, 0, LARGURA_PISTA, ALTURA_JANELA))

    # Trilhos discretos de rodagem nas 3 faixas
    for faixa in range(FAIXAS_PISTA):
        cx = esquerda_pista + faixa * largura_faixa + largura_faixa // 2
        pygame.draw.rect(tela, paleta.trilho_pneu, (cx - 26, 0, 14, ALTURA_JANELA))
        pygame.draw.rect(tela, paleta.trilho_pneu, (cx + 12, 0, 14, ALTURA_JANELA))

    # Meio-fio reforçado (granito com chanfro)
    pygame.draw.line(tela, paleta.meio_fio, (esquerda_pista, 0), (esquerda_pista, ALTURA_JANELA), 4)
    pygame.draw.line(tela, (30, 40, 38), (esquerda_pista + 2, 0), (esquerda_pista + 2, ALTURA_JANELA), 1)
    pygame.draw.line(tela, paleta.meio_fio, (direita_pista, 0), (direita_pista, ALTURA_JANELA), 4)
    pygame.draw.line(tela, (30, 40, 38), (direita_pista - 2, 0), (direita_pista - 2, ALTURA_JANELA), 1)
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
        pygame.draw.line(tela, "#556865", (direita_pista + 6, y), (direita_pista + 14, y), 2)

    # Símbolos de ciclorrota (sharrow) na faixa direita com sprite nítido
    sharrow_icone = carregar_icone("icone_sharrow")
    passo_sharrow = 270
    desloc_sharrow = int(distancia_m * ESCALA_PISTA_PX_POR_M) % passo_sharrow
    cx_direita = esquerda_pista + 2 * largura_faixa + largura_faixa // 2
    for y in range(desloc_sharrow - passo_sharrow, ALTURA_JANELA + 40, passo_sharrow):
        tela.blit(sharrow_icone, (cx_direita - sharrow_icone.get_width() // 2, y))

    # Quadras urbanas, árvores e postes à esquerda
    passo_bloco_m = 13.5
    primeiro_indice = math.floor((distancia_m - 12.0) / passo_bloco_m)
    ultimo_indice = math.ceil((distancia_m + 24.0) / passo_bloco_m)
    for idx in range(primeiro_indice, ultimo_indice + 1):
        marco_m = idx * passo_bloco_m
        y_centro = round(_y_tela(distancia_m, marco_m))
        largura_bloco = 136 if idx % 2 == 0 else 108
        altura_bloco = 175 if idx % 3 != 0 else 210
        bx = 20 if idx % 2 == 0 else 42
        bloco_rect = pygame.Rect(bx, y_centro - altura_bloco // 2, largura_bloco, altura_bloco)
        pygame.draw.rect(tela, paleta.bloco_urbano, bloco_rect, border_radius=10)
        pygame.draw.rect(tela, paleta.telhado_urbano, bloco_rect.inflate(-24, -28), border_radius=6)
        # Detalhe de ar condicionado / caixa d'água no topo do prédio
        pygame.draw.rect(tela, (25, 40, 36), (bloco_rect.centerx - 12, bloco_rect.centery - 10, 24, 20), border_radius=3)

        # Árvore estilizada na calçada esquerda com sombra
        arvore_x = esquerda_pista - 18
        arvore_y = y_centro - 48
        pygame.draw.circle(tela, "#0f1716", (arvore_x + paleta.sombra_dx, arvore_y + paleta.sombra_dy), 13)
        pygame.draw.circle(tela, paleta.copa_arvore, (arvore_x, arvore_y), 13)
        pygame.draw.circle(tela, paleta.copa_luz, (arvore_x - 3, arvore_y - 3), 7)
        pygame.draw.circle(tela, (70, 140, 115), (arvore_x - 5, arvore_y - 5), 3)

        # Poste de iluminação periódico
        if idx % 2 == 0:
            poste_x = esquerda_pista - 10
            poste_y = y_centro + 56
            if paleta.farois_ativos:
                tela.blit(_halo_poste(), (poste_x - 42, poste_y - 42))
            pygame.draw.circle(tela, "#8fa19b", (poste_x, poste_y), 4)
            pygame.draw.line(tela, "#8fa19b", (poste_x, poste_y), (poste_x + 12, poste_y), 2)

        # Abrigo de ponto de ônibus na calçada direita
        if idx % 5 == 1:
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
    tempo_s: float = 0.0,
) -> None:
    carro = perigo.area_carro(distancia_ciclista_m)
    retangulo_carro = pygame.Rect(round(carro.x), round(carro.y), round(carro.w), round(carro.h))
    if not tela.get_rect().colliderect(retangulo_carro.inflate(ALCANCE_PORTA * 2, 20)):
        return

    fase = perigo.fase
    esta_em_aviso = fase is FasePorta.AVISO
    esta_aberta = fase is FasePorta.ABERTA

    # Desenha o carro estacionado com sprite
    sprite_carro = carregar_sprite("carro_estacionado_aviso" if esta_em_aviso else "carro_estacionado")
    tela.blit(sprite_carro, retangulo_carro.topleft)

    if esta_em_aviso:
        # 1. Sinalização visual de perigo da porta: Área de swing projetada no asfalto da faixa direita
        porta_f = perigo.area_porta(distancia_ciclista_m)
        retangulo_porta = pygame.Rect(round(porta_f.x), round(porta_f.y), round(porta_f.w), round(porta_f.h))

        # Blit da hachura de aviso na zona de abertura da porta (68x24)
        sprite_zona = carregar_sprite("porta_aviso_zona")
        tela.blit(sprite_zona, retangulo_porta.topleft)

        # Borda pulsante da zona de risco
        pulso = 0.5 + 0.5 * math.sin(tempo_s * 10.0)
        alfa_borda = int(140 + 115 * pulso)
        surf_borda = pygame.Surface((retangulo_porta.width, retangulo_porta.height), pygame.SRCALPHA)
        pygame.draw.rect(surf_borda, (255, 207, 112, alfa_borda), (0, 0, retangulo_porta.width, retangulo_porta.height), width=2, border_radius=4)
        tela.blit(surf_borda, retangulo_porta.topleft)

        # Badge visual de perigo com ícone
        icone = carregar_icone("icone_porta")
        badge_y = retangulo_carro.top - 36
        badge_x = retangulo_carro.left - 40
        tela.blit(icone, (badge_x - 30, badge_y - 8))
        rotulo = fonte.render("! PORTA ABRINDO", True, AVISO)
        fundo_badge = pygame.Rect(badge_x + 12, badge_y, rotulo.get_width() + 14, rotulo.get_height() + 4)
        pygame.draw.rect(tela, FUNDO, fundo_badge, border_radius=5)
        pygame.draw.rect(tela, AVISO, fundo_badge, width=1, border_radius=5)
        tela.blit(rotulo, (fundo_badge.x + 7, fundo_badge.y + 2))

    elif esta_aberta:
        # Porta aberta com sprite detalhado (68x24)
        porta_f = perigo.area_porta(distancia_ciclista_m)
        retangulo_porta = pygame.Rect(round(porta_f.x), round(porta_f.y), round(porta_f.w), round(porta_f.h))
        sprite_porta = carregar_sprite("porta_aberta")
        tela.blit(sprite_porta, retangulo_porta.topleft)

        # Destaque de perigo e exclamação de impacto
        pygame.draw.rect(tela, PERIGO, retangulo_porta, width=2, border_radius=4)

        icone = carregar_icone("icone_alerta")
        tela.blit(icone, (retangulo_porta.left - 24, retangulo_porta.centery - icone.get_height() // 2))


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
                pulso = 0.5 + 0.5 * math.sin(tempo_s * (12.0 if (eh_ativo or ciclista_em_risco) else 7.0))

                superficie = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                alfa_fundo = int((75 if eh_ativo else 48) + 28 * pulso)
                pygame.draw.rect(
                    superficie,
                    (cor_rgb.r, cor_rgb.g, cor_rgb.b, alfa_fundo),
                    (0, 0, rect.width, rect.height),
                    border_radius=10,
                )

                # Hachura diagonal dinâmica tipo "Angles Morts"
                alfa_listra = 110 if (eh_ativo or ciclista_em_risco) else 70
                passo = 24
                desloc = int(tempo_s * 42) % passo
                for offset in range(-rect.height, rect.width + rect.height, passo):
                    x1 = offset + desloc
                    pygame.draw.line(
                        superficie,
                        (cor_rgb.r, cor_rgb.g, cor_rgb.b, alfa_listra),
                        (x1, 0),
                        (x1 - rect.height * 0.45, rect.height),
                        5,
                    )

                # Ícone Angles Morts / Ponto Cego desenhado no centro da zona
                icone_pc = carregar_icone("icone_ponto_cego")
                cx_icone = rect.width // 2 - icone_pc.get_width() // 2
                cy_icone = rect.height // 2 - icone_pc.get_height() // 2
                superficie.blit(icone_pc, (cx_icone, cy_icone))

                tela.blit(superficie, rect.topleft)
                espessura = 4 if (eh_ativo or ciclista_em_risco) else 2
                pygame.draw.rect(tela, cor_hex, rect, width=espessura, border_radius=10)

                # Seta de escape indicando recuo por frenagem
                cx = rect.centerx
                cy = rect.bottom - 24
                pygame.draw.lines(
                    tela,
                    cor_hex,
                    False,
                    [(cx - 12, cy - 8), (cx, cy + 4), (cx + 12, cy - 8)],
                    4,
                )

                rotulo_texto = "! ZONA CRÍTICA: ÔNIBUS FECHANDO" if eh_ativo else "! PONTO CEGO DO ÔNIBUS"
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

    # Cones de faróis na Hora do rush
    if paleta.farois_ativos:
        cone = _cone_farol()
        tela.blit(cone, (rect.left + 8 - cone.get_width() // 2, rect.top - cone.get_height() + 4))
        tela.blit(cone, (rect.right - 8 - cone.get_width() // 2, rect.top - cone.get_height() + 4))

    if veiculo.tipo is TipoVeiculo.ONIBUS:
        piscar_seta = veiculo.seta_direita_ativa and int(tempo_s * 6) % 2 == 0
        nome_sprite = f"onibus{'_seta' if piscar_seta else ''}{'_freando' if veiculo.freando else ''}"
        sprite = carregar_sprite(nome_sprite)
        tela.blit(sprite, rect.topleft)
    else:
        var = veiculo.cor_variante % 5
        nome_sprite = f"carro_{var}{'_freando' if veiculo.freando else ''}"
        sprite = carregar_sprite(nome_sprite)
        tela.blit(sprite, rect.topleft)

    # Seta âmbar piscante quando o veículo sinaliza troca de faixa
    if veiculo.seta_direcao != 0 and int(tempo_s * 6) % 2 == 0:
        x_seta = rect.right - 7 if veiculo.seta_direcao > 0 else rect.left + 2
        pygame.draw.rect(tela, AVISO, (x_seta, rect.top + 6, 5, 10), border_radius=2)
        pygame.draw.rect(tela, AVISO, (x_seta, rect.bottom - 16, 5, 10), border_radius=2)


def desenhar_ciclista(tela: pygame.Surface, ciclista: Ciclista, freando: bool) -> None:
    x, y = round(ciclista.x), CICLISTA_TELA_Y
    esta_freando = freando and ciclista.velocidade_mps > 0
    sprite = carregar_sprite("ciclista_freando" if esta_freando else "ciclista")
    # Sprite tem 32x56; seu centro (16, 28) alinha perfeitamente com a hitbox central (24x52)
    tela.blit(sprite, (x - 16, y - 28))


def desenhar_alerta_borda(
    tela: pygame.Surface,
    em_risco_critico: bool,
    em_aviso: bool,
    tempo_s: float,
) -> None:
    """Renderiza uma sinalização visual de perigo na borda da tela quando o ciclista entra em área de risco."""
    if not (em_risco_critico or em_aviso):
        return

    cor_base = PERIGO if em_risco_critico else AVISO
    cor_rgb = pygame.Color(cor_base)
    frequencia = 13.0 if em_risco_critico else 7.0
    pulso = 0.5 + 0.5 * math.sin(tempo_s * frequencia)

    espessura = 18 if em_risco_critico else 10
    alfa_max = int((160 if em_risco_critico else 90) + 70 * pulso)

    # Cria superfície com borda translúcida pulsante
    largura_t, altura_t = tela.get_size()
    alerta_surf = pygame.Surface((largura_t, altura_t), pygame.SRCALPHA)

    # Bordas superior, inferior, esquerda e direita com gradiente em faixas
    camadas = 4
    for c in range(camadas):
        fator = (camadas - c) / camadas
        alfa = int(alfa_max * fator * 0.45)
        cor = (cor_rgb.r, cor_rgb.g, cor_rgb.b, alfa)
        margem = c * (espessura // camadas)
        pygame.draw.rect(
            alerta_surf,
            cor,
            (margem, margem, largura_t - 2 * margem, altura_t - 2 * margem),
            width=(espessura // camadas) + 2,
        )

    # Cantos reforçados tipo mira / indicador de risco crítico
    if em_risco_critico:
        tam_canto = 48
        cor_canto = (cor_rgb.r, cor_rgb.g, cor_rgb.b, 230)
        # Canto Superior Esquerdo
        pygame.draw.line(alerta_surf, cor_canto, (8, 8), (8 + tam_canto, 8), 4)
        pygame.draw.line(alerta_surf, cor_canto, (8, 8), (8, 8 + tam_canto), 4)
        # Canto Superior Direito
        pygame.draw.line(alerta_surf, cor_canto, (largura_t - 8, 8), (largura_t - 8 - tam_canto, 8), 4)
        pygame.draw.line(alerta_surf, cor_canto, (largura_t - 8, 8), (largura_t - 8, 8 + tam_canto), 4)
        # Canto Inferior Esquerdo
        pygame.draw.line(alerta_surf, cor_canto, (8, altura_t - 8), (8 + tam_canto, altura_t - 8), 4)
        pygame.draw.line(alerta_surf, cor_canto, (8, altura_t - 8), (8, altura_t - 8 - tam_canto), 4)
        # Canto Inferior Direito
        pygame.draw.line(alerta_surf, cor_canto, (largura_t - 8, altura_t - 8), (largura_t - 8 - tam_canto, 8), 4)
        pygame.draw.line(alerta_surf, cor_canto, (largura_t - 8, altura_t - 8), (largura_t - 8, altura_t - 8 - tam_canto), 4)

    tela.blit(alerta_surf, (0, 0))


def desenhar_painel(
    tela: pygame.Surface,
    ciclista: Ciclista,
    fonte_titulo: pygame.font.Font,
    fonte_texto: pygame.font.Font,
    fonte_menor: pygame.font.Font,
    fonte_velocidade: pygame.font.Font,
    percurso: Percurso,
    mensagem_status: tuple[str, str] | None,
    marcos_perigos: list[tuple[float, bool]] | None = None,
) -> None:
    painel = pygame.Rect(748, 64, 464, 592)
    pygame.draw.rect(tela, PAINEL, painel, border_radius=4)
    pygame.draw.rect(tela, BORDA_PISTA, painel, width=1, border_radius=4)
    pygame.draw.rect(tela, DESTAQUE, (painel.x, painel.y, painel.width, 3))

    x = painel.x + 28
    largura_util = painel.width - 56
    paleta = PALETAS_TRECHO[min(percurso.indice_trecho, len(PALETAS_TRECHO) - 1)]

    # Cabeçalho sem sobreposição: título compacto à esquerda + badge de tráfego à direita
    fonte_cab = pygame.font.SysFont("Bahnschrift", 28, bold=True)
    tela.blit(fonte_cab.render("DEAD LANE", True, TEXTO_PRINCIPAL), (x, painel.y + 24))

    badge_texto = fonte_menor.render(paleta.rotulo_densidade, True, DESTAQUE)
    badge_rect = pygame.Rect(x + largura_util - badge_texto.get_width() - 20, painel.y + 24, badge_texto.get_width() + 20, 26)
    pygame.draw.rect(tela, ASFALTO, badge_rect, border_radius=3)
    pygame.draw.rect(tela, BORDA_PISTA, badge_rect, width=1, border_radius=3)
    tela.blit(badge_texto, (badge_rect.x + 10, badge_rect.y + 4))

    rotulo_trecho = f"Trecho {percurso.indice_trecho + 1}/{len(NOMES_TRECHOS)}  ·  {NOMES_TRECHOS[percurso.indice_trecho]}"
    tela.blit(fonte_texto.render(rotulo_trecho, True, TEXTO_SECUNDARIO), (x, painel.y + 62))
    pygame.draw.line(tela, BORDA_PISTA, (x, painel.y + 94), (x + largura_util, painel.y + 94), 1)

    # Velocímetro + Barra
    velocidade_exibida = f"{ciclista.velocidade_mps * 3.6:.0f}"
    rotulo = fonte_velocidade.render(velocidade_exibida, True, DESTAQUE)
    tela.blit(rotulo, (x, painel.y + 108))
    tela.blit(fonte_texto.render("km/h", True, TEXTO_SECUNDARIO), (x + rotulo.get_width() + 10, painel.y + 150))

    pygame.draw.rect(tela, ASFALTO, (x, painel.y + 190, largura_util, 6), border_radius=2)
    largura_barra_velocidade = round(largura_util * ciclista.velocidade_mps / VELOCIDADE_MAXIMA_MPS)
    if largura_barra_velocidade > 0:
        pygame.draw.rect(tela, DESTAQUE, (x, painel.y + 190, largura_barra_velocidade, 6), border_radius=2)

    # Progresso do percurso
    restante_m = max(0, int(COMPRIMENTO_PERCURSO_M - ciclista.distancia_m))
    rotulo_distancia = f"Percurso  {int(ciclista.distancia_m)} / {COMPRIMENTO_PERCURSO_M} m  ({restante_m} m restantes)"
    tela.blit(fonte_menor.render(rotulo_distancia, True, TEXTO_SECUNDARIO), (x, painel.y + 216))
    barra_y = painel.y + 244
    pygame.draw.rect(tela, ASFALTO, (x, barra_y, largura_util, 8), border_radius=2)
    largura_barra_percurso = round(largura_util * ciclista.distancia_m / COMPRIMENTO_PERCURSO_M)
    if largura_barra_percurso > 0:
        pygame.draw.rect(tela, DESTAQUE, (x, barra_y, largura_barra_percurso, 8), border_radius=2)
    for divisoria in (1, 2):
        tick_x = x + round(largura_util * divisoria / len(NOMES_TRECHOS))
        pygame.draw.line(tela, PAINEL, (tick_x, barra_y - 1), (tick_x, barra_y + 9), 3)

    if marcos_perigos:
        for progresso, superado in marcos_perigos:
            mx = x + round(largura_util * min(1.0, max(0.0, progresso)))
            cor_marco = DESTAQUE if superado else AVISO
            pygame.draw.circle(tela, cor_marco, (mx, barra_y + 16), 2)

    # Barra de Dash (Espaço)
    y_dash = painel.y + 280
    dash_pronto = ciclista.dash_pronto
    txt_dash = "DASH LATERAL [ESPAÇO]  ·  PRONTO" if dash_pronto else "DASH LATERAL [ESPAÇO]  ·  RECARREGANDO"
    cor_dash = DESTAQUE if dash_pronto else TEXTO_SECUNDARIO
    tela.blit(fonte_menor.render(txt_dash, True, cor_dash), (x, y_dash))
    pygame.draw.rect(tela, ASFALTO, (x, y_dash + 24, largura_util, 6), border_radius=2)
    larg_dash = round(largura_util * ciclista.progresso_recarga_dash)
    if larg_dash > 0:
        pygame.draw.rect(tela, DESTAQUE if dash_pronto else AVISO, (x, y_dash + 24, larg_dash, 6), border_radius=2)

    pygame.draw.line(tela, BORDA_PISTA, (x, painel.y + 332), (x + largura_util, painel.y + 332), 1)

    # Atalhos enxutos (sem paredão de 6 linhas e sem quadradinhos unicode)
    atalhos = (
        ("WASD / Setas", "Acelerar e mudar de faixa"),
        ("Espaço", "Dash lateral rápido"),
        ("B / P / Esc", "Boletim e pausa"),
        ("H  ·  R", "Instruções  ·  Reiniciar"),
    )
    for idx_a, (tecla_a, desc_a) in enumerate(atalhos):
        ya = painel.y + 350 + idx_a * 32
        tela.blit(fonte_menor.render(tecla_a, True, DESTAQUE), (x, ya))
        surf_d = fonte_texto.render(desc_a, True, TEXTO_SECUNDARIO)
        tela.blit(surf_d, (x + largura_util - surf_d.get_width(), ya - 1))

    if mensagem_status is None:
        return

    mensagem, cor = mensagem_status
    card = pygame.Rect(x, painel.bottom - 76, largura_util, 54)
    pygame.draw.rect(tela, ASFALTO, card, border_radius=4)
    pygame.draw.rect(tela, cor, card, width=1, border_radius=4)
    pygame.draw.rect(tela, cor, (card.x, card.y, 4, card.height))
    linhas_msg = _quebrar_texto(fonte_menor, mensagem, largura_util - 28)
    y_msg = card.centery - (len(linhas_msg) * 18) // 2
    for linha_m in linhas_msg[:2]:
        tela.blit(fonte_menor.render(linha_m, True, cor), (card.x + 16, y_msg))
        y_msg += 18


def _quebrar_texto(fonte: pygame.font.Font, texto: str, largura_max: int) -> list[str]:
    """Quebra texto em múltiplas linhas respeitando a largura máxima sem distorcer a fonte."""
    palavras = texto.split()
    linhas: list[str] = []
    atual = ""
    for palavra in palavras:
        candidata = f"{atual} {palavra}".strip()
        if fonte.size(candidata)[0] <= largura_max or not atual:
            atual = candidata
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def _desenhar_keycap_seta(tela: pygame.Surface, rect: pygame.Rect, direcao: str) -> None:
    """Desenha um keycap com seta vetorial nítida (independe de glifos Unicode da fonte)."""
    pygame.draw.rect(tela, ASFALTO, rect, border_radius=3)
    pygame.draw.rect(tela, BORDA_PISTA, rect, width=1, border_radius=3)
    cx, cy = rect.centerx, rect.centery
    if direcao == "cima":
        pts = [(cx, cy - 5), (cx - 5, cy + 4), (cx + 5, cy + 4)]
    elif direcao == "baixo":
        pts = [(cx, cy + 5), (cx - 5, cy - 4), (cx + 5, cy - 4)]
    elif direcao == "esquerda":
        pts = [(cx - 5, cy), (cx + 4, cy - 5), (cx + 4, cy + 5)]
    else:
        pts = [(cx + 5, cy), (cx - 4, cy - 5), (cx - 4, cy + 5)]
    pygame.draw.polygon(tela, DESTAQUE, pts)


def desenhar_tela_instrucoes(
    tela: pygame.Surface,
    tempo_s: float,
    fonte_titulo: pygame.font.Font,
    fonte_texto: pygame.font.Font,
    fonte_menor: pygame.font.Font,
    fonte_subtitulo: pygame.font.Font,
) -> None:
    """Renderiza a tela inicial de Instruções de Pilotagem com layout escuro de sinalização viária."""
    tela.fill(FUNDO)

    fonte_tecla = pygame.font.SysFont("Consolas", 16, bold=True)
    margem_x = 64
    largura_total = LARGURA_JANELA - 2 * margem_x
    x_fim = LARGURA_JANELA - margem_x

    # --- CABEÇALHO HERO ---
    icone_jogo = pygame.transform.smoothscale(carregar_icone("icone_jogo"), (56, 56))
    tela.blit(icone_jogo, (margem_x, 30))

    titulo = fonte_titulo.render("DEAD LANE", True, TEXTO_PRINCIPAL)
    subtitulo = fonte_texto.render("Pilotagem defensiva urbana  ·  Antecipe portas e pontos cegos", True, TEXTO_SECUNDARIO)
    tela.blit(titulo, (margem_x + 74, 24))
    tela.blit(subtitulo, (margem_x + 74, 72))

    # Dados reais do percurso à direita
    vel_max_kmh = round(VELOCIDADE_MAXIMA_MPS * 3.6)
    dados_pista = (
        ("PERCURSO", f"{COMPRIMENTO_PERCURSO_M} m"),
        ("TRECHOS", f"{len(NOMES_TRECHOS)}"),
        ("VEL. MÁX", f"{vel_max_kmh} km/h"),
    )
    x_stat = x_fim
    for rotulo_s, valor_s in reversed(dados_pista):
        surf_val = fonte_subtitulo.render(valor_s, True, DESTAQUE)
        surf_rot = fonte_menor.render(rotulo_s, True, TEXTO_SECUNDARIO)
        larg_bloco = max(surf_val.get_width(), surf_rot.get_width()) + 28
        x_stat -= larg_bloco
        tela.blit(surf_rot, (x_stat + larg_bloco - surf_rot.get_width(), 34))
        tela.blit(surf_val, (x_stat + larg_bloco - surf_val.get_width(), 58))

    pygame.draw.line(tela, BORDA_PISTA, (margem_x, 112), (x_fim, 112), 1)

    # --- FAIXA HORIZONTAL DE CONTROLES ---
    y_ctrl_sec = 132
    tela.blit(fonte_menor.render("CONTROLES", True, DESTAQUE), (margem_x, y_ctrl_sec))

    controles = (
        ("W", ("cima",), "Acelerar", "Até 58 km/h"),
        ("S", ("baixo",), "Frear", "Recua do risco"),
        ("A D", ("esquerda", "direita"), "Faixas", "Desvio lateral"),
        ("ESPAÇO", (), "Dash", "Desvia ou avança"),
        ("B / P", (), "Resultados", "Pausa e dados"),
    )
    espaco_ctrl = 14
    larg_ctrl = (largura_total - espaco_ctrl * (len(controles) - 1)) // len(controles)
    y_caixas_ctrl = y_ctrl_sec + 28

    for idx_c, (teclas, setas, acao, detalhe) in enumerate(controles):
        cx = margem_x + idx_c * (larg_ctrl + espaco_ctrl)
        box_c = pygame.Rect(cx, y_caixas_ctrl, larg_ctrl, 84)
        pygame.draw.rect(tela, PAINEL, box_c, border_radius=4)
        pygame.draw.rect(tela, BORDA_PISTA, box_c, width=1, border_radius=4)

        surf_k = fonte_tecla.render(teclas, True, DESTAQUE)
        badge_k = pygame.Rect(cx + 12, y_caixas_ctrl + 12, surf_k.get_width() + 14, 24)
        pygame.draw.rect(tela, ASFALTO, badge_k, border_radius=3)
        pygame.draw.rect(tela, BORDA_PISTA, badge_k, width=1, border_radius=3)
        tela.blit(surf_k, (badge_k.x + 7, badge_k.y + 4))

        if setas:
            sep = fonte_tecla.render("/", True, TEXTO_SECUNDARIO)
            tela.blit(sep, (badge_k.right + 6, y_caixas_ctrl + 16))
            x_seta = badge_k.right + 18
            for dir_s in setas:
                _desenhar_keycap_seta(tela, pygame.Rect(x_seta, y_caixas_ctrl + 12, 24, 24), dir_s)
                x_seta += 28

        tela.blit(fonte_menor.render(acao, True, TEXTO_PRINCIPAL), (cx + 12, y_caixas_ctrl + 42))
        tela.blit(fonte_texto.render(detalhe, True, TEXTO_SECUNDARIO), (cx + 12, y_caixas_ctrl + 60))

    # --- 3 PAINÉIS VISUAIS DE PERIGO (COM SPRITES REAIS) ---
    y_riscos_sec = 266
    tela.blit(fonte_menor.render("SINAIS DE RISCO NA AVENIDA", True, DESTAQUE), (margem_x, y_riscos_sec))

    espaco_card = 24
    larg_card = (largura_total - espaco_card * 2) // 3
    y_cards = y_riscos_sec + 28
    alt_card = 316

    perigos_info = (
        (
            "porta",
            "Porta abrindo (Dooring)",
            AVISO,
            "Pisca-alerta âmbar e faixa hachurada junto ao carro.",
            "Vá para a faixa central antes da abertura ou freie.",
        ),
        (
            "ponto_cego",
            "Ponto cego (Angles Morts)",
            PERIGO,
            "Seta ligada e zona listrada ao lado do ônibus.",
            "Não emparelhe: freie para recuar ou passe à esquerda.",
        ),
        (
            "borda",
            "Alerta na borda da tela",
            PERIGO,
            "Moldura pulsante em âmbar ou vermelho.",
            "Você entrou na zona de impacto. Reaja de imediato.",
        ),
    )

    for idx_p, (tipo_cena, titulo_p, cor_p, txt_sinal, txt_acao) in enumerate(perigos_info):
        px = margem_x + idx_p * (larg_card + espaco_card)
        card = pygame.Rect(px, y_cards, larg_card, alt_card)
        pygame.draw.rect(tela, PAINEL, card, border_radius=4)
        pygame.draw.rect(tela, BORDA_PISTA, card, width=1, border_radius=4)
        pygame.draw.rect(tela, cor_p, (px, y_cards, larg_card, 3))

        # Mini-cena visual com os sprites reais do jogo
        cena = pygame.Rect(px + 16, y_cards + 18, larg_card - 32, 112)
        pygame.draw.rect(tela, ASFALTO, cena, border_radius=3)
        pygame.draw.line(tela, MARCACAO_FAIXA, (cena.centerx - 24, cena.y + 8), (cena.centerx - 24, cena.bottom - 8), 2)

        if tipo_cena == "porta":
            carro_av = carregar_sprite("carro_estacionado_aviso")
            porta_spr = carregar_sprite("porta_aberta")
            zona_spr = carregar_sprite("porta_aviso_zona")
            carro_r = carro_av.get_rect(midright=(cena.right - 16, cena.centery))
            tela.blit(zona_spr, (carro_r.left - zona_spr.get_width() + 4, carro_r.top + 14))
            tela.blit(porta_spr, (carro_r.left - porta_spr.get_width() + 2, carro_r.top + 16))
            tela.blit(carro_av, carro_r)
            tela.blit(carregar_icone("icone_porta"), (cena.x + 14, cena.centery - 24))
        elif tipo_cena == "ponto_cego":
            onibus_spr = pygame.transform.smoothscale(carregar_sprite("onibus_seta"), (44, 96))
            onibus_r = onibus_spr.get_rect(midleft=(cena.x + 28, cena.centery))
            zona_cego = pygame.Rect(onibus_r.right + 4, onibus_r.top + 12, 84, 72)
            pygame.draw.rect(tela, "#331c22", zona_cego, border_radius=2)
            pygame.draw.rect(tela, PERIGO, zona_cego, width=1, border_radius=2)
            for hx in range(zona_cego.x + 8, zona_cego.right - 12, 14):
                pygame.draw.line(tela, AVISO, (hx, zona_cego.bottom - 6), (hx + 10, zona_cego.top + 6), 2)
            tela.blit(onibus_spr, onibus_r)
            tela.blit(carregar_icone("icone_ponto_cego"), (cena.right - 64, cena.centery - 24))
        else:
            pygame.draw.rect(tela, PERIGO, cena, width=3, border_radius=3)
            cic_spr = carregar_sprite("ciclista_freando")
            tela.blit(cic_spr, cic_spr.get_rect(center=(cena.centerx - 36, cena.centery)))
            tela.blit(carregar_icone("icone_alerta_borda"), (cena.centerx + 24, cena.centery - 24))

        # Texto do cartão sem distorção
        y_txt = cena.bottom + 16
        tela.blit(fonte_subtitulo.render(titulo_p, True, cor_p), (px + 18, y_txt))
        y_txt += 32

        tela.blit(fonte_menor.render("Sinal:", True, TEXTO_PRINCIPAL), (px + 18, y_txt))
        for linha in _quebrar_texto(fonte_texto, txt_sinal, larg_card - 88)[:2]:
            tela.blit(fonte_texto.render(linha, True, TEXTO_SECUNDARIO), (px + 72, y_txt))
            y_txt += 22

        y_txt += 8
        tela.blit(fonte_menor.render("Ação:", True, DESTAQUE), (px + 18, y_txt))
        for linha in _quebrar_texto(fonte_texto, txt_acao, larg_card - 88)[:2]:
            tela.blit(fonte_texto.render(linha, True, TEXTO_PRINCIPAL), (px + 72, y_txt))
            y_txt += 22

    # --- RODAPÉ ---
    y_rodape = 636
    pygame.draw.line(tela, BORDA_PISTA, (margem_x, y_rodape), (x_fim, y_rodape), 1)

    tela.blit(
        fonte_texto.render("Na dúvida, desacelere e aguarde a via desimpedir.   ·   Esc: Sair", True, TEXTO_SECUNDARIO),
        (margem_x, y_rodape + 26),
    )

    pulso = 0.5 + 0.5 * math.sin(tempo_s * 4.0)
    cta_rect = pygame.Rect(x_fim - 380, y_rodape + 16, 380, 44)
    pygame.draw.rect(tela, DESTAQUE, cta_rect, border_radius=4)
    cor_dot = FUNDO if pulso > 0.35 else ASFALTO
    pygame.draw.rect(tela, cor_dot, (cta_rect.x + 14, cta_rect.y + 14, 6, 16), border_radius=2)

    cta_txt = fonte_menor.render("ESPAÇO ou ENTER  ·  Iniciar corrida", True, FUNDO)
    tela.blit(cta_txt, (cta_rect.centerx - cta_txt.get_width() // 2 + 6, cta_rect.centery - cta_txt.get_height() // 2))
