"""Testes da comparação de desempenho em situações equivalentes (início × fim)."""

from pathlib import Path

import pytest

from src.comparacao import TODOS_OS_JOGADORES, comparar, gerar_relatorio, ler_registros
from src.configuracao import COMPRIMENTO_PERCURSO_M, SITUACOES_COMPARAVEIS
from src.metricas import RegistroDesempenho, RegistroPerigo, ResultadoPerigo
from src.percurso import Percurso
from src.perigos import GerenciadorPerigos
from src.trafego import GerenciadorTrafego

DELTA_S = 1 / 60
# Faixas que importam na manobra: a do ciclista (direita) e a rota de fuga da porta (central).
# Veículos na faixa da esquerda não bloqueiam a frenagem nem o desvio.
FAIXAS_DA_MANOBRA = (1, 2)
A, T, F = ResultadoPerigo.ANTECIPACAO, ResultadoPerigo.REACAO_TARDIA, ResultadoPerigo.FALHA


def _perigos_por_id() -> dict[str, object]:
    perigos = GerenciadorPerigos.criar_padrao()
    return {p.id_evento: p for p in [*perigos.portas, *perigos.pontos_cegos]}


# ---------------------------------------------------------------- equivalência das situações


def test_pares_comparam_o_primeiro_do_trecho_1_com_o_ultimo_do_trecho_3() -> None:
    perigos = GerenciadorPerigos.criar_padrao()
    por_tipo = {"porta": perigos.portas, "ponto_cego": perigos.pontos_cegos}

    for tipo, (id_inicio, id_fim) in SITUACOES_COMPARAVEIS.items():
        lista = por_tipo[tipo]
        assert lista[0].id_evento == id_inicio and lista[0].trecho == 0
        assert lista[-1].id_evento == id_fim and lista[-1].trecho == 2


def test_pares_tem_a_mesma_mecanica() -> None:
    por_id = _perigos_por_id()
    inicio, fim = (por_id[i] for i in SITUACOES_COMPARAVEIS["ponto_cego"])
    assert inicio.velocidade_onibus_mps == fim.velocidade_onibus_mps

    for tipo, (id_inicio, id_fim) in SITUACOES_COMPARAVEIS.items():
        assert type(por_id[id_inicio]) is type(por_id[id_fim])


def _veiculos_comuns_perto_dos_pares(velocidade_mps: float) -> dict[str, int]:
    """Percorre a avenida em velocidade constante e conta veículos comuns ao lado do ciclista em cada situação."""
    perigos = GerenciadorPerigos.criar_padrao()
    trafego = GerenciadorTrafego()
    percurso = Percurso()
    por_id = {p.id_evento: p for p in [*perigos.portas, *perigos.pontos_cegos]}
    # Trecho do percurso em que o ciclista enfrenta cada situação.
    janelas = {}
    for id_inicio, id_fim in SITUACOES_COMPARAVEIS.values():
        for id_evento in (id_inicio, id_fim):
            perigo = por_id[id_evento]
            if hasattr(perigo, "distancia_encontro_m"):
                janelas[id_evento] = (perigo.distancia_encontro_m, perigo.distancia_encontro_m + 45.0)
            else:
                janelas[id_evento] = (perigo.distancia_m - 15.0, perigo.distancia_m + 2.0)
    encontrados = dict.fromkeys(janelas, 0)

    distancia_m = 0.0
    while distancia_m < COMPRIMENTO_PERCURSO_M:
        distancia_m += velocidade_mps * DELTA_S
        percurso.atualizar(DELTA_S, distancia_m)
        trafego.atualizar(
            DELTA_S,
            distancia_m,
            zonas_bloqueadas=perigos.zonas_bloqueadas_faixa_direita(distancia_m),
            indice_trecho=percurso.indice_trecho,
            zonas_sem_trafego=perigos.zonas_sem_trafego(distancia_m),
        )
        for id_evento, (inicio, fim) in janelas.items():
            if inicio <= distancia_m <= fim:
                encontrados[id_evento] += sum(
                    v.faixa in FAIXAS_DA_MANOBRA and abs(v.distancia_m - distancia_m) < 12.0 for v in trafego.veiculos
                )
    return encontrados


@pytest.mark.parametrize("velocidade_mps", [6.0, 8.0, 10.0, 12.0])
def test_situacoes_comparaveis_ficam_sem_trafego_comum(velocidade_mps: float) -> None:
    assert set(_veiculos_comuns_perto_dos_pares(velocidade_mps).values()) == {0}


def test_portas_fora_da_comparacao_continuam_com_trafego_normal() -> None:
    perigos = GerenciadorPerigos.criar_padrao()
    portas_comparaveis = set(SITUACOES_COMPARAVEIS["porta"])

    for porta in perigos.portas:
        zonas = perigos.zonas_sem_trafego(porta.distancia_m - 30.0)
        sem_trafego = any(inicio <= porta.distancia_m <= fim for inicio, fim in zonas)
        assert sem_trafego == (porta.id_evento in portas_comparaveis), porta.id_evento


# ---------------------------------------------------------------- leitura e comparação dos resultados


def _salvar(tmp_path: Path, jogador: str, resultados: list[tuple[int, str, ResultadoPerigo, float | None]]) -> Path:
    registro = RegistroDesempenho(jogador=jogador, pasta_resultados=tmp_path / jogador)
    por_id = _perigos_por_id()
    for tentativa, id_evento, resultado, tempo in resultados:
        perigo = por_id[id_evento]
        tipo = "ponto_cego" if id_evento.startswith("ponto_cego") else "porta"
        marco = getattr(perigo, "distancia_encontro_m", getattr(perigo, "distancia_m", 0.0))
        registro.registros.append(
            RegistroPerigo(tentativa, jogador, id_evento, tipo, perigo.trecho + 1, marco, resultado, tempo, "")
        )
    return registro.salvar_csv()


def test_comparacao_calcula_inicio_e_fim_a_partir_do_csv(tmp_path: Path) -> None:
    caminho = _salvar(
        tmp_path,
        "Ana",
        [
            (1, "porta_1", T, 1.3),
            (1, "ponto_cego_1", F, None),
            (2, "porta_1", A, 0.5),
            (2, "ponto_cego_1", T, 2.2),
            (2, "porta_9", A, 0.3),
            (2, "ponto_cego_9", A, 0.0),
        ],
    )

    comparacoes = comparar(ler_registros([caminho]))

    porta, ponto_cego = comparacoes
    assert (porta.jogador, porta.tipo) == ("Ana", "porta")
    assert (porta.inicio.tentativas, porta.inicio.antecipacoes, porta.inicio.reacoes_tardias) == (2, 1, 1)
    assert porta.inicio.tempo_medio_resposta_s == pytest.approx(0.9)
    assert (porta.fim.tentativas, porta.fim.taxa_antecipacao) == (1, 1.0)
    assert porta.tendencia == "melhorou"

    assert ponto_cego.inicio.taxa_falha == 0.5
    assert ponto_cego.inicio.tempo_medio_resposta_s == pytest.approx(2.2)  # a falha não entra na média
    assert ponto_cego.fim.falhas == 0
    assert ponto_cego.tendencia == "melhorou"


def test_comparacao_com_varios_jogadores_inclui_o_total(tmp_path: Path) -> None:
    ana = _salvar(tmp_path, "Ana", [(1, "porta_1", A, 0.4), (1, "porta_9", F, None)])
    bia = _salvar(tmp_path, "Bia", [(1, "porta_1", A, 0.6)])

    comparacoes = comparar(ler_registros([ana, bia]))

    por_chave = {(c.jogador, c.tipo): c for c in comparacoes}
    assert por_chave[("Ana", "porta")].tendencia == "piorou"
    assert por_chave[("Bia", "porta")].tendencia == "sem dados"  # não chegou ao trecho 3
    total = por_chave[(TODOS_OS_JOGADORES, "porta")]
    assert (total.inicio.tentativas, total.fim.tentativas) == (2, 1)


def test_tendencia_usa_o_tempo_quando_os_resultados_empatam(tmp_path: Path) -> None:
    caminho = _salvar(tmp_path, "Ana", [(1, "porta_1", A, 0.8), (1, "porta_9", A, 0.3)])

    porta = comparar(ler_registros([caminho]))[0]

    assert porta.tendencia == "melhorou"


def test_relatorio_mostra_as_duas_situacoes_de_cada_par(tmp_path: Path) -> None:
    caminho = _salvar(tmp_path, "Ana", [(1, "porta_1", A, 0.5), (1, "porta_9", T, 1.4)])

    relatorio = gerar_relatorio(comparar(ler_registros([caminho])), [caminho])

    assert "## Ana" in relatorio
    assert "### Porta do carro — piorou" in relatorio
    assert "| Início (`porta_1`) | 1 | 1 | 0 | 0 | 100% | 0% | 0,50 s |" in relatorio
    assert "| Fim (`porta_9`) | 1 | 0 | 1 | 0 | 0% | 0% | 1,40 s |" in relatorio
    assert "### Ponto cego do ônibus — sem dados" in relatorio


def test_ler_registros_recusa_arquivo_em_outro_formato(tmp_path: Path) -> None:
    caminho = tmp_path / "outro.csv"
    caminho.write_text("a;b\n1;2\n", encoding="utf-8")

    with pytest.raises(ValueError):
        ler_registros([caminho])
