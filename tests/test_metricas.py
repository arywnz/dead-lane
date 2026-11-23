"""Testes do registro de antecipações, reações tardias e falhas."""

import csv
from datetime import datetime
from pathlib import Path

import pytest
from simulacao import SEGUIR, Comando, Simulacao

from src.ciclista import Ciclista
from src.configuracao import CENTROS_FAIXAS_X, LIMITE_ANTECIPACAO_PONTO_CEGO_S, LIMITE_ANTECIPACAO_PORTA_S
from src.metricas import RegistroDesempenho, RegistroPerigo, ResultadoPerigo, resumir
from src.perigos import FasePontoCego, FasePorta, GerenciadorPerigos, PerigoPontoCego, PerigoPorta

FAIXA_ESQUERDA_X, FAIXA_CENTRAL_X, FAIXA_DIREITA_X = CENTROS_FAIXAS_X


@pytest.fixture
def registro(tmp_path: Path) -> RegistroDesempenho:
    return RegistroDesempenho(jogador="teste", pasta_resultados=tmp_path, inicio_sessao=datetime(2026, 11, 22, 10, 0, 0))


def _cenario_porta(registro: RegistroDesempenho, x: float = FAIXA_DIREITA_X) -> tuple[Simulacao, PerigoPorta]:
    porta = PerigoPorta(distancia_m=40.0, id_evento="porta_1")
    perigos = GerenciadorPerigos(portas=[porta], pontos_cegos=[])
    return Simulacao(Ciclista(x=x), perigos, registro), porta


def _cenario_ponto_cego(registro: RegistroDesempenho, x: float = FAIXA_DIREITA_X) -> tuple[Simulacao, PerigoPontoCego]:
    ponto_cego = PerigoPontoCego(distancia_encontro_m=40.0, id_evento="ponto_cego_1")
    perigos = GerenciadorPerigos(portas=[], pontos_cegos=[ponto_cego])
    return Simulacao(Ciclista(x=x), perigos, registro), ponto_cego


def _rodar_ate_registrar(sim: Simulacao, politica) -> RegistroPerigo:
    sim.executar(politica, duracao_s=20.0, parar_quando=lambda s: bool(s.registro.registros))
    assert len(sim.registro.registros) == 1
    return sim.registro.registros[0]


# ---------------------------------------------------------------- porta do carro


def test_porta_desviar_no_aviso_e_antecipacao(registro: RegistroDesempenho) -> None:
    sim, porta = _cenario_porta(registro)

    def desviar(s: Simulacao) -> Comando:
        return Comando(lateral=-1 if porta.fase is not FasePorta.AGUARDANDO and s.ciclista.x > FAIXA_CENTRAL_X else 0)

    resultado = _rodar_ate_registrar(sim, desviar)

    assert resultado.resultado is ResultadoPerigo.ANTECIPACAO
    assert 0.0 < resultado.tempo_resposta_s < 0.2
    assert (resultado.id_evento, resultado.tipo, resultado.trecho) == ("porta_1", "porta", 1)


def test_porta_frear_no_aviso_e_antecipacao(registro: RegistroDesempenho) -> None:
    sim, porta = _cenario_porta(registro)

    resultado = _rodar_ate_registrar(sim, lambda s: Comando(frear=porta.fase is not FasePorta.AGUARDANDO))

    assert resultado.resultado is ResultadoPerigo.ANTECIPACAO
    assert 0.0 < resultado.tempo_resposta_s <= LIMITE_ANTECIPACAO_PORTA_S


def test_porta_ja_em_faixa_segura_e_antecipacao_sem_tempo_de_resposta(registro: RegistroDesempenho) -> None:
    sim, _porta = _cenario_porta(registro, x=FAIXA_CENTRAL_X)

    resultado = _rodar_ate_registrar(sim, lambda s: SEGUIR)

    assert resultado.resultado is ResultadoPerigo.ANTECIPACAO
    assert resultado.tempo_resposta_s == 0.0


def test_porta_desviar_so_com_a_porta_aberta_e_reacao_tardia(registro: RegistroDesempenho) -> None:
    sim, porta = _cenario_porta(registro)

    def desviar_tarde(s: Simulacao) -> Comando:
        return Comando(lateral=-1 if porta.fase is FasePorta.ABERTA and s.ciclista.x > FAIXA_CENTRAL_X else 0)

    resultado = _rodar_ate_registrar(sim, desviar_tarde)

    assert resultado.resultado is ResultadoPerigo.REACAO_TARDIA
    assert resultado.tempo_resposta_s > LIMITE_ANTECIPACAO_PORTA_S


def test_porta_sem_reacao_e_falha(registro: RegistroDesempenho) -> None:
    sim, _porta = _cenario_porta(registro)

    resultado = _rodar_ate_registrar(sim, lambda s: SEGUIR)

    assert resultado.resultado is ResultadoPerigo.FALHA
    assert resultado.tempo_resposta_s is None
    assert resultado.motivo == "Colisão com a porta. R para reiniciar."


def test_rota_de_colisao_considera_frenagem_e_porta_ja_passada() -> None:
    porta = PerigoPorta(distancia_m=40.0)
    sim, _ = _cenario_porta(RegistroDesempenho())
    porta.atualizar(0.0, 30.0)  # aviso começa com o ciclista a 10 m
    area = sim.area

    assert porta.ciclista_em_rota_de_colisao(area, 30.0, 8.0)
    assert not porta.ciclista_em_rota_de_colisao(area, 30.0, 0.0)  # parado antes da porta
    assert not porta.ciclista_em_rota_de_colisao(area, 30.0, 2.0)  # chega depois de a porta fechar
    assert not porta.ciclista_em_rota_de_colisao(area, 42.0, 8.0)  # já passou


# ---------------------------------------------------------------- ponto cego do ônibus


def test_ponto_cego_pela_esquerda_e_antecipacao(registro: RegistroDesempenho) -> None:
    sim, _ponto_cego = _cenario_ponto_cego(registro, x=FAIXA_ESQUERDA_X)

    resultado = _rodar_ate_registrar(sim, lambda s: SEGUIR)

    assert resultado.resultado is ResultadoPerigo.ANTECIPACAO
    assert resultado.tempo_resposta_s == 0.0
    assert resultado.tipo == "ponto_cego"


def test_ponto_cego_frear_no_aviso_antes_de_entrar_na_zona_e_antecipacao(registro: RegistroDesempenho) -> None:
    sim, ponto_cego = _cenario_ponto_cego(registro)

    resultado = _rodar_ate_registrar(sim, lambda s: Comando(frear=ponto_cego.fase is not FasePontoCego.AGUARDANDO))

    assert not ponto_cego.ciclista_esteve_na_zona
    assert resultado.resultado is ResultadoPerigo.ANTECIPACAO


def test_ponto_cego_frear_ja_dentro_da_zona_e_reacao_tardia(registro: RegistroDesempenho) -> None:
    sim, ponto_cego = _cenario_ponto_cego(registro)
    inicio_aviso: list[float] = []

    def frear_tarde(s: Simulacao) -> Comando:
        if ponto_cego.fase is FasePontoCego.AGUARDANDO:
            return SEGUIR
        if not inicio_aviso:
            inicio_aviso.append(s.tempo_s)
        # Só freia (a saída indicada pelo jogo) depois de entrar na zona, 1,5 s após o aviso.
        return Comando(frear=s.tempo_s - inicio_aviso[0] >= 1.5)

    resultado = _rodar_ate_registrar(sim, frear_tarde)

    assert ponto_cego.ciclista_esteve_na_zona
    assert resultado.resultado is ResultadoPerigo.REACAO_TARDIA
    assert resultado.tempo_resposta_s > LIMITE_ANTECIPACAO_PONTO_CEGO_S


def test_ponto_cego_sem_reacao_e_falha(registro: RegistroDesempenho) -> None:
    sim, _ponto_cego = _cenario_ponto_cego(registro)

    resultado = _rodar_ate_registrar(sim, lambda s: SEGUIR)

    assert resultado.resultado is ResultadoPerigo.FALHA
    assert resultado.motivo == "Ficou no ponto cego do ônibus. R para reiniciar."


# ---------------------------------------------------------------- tentativas, CSV e resumo


def test_cada_tentativa_grava_um_resultado_por_perigo_no_csv(registro: RegistroDesempenho) -> None:
    sim, _ = _cenario_porta(registro)
    _rodar_ate_registrar(sim, lambda s: SEGUIR)
    caminho = registro.encerrar_tentativa()

    sim, _ = _cenario_porta(registro, x=FAIXA_CENTRAL_X)
    sim.executar(lambda s: SEGUIR, duracao_s=20.0, parar_quando=lambda s: len(registro.registros) == 2)
    assert registro.encerrar_tentativa() == caminho

    assert caminho == registro.caminho_csv and caminho.name == "sessao_20261122_100000.csv"
    assert caminho.read_bytes().startswith(b"\xef\xbb\xbf")  # BOM para o Excel reconhecer os acentos
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo, delimiter=";"))
    assert [(l["tentativa"], l["resultado"], l["tempo_resposta_s"]) for l in linhas] == [
        ("1", "falha", ""),
        ("2", "antecipacao", "0.00"),
    ]
    assert all(l["jogador"] == "teste" and l["id_evento"] == "porta_1" for l in linhas)


def test_tentativa_sem_perigos_nao_cria_arquivo(registro: RegistroDesempenho) -> None:
    assert registro.encerrar_tentativa() is None
    assert not registro.caminho_csv.exists()
    assert registro.tentativa == 2


def test_vitoria_classifica_perigo_ainda_em_andamento(registro: RegistroDesempenho) -> None:
    sim, porta = _cenario_porta(registro, x=FAIXA_CENTRAL_X)
    sim.executar(lambda s: SEGUIR, duracao_s=20.0, parar_quando=lambda s: porta.fase is FasePorta.AVISO)

    registro.encerrar_tentativa(tempo_vitoria_s=sim.tempo_s)

    assert [r.resultado for r in registro.registros] == [ResultadoPerigo.ANTECIPACAO]


def test_colisao_descarta_perigos_interrompidos(registro: RegistroDesempenho) -> None:
    sim, porta = _cenario_porta(registro, x=FAIXA_CENTRAL_X)
    sim.executar(lambda s: SEGUIR, duracao_s=20.0, parar_quando=lambda s: porta.fase is FasePorta.AVISO)

    registro.registrar_colisao_trafego()
    registro.encerrar_tentativa()

    assert registro.registros == []
    assert registro.resumo().colisoes_trafego == 1


def _registro(tipo: str, resultado: ResultadoPerigo, tempo: float | None) -> RegistroPerigo:
    return RegistroPerigo(1, "", f"{tipo}_1", tipo, 1, 0.0, resultado, tempo, "")


def test_resumo_conta_resultados_tempo_medio_e_erro_mais_comum() -> None:
    resumo = resumir(
        [
            _registro("porta", ResultadoPerigo.ANTECIPACAO, 0.4),
            _registro("porta", ResultadoPerigo.REACAO_TARDIA, 1.2),
            _registro("ponto_cego", ResultadoPerigo.FALHA, None),
            _registro("ponto_cego", ResultadoPerigo.REACAO_TARDIA, 2.0),
            _registro("ponto_cego", ResultadoPerigo.ANTECIPACAO, 0.0),
        ],
        colisoes_trafego=1,
    )

    assert (resumo.antecipacoes, resumo.reacoes_tardias, resumo.falhas) == (2, 2, 1)
    assert resumo.total_perigos == 5
    assert resumo.colisoes_trafego == 1
    assert resumo.tempo_medio_resposta_s == pytest.approx((0.4 + 1.2 + 2.0 + 0.0) / 4)
    assert resumo.erro_mais_comum == "ponto_cego"


def test_resumo_vazio() -> None:
    resumo = resumir([])

    assert resumo.total_perigos == 0
    assert resumo.tempo_medio_resposta_s is None
    assert resumo.erro_mais_comum is None
