import pygame

from src.cenario_visual import (
    AVISO,
    DESTAQUE,
    FUNDO,
    PERIGO,
    desenhar_cenario_avenida,
    desenhar_ciclista,
    desenhar_marcos_percurso,
    desenhar_painel,
    desenhar_perigo_ponto_cego,
    desenhar_perigo_porta,
    desenhar_veiculo,
)
from src.ciclista import Ciclista
from src.configuracao import (
    ALTURA_COLISAO_CICLISTA,
    ALTURA_JANELA,
    CICLISTA_TELA_Y,
    COMPRIMENTO_PERCURSO_M,
    FPS_ALVO,
    LARGURA_COLISAO_CICLISTA,
    LARGURA_JANELA,
    TEMPO_MAXIMO_QUADRO_S,
)
from src.percurso import Percurso
from src.perigos import FasePontoCego, FasePorta, GerenciadorPerigos
from src.trafego import GerenciadorTrafego


def _obter_mensagem_status(
    motivo_colisao: str | None,
    percurso: Percurso,
    perigos: GerenciadorPerigos,
    ciclista_no_ponto_cego: bool,
    feedback_seguro_s: float,
) -> tuple[str, str] | None:
    if motivo_colisao:
        return motivo_colisao, PERIGO
    if percurso.concluido:
        return "Vitória! Percurso concluído.", DESTAQUE

    ponto_cego = perigos.ponto_cego_em_destaque()
    if ponto_cego is not None:
        if ponto_cego.fase is FasePontoCego.ATIVO:
            return "Ônibus fechando à direita! Afaste-se.", PERIGO
        if ciclista_no_ponto_cego:
            return "Você está no ponto cego! Freie para sair.", PERIGO
        return "Ponto cego do ônibus. Freie ou passe à esquerda.", AVISO

    porta = perigos.porta_em_destaque()
    if porta is not None:
        if porta.fase is FasePorta.ABERTA:
            return "Porta aberta na faixa direita.", PERIGO
        return "Aviso de porta. Freie ou mude de faixa.", AVISO

    if feedback_seguro_s > 0.0:
        return "Saiu do ponto cego com segurança!", DESTAQUE
    if percurso.intervalo_restante_s > 0:
        return f"Checkpoint {percurso.indice_trecho} alcançado.", DESTAQUE
    return None


def executar() -> None:
    pygame.display.init()
    pygame.font.init()
    try:
        tela = pygame.display.set_mode((LARGURA_JANELA, ALTURA_JANELA))
        pygame.display.set_caption("Dead Lane")
        relogio = pygame.time.Clock()
        ciclista = Ciclista()
        percurso = Percurso()
        perigos = GerenciadorPerigos.criar_padrao()
        trafego = GerenciadorTrafego()
        motivo_colisao: str | None = None
        tempo_total_s = 0.0
        feedback_seguro_s = 0.0
        area_ciclista = pygame.FRect(0, 0, LARGURA_COLISAO_CICLISTA, ALTURA_COLISAO_CICLISTA)
        area_ciclista.centery = CICLISTA_TELA_Y
        fonte_titulo = pygame.font.SysFont("Segoe UI", 42, bold=True)
        fonte_texto = pygame.font.SysFont("Segoe UI", 20)
        fonte_menor = pygame.font.SysFont("Segoe UI", 17, bold=True)
        fonte_velocidade = pygame.font.SysFont("Segoe UI", 64, bold=True)

        while True:
            delta_s = min(relogio.tick(FPS_ALVO) / 1000, TEMPO_MAXIMO_QUADRO_S)
            tempo_total_s += delta_s
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    return
                if evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_ESCAPE:
                        return
                    if evento.key == pygame.K_r:
                        ciclista = Ciclista()
                        percurso = Percurso()
                        perigos = GerenciadorPerigos.criar_padrao()
                        trafego = GerenciadorTrafego()
                        motivo_colisao = None
                        feedback_seguro_s = 0.0

            frear = False
            ciclista_no_ponto_cego = False
            if motivo_colisao is None and not percurso.concluido:
                teclas = pygame.key.get_pressed()
                esquerda = teclas[pygame.K_a] or teclas[pygame.K_LEFT]
                direita = teclas[pygame.K_d] or teclas[pygame.K_RIGHT]
                acelerar = teclas[pygame.K_w] or teclas[pygame.K_UP]
                frear = teclas[pygame.K_s] or teclas[pygame.K_DOWN]

                ciclista.atualizar(delta_s, int(direita) - int(esquerda), acelerar, frear)
                ciclista.distancia_m = min(ciclista.distancia_m, COMPRIMENTO_PERCURSO_M)
                area_ciclista.centerx = ciclista.x

                percurso.atualizar(delta_s, ciclista.distancia_m)
                perigos.atualizar(
                    delta_s,
                    ciclista.distancia_m,
                    area_ciclista,
                    permitir_aviso=percurso.pode_iniciar_perigo,
                )

                if perigos.consumir_feedback_seguro() is not None:
                    feedback_seguro_s = 1.6
                else:
                    feedback_seguro_s = max(0.0, feedback_seguro_s - delta_s)

                onibus_perigo = perigos.onibus_ativos(ciclista.distancia_m)
                zonas_bloqueadas = perigos.zonas_bloqueadas_faixa_direita(ciclista.distancia_m)
                zonas_sem_trafego = perigos.zonas_exclusivas_ponto_cego(ciclista.distancia_m)
                trafego.atualizar(
                    delta_s,
                    ciclista.distancia_m,
                    zonas_bloqueadas=zonas_bloqueadas,
                    veiculos_externos=onibus_perigo,
                    indice_trecho=percurso.indice_trecho,
                    zonas_sem_trafego=zonas_sem_trafego,
                )

                ponto_cego_destaque = perigos.ponto_cego_em_destaque()
                ciclista_no_ponto_cego = (
                    ponto_cego_destaque is not None
                    and ponto_cego_destaque.ciclista_na_zona(area_ciclista, ciclista.distancia_m)
                )

                motivo_colisao = perigos.verificar_colisao(area_ciclista, ciclista.distancia_m)
                if motivo_colisao is None:
                    for veiculo in trafego.veiculos:
                        if area_ciclista.colliderect(veiculo.area_colisao(ciclista.distancia_m)):
                            motivo_colisao = "Colisão com veículo na avenida. R para reiniciar."
                            break

            tela.fill(FUNDO)
            desenhar_cenario_avenida(tela, ciclista.distancia_m, percurso.indice_trecho)
            desenhar_marcos_percurso(tela, ciclista.distancia_m, fonte_texto)
            for porta in perigos.portas:
                desenhar_perigo_porta(tela, porta, ciclista.distancia_m, fonte_texto)
            for veiculo in trafego.veiculos:
                desenhar_veiculo(tela, veiculo, ciclista.distancia_m, percurso.indice_trecho, tempo_total_s)
            for ponto_cego in perigos.pontos_cegos:
                em_risco = ponto_cego.ciclista_na_zona(area_ciclista, ciclista.distancia_m)
                desenhar_perigo_ponto_cego(
                    tela,
                    ponto_cego,
                    ciclista.distancia_m,
                    percurso.indice_trecho,
                    tempo_total_s,
                    fonte_menor,
                    em_risco,
                )
            desenhar_ciclista(tela, ciclista, frear)
            mensagem_status = _obter_mensagem_status(
                motivo_colisao,
                percurso,
                perigos,
                ciclista_no_ponto_cego,
                feedback_seguro_s,
            )
            desenhar_painel(
                tela,
                ciclista,
                fonte_titulo,
                fonte_texto,
                fonte_menor,
                fonte_velocidade,
                percurso,
                mensagem_status,
                perigos.marcos_normalizados(COMPRIMENTO_PERCURSO_M),
            )
            pygame.display.flip()
    finally:
        pygame.quit()


if __name__ == "__main__":
    executar()
