"""Gerenciador de áudio usando gravações reais em assets/sounds/."""

from __future__ import annotations

import pygame

from src.assets import obter_pasta_assets


class GerenciadorSom:
    """Carrega e reproduz efeitos sonoros de veículos, alertas e ambiente urbano."""

    def __init__(self) -> None:
        self.ativo = False
        self._som_alerta: pygame.mixer.Sound | None = None
        self._som_dash: pygame.mixer.Sound | None = None
        self._som_colisao: pygame.mixer.Sound | None = None
        self._som_carro: pygame.mixer.Sound | None = None
        self._som_onibus: pygame.mixer.Sound | None = None
        self._som_ambiente: pygame.mixer.Sound | None = None
        self._canal_ambiente: pygame.mixer.Channel | None = None
        self._ambiente_tocando = False
        self._cooldown_veiculo_s = 0.0

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)

            pasta_sons = obter_pasta_assets() / "sounds"
            self._som_ambiente = self._carregar(pasta_sons / "ambiente_cidade.wav", volume=0.26)
            self._som_alerta = self._carregar(pasta_sons / "alerta.ogg", volume=0.32)
            self._som_dash = self._carregar(pasta_sons / "dash.ogg", volume=0.50)
            self._som_colisao = self._carregar(pasta_sons / "colisao.wav", volume=0.55)
            self._som_carro = self._carregar(pasta_sons / "carro.wav", volume=0.45)
            self._som_onibus = self._carregar(pasta_sons / "onibus.ogg", volume=0.48)
            self.ativo = True
        except Exception:
            self.ativo = False

    @staticmethod
    def _carregar(caminho, volume: float) -> pygame.mixer.Sound | None:
        if not caminho.exists():
            return None
        try:
            som = pygame.mixer.Sound(str(caminho))
            som.set_volume(volume)
            return som
        except Exception:
            return None

    def _tocar(self, som: pygame.mixer.Sound | None, maxtime_ms: int = 0) -> None:
        if self.ativo and som is not None:
            try:
                som.play(maxtime=maxtime_ms)
            except Exception:
                pass

    def atualizar_ambiente(self, delta_s: float, jogando: bool) -> None:
        if not self.ativo or self._som_ambiente is None:
            return
        if self._cooldown_veiculo_s > 0.0:
            self._cooldown_veiculo_s = max(0.0, self._cooldown_veiculo_s - delta_s)
        try:
            if jogando and not self._ambiente_tocando:
                self._canal_ambiente = self._som_ambiente.play(loops=-1, fade_ms=400)
                self._ambiente_tocando = True
            elif not jogando and self._ambiente_tocando:
                if self._canal_ambiente is not None:
                    self._canal_ambiente.fadeout(250)
                self._ambiente_tocando = False
        except Exception:
            pass

    def tocar_passagem_veiculo(self, *, eh_onibus: bool) -> None:
        if not self.ativo or self._cooldown_veiculo_s > 0.0:
            return
        self._cooldown_veiculo_s = 1.6 if eh_onibus else 1.2
        if eh_onibus:
            self._tocar(self._som_onibus, maxtime_ms=1700)
        else:
            self._tocar(self._som_carro)

    def tocar_alerta(self) -> None:
        self._tocar(self._som_alerta, maxtime_ms=650)

    def tocar_dash(self) -> None:
        self._tocar(self._som_dash)

    def tocar_colisao(self) -> None:
        self._tocar(self._som_colisao)

    def tocar_vitoria(self) -> None:
        self._tocar(self._som_alerta, maxtime_ms=280)
