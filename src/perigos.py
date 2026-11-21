from dataclasses import dataclass, field
from enum import Enum, auto

import pygame

from src.configuracao import (
    ALCANCE_PORTA,
    ALTURA_PORTA,
    ANTECEDENCIA_ENTRADA_ONIBUS_M,
    CENTRO_PISTA_X,
    CICLISTA_TELA_Y,
    COMPRIMENTO_CARRO_ESTACIONADO,
    DESLOCAMENTO_FECHAMENTO_ONIBUS_PX,
    DISTANCIA_AVISO_PONTO_CEGO_M,
    DISTANCIA_AVISO_PORTA_M,
    DISTANCIA_ENTRADA_ONIBUS_M,
    DURACAO_AVISO_PONTO_CEGO_S,
    DURACAO_AVISO_PORTA_S,
    DURACAO_PONTO_CEGO_ATIVO_S,
    DURACAO_PORTA_ABERTA_S,
    ESCALA_PISTA_PX_POR_M,
    LARGURA_CARRO_ESTACIONADO,
    LARGURA_PISTA,
    LARGURA_PONTO_CEGO,
    POSICAO_PONTO_CEGO_M,
    POSICAO_PORTA_M,
    VELOCIDADE_ONIBUS_MPS,
)
from src.trafego import TipoVeiculo, Veiculo


class FasePorta(Enum):
    AGUARDANDO = auto()
    AVISO = auto()
    ABERTA = auto()
    FECHADA = auto()


class FasePontoCego(Enum):
    AGUARDANDO = auto()
    AVISO = auto()
    ATIVO = auto()
    ENCERRADO = auto()


@dataclass
class PerigoPorta:
    distancia_m: float = POSICAO_PORTA_M
    trecho: int = 0
    id_evento: str = "porta_1"
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


@dataclass
class PerigoPontoCego:
    """Ônibus na faixa central com região lateral de ponto cego à direita."""

    distancia_encontro_m: float = POSICAO_PONTO_CEGO_M
    velocidade_onibus_mps: float = VELOCIDADE_ONIBUS_MPS
    trecho: int = 0
    id_evento: str = "ponto_cego_1"
    onibus: Veiculo | None = field(default=None, init=False)
    _tempo_decorrido_s: float | None = field(default=None, init=False)
    ciclista_esteve_na_zona: bool = field(default=False, init=False)
    saiu_com_seguranca: bool = field(default=False, init=False)
    evitado_totalmente: bool = field(default=False, init=False)

    @property
    def fase(self) -> FasePontoCego:
        if self._tempo_decorrido_s is None:
            return FasePontoCego.AGUARDANDO
        if self._tempo_decorrido_s < DURACAO_AVISO_PONTO_CEGO_S:
            return FasePontoCego.AVISO
        if self._tempo_decorrido_s < DURACAO_AVISO_PONTO_CEGO_S + DURACAO_PONTO_CEGO_ATIVO_S:
            return FasePontoCego.ATIVO
        return FasePontoCego.ENCERRADO

    def atualizar(
        self,
        delta_s: float,
        distancia_ciclista_m: float,
        area_ciclista: pygame.FRect | None = None,
        *,
        permitir_aviso: bool = True,
    ) -> None:
        if self.onibus is None:
            if distancia_ciclista_m >= self.distancia_encontro_m - ANTECEDENCIA_ENTRADA_ONIBUS_M:
                self.onibus = Veiculo(
                    tipo=TipoVeiculo.ONIBUS,
                    faixa=1,
                    distancia_m=distancia_ciclista_m + DISTANCIA_ENTRADA_ONIBUS_M,
                    velocidade_base_mps=self.velocidade_onibus_mps,
                    velocidade_mps=self.velocidade_onibus_mps,
                    eh_perigo=True,
                )
            else:
                return

        self.onibus.atualizar(delta_s)
        diferenca_m = self.onibus.distancia_m - distancia_ciclista_m

        if self._tempo_decorrido_s is not None:
            self._tempo_decorrido_s = min(
                self._tempo_decorrido_s + delta_s,
                DURACAO_AVISO_PONTO_CEGO_S + DURACAO_PONTO_CEGO_ATIVO_S,
            )
        elif permitir_aviso and -3.5 <= diferenca_m <= DISTANCIA_AVISO_PONTO_CEGO_M:
            self._tempo_decorrido_s = 0.0

        fase_atual = self.fase
        self.onibus.seta_direita_ativa = fase_atual in (FasePontoCego.AVISO, FasePontoCego.ATIVO)

        if fase_atual is FasePontoCego.ATIVO:
            progresso_ativo = (self._tempo_decorrido_s - DURACAO_AVISO_PONTO_CEGO_S) / DURACAO_PONTO_CEGO_ATIVO_S
            fator = min(1.0, max(0.0, progresso_ativo * 1.4))
            self.onibus.deslocamento_x = DESLOCAMENTO_FECHAMENTO_ONIBUS_PX * fator
        elif fase_atual is FasePontoCego.ENCERRADO:
            self.onibus.deslocamento_x = max(0.0, self.onibus.deslocamento_x - 36.0 * delta_s)

        if area_ciclista is not None:
            na_zona = self.ciclista_na_zona(area_ciclista, distancia_ciclista_m)
            if fase_atual is FasePontoCego.AVISO:
                if na_zona:
                    self.ciclista_esteve_na_zona = True
                    self.saiu_com_seguranca = False
                elif self.ciclista_esteve_na_zona:
                    self.saiu_com_seguranca = True
            elif fase_atual is FasePontoCego.ATIVO:
                if self.ciclista_esteve_na_zona and not na_zona:
                    self.saiu_com_seguranca = True
            elif fase_atual is FasePontoCego.ENCERRADO:
                if not self.ciclista_esteve_na_zona:
                    self.evitado_totalmente = True
                elif not na_zona:
                    self.saiu_com_seguranca = True

    def area_ponto_cego(self, distancia_ciclista_m: float) -> pygame.FRect | None:
        if self.onibus is None:
            return None
        bus_rect = self.onibus.area_visual(distancia_ciclista_m)
        borda_direita_pista = CENTRO_PISTA_X + LARGURA_PISTA / 2
        esquerda = bus_rect.right - 4
        largura = min(LARGURA_PONTO_CEGO, borda_direita_pista - esquerda)
        if largura <= 0:
            return None
        return pygame.FRect(esquerda, bus_rect.top + 36, largura, bus_rect.height - 44)

    def ciclista_na_zona(self, area_ciclista: pygame.FRect, distancia_ciclista_m: float) -> bool:
        zona = self.area_ponto_cego(distancia_ciclista_m)
        return zona is not None and area_ciclista.colliderect(zona)

    def houve_incidente(self, area_ciclista: pygame.FRect, distancia_ciclista_m: float) -> bool:
        return self.fase is FasePontoCego.ATIVO and self.ciclista_na_zona(area_ciclista, distancia_ciclista_m)
