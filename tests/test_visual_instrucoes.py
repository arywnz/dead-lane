"""Testes para garantir que os novos sprites, sinalizações, tela de instruções e boletim renderizam sem erros."""

import os
import pygame
import pytest

# Usar driver de vídeo dummy para rodar em ambiente sem display gráfico
os.environ["SDL_VIDEODRIVER"] = "dummy"

from src.assets import carregar_icone, carregar_sprite
from src.boletim import (
    calcular_patente,
    desenhar_boletim_pilotagem,
    gerar_dica_personalizada,
)
from src.cenario_visual import (
    desenhar_alerta_borda,
    desenhar_cenario_avenida,
    desenhar_ciclista,
    desenhar_marcos_percurso,
    desenhar_painel,
    desenhar_perigo_ponto_cego,
    desenhar_perigo_porta,
    desenhar_tela_instrucoes,
    desenhar_veiculo,
)
from src.ciclista import Ciclista
from src.comparacao import Comparacao, DesempenhoSituacao
from src.configuracao import (
    ALTURA_COLISAO_CICLISTA,
    ALTURA_JANELA,
    CENTRO_PISTA_X,
    CICLISTA_TELA_Y,
    COMPRIMENTO_PERCURSO_M,
    LARGURA_COLISAO_CICLISTA,
    LARGURA_JANELA,
)
from src.metricas import ResumoDesempenho
from src.percurso import Percurso
from src.perigos import GerenciadorPerigos
from src.trafego import GerenciadorTrafego, TipoVeiculo, Veiculo


@pytest.fixture(scope="module", autouse=True)
def setup_pygame():
    pygame.init()
    pygame.font.init()
    tela = pygame.display.set_mode((LARGURA_JANELA, ALTURA_JANELA))
    yield tela
    pygame.quit()


def test_sprites_e_icones_carregam(setup_pygame):
    nomes_sprites = [
        "ciclista",
        "ciclista_freando",
        "carro_estacionado",
        "carro_estacionado_aviso",
        "porta_aberta",
        "porta_aviso_zona",
        "onibus",
        "onibus_seta",
        "carro_0",
        "carro_1",
    ]
    for nome in nomes_sprites:
        surf = carregar_sprite(nome)
        assert isinstance(surf, pygame.Surface)
        assert surf.get_width() > 0 and surf.get_height() > 0

    nomes_icones = [
        "icone_alerta",
        "icone_porta",
        "icone_ponto_cego",
        "icone_alerta_borda",
        "icone_sharrow",
    ]
    for nome in nomes_icones:
        surf = carregar_icone(nome)
        assert isinstance(surf, pygame.Surface)
        assert surf.get_width() > 0 and surf.get_height() > 0


def test_tela_instrucoes_renderiza(setup_pygame):
    tela = setup_pygame
    fonte_titulo = pygame.font.SysFont("Segoe UI", 42, bold=True)
    fonte_subtitulo = pygame.font.SysFont("Segoe UI", 24, bold=True)
    fonte_texto = pygame.font.SysFont("Segoe UI", 20)
    fonte_menor = pygame.font.SysFont("Segoe UI", 17, bold=True)

    desenhar_tela_instrucoes(
        tela,
        tempo_s=1.5,
        fonte_titulo=fonte_titulo,
        fonte_texto=fonte_texto,
        fonte_menor=fonte_menor,
        fonte_subtitulo=fonte_subtitulo,
    )
    assert tela.get_at((640, 360)) is not None


def test_elementos_de_jogo_e_alertas_renderizam(setup_pygame):
    tela = setup_pygame
    ciclista = Ciclista(x=CENTRO_PISTA_X)
    percurso = Percurso()
    perigos = GerenciadorPerigos.criar_padrao()
    fonte_texto = pygame.font.SysFont("Segoe UI", 20)
    fonte_menor = pygame.font.SysFont("Segoe UI", 17, bold=True)

    # 1. Cenário
    desenhar_cenario_avenida(tela, ciclista.distancia_m, percurso.indice_trecho)
    desenhar_marcos_percurso(tela, ciclista.distancia_m, fonte_texto)

    # 2. Ciclista (normal e freando)
    desenhar_ciclista(tela, ciclista, freando=False)
    desenhar_ciclista(tela, ciclista, freando=True)

    # 3. Porta
    for porta in perigos.portas[:2]:
        desenhar_perigo_porta(tela, porta, ciclista.distancia_m, fonte_texto, tempo_s=1.0)

    # 4. Veículo
    carro = Veiculo(
        tipo=TipoVeiculo.CARRO,
        faixa=0,
        distancia_m=ciclista.distancia_m + 10.0,
        velocidade_base_mps=6.0,
        velocidade_mps=6.0,
    )
    desenhar_veiculo(tela, carro, ciclista.distancia_m, percurso.indice_trecho, tempo_s=1.0)

    onibus = Veiculo(
        tipo=TipoVeiculo.ONIBUS,
        faixa=1,
        distancia_m=ciclista.distancia_m + 15.0,
        velocidade_base_mps=5.0,
        velocidade_mps=5.0,
        seta_direita_ativa=True,
    )
    desenhar_veiculo(tela, onibus, ciclista.distancia_m, percurso.indice_trecho, tempo_s=1.0)

    # 5. Ponto cego
    for pc in perigos.pontos_cegos[:2]:
        pc.atualizar(0.1, ciclista.distancia_m)
        desenhar_perigo_ponto_cego(
            tela,
            pc,
            ciclista.distancia_m,
            percurso.indice_trecho,
            tempo_s=1.0,
            fonte=fonte_menor,
            ciclista_em_risco=True,
        )

    # 6. Alerta de borda (crítico e aviso)
    desenhar_alerta_borda(tela, em_risco_critico=True, em_aviso=False, tempo_s=1.0)
    desenhar_alerta_borda(tela, em_risco_critico=False, em_aviso=True, tempo_s=1.0)


def test_hitbox_ciclista_inalterada():
    area_ciclista = pygame.FRect(0, 0, LARGURA_COLISAO_CICLISTA, ALTURA_COLISAO_CICLISTA)
    assert area_ciclista.width == 24
    assert area_ciclista.height == 52


def test_calcular_patente():
    # Rank S: 0 falhas, taxa de antecipação >= 85%
    resumo_s = ResumoDesempenho(antecipacoes=17, reacoes_tardias=1, falhas=0, colisoes_trafego=0, tempo_medio_resposta_s=0.2, erro_mais_comum=None)
    pat_s = calcular_patente(resumo_s)
    assert pat_s.rank == "S"

    # Rank A: 0 falhas, taxa de antecipação >= 65%
    resumo_a = ResumoDesempenho(antecipacoes=13, reacoes_tardias=5, falhas=0, colisoes_trafego=0, tempo_medio_resposta_s=0.5, erro_mais_comum="porta")
    pat_a = calcular_patente(resumo_a)
    assert pat_a.rank == "A"

    # Rank B: <= 2 falhas, taxa de antecipação >= 40%
    resumo_b = ResumoDesempenho(antecipacoes=9, reacoes_tardias=7, falhas=2, colisoes_trafego=0, tempo_medio_resposta_s=0.9, erro_mais_comum="ponto_cego")
    pat_b = calcular_patente(resumo_b)
    assert pat_b.rank == "B"

    # Rank C: muitas falhas
    resumo_c = ResumoDesempenho(antecipacoes=3, reacoes_tardias=10, falhas=5, colisoes_trafego=1, tempo_medio_resposta_s=1.5, erro_mais_comum="porta")
    pat_c = calcular_patente(resumo_c)
    assert pat_c.rank == "C"


def test_gerar_dica_personalizada():
    dica_porta = gerar_dica_personalizada(ResumoDesempenho(10, 5, 2, 0, 0.4, "porta"))
    assert "Portas de Carros" in dica_porta
    assert "faixa central" in dica_porta

    dica_pc = gerar_dica_personalizada(ResumoDesempenho(10, 5, 2, 0, 0.4, "ponto_cego"))
    assert "Ponto Cego de Ônibus" in dica_pc
    assert "Angles Morts" in dica_pc

    dica_trafego = gerar_dica_personalizada(ResumoDesempenho(15, 0, 0, 2, 0.1, None))
    assert "Fluxo e Espaçamento" in dica_trafego

    dica_perfeita = gerar_dica_personalizada(ResumoDesempenho(18, 0, 0, 0, 0.0, None))
    assert "Excelência" in dica_perfeita


def test_desenhar_boletim_pilotagem(setup_pygame):
    tela = setup_pygame
    resumo = ResumoDesempenho(
        antecipacoes=15,
        reacoes_tardias=3,
        falhas=0,
        colisoes_trafego=0,
        tempo_medio_resposta_s=0.35,
        erro_mais_comum="porta",
    )
    comparacoes = [
        Comparacao(
            jogador="Teste",
            tipo="porta",
            inicio=DesempenhoSituacao("porta_1", 1, 1, 0, 0, 0.6),
            fim=DesempenhoSituacao("porta_9", 1, 1, 0, 0, 0.2),
        ),
        Comparacao(
            jogador="Teste",
            tipo="ponto_cego",
            inicio=DesempenhoSituacao("ponto_cego_1", 1, 0, 1, 0, 1.2),
            fim=DesempenhoSituacao("ponto_cego_9", 1, 1, 0, 0, 0.1),
        ),
    ]

    botoes = desenhar_boletim_pilotagem(
        tela,
        resumo=resumo,
        comparacoes=comparacoes,
        tempo_percurso_s=185.4,
        jogador="CiclistaTeste",
        tempo_animacao_s=2.0,
    )

    assert "jogar_novamente" in botoes
    assert "sair" in botoes
    assert isinstance(botoes["jogar_novamente"], pygame.Rect)
    assert isinstance(botoes["sair"], pygame.Rect)
    assert tela.get_at((640, 360)) is not None


def test_desenhar_boletim_pilotagem_pausa(setup_pygame):
    tela = setup_pygame
    resumo = ResumoDesempenho(
        antecipacoes=5,
        reacoes_tardias=1,
        falhas=0,
        colisoes_trafego=0,
        tempo_medio_resposta_s=0.25,
        erro_mais_comum=None,
    )
    botoes = desenhar_boletim_pilotagem(
        tela,
        resumo=resumo,
        comparacoes=[],
        tempo_percurso_s=45.0,
        jogador="CiclistaPausa",
        em_pausa=True,
    )

    assert "continuar" in botoes
    assert "recomecar" in botoes
    assert "sair" in botoes
    assert isinstance(botoes["continuar"], pygame.Rect)
    assert isinstance(botoes["recomecar"], pygame.Rect)
    assert isinstance(botoes["sair"], pygame.Rect)

