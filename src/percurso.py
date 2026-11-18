from dataclasses import dataclass

from src.configuracao import INTERVALO_PONTO_CONTROLE_S, COMPRIMENTO_PERCURSO_M, COMPRIMENTO_TRECHO_M, NOMES_TRECHOS


@dataclass
class Percurso:
    indice_trecho: int = 0
    intervalo_restante_s: float = 0.0
    concluido: bool = False

    @property
    def pode_iniciar_perigo(self) -> bool:
        return not self.concluido and self.intervalo_restante_s == 0.0

    def atualizar(self, delta_s: float, distancia_m: float) -> None:
        proximo_trecho = min(int(distancia_m // COMPRIMENTO_TRECHO_M), len(NOMES_TRECHOS) - 1)
        if proximo_trecho > self.indice_trecho:
            self.indice_trecho = proximo_trecho
            self.intervalo_restante_s = INTERVALO_PONTO_CONTROLE_S
        else:
            self.intervalo_restante_s = max(0.0, self.intervalo_restante_s - delta_s)

        self.concluido = distancia_m >= COMPRIMENTO_PERCURSO_M
