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
from src.perigos import FasePontoCego, FasePorta, PerigoPontoCego, PerigoPorta
from src.trafego import GerenciadorTrafego


def _obter_mensagem_status(
    motivo_colisao: str | None,
    percurso: Percurso,
    perigo_porta: PerigoPorta,
    perigo_ponto_cego: PerigoPontoCego,
    ciclista_no_ponto_cego: bool,
    feedback_seguro_s: float,
) -> tuple[str, str] | None:
    if motivo_colisao:
        return motivo_colisao, PERIGO
    if percurso.concluido:
        return "Vitória! Percurso concluído.", DESTAQUE
    if perigo_ponto_cego.fase is FasePontoCego.ATIVO:
        return "Ônibus fechando à direita! Afaste-se.", PERIGO
    if perigo_ponto_cego.fase is FasePontoCego.AVISO:
        if ciclista_no_ponto_cego:
            return "Você está no ponto cego! Freie para sair.", PERIGO
        return "Ponto cego do ônibus. Freie ou passe à esquerda.", AVISO
    if perigo_porta.fase is FasePorta.AVISO:
        return "Aviso de porta. Freie ou mude de faixa.", AVISO
    if perigo_porta.fase is FasePorta.ABERTA:
        return "Porta aberta na faixa direita.", PERIGO
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
        perigo_porta = PerigoPorta()
        perigo_ponto_cego = PerigoPontoCego()
        trafego = GerenciadorTrafego()
        motivo_colisao: str | None = None
        tempo_total_s = 0.0
        feedback_seguro_s = 0.0
        ultimo_feedback_ponto_cego = False
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
                        perigo_porta = PerigoPorta()
                        perigo_ponto_cego = PerigoPontoCego()
                        trafego = GerenciadorTrafego()
                        motivo_colisao = None
                        feedback_seguro_s = 0.0
                        ultimo_feedback_ponto_cego = False

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
                perigo_porta.atualizar(delta_s, ciclista.distancia_m, permitir_aviso=percurso.pode_iniciar_perigo)
                perigo_ponto_cego.atualizar(
                    delta_s,
                    ciclista.distancia_m,
                    area_ciclista,
                    permitir_aviso=percurso.pode_iniciar_perigo,
                )

                if perigo_ponto_cego.saiu_com_seguranca and not ultimo_feedback_ponto_cego:
                    feedback_seguro_s = 1.6
                    ultimo_feedback_ponto_cego = True
                else:
                    feedback_seguro_s = max(0.0, feedback_seguro_s - delta_s)

                veiculos_externos = [perigo_ponto_cego.onibus] if perigo_ponto_cego.onibus is not None else ()
                zonas_bloqueadas = (
                    (perigo_porta.distancia_m - 12.0, perigo_porta.distancia_m + 12.0),
                    (perigo_ponto_cego.distancia_encontro_m - 18.0, perigo_ponto_cego.distancia_encontro_m + 18.0),
                )
                trafego.atualizar(
                    delta_s,
                    ciclista.distancia_m,
                    zonas_bloqueadas=zonas_bloqueadas,
                    veiculos_externos=veiculos_externos,
                )

                ciclista_no_ponto_cego = perigo_ponto_cego.ciclista_na_zona(area_ciclista, ciclista.distancia_m)

                if perigo_porta.fase is FasePorta.ABERTA and area_ciclista.colliderect(
                    perigo_porta.area_porta(ciclista.distancia_m)
                ):
                    motivo_colisao = "Colisão com a porta. R para reiniciar."
                elif perigo_ponto_cego.houve_incidente(area_ciclista, ciclista.distancia_m):
                    motivo_colisao = "Ficou no ponto cego do ônibus. R para reiniciar."
                elif perigo_ponto_cego.onibus is not None and area_ciclista.colliderect(
                    perigo_ponto_cego.onibus.area_colisao(ciclista.distancia_m)
                ):
                    motivo_colisao = "Colisão com o ônibus. R para reiniciar."
                else:
                    for veiculo in trafego.veiculos:
                        if area_ciclista.colliderect(veiculo.area_colisao(ciclista.distancia_m)):
                            motivo_colisao = "Colisão com veículo na avenida. R para reiniciar."
                            break

            tela.fill(FUNDO)
            desenhar_cenario_avenida(tela, ciclista.distancia_m, percurso.indice_trecho)
            desenhar_marcos_percurso(tela, ciclista.distancia_m, fonte_texto)
            desenhar_perigo_porta(tela, perigo_porta, ciclista.distancia_m, fonte_texto)
            for veiculo in trafego.veiculos:
                desenhar_veiculo(tela, veiculo, ciclista.distancia_m, percurso.indice_trecho, tempo_total_s)
            desenhar_perigo_ponto_cego(
                tela,
                perigo_ponto_cego,
                ciclista.distancia_m,
                percurso.indice_trecho,
                tempo_total_s,
                fonte_menor,
                ciclista_no_ponto_cego,
            )
            desenhar_ciclista(tela, ciclista, frear)
            mensagem_status = _obter_mensagem_status(
                motivo_colisao,
                percurso,
                perigo_porta,
                perigo_ponto_cego,
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
            )
            pygame.display.flip()
    finally:
        pygame.quit()


if __name__ == "__main__":
    executar()
