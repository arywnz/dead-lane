from dataclasses import dataclass

from src.configuracao import (
    ACELERACAO_MPS2,
    CENTRO_PISTA_X,
    CICLISTA_MAX_X,
    CICLISTA_MIN_X,
    DASH_BONUS_ESCAPADA_S,
    DASH_DURACAO_S,
    DASH_RECARGA_S,
    DASH_VELOCIDADE_AVANCO_MPS,
    DASH_VELOCIDADE_LATERAL_PXPS,
    FRENAGEM_MPS2,
    VELOCIDADE_INICIAL_MPS,
    VELOCIDADE_LATERAL_PXPS,
    VELOCIDADE_MAXIMA_MPS,
)


@dataclass
class Ciclista:
    x: float = CENTRO_PISTA_X
    velocidade_mps: float = VELOCIDADE_INICIAL_MPS
    distancia_m: float = 0.0
    dash_restante_s: float = 0.0
    dash_recarga_s: float = 0.0
    dash_direcao: int = 0
    dash_avanco: bool = False
    _dash_em_risco: bool = False
    _bonus_dash_ganho: bool = False

    @property
    def dash_pronto(self) -> bool:
        return self.dash_recarga_s <= 0.0 and self.dash_restante_s <= 0.0

    @property
    def progresso_recarga_dash(self) -> float:
        if DASH_RECARGA_S <= 0:
            return 1.0
        return max(0.0, min(1.0, 1.0 - self.dash_recarga_s / DASH_RECARGA_S))

    def acionar_dash(self, direcao_lateral: int, *, em_risco: bool = False) -> bool:
        """Dispara dash lateral (se A/D ativo) ou dash para frente (se sem direção lateral)."""
        if not self.dash_pronto:
            return False
        self.dash_avanco = direcao_lateral == 0
        self.dash_direcao = direcao_lateral
        self.dash_restante_s = DASH_DURACAO_S
        self.dash_recarga_s = DASH_RECARGA_S
        self._dash_em_risco = em_risco
        return True

    def consumir_bonus_dash(self) -> bool:
        if self._bonus_dash_ganho:
            self._bonus_dash_ganho = False
            return True
        return False

    def atualizar(self, delta_s: float, direcao_lateral: int, acelerar: bool, frear: bool) -> None:
        aceleracao = 0.0
        if frear:
            aceleracao = -FRENAGEM_MPS2
        elif acelerar:
            aceleracao = ACELERACAO_MPS2

        tempo_aceleracao_s = delta_s
        if aceleracao > 0:
            tempo_aceleracao_s = min(delta_s, (VELOCIDADE_MAXIMA_MPS - self.velocidade_mps) / aceleracao)
        elif aceleracao < 0:
            tempo_aceleracao_s = min(delta_s, self.velocidade_mps / -aceleracao)

        nova_velocidade = min(VELOCIDADE_MAXIMA_MPS, max(0.0, self.velocidade_mps + aceleracao * tempo_aceleracao_s))
        avanco_m = (self.velocidade_mps + nova_velocidade) * 0.5 * tempo_aceleracao_s
        avanco_m += nova_velocidade * (delta_s - tempo_aceleracao_s)
        self.velocidade_mps = nova_velocidade

        if self.dash_recarga_s > 0.0:
            self.dash_recarga_s = max(0.0, self.dash_recarga_s - delta_s)

        if self.dash_restante_s > 0.0:
            tempo_dash = min(delta_s, self.dash_restante_s)
            self.dash_restante_s = max(0.0, self.dash_restante_s - delta_s)
            if self.dash_avanco:
                avanco_m = max(avanco_m, DASH_VELOCIDADE_AVANCO_MPS * tempo_dash + nova_velocidade * (delta_s - tempo_dash))
                deslocamento_x = 0.0
            else:
                deslocamento_x = self.dash_direcao * DASH_VELOCIDADE_LATERAL_PXPS * tempo_dash
            if self.dash_restante_s == 0.0 and self._dash_em_risco:
                self._dash_em_risco = False
                self.dash_recarga_s = max(0.0, self.dash_recarga_s - DASH_BONUS_ESCAPADA_S)
                self._bonus_dash_ganho = True
        else:
            tempo_movimento_lateral_s = min(delta_s, avanco_m / VELOCIDADE_INICIAL_MPS)
            deslocamento_x = direcao_lateral * VELOCIDADE_LATERAL_PXPS * tempo_movimento_lateral_s

        self.distancia_m += avanco_m
        novo_x = self.x + deslocamento_x
        self.x = min(CICLISTA_MAX_X, max(CICLISTA_MIN_X, novo_x))
