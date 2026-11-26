"""Testes da colisão com a porta do carro estacionado."""

from __future__ import annotations

from simulacao import SEGUIR, Comando, Simulacao, criar_area_ciclista

from jogo import criar_partida
from src.ciclista import Ciclista
from src.configuracao import (
    ALTURA_COLISAO_CICLISTA,
    ALTURA_PORTA,
    CENTROS_FAIXAS_X,
    DURACAO_AVISO_PORTA_S,
    DURACAO_PORTA_ABERTA_S,
    ESCALA_PISTA_PX_POR_M,
    VELOCIDADE_INICIAL_MPS,
)
from src.perigos import FasePontoCego, FasePorta, GerenciadorPerigos, PerigoPorta

MENSAGEM_PORTA = "Colisão com a porta. R para reiniciar."
FAIXA_DIREITA_X = CENTROS_FAIXAS_X[2]
FAIXA_CENTRAL_X = CENTROS_FAIXAS_X[1]
# Distância (m) em que o retângulo do ciclista ainda encosta na porta, para frente ou para trás.
TOLERANCIA_CONTATO_M = (ALTURA_COLISAO_CICLISTA / 2 + ALTURA_PORTA / 2) / ESCALA_PISTA_PX_POR_M


def _simulacao_com_porta(distancia_porta_m: float = 40.0, x_ciclista: float = FAIXA_DIREITA_X) -> tuple[Simulacao, PerigoPorta]:
    porta = PerigoPorta(distancia_m=distancia_porta_m)
    perigos = GerenciadorPerigos(portas=[porta], pontos_cegos=[])
    return Simulacao(Ciclista(x=x_ciclista), perigos), porta


def _seguir_reto(_sim: Simulacao) -> Comando:
    return SEGUIR


def test_ciclista_que_nao_reage_colide_com_a_porta_aberta() -> None:
    sim, porta = _simulacao_com_porta()

    colisao = sim.executar(_seguir_reto, duracao_s=10.0)

    assert colisao == MENSAGEM_PORTA
    assert porta.fase is FasePorta.ABERTA
    assert abs(sim.ciclista.distancia_m - porta.distancia_m) < TOLERANCIA_CONTATO_M


def test_frear_durante_o_aviso_para_antes_da_porta() -> None:
    sim, porta = _simulacao_com_porta()

    def frear_apos_aviso(s: Simulacao) -> Comando:
        return Comando(frear=porta.fase is not FasePorta.AGUARDANDO)

    colisao = sim.executar(frear_apos_aviso, duracao_s=10.0)

    assert colisao is None
    assert porta.fase is FasePorta.FECHADA
    assert sim.ciclista.velocidade_mps == 0.0
    assert sim.ciclista.distancia_m < porta.distancia_m - TOLERANCIA_CONTATO_M


def test_passar_pela_porta_fechada_depois_de_frear_e_seguro() -> None:
    sim, porta = _simulacao_com_porta()
    sim.executar(lambda s: Comando(frear=porta.fase is not FasePorta.AGUARDANDO), duracao_s=10.0)
    assert porta.fase is FasePorta.FECHADA

    colisao = sim.executar(
        lambda s: Comando(acelerar=True),
        duracao_s=10.0,
        parar_quando=lambda s: s.ciclista.distancia_m > porta.distancia_m + 5.0,
    )

    assert colisao is None
    assert sim.ciclista.distancia_m > porta.distancia_m + 5.0


def test_mudar_para_a_faixa_central_durante_o_aviso_evita_a_porta() -> None:
    sim, porta = _simulacao_com_porta()

    def desviar_apos_aviso(s: Simulacao) -> Comando:
        precisa_desviar = porta.fase is not FasePorta.AGUARDANDO and s.ciclista.x > FAIXA_CENTRAL_X
        return Comando(lateral=-1 if precisa_desviar else 0)

    colisao = sim.executar(
        desviar_apos_aviso,
        duracao_s=10.0,
        parar_quando=lambda s: s.ciclista.distancia_m > porta.distancia_m + 5.0,
    )

    assert colisao is None
    assert sim.ciclista.distancia_m > porta.distancia_m + 5.0
    assert porta.fase is not FasePorta.AGUARDANDO


def test_ciclista_na_faixa_central_nunca_encosta_na_porta() -> None:
    sim, porta = _simulacao_com_porta(x_ciclista=FAIXA_CENTRAL_X)

    colisao = sim.executar(
        _seguir_reto,
        duracao_s=10.0,
        parar_quando=lambda s: s.ciclista.distancia_m > porta.distancia_m + 5.0,
    )

    assert colisao is None


def test_somente_a_porta_aberta_causa_colisao() -> None:
    distancia_m = 10.0
    porta = PerigoPorta(distancia_m=distancia_m)
    perigos = GerenciadorPerigos(portas=[porta], pontos_cegos=[])
    na_porta = criar_area_ciclista(FAIXA_DIREITA_X)
    fora_da_porta = criar_area_ciclista(FAIXA_CENTRAL_X)

    assert porta.fase is FasePorta.AGUARDANDO
    assert perigos.verificar_colisao(na_porta, distancia_m) is None

    perigos.atualizar(0.0, distancia_m, na_porta)
    assert porta.fase is FasePorta.AVISO
    assert perigos.verificar_colisao(na_porta, distancia_m) is None

    perigos.atualizar(DURACAO_AVISO_PORTA_S, distancia_m, na_porta)
    assert porta.fase is FasePorta.ABERTA
    assert perigos.verificar_colisao(na_porta, distancia_m) == MENSAGEM_PORTA
    assert perigos.verificar_colisao(fora_da_porta, distancia_m) is None

    perigos.atualizar(DURACAO_PORTA_ABERTA_S, distancia_m, na_porta)
    assert porta.fase is FasePorta.FECHADA
    assert perigos.verificar_colisao(na_porta, distancia_m) is None


def test_porta_nao_avisa_durante_o_intervalo_do_checkpoint() -> None:
    porta = PerigoPorta(distancia_m=10.0)

    porta.atualizar(0.5, 5.0, permitir_aviso=False)

    assert porta.fase is FasePorta.AGUARDANDO


def _bater_na_primeira_porta(ciclista: Ciclista, perigos: GerenciadorPerigos) -> str | None:
    ciclista.x = FAIXA_DIREITA_X
    sim = Simulacao(ciclista, perigos)
    primeira_porta = perigos.portas[0]
    return sim.executar(
        _seguir_reto,
        duracao_s=primeira_porta.distancia_m / VELOCIDADE_INICIAL_MPS + 5.0,
        parar_quando=lambda s: s.ciclista.distancia_m > primeira_porta.distancia_m + 5.0,
    )


def test_reiniciar_apos_colisao_restaura_o_percurso() -> None:
    ciclista, _percurso, perigos, _trafego = criar_partida()
    assert _bater_na_primeira_porta(ciclista, perigos) == MENSAGEM_PORTA
    distancia_primeira_colisao = ciclista.distancia_m

    ciclista, percurso, perigos, trafego = criar_partida()

    assert ciclista.distancia_m == 0.0
    assert ciclista.velocidade_mps == VELOCIDADE_INICIAL_MPS
    assert percurso.indice_trecho == 0 and not percurso.concluido
    assert all(p.fase is FasePorta.AGUARDANDO for p in perigos.portas)
    assert all(pc.fase is FasePontoCego.AGUARDANDO and pc.onibus is None for pc in perigos.pontos_cegos)
    assert trafego.veiculos == []

    # A nova tentativa se comporta exatamente como a primeira.
    assert _bater_na_primeira_porta(ciclista, perigos) == MENSAGEM_PORTA
    assert ciclista.distancia_m == distancia_primeira_colisao


def test_porta_esquerda_colide_na_faixa_esquerda_e_poupa_faixa_central() -> None:
    faixa_esquerda_x = CENTROS_FAIXAS_X[0]
    porta_esq = PerigoPorta(distancia_m=40.0, lado="esquerda")
    sim_col = Simulacao(Ciclista(x=faixa_esquerda_x), GerenciadorPerigos(portas=[porta_esq], pontos_cegos=[]))
    assert sim_col.executar(_seguir_reto, duracao_s=10.0) == MENSAGEM_PORTA

    porta_esq_2 = PerigoPorta(distancia_m=40.0, lado="esquerda")
    sim_seg = Simulacao(Ciclista(x=FAIXA_CENTRAL_X), GerenciadorPerigos(portas=[porta_esq_2], pontos_cegos=[]))
    assert (
        sim_seg.executar(
            _seguir_reto,
            duracao_s=10.0,
            parar_quando=lambda s: s.ciclista.distancia_m > porta_esq_2.distancia_m + 5.0,
        )
        is None
    )


def test_porta_em_velocidade_maxima_ainda_causa_colisao() -> None:
    for lado, x_ini in (("direita", FAIXA_DIREITA_X), ("esquerda", CENTROS_FAIXAS_X[0])):
        porta = PerigoPorta(distancia_m=60.0, lado=lado)
        sim = Simulacao(Ciclista(x=x_ini, velocidade_mps=16.0), GerenciadorPerigos(portas=[porta], pontos_cegos=[]))
        assert sim.executar(_seguir_reto, duracao_s=10.0) == MENSAGEM_PORTA


def test_percurso_inclui_portas_nos_dois_lados() -> None:
    _c, _p, perigos, _t = criar_partida(aleatorio=False)
    lados = {porta.lado for porta in perigos.portas}
    assert lados == {"esquerda", "direita"}
