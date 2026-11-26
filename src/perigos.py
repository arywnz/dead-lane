from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
import random

import pygame

from src.configuracao import (
    ALCANCE_PORTA,
    ALTURA_PORTA,
    ANTECEDENCIA_ENTRADA_ONIBUS_M,
    CENTRO_PISTA_X,
    CICLISTA_TELA_Y,
    COMPRIMENTO_CARRO_ESTACIONADO,
    CONFIG_TRECHOS,
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
    MARGEM_SEM_TRAFEGO_COMPARAVEL_M,
    POSICAO_PONTO_CEGO_M,
    POSICAO_PORTA_M,
    SITUACOES_COMPARAVEIS,
    VELOCIDADE_INICIAL_MPS,
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
    lado: str = "direita"
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

    def atualizar(
        self,
        delta_s: float,
        distancia_ciclista_m: float,
        *,
        permitir_aviso: bool = True,
        velocidade_mps: float = VELOCIDADE_INICIAL_MPS,
    ) -> None:
        if self._tempo_decorrido_s is not None:
            self._tempo_decorrido_s = min(self._tempo_decorrido_s + delta_s, DURACAO_AVISO_PORTA_S + DURACAO_PORTA_ABERTA_S)
        else:
            # Em velocidades altas, antecipa o aviso para a porta realmente abrir à frente do piloto.
            distancia_aviso_m = max(DISTANCIA_AVISO_PORTA_M, min(20.0, velocidade_mps * 1.32))
            if permitir_aviso and 0 <= self.distancia_m - distancia_ciclista_m <= distancia_aviso_m:
                self._tempo_decorrido_s = 0.0

    def area_carro(self, distancia_ciclista_m: float) -> pygame.FRect:
        if self.lado == "esquerda":
            esquerda_carro = CENTRO_PISTA_X - LARGURA_PISTA / 2 - LARGURA_CARRO_ESTACIONADO
        else:
            esquerda_carro = CENTRO_PISTA_X + LARGURA_PISTA / 2
        porta_y = CICLISTA_TELA_Y + (distancia_ciclista_m - self.distancia_m) * ESCALA_PISTA_PX_POR_M
        return pygame.FRect(esquerda_carro, porta_y - ALTURA_PORTA, LARGURA_CARRO_ESTACIONADO, COMPRIMENTO_CARRO_ESTACIONADO)

    def area_porta(self, distancia_ciclista_m: float) -> pygame.FRect:
        carro = self.area_carro(distancia_ciclista_m)
        if self.lado == "esquerda":
            return pygame.FRect(carro.right, carro.top + ALTURA_PORTA / 2, ALCANCE_PORTA, ALTURA_PORTA)
        return pygame.FRect(carro.left - ALCANCE_PORTA, carro.top + ALTURA_PORTA / 2, ALCANCE_PORTA, ALTURA_PORTA)

    def ciclista_em_rota_de_colisao(
        self,
        area_ciclista: pygame.FRect,
        distancia_ciclista_m: float,
        velocidade_mps: float,
    ) -> bool:
        """Indica se, mantendo a posição lateral e a velocidade atuais, o ciclista encostaria na porta aberta."""
        if self.fase is FasePorta.FECHADA:
            return False
        porta = self.area_porta(distancia_ciclista_m)
        if area_ciclista.right <= porta.left or area_ciclista.left >= porta.right:
            return False

        tolerancia_m = (area_ciclista.height / 2 + ALTURA_PORTA / 2) / ESCALA_PISTA_PX_POR_M
        ate_inicio_contato_m = self.distancia_m - tolerancia_m - distancia_ciclista_m
        ate_fim_contato_m = self.distancia_m + tolerancia_m - distancia_ciclista_m
        if ate_fim_contato_m <= 0:
            return False

        tempo_decorrido_s = self._tempo_decorrido_s or 0.0
        abre_em_s = DURACAO_AVISO_PORTA_S - tempo_decorrido_s
        fecha_em_s = DURACAO_AVISO_PORTA_S + DURACAO_PORTA_ABERTA_S - tempo_decorrido_s
        if ate_inicio_contato_m <= 0:
            # Já está ao lado da porta: o risco dura enquanto ela ainda puder abrir nele.
            fim_contato_s = ate_fim_contato_m / velocidade_mps if velocidade_mps > 0 else float("inf")
            return fim_contato_s > abre_em_s
        if velocidade_mps <= 0:
            return False
        inicio_contato_s = ate_inicio_contato_m / velocidade_mps
        fim_contato_s = ate_fim_contato_m / velocidade_mps
        return inicio_contato_s < fecha_em_s and fim_contato_s > abre_em_s


@dataclass
class PerigoPontoCego:
    """Ônibus na faixa central com região lateral de ponto cego à direita."""

    distancia_encontro_m: float = POSICAO_PONTO_CEGO_M
    velocidade_onibus_mps: float = VELOCIDADE_ONIBUS_MPS
    trecho: int = 0
    id_evento: str = "ponto_cego_1"
    lado: str = "direita"
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
        velocidade_mps: float = VELOCIDADE_INICIAL_MPS,
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
        velocidade_relativa = max(0.0, velocidade_mps - self.velocidade_onibus_mps)
        distancia_aviso_m = max(DISTANCIA_AVISO_PONTO_CEGO_M, min(15.5, velocidade_relativa * 1.45))

        if self._tempo_decorrido_s is not None:
            self._tempo_decorrido_s = min(
                self._tempo_decorrido_s + delta_s,
                DURACAO_AVISO_PONTO_CEGO_S + DURACAO_PONTO_CEGO_ATIVO_S,
            )
        elif permitir_aviso and -3.5 <= diferenca_m <= distancia_aviso_m:
            self._tempo_decorrido_s = 0.0

        fase_atual = self.fase
        em_sinal = fase_atual in (FasePontoCego.AVISO, FasePontoCego.ATIVO)
        sinal_lado = 1 if self.lado == "direita" else -1
        self.onibus.seta_direita_ativa = em_sinal and self.lado == "direita"
        self.onibus.seta_direcao = sinal_lado if em_sinal else 0

        if fase_atual is FasePontoCego.ATIVO:
            progresso_ativo = (self._tempo_decorrido_s - DURACAO_AVISO_PONTO_CEGO_S) / DURACAO_PONTO_CEGO_ATIVO_S
            fator = min(1.0, max(0.0, progresso_ativo * 1.4))
            self.onibus.deslocamento_x = sinal_lado * DESLOCAMENTO_FECHAMENTO_ONIBUS_PX * fator
        elif fase_atual is FasePontoCego.ENCERRADO:
            self.onibus.deslocamento_x = sinal_lado * DESLOCAMENTO_FECHAMENTO_ONIBUS_PX

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
        if self.lado == "esquerda":
            borda_esquerda_pista = CENTRO_PISTA_X - LARGURA_PISTA / 2
            direita = bus_rect.left + 4
            largura = min(LARGURA_PONTO_CEGO, direita - borda_esquerda_pista)
            if largura <= 0:
                return None
            return pygame.FRect(direita - largura, bus_rect.top + 36, largura, bus_rect.height - 44)
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


def criar_perigos_percurso(aleatorio: bool = False) -> tuple[list[PerigoPorta], list[PerigoPontoCego]]:
    """Constrói os perigos distribuídos nos três trechos com intervalos decrescentes."""
    portas: list[PerigoPorta] = []
    pontos_cegos: list[PerigoPontoCego] = []
    contador_porta = 0
    contador_ponto_cego = 0
    ultimo_marco_m = 0.0

    for indice_trecho, config in enumerate(CONFIG_TRECHOS):
        for tipo, marco_m in config["perigos"]:
            if aleatorio:
                marco_m = max(ultimo_marco_m + 72.0, marco_m + random.uniform(-22.0, 22.0))
            ultimo_marco_m = marco_m
            if tipo == "porta":
                contador_porta += 1
                id_porta = f"porta_{contador_porta}"
                ids_porta_comparaveis = set(SITUACOES_COMPARAVEIS["porta"])
                if id_porta in ids_porta_comparaveis:
                    # Mantém o par comparável início x fim no mesmo lado para comparação justa.
                    lado_porta = "direita"
                else:
                    lado_porta = "esquerda" if contador_porta % 2 == 0 else "direita"
                    if aleatorio and random.random() < 0.35:
                        lado_porta = "direita" if lado_porta == "esquerda" else "esquerda"
                portas.append(
                    PerigoPorta(
                        distancia_m=marco_m,
                        trecho=indice_trecho,
                        id_evento=id_porta,
                        lado=lado_porta,
                    )
                )
            elif tipo == "ponto_cego":
                contador_ponto_cego += 1
                if aleatorio:
                    lado_pc = "esquerda" if contador_ponto_cego % 2 == 1 else "direita"
                    if random.random() < 0.35:
                        lado_pc = "direita" if lado_pc == "esquerda" else "esquerda"
                else:
                    lado_pc = "direita"
                pontos_cegos.append(
                    PerigoPontoCego(
                        distancia_encontro_m=marco_m,
                        trecho=indice_trecho,
                        id_evento=f"ponto_cego_{contador_ponto_cego}",
                        lado=lado_pc,
                    )
                )

    return portas, pontos_cegos


@dataclass
class GerenciadorPerigos:
    """Coordena a ativação, consultas e colisões dos perigos ao longo dos três trechos."""

    portas: list[PerigoPorta]
    pontos_cegos: list[PerigoPontoCego]
    _feedbacks_emitidos: set[str] = field(default_factory=set, init=False)

    @classmethod
    def criar_padrao(cls, *, aleatorio: bool = False) -> "GerenciadorPerigos":
        portas, pontos_cegos = criar_perigos_percurso(aleatorio=aleatorio)
        return cls(portas=portas, pontos_cegos=pontos_cegos)

    def atualizar(
        self,
        delta_s: float,
        distancia_ciclista_m: float,
        area_ciclista: pygame.FRect,
        *,
        permitir_aviso: bool = True,
        velocidade_mps: float = VELOCIDADE_INICIAL_MPS,
    ) -> None:
        for porta in self.portas:
            em_andamento = porta.fase in (FasePorta.AVISO, FasePorta.ABERTA)
            proxima = -15.0 <= porta.distancia_m - distancia_ciclista_m <= 28.0
            if em_andamento or (proxima and porta.fase is FasePorta.AGUARDANDO):
                porta.atualizar(
                    delta_s,
                    distancia_ciclista_m,
                    permitir_aviso=permitir_aviso,
                    velocidade_mps=velocidade_mps,
                )

        for ponto_cego in self.pontos_cegos:
            em_andamento = ponto_cego.fase in (FasePontoCego.AVISO, FasePontoCego.ATIVO)
            visivel = (
                ponto_cego.onibus is not None
                and -18.0 <= ponto_cego.onibus.distancia_m - distancia_ciclista_m <= 48.0
            )
            em_aproximacao = (
                ponto_cego.onibus is None
                and distancia_ciclista_m >= ponto_cego.distancia_encontro_m - ANTECEDENCIA_ENTRADA_ONIBUS_M - 4.0
            )
            if em_andamento or visivel or em_aproximacao:
                ponto_cego.atualizar(
                    delta_s,
                    distancia_ciclista_m,
                    area_ciclista,
                    permitir_aviso=permitir_aviso,
                    velocidade_mps=velocidade_mps,
                )

    def porta_em_destaque(self, distancia_ciclista_m: float | None = None) -> PerigoPorta | None:
        def _visivel(p: PerigoPorta) -> bool:
            return distancia_ciclista_m is None or -10.0 <= p.distancia_m - distancia_ciclista_m <= 28.0

        abertas = [p for p in self.portas if p.fase is FasePorta.ABERTA and _visivel(p)]
        if abertas:
            return abertas[0]
        avisos = [p for p in self.portas if p.fase is FasePorta.AVISO and _visivel(p)]
        return avisos[0] if avisos else None

    def ponto_cego_em_destaque(self, distancia_ciclista_m: float | None = None) -> PerigoPontoCego | None:
        def _visivel(pc: PerigoPontoCego) -> bool:
            if pc.onibus is None:
                return False
            return distancia_ciclista_m is None or -14.0 <= pc.onibus.distancia_m - distancia_ciclista_m <= 36.0

        ativos = [p for p in self.pontos_cegos if p.fase is FasePontoCego.ATIVO and _visivel(p)]
        if ativos:
            return ativos[0]
        avisos = [p for p in self.pontos_cegos if p.fase is FasePontoCego.AVISO and _visivel(p)]
        return avisos[0] if avisos else None

    def onibus_ativos(self, distancia_ciclista_m: float) -> list[Veiculo]:
        return [
            p.onibus
            for p in self.pontos_cegos
            if p.onibus is not None and -16.0 <= p.onibus.distancia_m - distancia_ciclista_m <= 48.0
        ]

    def zonas_bloqueadas_faixa_direita(self, distancia_ciclista_m: float) -> list[tuple[float, float]]:
        zonas: list[tuple[float, float]] = []
        for p in self.portas:
            if p.lado == "direita" and -15.0 <= p.distancia_m - distancia_ciclista_m <= 45.0:
                zonas.append((p.distancia_m - 12.0, p.distancia_m + 12.0))
        return zonas

    def zonas_bloqueadas_faixa_esquerda(self, distancia_ciclista_m: float) -> list[tuple[float, float]]:
        zonas: list[tuple[float, float]] = []
        for p in self.portas:
            if p.lado == "esquerda" and -15.0 <= p.distancia_m - distancia_ciclista_m <= 45.0:
                zonas.append((p.distancia_m - 12.0, p.distancia_m + 12.0))
        return zonas

    def em_risco_iminente(
        self,
        area_ciclista: pygame.FRect,
        distancia_ciclista_m: float,
        velocidade_mps: float,
    ) -> bool:
        """Retorna True se o piloto está em risco imediato de algum perigo ativo."""
        for porta in self.portas:
            if porta.fase in (FasePorta.AVISO, FasePorta.ABERTA) and porta.ciclista_em_rota_de_colisao(
                area_ciclista, distancia_ciclista_m, velocidade_mps
            ):
                return True
        for pc in self.pontos_cegos:
            if pc.fase in (FasePontoCego.AVISO, FasePontoCego.ATIVO) and pc.ciclista_na_zona(
                area_ciclista, distancia_ciclista_m
            ):
                return True
        return False

    def zonas_exclusivas_ponto_cego(self, distancia_ciclista_m: float) -> list[tuple[float, float]]:
        zonas: list[tuple[float, float]] = []
        for pc in self.pontos_cegos:
            if -20.0 <= pc.distancia_encontro_m - distancia_ciclista_m <= 85.0:
                zonas.append((pc.distancia_encontro_m - 42.0, pc.distancia_encontro_m + 50.0))
        return zonas

    def zonas_sem_trafego(self, distancia_ciclista_m: float) -> list[tuple[float, float]]:
        """Zonas sem tráfego comum: encontros com ônibus e, com margem maior, as situações da comparação início × fim."""
        zonas = self.zonas_exclusivas_ponto_cego(distancia_ciclista_m)
        ids_comparaveis = {id_evento for par in SITUACOES_COMPARAVEIS.values() for id_evento in par}
        antes_m, depois_m = MARGEM_SEM_TRAFEGO_COMPARAVEL_M
        marcos = [(p.id_evento, p.distancia_m) for p in self.portas]
        marcos += [(pc.id_evento, pc.distancia_encontro_m) for pc in self.pontos_cegos]
        for id_evento, marco_m in marcos:
            # O tráfego nasce à frente do ciclista; a zona vale enquanto ainda pode receber veículos novos.
            if id_evento in ids_comparaveis and -depois_m <= marco_m - distancia_ciclista_m <= antes_m + 45.0:
                zonas.append((marco_m - antes_m, marco_m + depois_m))
        return zonas

    def verificar_colisao(self, area_ciclista: pygame.FRect, distancia_ciclista_m: float) -> str | None:
        colisao = self.verificar_colisao_detalhada(area_ciclista, distancia_ciclista_m)
        return colisao[0] if colisao is not None else None

    def verificar_colisao_detalhada(
        self,
        area_ciclista: pygame.FRect,
        distancia_ciclista_m: float,
    ) -> tuple[str, str] | None:
        """Retorna (motivo, id_evento) do perigo que causou a colisão, ou None."""
        for porta in self.portas:
            if porta.fase is FasePorta.ABERTA and area_ciclista.colliderect(porta.area_porta(distancia_ciclista_m)):
                return "Colisão com a porta. R para reiniciar.", porta.id_evento
        for pc in self.pontos_cegos:
            if pc.houve_incidente(area_ciclista, distancia_ciclista_m):
                return "Ficou no ponto cego do ônibus. R para reiniciar.", pc.id_evento
            if (
                pc.onibus is not None
                and -12.0 <= pc.onibus.distancia_m - distancia_ciclista_m <= 12.0
                and area_ciclista.colliderect(pc.onibus.area_colisao(distancia_ciclista_m))
            ):
                return "Colisão com o ônibus. R para reiniciar.", pc.id_evento
        return None

    def consumir_feedback_seguro(self) -> str | None:
        for pc in self.pontos_cegos:
            if pc.saiu_com_seguranca and pc.id_evento not in self._feedbacks_emitidos:
                self._feedbacks_emitidos.add(pc.id_evento)
                return "Saiu do ponto cego com segurança!"
        return None

    def marcos_normalizados(self, comprimento_total_m: float) -> list[tuple[float, bool]]:
        """Retorna pares (progresso_0_a_1, ja_passou_ou_ativo) para exibição no HUD."""
        marcos: list[tuple[float, bool]] = []
        for porta in self.portas:
            marcos.append((porta.distancia_m / comprimento_total_m, porta.fase is FasePorta.FECHADA))
        for pc in self.pontos_cegos:
            marcos.append((pc.distancia_encontro_m / comprimento_total_m, pc.fase is FasePontoCego.ENCERRADO))
        marcos.sort(key=lambda item: item[0])
        return marcos
