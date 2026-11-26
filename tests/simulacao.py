"""Simulação quadro a quadro do ciclista e dos perigos, na mesma ordem usada em jogo.py."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import pygame

from src.ciclista import Ciclista
from src.configuracao import ALTURA_COLISAO_CICLISTA, CICLISTA_TELA_Y, LARGURA_COLISAO_CICLISTA
from src.metricas import RegistroDesempenho
from src.perigos import GerenciadorPerigos

DELTA_S = 1 / 60


@dataclass(frozen=True)
class Comando:
    lateral: int = 0
    acelerar: bool = False
    frear: bool = False


SEGUIR = Comando()


def criar_area_ciclista(x: float) -> pygame.FRect:
    area = pygame.FRect(0, 0, LARGURA_COLISAO_CICLISTA, ALTURA_COLISAO_CICLISTA)
    area.centery = CICLISTA_TELA_Y
    area.centerx = x
    return area


@dataclass
class Simulacao:
    ciclista: Ciclista
    perigos: GerenciadorPerigos
    registro: RegistroDesempenho | None = None
    area: pygame.FRect = field(init=False)
    tempo_s: float = 0.0

    def __post_init__(self) -> None:
        self.area = criar_area_ciclista(self.ciclista.x)

    def passo(self, comando: Comando = SEGUIR) -> str | None:
        self.tempo_s += DELTA_S
        self.ciclista.atualizar(DELTA_S, comando.lateral, comando.acelerar, comando.frear)
        self.area.centerx = self.ciclista.x
        self.perigos.atualizar(
            DELTA_S,
            self.ciclista.distancia_m,
            self.area,
            velocidade_mps=self.ciclista.velocidade_mps,
        )
        if self.registro is not None:
            self.registro.atualizar(
                self.tempo_s,
                self.perigos,
                self.area,
                self.ciclista.distancia_m,
                self.ciclista.velocidade_mps,
            )
        colisao = self.perigos.verificar_colisao_detalhada(self.area, self.ciclista.distancia_m)
        if colisao is None:
            return None
        motivo, id_evento = colisao
        if self.registro is not None:
            self.registro.registrar_colisao(self.perigos, id_evento, motivo)
        return motivo

    def executar(
        self,
        politica: Callable[["Simulacao"], Comando],
        *,
        duracao_s: float,
        parar_quando: Callable[["Simulacao"], bool] | None = None,
    ) -> str | None:
        """Roda até colidir, até `parar_quando` ser verdadeiro ou até acabar o tempo."""
        for _ in range(round(duracao_s / DELTA_S)):
            colisao = self.passo(politica(self))
            if colisao is not None:
                return colisao
            if parar_quando is not None and parar_quando(self):
                return None
        return None
