from dataclasses import dataclass

from src.configuracao import (
    ACELERACAO_MPS2,
    FRENAGEM_MPS2,
    VELOCIDADE_LATERAL_PXPS,
    VELOCIDADE_MAXIMA_MPS,
    CICLISTA_MAX_X,
    CICLISTA_MIN_X,
    CENTRO_PISTA_X,
    VELOCIDADE_INICIAL_MPS,
)


@dataclass
class Ciclista:
    x: float = CENTRO_PISTA_X
    velocidade_mps: float = VELOCIDADE_INICIAL_MPS
    distancia_m: float = 0.0

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
        self.distancia_m += avanco_m

        tempo_movimento_lateral_s = min(delta_s, avanco_m / VELOCIDADE_INICIAL_MPS)
        novo_x = self.x + direcao_lateral * VELOCIDADE_LATERAL_PXPS * tempo_movimento_lateral_s
        self.x = min(CICLISTA_MAX_X, max(CICLISTA_MIN_X, novo_x))
