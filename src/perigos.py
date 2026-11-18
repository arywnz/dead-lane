from dataclasses import dataclass, field
from enum import Enum, auto

import pygame

from src.configuracao import (
    DURACAO_PORTA_ABERTA_S,
    ALTURA_PORTA,
    ALCANCE_PORTA,
    POSICAO_PORTA_M,
    DISTANCIA_AVISO_PORTA_M,
    DURACAO_AVISO_PORTA_S,
    COMPRIMENTO_CARRO_ESTACIONADO,
    LARGURA_CARRO_ESTACIONADO,
    CICLISTA_TELA_Y,
    CENTRO_PISTA_X,
    ESCALA_PISTA_PX_POR_M,
    LARGURA_PISTA,
)


class FasePorta(Enum):
    AGUARDANDO = auto()
    AVISO = auto()
    ABERTA = auto()
    FECHADA = auto()


@dataclass
class PerigoPorta:
    distancia_m: float = POSICAO_PORTA_M
    _tempo_decorrido_s: float | None = field(default=None, init=False)

    @property
    def fase(self) -> FasePorta:
        if self._tempo_decorrido_s is None:
            return FasePorta.AGUARDANDO
        if self._tempo_decorrido_s < DURACAO_AVISO_PORTA_S:
            return FasePorta.AVISO
        if self._tempo_decorrido_s < DURACAO_AVISO_PORTA_S + DURACAO_PORTA_ABERTA_S:
            return FasePorta.ABERTA
        return FasePorta.FECHADA

    def atualizar(self, delta_s: float, distancia_ciclista_m: float, *, permitir_aviso: bool = True) -> None:
        if self._tempo_decorrido_s is not None:
            self._tempo_decorrido_s = min(self._tempo_decorrido_s + delta_s, DURACAO_AVISO_PORTA_S + DURACAO_PORTA_ABERTA_S)
        elif permitir_aviso and 0 <= self.distancia_m - distancia_ciclista_m <= DISTANCIA_AVISO_PORTA_M:
            self._tempo_decorrido_s = 0.0

    def area_carro(self, distancia_ciclista_m: float) -> pygame.FRect:
        esquerda_carro = CENTRO_PISTA_X + LARGURA_PISTA / 2
        porta_y = CICLISTA_TELA_Y + (distancia_ciclista_m - self.distancia_m) * ESCALA_PISTA_PX_POR_M
        return pygame.FRect(esquerda_carro, porta_y - ALTURA_PORTA, LARGURA_CARRO_ESTACIONADO, COMPRIMENTO_CARRO_ESTACIONADO)

    def area_porta(self, distancia_ciclista_m: float) -> pygame.FRect:
        carro = self.area_carro(distancia_ciclista_m)
        return pygame.FRect(carro.left - ALCANCE_PORTA, carro.top + ALTURA_PORTA / 2, ALCANCE_PORTA, ALTURA_PORTA)
