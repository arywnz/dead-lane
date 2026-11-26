from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum, auto
import random

import pygame

from src.configuracao import (
    CENTROS_FAIXAS_X,
    CICLISTA_TELA_Y,
    COMPRIMENTO_CARRO,
    COMPRIMENTO_ONIBUS,
    COMPRIMENTO_PERCURSO_M,
    CONFIG_TRECHOS,
    DISTANCIA_SEGURA_MESMA_FAIXA_M,
    ESCALA_PISTA_PX_POR_M,
    FAIXAS_PISTA,
    INTERVALO_TRAFEGO_PADRAO_M,
    LARGURA_CARRO,
    LARGURA_FAIXA,
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
    seta_direcao: int = 0
    _faixa_destino: int | None = None
    _tempo_seta_s: float = 0.0

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
        if self._faixa_destino is not None:
            if self._tempo_seta_s > 0.0:
                self._tempo_seta_s = max(0.0, self._tempo_seta_s - delta_s)
            else:
                alvo_dx = (self._faixa_destino - self.faixa) * LARGURA_FAIXA
                passo = (1.0 if alvo_dx > 0 else -1.0) * 115.0 * delta_s
                if abs(alvo_dx - self.deslocamento_x) <= abs(passo):
                    self.faixa = self._faixa_destino
                    self.deslocamento_x = 0.0
                    self._faixa_destino = None
                    self.seta_direcao = 0
                else:
                    self.deslocamento_x += passo

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
    aleatorio: bool = False
    veiculos: list[Veiculo] = field(default_factory=list)
    _proximo_marco_spawn_m: float = field(default=22.0, init=False)
    _indice_padrao: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if self.aleatorio:
            self._proximo_marco_spawn_m = random.uniform(18.0, 44.0)
            self._indice_padrao = random.randrange(len(_PADRAO_SPAWN))

    def atualizar(
        self,
        delta_s: float,
        distancia_ciclista_m: float,
        zonas_bloqueadas: Sequence[tuple[float, float]] = (),
        veiculos_externos: Sequence[Veiculo] = (),
        indice_trecho: int | None = None,
        zonas_sem_trafego: Sequence[tuple[float, float]] = (),
        zonas_bloqueadas_esquerda: Sequence[tuple[float, float]] = (),
        pausar_spawn: bool = False,
    ) -> None:
        if indice_trecho is not None:
            config = CONFIG_TRECHOS[min(indice_trecho, len(CONFIG_TRECHOS) - 1)]
            self.intervalo_m = config["intervalo_trafego_m"]
            self.max_veiculos = config["max_veiculos_ambiente"]

        todos_antes = [*self.veiculos, *veiculos_externos]
        for veiculo in self.veiculos:
            estava_dando_seta = veiculo._faixa_destino is not None and veiculo._tempo_seta_s > 0.0
            distancia_anterior_m = veiculo.distancia_m
            veiculo.distancia_m += veiculo.velocidade_mps * delta_s

            if veiculo._faixa_destino is not None:
                if veiculo._tempo_seta_s > 0.0:
                    veiculo._tempo_seta_s = max(0.0, veiculo._tempo_seta_s - delta_s)
                    # Revalida a faixa destino no instante em que a troca vai começar.
                    if veiculo._tempo_seta_s == 0.0 and estava_dando_seta:
                        if not self._faixa_disponivel_para_troca(
                            veiculo,
                            veiculo._faixa_destino,
                            todos_antes,
                            zonas_bloqueadas,
                            zonas_bloqueadas_esquerda,
                            zonas_sem_trafego,
                        ):
                            veiculo._faixa_destino = None
                            veiculo.seta_direcao = 0
                if veiculo._faixa_destino is not None and veiculo._tempo_seta_s == 0.0:
                    alvo_dx = (veiculo._faixa_destino - veiculo.faixa) * LARGURA_FAIXA
                    passo = (1.0 if alvo_dx > 0 else -1.0) * 115.0 * delta_s
                    if abs(alvo_dx - veiculo.deslocamento_x) <= abs(passo):
                        veiculo.faixa = veiculo._faixa_destino
                        veiculo.deslocamento_x = 0.0
                        veiculo._faixa_destino = None
                        veiculo.seta_direcao = 0
                    else:
                        # Aborta se a outra faixa fechou enquanto ainda quase não deslocou.
                        if abs(veiculo.deslocamento_x) < 10.0 and not self._faixa_disponivel_para_troca(
                            veiculo,
                            veiculo._faixa_destino,
                            todos_antes,
                            zonas_bloqueadas,
                            zonas_bloqueadas_esquerda,
                            zonas_sem_trafego,
                        ):
                            veiculo.deslocamento_x = 0.0
                            veiculo._faixa_destino = None
                            veiculo.seta_direcao = 0
                        else:
                            veiculo.deslocamento_x += passo

            # Evita veículos entrando nas portas abertas das faixas laterais (direita ou esquerda)
            if veiculo._faixa_destino is None and not veiculo.eh_perigo:
                zonas_da_faixa = (
                    zonas_bloqueadas
                    if veiculo.faixa == 2
                    else (zonas_bloqueadas_esquerda if veiculo.faixa == 0 else ())
                )
                if zonas_da_faixa and self._faixa_bloqueada(veiculo.distancia_m + 6.0, 10.0, zonas_da_faixa):
                    if not self._tentar_iniciar_troca_faixa(
                        veiculo,
                        todos_antes,
                        zonas_bloqueadas=zonas_bloqueadas,
                        zonas_bloqueadas_esquerda=zonas_bloqueadas_esquerda,
                        zonas_sem_trafego=zonas_sem_trafego,
                        faixas_preferidas=(1,),
                    ):
                        # Se não puder mudar de faixa antes da porta, reduz para não atravessar a porta aberta.
                        for inicio_z, fim_z in zonas_da_faixa:
                            if inicio_z - 8.0 <= veiculo.distancia_m <= inicio_z + 1.0:
                                veiculo.velocidade_mps = min(veiculo.velocidade_mps, 1.5)
                                veiculo.freando = True
                                if veiculo.distancia_m > inicio_z - 1.5 and distancia_anterior_m <= inicio_z - 1.5:
                                    veiculo.distancia_m = inicio_z - 1.5
                                break

            if (
                self.aleatorio
                and veiculo._faixa_destino is None
                and 4.0 <= veiculo.distancia_m - distancia_ciclista_m <= 28.0
                and random.random() < 0.45 * delta_s
            ):
                self._tentar_iniciar_troca_faixa(
                    veiculo,
                    todos_antes,
                    zonas_bloqueadas=zonas_bloqueadas,
                    zonas_bloqueadas_esquerda=zonas_bloqueadas_esquerda,
                    zonas_sem_trafego=zonas_sem_trafego,
                )

        # Mantém corredores sem tráfego (ponto cego e pares comparáveis) livres sem teleporte visual.
        veiculos_liberando_corredor: set[int] = set()
        if zonas_sem_trafego:
            for veiculo in self.veiculos:
                if veiculo.eh_perigo:
                    continue
                for inicio, fim in zonas_sem_trafego:
                    if inicio - 28.0 <= veiculo.distancia_m <= fim + 10.0:
                        if veiculo.distancia_m <= inicio + 12.0:
                            # Veículo antes do corredor reduz para não entrar junto com o piloto
                            veiculo.velocidade_mps = min(veiculo.velocidade_mps, 2.8)
                            veiculo.freando = True
                        elif veiculo.distancia_m > distancia_ciclista_m + 2.0:
                            # Veículo já dentro e à frente libera o corredor adiante
                            veiculo.velocidade_mps = max(veiculo.velocidade_mps, 11.5)
                            veiculo.freando = False
                        else:
                            veiculo.velocidade_mps = min(veiculo.velocidade_mps, 2.8)
                            veiculo.freando = True
                        veiculos_liberando_corredor.add(id(veiculo))
                        break

        self._aplicar_seguimento(
            delta_s,
            veiculos_externos,
            zonas_bloqueadas=zonas_bloqueadas,
            zonas_bloqueadas_esquerda=zonas_bloqueadas_esquerda,
            zonas_sem_trafego=zonas_sem_trafego,
            veiculos_liberando_corredor=veiculos_liberando_corredor,
        )

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
            if not pausar_spawn and len(self.veiculos) < self.max_veiculos:
                if self.aleatorio:
                    self._indice_padrao = random.randrange(len(_PADRAO_SPAWN))
                self._tentar_gerar_veiculo(
                    self._proximo_marco_spawn_m,
                    zonas_bloqueadas=zonas_bloqueadas,
                    zonas_bloqueadas_esquerda=zonas_bloqueadas_esquerda,
                    veiculos_externos=veiculos_externos,
                    zonas_sem_trafego=zonas_sem_trafego,
                )
            fator = random.uniform(0.75, 1.25) if self.aleatorio else 1.0
            self._proximo_marco_spawn_m += self.intervalo_m * fator

    def _aplicar_seguimento(
        self,
        delta_s: float,
        veiculos_externos: Sequence[Veiculo],
        *,
        zonas_bloqueadas: Sequence[tuple[float, float]] = (),
        zonas_bloqueadas_esquerda: Sequence[tuple[float, float]] = (),
        zonas_sem_trafego: Sequence[tuple[float, float]] = (),
        veiculos_liberando_corredor: set[int] | None = None,
    ) -> None:
        todos = [*self.veiculos, *veiculos_externos]
        liberando = veiculos_liberando_corredor or set()
        # Processa da frente para trás para evitar sobreposição em cadeia.
        ordenados = sorted(self.veiculos, key=lambda v: v.distancia_m, reverse=True)
        for tras in ordenados:
            if tras.eh_perigo:
                continue

            # Encontra o veículo mais próximo à frente que sobrepõe lateralmente (ou compartilha faixa/destino).
            frente_mais_proxima: Veiculo | None = None
            menor_espaco = float("inf")
            for outro in todos:
                if outro is tras or outro.distancia_m <= tras.distancia_m:
                    continue
                compartilha_faixa = (
                    outro.faixa == tras.faixa
                    or (tras._faixa_destino is not None and outro.faixa == tras._faixa_destino)
                    or (outro._faixa_destino is not None and outro._faixa_destino == tras.faixa)
                    or (
                        tras._faixa_destino is not None
                        and outro._faixa_destino is not None
                        and outro._faixa_destino == tras._faixa_destino
                    )
                )
                sobrepoe_lateral = abs(outro.x - tras.x) < (outro.largura + tras.largura) * 0.5 + 6.0
                if not (compartilha_faixa or sobrepoe_lateral):
                    continue
                espaco = outro.distancia_m - tras.distancia_m
                if espaco < menor_espaco:
                    menor_espaco = espaco
                    frente_mais_proxima = outro

            if frente_mais_proxima is None:
                if id(tras) not in liberando:
                    if tras.velocidade_mps > tras.velocidade_base_mps:
                        tras.velocidade_mps = max(tras.velocidade_base_mps, tras.velocidade_mps - 2.4 * delta_s)
                    else:
                        tras.velocidade_mps = min(tras.velocidade_base_mps, tras.velocidade_mps + 2.4 * delta_s)
                    tras.freando = False
                continue

            min_fisico = (tras.comprimento_m + frente_mais_proxima.comprimento_m) * 0.5 + 0.9
            distancia_necessaria = (
                (tras.comprimento_m + frente_mais_proxima.comprimento_m) * 0.5 + DISTANCIA_SEGURA_MESMA_FAIXA_M
            )

            # Trava física anti-clipping: impede sobreposição visual de para-choques.
            if menor_espaco < min_fisico:
                tras.distancia_m = frente_mais_proxima.distancia_m - min_fisico
                tras.velocidade_mps = min(tras.velocidade_mps, max(0.0, frente_mais_proxima.velocidade_mps - 0.5))
                tras.freando = True
                if self.aleatorio and tras._faixa_destino is None:
                    self._tentar_iniciar_troca_faixa(
                        tras,
                        todos,
                        zonas_bloqueadas=zonas_bloqueadas,
                        zonas_bloqueadas_esquerda=zonas_bloqueadas_esquerda,
                        zonas_sem_trafego=zonas_sem_trafego,
                    )
            elif menor_espaco < distancia_necessaria:
                tras.velocidade_mps = min(tras.velocidade_mps, max(0.0, frente_mais_proxima.velocidade_mps - 0.8))
                tras.freando = True
                if self.aleatorio and tras._faixa_destino is None:
                    self._tentar_iniciar_troca_faixa(
                        tras,
                        todos,
                        zonas_bloqueadas=zonas_bloqueadas,
                        zonas_bloqueadas_esquerda=zonas_bloqueadas_esquerda,
                        zonas_sem_trafego=zonas_sem_trafego,
                    )
            elif menor_espaco < distancia_necessaria + 4.5 and tras.velocidade_mps > frente_mais_proxima.velocidade_mps:
                tras.velocidade_mps = frente_mais_proxima.velocidade_mps
                tras.freando = True
                if self.aleatorio and tras._faixa_destino is None:
                    self._tentar_iniciar_troca_faixa(
                        tras,
                        todos,
                        zonas_bloqueadas=zonas_bloqueadas,
                        zonas_bloqueadas_esquerda=zonas_bloqueadas_esquerda,
                        zonas_sem_trafego=zonas_sem_trafego,
                    )
            else:
                if id(tras) not in liberando:
                    if tras.velocidade_mps > tras.velocidade_base_mps:
                        tras.velocidade_mps = max(tras.velocidade_base_mps, tras.velocidade_mps - 2.4 * delta_s)
                    else:
                        tras.velocidade_mps = min(tras.velocidade_base_mps, tras.velocidade_mps + 2.4 * delta_s)
                    tras.freando = False

    def _faixa_disponivel_para_troca(
        self,
        veiculo: Veiculo,
        faixa_alvo: int,
        todos: Sequence[Veiculo],
        zonas_bloqueadas: Sequence[tuple[float, float]],
        zonas_bloqueadas_esquerda: Sequence[tuple[float, float]],
        zonas_sem_trafego: Sequence[tuple[float, float]],
    ) -> bool:
        if not (0 <= faixa_alvo < FAIXAS_PISTA) or faixa_alvo == veiculo.faixa:
            return False
        if veiculo.tipo is TipoVeiculo.ONIBUS and faixa_alvo == 2:
            return False
        if faixa_alvo == 2 and self._faixa_bloqueada(veiculo.distancia_m, 16.0, zonas_bloqueadas):
            return False
        if faixa_alvo == 0 and self._faixa_bloqueada(veiculo.distancia_m, 16.0, zonas_bloqueadas_esquerda):
            return False
        if any(inicio - 10.0 <= veiculo.distancia_m <= fim + 10.0 for inicio, fim in zonas_sem_trafego):
            return False

        # Garante que não sobrepõe outro veículo na faixa alvo (nem quem está indo para lá)
        for outro in todos:
            if outro is veiculo:
                continue
            no_alvo = (
                outro.faixa == faixa_alvo
                or outro._faixa_destino == faixa_alvo
                or abs(outro.x - CENTROS_FAIXAS_X[faixa_alvo]) < (veiculo.largura + outro.largura) * 0.5 + 8.0
            )
            if no_alvo:
                folga_min = (veiculo.comprimento_m + outro.comprimento_m) * 0.65 + 7.5
                if abs(outro.distancia_m - veiculo.distancia_m) < folga_min:
                    return False

        # Garante que a troca de faixa não fecha um muro intransponível nas 3 faixas
        faixas_ocupadas_depois = {faixa_alvo}
        for outro in todos:
            if outro is veiculo:
                continue
            if abs(outro.distancia_m - veiculo.distancia_m) <= 10.0 + (veiculo.comprimento_m + outro.comprimento_m) * 0.5:
                faixas_ocupadas_depois.add(outro.faixa)
                if outro._faixa_destino is not None:
                    faixas_ocupadas_depois.add(outro._faixa_destino)
        if len(faixas_ocupadas_depois) >= FAIXAS_PISTA:
            return False

        return True

    def _tentar_iniciar_troca_faixa(
        self,
        veiculo: Veiculo,
        todos: Sequence[Veiculo],
        *,
        zonas_bloqueadas: Sequence[tuple[float, float]] = (),
        zonas_bloqueadas_esquerda: Sequence[tuple[float, float]] = (),
        zonas_sem_trafego: Sequence[tuple[float, float]] = (),
        faixas_preferidas: Sequence[int] | None = None,
    ) -> bool:
        if faixas_preferidas is not None:
            candidatas = [f for f in faixas_preferidas if abs(f - veiculo.faixa) == 1 and 0 <= f < FAIXAS_PISTA]
        else:
            candidatas = [f for f in (veiculo.faixa - 1, veiculo.faixa + 1) if 0 <= f < FAIXAS_PISTA]
            random.shuffle(candidatas)
        for faixa_alvo in candidatas:
            if self._faixa_disponivel_para_troca(
                veiculo,
                faixa_alvo,
                todos,
                zonas_bloqueadas,
                zonas_bloqueadas_esquerda,
                zonas_sem_trafego,
            ):
                veiculo._faixa_destino = faixa_alvo
                veiculo.seta_direcao = 1 if faixa_alvo > veiculo.faixa else -1
                veiculo._tempo_seta_s = 0.85
                return True
        return False

    def _tentar_gerar_veiculo(
        self,
        distancia_spawn_m: float,
        zonas_bloqueadas: Sequence[tuple[float, float]],
        veiculos_externos: Sequence[Veiculo],
        zonas_sem_trafego: Sequence[tuple[float, float]] = (),
        zonas_bloqueadas_esquerda: Sequence[tuple[float, float]] = (),
    ) -> None:
        # Mantém corredor livre nos encontros com ônibus de ponto cego
        if any(inicio <= distancia_spawn_m <= fim for inicio, fim in zonas_sem_trafego):
            return
        for externo in veiculos_externos:
            if externo.eh_perigo and abs(externo.distancia_m - distancia_spawn_m) <= 26.0:
                return

        tipo, faixa_pref, cor_variante, ajuste_vel = _PADRAO_SPAWN[self._indice_padrao % len(_PADRAO_SPAWN)]
        self._indice_padrao += 1

        todos = [*self.veiculos, *veiculos_externos]
        faixas_ocupadas = self._faixas_ocupadas_perto(todos, distancia_spawn_m, meia_janela_m=13.0)
        faixa2_bloqueada = self._faixa_bloqueada(distancia_spawn_m, meia_janela_m=16.0, zonas_bloqueadas=zonas_bloqueadas)
        faixa0_bloqueada = self._faixa_bloqueada(
            distancia_spawn_m, meia_janela_m=16.0, zonas_bloqueadas=zonas_bloqueadas_esquerda
        )
        faixas_restritas = set(faixas_ocupadas)
        if faixa2_bloqueada:
            faixas_restritas.add(2)
        if faixa0_bloqueada:
            faixas_restritas.add(0)

        # Garante ao menos uma faixa livre para passagem do piloto
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
    def _faixa_bloqueada(
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
                if v._faixa_destino is not None:
                    ocupadas.add(v._faixa_destino)
        return ocupadas

    @staticmethod
    def _colide_com_existente(
        veiculos: Sequence[Veiculo],
        faixa: int,
        distancia_m: float,
        comprimento_novo_m: float,
    ) -> bool:
        for v in veiculos:
            if v.faixa != faixa and v._faixa_destino != faixa:
                continue
            min_sep = (v.comprimento_m + comprimento_novo_m) * 0.5 + DISTANCIA_SEGURA_MESMA_FAIXA_M + 3.0
            if abs(v.distancia_m - distancia_m) < min_sep:
                return True
        return False
