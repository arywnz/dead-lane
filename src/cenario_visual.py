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

    if marcos_perigos:
        for progresso, superado in marcos_perigos:
            mx = x + round(largura_util * min(1.0, max(0.0, progresso)))
            cor_marco = DESTAQUE if superado else AVISO
            pygame.draw.circle(tela, cor_marco, (mx, barra_y + 15), 2)

    pygame.draw.line(tela, BORDA_PISTA, (x, 362), (x + largura_util, 362))

    for linha, (acao, teclas) in enumerate(
        (
            ("Acelerar", "W / ↑"),
            ("Frear (Defensivo)", "S / ↓"),
            ("Mover para os lados", "A D / ← →"),
            ("Instruções", "H / I"),
            ("Reiniciar", "R"),
            ("Sair", "Esc"),
        )
    ):
        y = 380 + linha * 30
        tela.blit(fonte_texto.render(acao, True, TEXTO_PRINCIPAL), (x, y))
        rotulo_tecla = fonte_texto.render(teclas, True, TEXTO_SECUNDARIO)
        tela.blit(rotulo_tecla, (x + largura_util - rotulo_tecla.get_width(), y))

    if mensagem_status is None:
        return

    mensagem, cor = mensagem_status
    card = pygame.Rect(x, 566, largura_util, 56)
    pygame.draw.rect(tela, FUNDO, card, border_radius=12)
    pygame.draw.rect(tela, cor, card, width=2, border_radius=12)
    pygame.draw.rect(tela, cor, (card.x + 8, card.y + 12, 4, card.height - 24), border_radius=2)
    texto_render = fonte_menor.render(mensagem, True, cor)
    if texto_render.get_width() > largura_util - 32:
        texto_render = pygame.transform.smoothscale(
            texto_render,
            (largura_util - 32, texto_render.get_height()),
        )
    tela.blit(texto_render, (card.x + 20, card.centery - texto_render.get_height() // 2))


def desenhar_tela_instrucoes(
    tela: pygame.Surface,
    tempo_s: float,
    fonte_titulo: pygame.font.Font,
    fonte_texto: pygame.font.Font,
    fonte_menor: pygame.font.Font,
    fonte_subtitulo: pygame.font.Font,
) -> None:
    """Renderiza a tela inicial de Instruções de Pilotagem com controles e reconhecimento visual de perigos."""
    tela.fill(FUNDO)

    # Faixas decorativas sutis de asfalto ao fundo
    pygame.draw.rect(tela, ASFALTO, (0, 0, 1280, 8))
    pygame.draw.rect(tela, ASFALTO, (0, ALTURA_JANELA - 8, 1280, 8))

    # Cabeçalho
    cx = 640
    titulo = fonte_titulo.render("DEAD LANE", True, DESTAQUE)
    subtitulo = fonte_subtitulo.render("INSTRUÇÕES DE PILOTAGEM DEFENSIVA", True, TEXTO_PRINCIPAL)
    descricao = fonte_texto.render("Aprenda a reconhecer os avisos visuais de perigo antes de iniciar o percurso urbano.", True, TEXTO_SECUNDARIO)

    tela.blit(titulo, (cx - titulo.get_width() // 2, 28))
    tela.blit(subtitulo, (cx - subtitulo.get_width() // 2, 80))
    tela.blit(descricao, (cx - descricao.get_width() // 2, 116))

    # Dois cartões principais: Esquerda (Controles) e Direita (Avisos Visuais de Perigo)
    largura_card = 560
    altura_card = 460
    y_cards = 152

    # --- CARD 1: CONTROLES DE PILOTAGEM ---
    card1 = pygame.Rect(60, y_cards, largura_card, altura_card)
    pygame.draw.rect(tela, PAINEL, card1, border_radius=18)
    pygame.draw.rect(tela, "#2e423b", card1, width=2, border_radius=18)

    titulo_card1 = fonte_subtitulo.render("Controles da Bicicleta", True, TEXTO_PRINCIPAL)
    tela.blit(titulo_card1, (card1.x + 24, card1.y + 20))
    pygame.draw.line(tela, BORDA_PISTA, (card1.x + 24, card1.y + 54), (card1.right - 24, card1.y + 54), 1)

    controles = (
        ("W  ou  ↑", "Acelerar", "Desenvolve velocidade até 43 km/h. Cuidado ao se aproximar de veículos lentos."),
        ("S  ou  ↓", "Frear (Crucial)", "Sua ferramenta mais segura! Reduz velocidade para sair do ponto cego e parar antes da porta."),
        ("A  D  ou  ←  →", "Mudar de Faixa", "Desvia lateralmente. A faixa central é a rota de fuga ideal quando a direita está em risco."),
        ("R", "Reiniciar", "Reinicia a partida do início a qualquer momento."),
        ("Esc", "Sair", "Encerra o jogo."),
    )

    y_ctrl = card1.y + 68
    for teclas, acao, desc in controles:
        # Badge da tecla
        rotulo_k = fonte_menor.render(teclas, True, DESTAQUE)
        badge_k = pygame.Rect(card1.x + 24, y_ctrl, max(130, rotulo_k.get_width() + 16), 26)
        pygame.draw.rect(tela, "#263933", badge_k, border_radius=6)
        tela.blit(rotulo_k, (badge_k.centerx - rotulo_k.get_width() // 2, badge_k.centery - rotulo_k.get_height() // 2))

        # Nome da ação
        tela.blit(fonte_menor.render(acao, True, TEXTO_PRINCIPAL), (badge_k.right + 14, y_ctrl + 3))

        # Descrição explicativa
        render_desc = fonte_texto.render(desc, True, TEXTO_SECUNDARIO)
        if render_desc.get_width() > card1.width - 48:
            render_desc = pygame.transform.smoothscale(render_desc, (card1.width - 48, 18))
        tela.blit(render_desc, (card1.x + 24, y_ctrl + 30))

        y_ctrl += 64

    # Dica defensiva no rodapé do Card 1
    dica_box = pygame.Rect(card1.x + 20, card1.bottom - 56, card1.width - 40, 42)
    pygame.draw.rect(tela, "#16221f", dica_box, border_radius=8)
    dica_txt = fonte_menor.render("Regra de Ouro: Na dúvida, desacelere e espere a via desimpedir!", True, DESTAQUE)
    tela.blit(dica_txt, (dica_box.centerx - dica_txt.get_width() // 2, dica_box.centery - dica_txt.get_height() // 2))

    # --- CARD 2: RECONHECIMENTO DOS AVISOS VISUAIS ---
    card2 = pygame.Rect(660, y_cards, largura_card, altura_card)
    pygame.draw.rect(tela, PAINEL, card2, border_radius=18)
    pygame.draw.rect(tela, "#2e423b", card2, width=2, border_radius=18)

    titulo_card2 = fonte_subtitulo.render("Reconhecimento de Perigos", True, TEXTO_PRINCIPAL)
    tela.blit(titulo_card2, (card2.x + 24, card2.y + 20))
    pygame.draw.line(tela, BORDA_PISTA, (card2.x + 24, card2.y + 54), (card2.right - 24, card2.y + 54), 1)

    perigos_info = (
        (
            "icone_porta",
            "Porta de Carro Abrindo (Dooring)",
            AVISO,
            "Aviso: Carro com pisca-alerta âmbar e área hachurada na pista.",
            "Ação: Mude para a faixa central com antecedência ou freie totalmente.",
        ),
        (
            "icone_ponto_cego",
            "Ponto Cego do Ônibus (Angles Morts)",
            PERIGO,
            "Aviso: Zona listrada amarela/vermelha e seta piscante no ônibus.",
            "Ação: O motorista não te vê! NUNCA emparelhe: freie para recuar ou ultrapasse pela esquerda.",
        ),
        (
            "icone_alerta_borda",
            "Alerta Periférico na Borda da Tela",
            PERIGO,
            "Aviso: Bordas da tela pulsando em vermelho/âmbar.",
            "Ação: Indica que você entrou em área de risco iminente de colisão. Reaja imediatamente!",
        ),
    )

    y_p = card2.y + 68
    for icone_nome, titulo_p, cor_destaque, desc1, desc2 in perigos_info:
        icone = carregar_icone(icone_nome)
        tela.blit(icone, (card2.x + 24, y_p + 4))

        tela.blit(fonte_menor.render(titulo_p, True, cor_destaque), (card2.x + 82, y_p))

        d1 = fonte_texto.render(desc1, True, TEXTO_PRINCIPAL)
        if d1.get_width() > card2.width - 106:
            d1 = pygame.transform.smoothscale(d1, (card2.width - 106, 17))
        tela.blit(d1, (card2.x + 82, y_p + 24))

        d2 = fonte_texto.render(desc2, True, TEXTO_SECUNDARIO)
        if d2.get_width() > card2.width - 106:
            d2 = pygame.transform.smoothscale(d2, (card2.width - 106, 17))
        tela.blit(d2, (card2.x + 82, y_p + 46))

        pygame.draw.line(tela, "#263531", (card2.x + 24, y_p + 96), (card2.right - 24, y_p + 96), 1)
        y_p += 114

    # Botão / Chamada para Ação no rodapé da tela
    pulso_cta = 0.5 + 0.5 * math.sin(tempo_s * 5.0)
    alfa_cta = int(200 + 55 * pulso_cta)
    cta_texto = fonte_subtitulo.render("Pressione [ESPAÇO] ou [ENTER] para Iniciar a Partida", True, (216, 249, 117, alfa_cta))

    cta_rect = pygame.Rect(cx - 360, ALTURA_JANELA - 86, 720, 50)
    pygame.draw.rect(tela, "#1e2e29", cta_rect, border_radius=12)
    pygame.draw.rect(tela, DESTAQUE, cta_rect, width=2, border_radius=12)
    tela.blit(cta_texto, (cta_rect.centerx - cta_texto.get_width() // 2, cta_rect.centery - cta_texto.get_height() // 2))
