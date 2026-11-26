"""Comparação do desempenho em situações equivalentes no início e no fim do percurso."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from src.configuracao import SITUACOES_COMPARAVEIS
from src.metricas import CAMPOS_CSV, RegistroPerigo, ResultadoPerigo

NOMES_TIPOS = {"porta": "Porta do carro", "ponto_cego": "Ponto cego do ônibus"}
TODOS_OS_JOGADORES = "Todos os jogadores"


@dataclass(frozen=True)
class DesempenhoSituacao:
    id_evento: str
    tentativas: int
    antecipacoes: int
    reacoes_tardias: int
    falhas: int
    tempo_medio_resposta_s: float | None

    @property
    def taxa_antecipacao(self) -> float | None:
        return self.antecipacoes / self.tentativas if self.tentativas else None

    @property
    def taxa_falha(self) -> float | None:
        return self.falhas / self.tentativas if self.tentativas else None


@dataclass(frozen=True)
class Comparacao:
    jogador: str
    tipo: str
    inicio: DesempenhoSituacao
    fim: DesempenhoSituacao

    @property
    def tendencia(self) -> str:
        """Melhorou, piorou, igual ou sem dados, olhando primeiro as falhas e antecipações e depois o tempo."""
        if not self.inicio.tentativas or not self.fim.tentativas:
            return "sem dados"
        nota_inicio = self.inicio.taxa_antecipacao - self.inicio.taxa_falha
        nota_fim = self.fim.taxa_antecipacao - self.fim.taxa_falha
        if abs(nota_fim - nota_inicio) > 1e-9:
            return "melhorou" if nota_fim > nota_inicio else "piorou"
        tempo_inicio, tempo_fim = self.inicio.tempo_medio_resposta_s, self.fim.tempo_medio_resposta_s
        if tempo_inicio is None or tempo_fim is None or abs(tempo_fim - tempo_inicio) < 0.05:
            return "igual"
        return "melhorou" if tempo_fim < tempo_inicio else "piorou"


def ler_registros(caminhos: Iterable[Path]) -> list[RegistroPerigo]:
    """Lê os CSVs gravados por `RegistroDesempenho`."""
    registros: list[RegistroPerigo] = []
    for caminho in caminhos:
        with Path(caminho).open(encoding="utf-8-sig", newline="") as arquivo:
            leitor = csv.DictReader(arquivo, delimiter=";")
            if leitor.fieldnames is None or tuple(leitor.fieldnames) != CAMPOS_CSV:
                raise ValueError(f"{caminho} não está no formato de resultados do Dead Lane.")
            for linha in leitor:
                tempo = linha["tempo_resposta_s"]
                registros.append(
                    RegistroPerigo(
                        tentativa=int(linha["tentativa"]),
                        jogador=linha["jogador"],
                        id_evento=linha["id_evento"],
                        tipo=linha["tipo"],
                        trecho=int(linha["trecho"]),
                        marco_m=float(linha["marco_m"]),
                        resultado=ResultadoPerigo(linha["resultado"]),
                        tempo_resposta_s=float(tempo) if tempo else None,
                        motivo=linha["motivo"],
                    )
                )
    return registros


def _desempenho(registros: list[RegistroPerigo], id_evento: str) -> DesempenhoSituacao:
    da_situacao = [r for r in registros if r.id_evento == id_evento]
    tempos = [
        r.tempo_resposta_s
        for r in da_situacao
        if r.resultado is not ResultadoPerigo.FALHA and r.tempo_resposta_s is not None
    ]
    return DesempenhoSituacao(
        id_evento=id_evento,
        tentativas=len(da_situacao),
        antecipacoes=sum(r.resultado is ResultadoPerigo.ANTECIPACAO for r in da_situacao),
        reacoes_tardias=sum(r.resultado is ResultadoPerigo.REACAO_TARDIA for r in da_situacao),
        falhas=sum(r.resultado is ResultadoPerigo.FALHA for r in da_situacao),
        tempo_medio_resposta_s=sum(tempos) / len(tempos) if tempos else None,
    )


def comparar(registros: list[RegistroPerigo]) -> list[Comparacao]:
    """Compara, por jogador e por tipo de perigo, a situação do início com a equivalente do fim."""
    jogadores = sorted({r.jogador for r in registros})
    grupos = [(jogador or "(sem nome)", [r for r in registros if r.jogador == jogador]) for jogador in jogadores]
    if len(jogadores) > 1:
        grupos.append((TODOS_OS_JOGADORES, registros))

    comparacoes: list[Comparacao] = []
    for jogador, do_jogador in grupos:
        for tipo, (id_inicio, id_fim) in SITUACOES_COMPARAVEIS.items():
            comparacoes.append(
                Comparacao(
                    jogador=jogador,
                    tipo=tipo,
                    inicio=_desempenho(do_jogador, id_inicio),
                    fim=_desempenho(do_jogador, id_fim),
                )
            )
    return comparacoes


def _porcentagem(valor: float | None) -> str:
    return "—" if valor is None else f"{valor * 100:.0f}%"


def _segundos(valor: float | None) -> str:
    return "—" if valor is None else f"{valor:.2f} s".replace(".", ",")


def _linha_situacao(rotulo: str, desempenho: DesempenhoSituacao) -> str:
    return (
        f"| {rotulo} (`{desempenho.id_evento}`) | {desempenho.tentativas} | {desempenho.antecipacoes} | "
        f"{desempenho.reacoes_tardias} | {desempenho.falhas} | {_porcentagem(desempenho.taxa_antecipacao)} | "
        f"{_porcentagem(desempenho.taxa_falha)} | {_segundos(desempenho.tempo_medio_resposta_s)} |"
    )


def gerar_relatorio(comparacoes: list[Comparacao], arquivos: list[Path]) -> str:
    linhas = [
        "# Comparação de desempenho em situações equivalentes",
        "",
        "Relatório gerado por `comparar_desempenho.py` a partir dos resultados gravados pelo jogo.",
        "Cada par compara o primeiro perigo de um tipo no trecho 1 (*Manhã tranquila*) com o último do mesmo tipo "
        "no trecho 3 (*Hora do rush*). As duas situações têm o mesmo aviso e nenhum veículo comum nas faixas usadas para "
        "evitar o perigo, então a diferença de desempenho vem do jogador, e não do cenário.",
        "",
        "Arquivos analisados: " + ", ".join(f"`{Path(a).name}`" for a in arquivos),
        "",
        "O tempo médio de resposta considera só as situações resolvidas (antecipações e reações tardias).",
    ]
    jogador_atual = None
    for comparacao in comparacoes:
        if comparacao.jogador != jogador_atual:
            jogador_atual = comparacao.jogador
            linhas += ["", f"## {jogador_atual}"]
        linhas += [
            "",
            f"### {NOMES_TIPOS.get(comparacao.tipo, comparacao.tipo)} — {comparacao.tendencia}",
            "",
            "| Situação | Tentativas | Antecipações | Reações tardias | Falhas | Taxa de antecipação | Taxa de falha | Tempo médio de resposta |",
            "|---|---|---|---|---|---|---|---|",
            _linha_situacao("Início", comparacao.inicio),
            _linha_situacao("Fim", comparacao.fim),
        ]
    return "\n".join(linhas) + "\n"
