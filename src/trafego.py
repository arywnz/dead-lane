from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum, auto

import pygame

from src.configuracao import (
    CENTROS_FAIXAS_X,
    CICLISTA_TELA_Y,
    COMPRIMENTO_CARRO,
    COMPRIMENTO_ONIBUS,
    COMPRIMENTO_PERCURSO_M,
    DISTANCIA_SEGURA_MESMA_FAIXA_M,
    ESCALA_PISTA_PX_POR_M,
    FAIXAS_PISTA,
    INTERVALO_TRAFEGO_PADRAO_M,
    LARGURA_CARRO,
    LARGURA_ONIBUS,
    MARGEM_REMOCAO_TRAFEGO_ATRAS_M,
    MARGEM_REMOCAO_TRAFEGO_FRENTE_M,
    MARGEM_SPAWN_TRAFEGO_FRENTE_M,
    MAX_VEICULOS_AMBIENTE_PADRAO,
    VELOCIDADE_ONIBUS_MPS,
)


class TipoVeiculo(Enum):
    CARRO = auto()
    ONIBUS = auto()


@dataclass
class Veiculo:
    """Veículo urbano em movimento no mesmo sentido do ciclista."""

    tipo: TipoVeiculo
    faixa: int
    distancia_m: float
    velocidade_base_mps: float
    velocidade_mps: float
    cor_variante: int = 0
    freando: bool = False
    deslocamento_x: float = 0.0
    seta_direita_ativa: bool = False
    eh_perigo: bool = False

    @property
    def largura(self) -> int:
        return LARGURA_ONIBUS if self.tipo is TipoVeiculo.ONIBUS else LARGURA_CARRO

    @property
    def comprimento(self) -> int:
        return COMPRIMENTO_ONIBUS if self.tipo is TipoVeiculo.ONIBUS else COMPRIMENTO_CARRO

    @property
    def comprimento_m(self) -> float:
        return self.comprimento / ESCALA_PISTA_PX_POR_M

    @property
    def x(self) -> float:
        return CENTROS_FAIXAS_X[self.faixa] + self.deslocamento_x

    def atualizar(self, delta_s: float) -> None:
        self.distancia_m += self.velocidade_mps * delta_s

    def area_visual(self, distancia_ciclista_m: float) -> pygame.FRect:
        centro_y = CICLISTA_TELA_Y + (distancia_ciclista_m - self.distancia_m) * ESCALA_PISTA_PX_POR_M
        return pygame.FRect(
            self.x - self.largura / 2,
            centro_y - self.comprimento / 2,
            self.largura,
            self.comprimento,
        )

    def area_colisao(self, distancia_ciclista_m: float) -> pygame.FRect:
        return self.area_visual(distancia_ciclista_m).inflate(-6, -8)


# Sequência determinística de (tipo, faixa_preferida, cor_variante, ajuste_vel)
_PADRAO_SPAWN: tuple[tuple[TipoVeiculo, int, int, float], ...] = (
    (TipoVeiculo.CARRO, 0, 0, 0.2),
    (TipoVeiculo.ONIBUS, 1, 0, 0.0),
    (TipoVeiculo.CARRO, 2, 1, -0.1),
    (TipoVeiculo.CARRO, 0, 2, 0.4),
    (TipoVeiculo.CARRO, 1, 3, 0.1),
    (TipoVeiculo.ONIBUS, 0, 1, 0.0),
    (TipoVeiculo.CARRO, 2, 4, 0.0),
    (TipoVeiculo.CARRO, 1, 0, 0.3),
)

_VELOCIDADE_POR_FAIXA: dict[int, float] = {
    0: 6.4,
    1: 5.7,
    2: 5.3,
}


@dataclass
class GerenciadorTrafego:
    """Controla spawn, seguimento seguro e reciclagem de veículos na avenida."""

    intervalo_m: float = INTERVALO_TRAFEGO_PADRAO_M
    max_veiculos: int = MAX_VEICULOS_AMBIENTE_PADRAO
    veiculos: list[Veiculo] = field(default_factory=list)
    _proximo_marco_spawn_m: float = field(default=22.0, init=False)
    _indice_padrao: int = field(default=0, init=False)

    def atualizar(
        self,
        delta_s: float,
        distancia_ciclista_m: float,
        zonas_bloqueadas: Sequence[tuple[float, float]] = (),
        veiculos_externos: Sequence[Veiculo] = (),
    ) -> None:
        for veiculo in self.veiculos:
            veiculo.atualizar(delta_s)

        self._aplicar_seguimento(delta_s, veiculos_externos)

        limite_atras = distancia_ciclista_m - MARGEM_REMOCAO_TRAFEGO_ATRAS_M
        limite_frente = min(COMPRIMENTO_PERCURSO_M + 20.0, distancia_ciclista_m + MARGEM_REMOCAO_TRAFEGO_FRENTE_M)
        self.veiculos = [
            v for v in self.veiculos if limite_atras <= v.distancia_m <= limite_frente
        ]

        alvo_spawn_m = distancia_ciclista_m + MARGEM_SPAWN_TRAFEGO_FRENTE_M
        while (
            alvo_spawn_m >= self._proximo_marco_spawn_m
            and self._proximo_marco_spawn_m < COMPRIMENTO_PERCURSO_M - 30.0
        ):
            if len(self.veiculos) < self.max_veiculos:
                self._tentar_gerar_veiculo(
                    self._proximo_marco_spawn_m,
                    zonas_bloqueadas=zonas_bloqueadas,
                    veiculos_externos=veiculos_externos,
                )
            self._proximo_marco_spawn_m += self.intervalo_m

    def _aplicar_seguimento(
        self,
        delta_s: float,
        veiculos_externos: Sequence[Veiculo],
    ) -> None:
        todos = [*self.veiculos, *veiculos_externos]
        for faixa in range(FAIXAS_PISTA):
            na_faixa = sorted((v for v in todos if v.faixa == faixa), key=lambda v: v.distancia_m)
            for idx, tras in enumerate(na_faixa):
                if tras.eh_perigo:
                    continue
                if idx == len(na_faixa) - 1:
                    tras.velocidade_mps = min(tras.velocidade_base_mps, tras.velocidade_mps + 2.4 * delta_s)
                    tras.freando = False
                    continue

                frente = na_faixa[idx + 1]
                espaco = frente.distancia_m - tras.distancia_m
                distancia_necessaria = (tras.comprimento_m + frente.comprimento_m) * 0.5 + DISTANCIA_SEGURA_MESMA_FAIXA_M
                if espaco < distancia_necessaria:
                    tras.velocidade_mps = min(tras.velocidade_mps, max(0.0, frente.velocidade_mps - 0.8))
                    tras.freando = True
                elif espaco < distancia_necessaria + 4.5 and tras.velocidade_base_mps > frente.velocidade_mps:
                    tras.velocidade_mps = frente.velocidade_mps
                    tras.freando = True
                else:
                    tras.velocidade_mps = min(tras.velocidade_base_mps, tras.velocidade_mps + 2.4 * delta_s)
                    tras.freando = False

    def _tentar_gerar_veiculo(
        self,
        distancia_spawn_m: float,
        zonas_bloqueadas: Sequence[tuple[float, float]],
        veiculos_externos: Sequence[Veiculo],
    ) -> None:
        tipo, faixa_pref, cor_variante, ajuste_vel = _PADRAO_SPAWN[self._indice_padrao % len(_PADRAO_SPAWN)]
        self._indice_padrao += 1

        todos = [*self.veiculos, *veiculos_externos]
        faixas_ocupadas = self._faixas_ocupadas_perto(todos, distancia_spawn_m, meia_janela_m=13.0)
        faixa2_bloqueada = self._faixa2_bloqueada(distancia_spawn_m, meia_janela_m=16.0, zonas_bloqueadas=zonas_bloqueadas)
        faixas_restritas = set(faixas_ocupadas)
        if faixa2_bloqueada:
            faixas_restritas.add(2)

        # Garante ao menos uma faixa livre para passagem do ciclista
        if len(faixas_restritas) >= FAIXAS_PISTA - 1:
            return

        candidatas = [faixa_pref, *(f for f in range(FAIXAS_PISTA) if f != faixa_pref)]
        comprimento_novo_m = (COMPRIMENTO_ONIBUS if tipo is TipoVeiculo.ONIBUS else COMPRIMENTO_CARRO) / ESCALA_PISTA_PX_POR_M

        for faixa in candidatas:
            if faixa in faixas_restritas:
                continue
            if tipo is TipoVeiculo.ONIBUS and faixa == 2:
                continue
            if self._colide_com_existente(todos, faixa, distancia_spawn_m, comprimento_novo_m):
                continue

            velocidade = (
                VELOCIDADE_ONIBUS_MPS
                if tipo is TipoVeiculo.ONIBUS
                else _VELOCIDADE_POR_FAIXA[faixa] + ajuste_vel
            )
            self.veiculos.append(
                Veiculo(
                    tipo=tipo,
                    faixa=faixa,
                    distancia_m=distancia_spawn_m,
                    velocidade_base_mps=velocidade,
                    velocidade_mps=velocidade,
                    cor_variante=cor_variante,
                )
            )
            return

    @staticmethod
    def _faixa2_bloqueada(
        centro_m: float,
        meia_janela_m: float,
        zonas_bloqueadas: Sequence[tuple[float, float]],
    ) -> bool:
        inicio_janela = centro_m - meia_janela_m
        fim_janela = centro_m + meia_janela_m
        return any(inicio <= fim_janela and fim >= inicio_janela for inicio, fim in zonas_bloqueadas)

    @staticmethod
    def _faixas_ocupadas_perto(
        veiculos: Sequence[Veiculo],
        centro_m: float,
        meia_janela_m: float,
    ) -> set[int]:
        ocupadas: set[int] = set()
        for v in veiculos:
            if abs(v.distancia_m - centro_m) <= meia_janela_m + v.comprimento_m * 0.5:
                ocupadas.add(v.faixa)
        return ocupadas

    @staticmethod
    def _colide_com_existente(
        veiculos: Sequence[Veiculo],
        faixa: int,
        distancia_m: float,
        comprimento_novo_m: float,
    ) -> bool:
        for v in veiculos:
            if v.faixa != faixa:
                continue
            min_sep = (v.comprimento_m + comprimento_novo_m) * 0.5 + DISTANCIA_SEGURA_MESMA_FAIXA_M + 3.0
            if abs(v.distancia_m - distancia_m) < min_sep:
                return True
        return False
