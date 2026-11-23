"""Registro de desempenho: classifica cada perigo como antecipação, reação tardia ou falha.

Para cada perigo, o registro começa no aviso e acompanha, quadro a quadro, se o ciclista
está em risco (rota de colisão com a porta ou dentro do ponto cego do ônibus). O tempo de
resposta é o intervalo entre o aviso e o instante em que o ciclista saiu do risco pela
última vez, ou seja, a ação que realmente resolveu a situação.
"""

import csv
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from enum import Enum
from pathlib import Path

import pygame

from src.configuracao import LIMITE_ANTECIPACAO_PONTO_CEGO_S, LIMITE_ANTECIPACAO_PORTA_S, PASTA_RESULTADOS
from src.perigos import FasePontoCego, FasePorta, GerenciadorPerigos

TIPO_PORTA = "porta"
TIPO_PONTO_CEGO = "ponto_cego"
LIMITES_ANTECIPACAO_S = {
    TIPO_PORTA: LIMITE_ANTECIPACAO_PORTA_S,
    TIPO_PONTO_CEGO: LIMITE_ANTECIPACAO_PONTO_CEGO_S,
}


class ResultadoPerigo(str, Enum):
    ANTECIPACAO = "antecipacao"
    REACAO_TARDIA = "reacao_tardia"
    FALHA = "falha"


@dataclass(frozen=True)
class RegistroPerigo:
    tentativa: int
    jogador: str
    id_evento: str
    tipo: str
    trecho: int
    marco_m: float
    resultado: ResultadoPerigo
    tempo_resposta_s: float | None
    motivo: str


@dataclass(frozen=True)
class ResumoDesempenho:
    antecipacoes: int
    reacoes_tardias: int
    falhas: int
    colisoes_trafego: int
    tempo_medio_resposta_s: float | None
    # Tipo de perigo ("porta" ou "ponto_cego") com mais falhas e reações tardias somadas.
    erro_mais_comum: str | None

    @property
    def total_perigos(self) -> int:
        return self.antecipacoes + self.reacoes_tardias + self.falhas


@dataclass
class _Acompanhamento:
    tipo: str
    trecho: int
    marco_m: float
    tempo_aviso_s: float
    em_risco: bool = False
    esteve_em_risco: bool = False
    tempo_resolucao_s: float | None = None


CAMPOS_CSV = tuple(campo.name for campo in fields(RegistroPerigo))


class RegistroDesempenho:
    """Acompanha os perigos de cada tentativa e grava um resultado por perigo em CSV."""

    def __init__(
        self,
        jogador: str = "",
        pasta_resultados: str | Path = PASTA_RESULTADOS,
        inicio_sessao: datetime | None = None,
    ) -> None:
        self.jogador = jogador
        self.tentativa = 1
        self.registros: list[RegistroPerigo] = []
        self.colisoes_trafego = 0
        inicio = inicio_sessao or datetime.now()
        self.caminho_csv = Path(pasta_resultados) / f"sessao_{inicio:%Y%m%d_%H%M%S}.csv"
        self._acompanhamentos: dict[str, _Acompanhamento] = {}
        self._finalizados: set[str] = set()
        self._registros_gravados = 0

    @property
    def registros_tentativa_atual(self) -> list[RegistroPerigo]:
        return [r for r in self.registros if r.tentativa == self.tentativa]

    def atualizar(
        self,
        tempo_s: float,
        perigos: GerenciadorPerigos,
        area_ciclista: pygame.FRect,
        distancia_ciclista_m: float,
        velocidade_mps: float,
    ) -> None:
        """Deve ser chamado a cada quadro, depois de `perigos.atualizar`."""
        for porta in perigos.portas:
            self._acompanhar(
                tempo_s,
                porta.id_evento,
                TIPO_PORTA,
                porta.trecho,
                porta.distancia_m,
                em_andamento=porta.fase in (FasePorta.AVISO, FasePorta.ABERTA),
                encerrado=porta.fase is FasePorta.FECHADA,
                em_risco=lambda p=porta: p.ciclista_em_rota_de_colisao(
                    area_ciclista, distancia_ciclista_m, velocidade_mps
                ),
            )
        for ponto_cego in perigos.pontos_cegos:
            self._acompanhar(
                tempo_s,
                ponto_cego.id_evento,
                TIPO_PONTO_CEGO,
                ponto_cego.trecho,
                ponto_cego.distancia_encontro_m,
                em_andamento=ponto_cego.fase in (FasePontoCego.AVISO, FasePontoCego.ATIVO),
                encerrado=ponto_cego.fase is FasePontoCego.ENCERRADO,
                em_risco=lambda pc=ponto_cego: pc.ciclista_na_zona(area_ciclista, distancia_ciclista_m),
            )

    def registrar_colisao(self, perigos: GerenciadorPerigos, id_evento: str, motivo: str) -> None:
        """Registra a falha no perigo que causou a colisão."""
        if id_evento in self._finalizados:
            return
        for porta in perigos.portas:
            if porta.id_evento == id_evento:
                self._finalizar(id_evento, TIPO_PORTA, porta.trecho, porta.distancia_m, ResultadoPerigo.FALHA, None, motivo)
                return
        for ponto_cego in perigos.pontos_cegos:
            if ponto_cego.id_evento == id_evento:
                self._finalizar(
                    id_evento,
                    TIPO_PONTO_CEGO,
                    ponto_cego.trecho,
                    ponto_cego.distancia_encontro_m,
                    ResultadoPerigo.FALHA,
                    None,
                    motivo,
                )
                return

    def registrar_colisao_trafego(self) -> None:
        """Batidas em veículos comuns não são perigos planejados; ficam contadas à parte."""
        self.colisoes_trafego += 1

    def encerrar_tentativa(self, tempo_vitoria_s: float | None = None) -> Path | None:
        """Grava os resultados da tentativa atual e prepara a próxima. Retorna o CSV, se algo foi gravado.

        Na vitória (`tempo_vitoria_s` informado), perigos ainda em andamento terminam sem colisão
        e são classificados. Em colisões, reinícios ou saída, perigos interrompidos são descartados.
        """
        if tempo_vitoria_s is not None:
            for id_evento in list(self._acompanhamentos):
                self._classificar_resolvido(tempo_vitoria_s, id_evento)
        caminho = self.salvar_csv()
        self.tentativa += 1
        self._acompanhamentos.clear()
        self._finalizados.clear()
        return caminho

    def salvar_csv(self) -> Path | None:
        novos = self.registros[self._registros_gravados :]
        if not novos:
            return None
        self.caminho_csv.parent.mkdir(parents=True, exist_ok=True)
        arquivo_novo = not self.caminho_csv.exists()
        with self.caminho_csv.open("a", newline="", encoding="utf-8-sig" if arquivo_novo else "utf-8") as arquivo:
            escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_CSV, delimiter=";")
            if arquivo_novo:
                escritor.writeheader()
            for registro in novos:
                linha = asdict(registro)
                linha["resultado"] = registro.resultado.value
                linha["tempo_resposta_s"] = "" if registro.tempo_resposta_s is None else f"{registro.tempo_resposta_s:.2f}"
                escritor.writerow(linha)
        self._registros_gravados = len(self.registros)
        return self.caminho_csv

    def resumo(self, apenas_tentativa_atual: bool = False) -> ResumoDesempenho:
        """Totais para o boletim: contagens, tempo médio de resposta e o tipo de erro mais comum."""
        registros = self.registros_tentativa_atual if apenas_tentativa_atual else self.registros
        return resumir(registros, self.colisoes_trafego)

    def _acompanhar(
        self,
        tempo_s: float,
        id_evento: str,
        tipo: str,
        trecho: int,
        marco_m: float,
        *,
        em_andamento: bool,
        encerrado: bool,
        em_risco: Callable[[], bool],
    ) -> None:
        if id_evento in self._finalizados or not (em_andamento or encerrado):
            return
        acompanhamento = self._acompanhamentos.setdefault(
            id_evento,
            _Acompanhamento(tipo=tipo, trecho=trecho, marco_m=marco_m, tempo_aviso_s=tempo_s),
        )

        if em_andamento:
            risco = em_risco()
            if risco:
                acompanhamento.esteve_em_risco = True
                acompanhamento.tempo_resolucao_s = None
            elif acompanhamento.em_risco:
                acompanhamento.tempo_resolucao_s = tempo_s
            acompanhamento.em_risco = risco
            return

        self._classificar_resolvido(tempo_s, id_evento)

    def _classificar_resolvido(self, tempo_s: float, id_evento: str) -> None:
        """Perigo encerrado sem colisão: classifica pelo tempo entre o aviso e a saída do risco."""
        acompanhamento = self._acompanhamentos[id_evento]
        if not acompanhamento.esteve_em_risco:
            tempo_resposta_s = 0.0
            motivo = "Já estava em posição segura no aviso."
        else:
            resolucao_s = tempo_s if acompanhamento.tempo_resolucao_s is None else acompanhamento.tempo_resolucao_s
            tempo_resposta_s = max(0.0, resolucao_s - acompanhamento.tempo_aviso_s)
            motivo = "Saiu do risco após o aviso."
        resultado = (
            ResultadoPerigo.ANTECIPACAO
            if tempo_resposta_s <= LIMITES_ANTECIPACAO_S[acompanhamento.tipo]
            else ResultadoPerigo.REACAO_TARDIA
        )
        self._finalizar(
            id_evento,
            acompanhamento.tipo,
            acompanhamento.trecho,
            acompanhamento.marco_m,
            resultado,
            tempo_resposta_s,
            motivo,
        )

    def _finalizar(
        self,
        id_evento: str,
        tipo: str,
        trecho: int,
        marco_m: float,
        resultado: ResultadoPerigo,
        tempo_resposta_s: float | None,
        motivo: str,
    ) -> None:
        self._finalizados.add(id_evento)
        self._acompanhamentos.pop(id_evento, None)
        self.registros.append(
            RegistroPerigo(
                tentativa=self.tentativa,
                jogador=self.jogador,
                id_evento=id_evento,
                tipo=tipo,
                trecho=trecho + 1,
                marco_m=marco_m,
                resultado=resultado,
                tempo_resposta_s=tempo_resposta_s,
                motivo=motivo,
            )
        )


def resumir(registros: list[RegistroPerigo], colisoes_trafego: int = 0) -> ResumoDesempenho:
    contagem = Counter(r.resultado for r in registros)
    tempos = [r.tempo_resposta_s for r in registros if r.tempo_resposta_s is not None]
    erros = Counter(r.tipo for r in registros if r.resultado is not ResultadoPerigo.ANTECIPACAO)
    return ResumoDesempenho(
        antecipacoes=contagem[ResultadoPerigo.ANTECIPACAO],
        reacoes_tardias=contagem[ResultadoPerigo.REACAO_TARDIA],
        falhas=contagem[ResultadoPerigo.FALHA],
        colisoes_trafego=colisoes_trafego,
        tempo_medio_resposta_s=sum(tempos) / len(tempos) if tempos else None,
        erro_mais_comum=erros.most_common(1)[0][0] if erros else None,
    )
