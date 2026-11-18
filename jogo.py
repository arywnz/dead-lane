import pygame

from src.configuracao import (
    COMPRIMENTO_PERCURSO_M,
    TEMPO_MAXIMO_QUADRO_S,
    VELOCIDADE_MAXIMA_MPS,
    ALTURA_COLISAO_CICLISTA,
    LARGURA_COLISAO_CICLISTA,
    CICLISTA_TELA_Y,
    CENTRO_PISTA_X,
    FAIXAS_PISTA,
    ESCALA_PISTA_PX_POR_M,
    LARGURA_PISTA,
    COMPRIMENTO_TRECHO_M,
    NOMES_TRECHOS,
    FPS_ALVO,
    ALTURA_JANELA,
    LARGURA_JANELA,
)
from src.percurso import Percurso
from src.perigos import PerigoPorta, FasePorta
from src.ciclista import Ciclista

FUNDO = "#121d1b"
ASFALTO = "#242c2d"
BORDA_PISTA = "#465451"
CALCADA = "#2e3b37"
MARCACAO_FAIXA = "#687675"
TEXTO_PRINCIPAL = "#edf1e6"
TEXTO_SECUNDARIO = "#aebdb4"
DESTAQUE = "#d8f975"
PAINEL = "#1b2824"
AVISO = "#ffcf70"
PERIGO = "#ff786f"


def desenhar_pista(tela: pygame.Surface, distancia_m: float) -> None:
    esquerda_pista = CENTRO_PISTA_X - LARGURA_PISTA // 2
    direita_pista = esquerda_pista + LARGURA_PISTA
    pygame.draw.rect(tela, CALCADA, (esquerda_pista - 27, 0, LARGURA_PISTA + 54, ALTURA_JANELA))
    pygame.draw.rect(tela, ASFALTO, (esquerda_pista, 0, LARGURA_PISTA, ALTURA_JANELA))
    pygame.draw.line(tela, BORDA_PISTA, (esquerda_pista, 0), (esquerda_pista, ALTURA_JANELA), 4)
    pygame.draw.line(tela, BORDA_PISTA, (direita_pista, 0), (direita_pista, ALTURA_JANELA), 4)

    espacamento_tracos = 110
    deslocamento = int(distancia_m * ESCALA_PISTA_PX_POR_M) % espacamento_tracos
    for faixa in range(1, FAIXAS_PISTA):
        faixa_x = esquerda_pista + faixa * LARGURA_PISTA // FAIXAS_PISTA
        for y in range(deslocamento - espacamento_tracos, ALTURA_JANELA, espacamento_tracos):
            pygame.draw.rect(tela, MARCACAO_FAIXA, (faixa_x - 2, y, 4, 53))


def desenhar_marcos_percurso(tela: pygame.Surface, distancia_m: float, fonte: pygame.font.Font) -> None:
    esquerda_pista = CENTRO_PISTA_X - LARGURA_PISTA // 2
    direita_pista = esquerda_pista + LARGURA_PISTA
    for numero_trecho in range(1, len(NOMES_TRECHOS) + 1):
        marco_m = numero_trecho * COMPRIMENTO_TRECHO_M
        y = round(CICLISTA_TELA_Y + (distancia_m - marco_m) * ESCALA_PISTA_PX_POR_M)
        if 0 <= y < ALTURA_JANELA:
            chegada = marco_m == COMPRIMENTO_PERCURSO_M
            cor = DESTAQUE if chegada else TEXTO_PRINCIPAL
            rotulo = "Chegada" if chegada else f"Checkpoint {numero_trecho}"
            legenda = fonte.render(rotulo, True, cor)
            retangulo_legenda = legenda.get_rect(midbottom=(CENTRO_PISTA_X, y - 7))
            pygame.draw.line(tela, cor, (esquerda_pista, y), (direita_pista, y), 4)
            pygame.draw.rect(tela, ASFALTO, retangulo_legenda.inflate(20, 6), border_radius=5)
            tela.blit(legenda, retangulo_legenda)


def desenhar_ciclista(tela: pygame.Surface, ciclista: Ciclista, freando: bool) -> None:
    x, y = round(ciclista.x), CICLISTA_TELA_Y
    pygame.draw.ellipse(tela, "#151b1a", (x - 17, y - 25, 38, 54))
    pygame.draw.rect(tela, "#101716", (x - 4, y - 26, 8, 52), border_radius=4)
    pygame.draw.line(tela, "#edf1e6", (x - 12, y - 12), (x + 12, y - 12), 4)
    pygame.draw.rect(tela, DESTAQUE, (x - 9, y - 8, 18, 25), border_radius=7)
    pygame.draw.circle(tela, TEXTO_PRINCIPAL, (x, y - 9), 7)
    if freando and ciclista.velocidade_mps > 0:
        pygame.draw.circle(tela, PERIGO, (x, y + 22), 4)


def desenhar_perigo_porta(
    tela: pygame.Surface,
    perigo: PerigoPorta,
    distancia_ciclista_m: float,
    fonte: pygame.font.Font,
) -> None:
    carro = perigo.area_carro(distancia_ciclista_m)
    retangulo_carro = pygame.Rect(round(carro.x), round(carro.y), round(carro.w), round(carro.h))
    if not tela.get_rect().colliderect(retangulo_carro):
        return

    pygame.draw.rect(tela, "#4c6268", retangulo_carro, border_radius=10)
    pygame.draw.rect(tela, FUNDO, retangulo_carro.inflate(-14, -35), border_radius=6)
    pygame.draw.line(tela, BORDA_PISTA, retangulo_carro.midtop, retangulo_carro.midbottom, 2)

    fase = perigo.fase
    if fase is FasePorta.AVISO:
        pygame.draw.rect(tela, AVISO, retangulo_carro, width=3, border_radius=10)
        rotulo = fonte.render("! Porta", True, AVISO)
        tela.blit(rotulo, (retangulo_carro.right - rotulo.get_width(), retangulo_carro.top - rotulo.get_height() - 6))
    elif fase is FasePorta.ABERTA:
        porta = perigo.area_porta(distancia_ciclista_m)
        retangulo_porta = pygame.Rect(round(porta.x), round(porta.y), round(porta.w), round(porta.h))
        pygame.draw.rect(tela, PERIGO, retangulo_porta, border_radius=4)
        pygame.draw.line(tela, FUNDO, retangulo_porta.midleft, retangulo_porta.midright, 2)


def desenhar_painel(
    tela: pygame.Surface,
    ciclista: Ciclista,
    fonte_titulo: pygame.font.Font,
    fonte_texto: pygame.font.Font,
    fonte_velocidade: pygame.font.Font,
    fase_porta: FasePorta,
    colidiu: bool,
    percurso: Percurso,
) -> None:
    painel = pygame.Rect(748, 115, 448, 540)
    pygame.draw.rect(tela, PAINEL, painel, border_radius=22)
    x = painel.x + 34
    tela.blit(fonte_titulo.render("Dead Lane", True, TEXTO_PRINCIPAL), (x, 139))
    rotulo_trecho = f"Trecho {percurso.indice_trecho + 1}/{len(NOMES_TRECHOS)} · {NOMES_TRECHOS[percurso.indice_trecho]}"
    tela.blit(fonte_texto.render(rotulo_trecho, True, TEXTO_SECUNDARIO), (x, 194))

    velocidade_exibida = f"{ciclista.velocidade_mps * 3.6:.0f}"
    rotulo = fonte_velocidade.render(velocidade_exibida, True, DESTAQUE)
    tela.blit(rotulo, (x, 226))
    tela.blit(fonte_texto.render("km/h", True, TEXTO_SECUNDARIO), (x + rotulo.get_width() + 12, 271))
    pygame.draw.rect(tela, BORDA_PISTA, (x, 315, 380, 6), border_radius=3)
    largura_barra_velocidade = round(380 * ciclista.velocidade_mps / VELOCIDADE_MAXIMA_MPS)
    if largura_barra_velocidade:
        pygame.draw.rect(tela, DESTAQUE, (x, 315, largura_barra_velocidade, 6), border_radius=3)

    rotulo_distancia = f"Percurso   {int(ciclista.distancia_m)} / {COMPRIMENTO_PERCURSO_M} m"
    tela.blit(fonte_texto.render(rotulo_distancia, True, TEXTO_SECUNDARIO), (x, 349))
    pygame.draw.rect(tela, BORDA_PISTA, (x, 387, 380, 6), border_radius=3)
    largura_barra_percurso = round(380 * ciclista.distancia_m / COMPRIMENTO_PERCURSO_M)
    if largura_barra_percurso:
        pygame.draw.rect(tela, DESTAQUE, (x, 387, largura_barra_percurso, 6), border_radius=3)
    pygame.draw.line(tela, BORDA_PISTA, (x, 408), (x + 380, 408))
    for linha, (acao, teclas) in enumerate(
        (
            ("Acelerar", "W / ↑"),
            ("Frear", "S / ↓"),
            ("Mover para os lados", "A D / ← →"),
            ("Reiniciar", "R"),
            ("Sair", "Esc"),
        )
    ):
        y = 430 + linha * 36
        tela.blit(fonte_texto.render(acao, True, TEXTO_PRINCIPAL), (x, y))
        rotulo_tecla = fonte_texto.render(teclas, True, TEXTO_SECUNDARIO)
        tela.blit(rotulo_tecla, (x + 380 - rotulo_tecla.get_width(), y))

    if colidiu:
        mensagem, cor = "Colisão com a porta. R para reiniciar.", PERIGO
    elif percurso.concluido:
        mensagem, cor = "Vitória! Percurso concluído.", DESTAQUE
    elif fase_porta is FasePorta.AVISO:
        mensagem, cor = "Aviso de porta. Freie ou mude de faixa.", AVISO
    elif fase_porta is FasePorta.ABERTA:
        mensagem, cor = "Porta aberta na faixa direita.", PERIGO
    elif percurso.intervalo_restante_s > 0:
        mensagem, cor = f"Checkpoint {percurso.indice_trecho} alcançado.", DESTAQUE
    else:
        return
    tela.blit(fonte_texto.render(mensagem, True, cor), (x, 617))


def executar() -> None:
    pygame.display.init()
    pygame.font.init()
    try:
        tela = pygame.display.set_mode((LARGURA_JANELA, ALTURA_JANELA))
        pygame.display.set_caption("Dead Lane")
        relogio = pygame.time.Clock()
        ciclista = Ciclista()
        percurso = Percurso()
        perigo = PerigoPorta()
        colidiu = False
        area_ciclista = pygame.FRect(0, 0, LARGURA_COLISAO_CICLISTA, ALTURA_COLISAO_CICLISTA)
        area_ciclista.centery = CICLISTA_TELA_Y
        fonte_titulo = pygame.font.SysFont("Segoe UI", 44, bold=True)
        fonte_texto = pygame.font.SysFont("Segoe UI", 21)
        fonte_velocidade = pygame.font.SysFont("Segoe UI", 68, bold=True)

        while True:
            delta_s = min(relogio.tick(FPS_ALVO) / 1000, TEMPO_MAXIMO_QUADRO_S)
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    return
                if evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_ESCAPE:
                        return
                    if evento.key == pygame.K_r:
                        ciclista = Ciclista()
                        percurso = Percurso()
                        perigo = PerigoPorta()
                        colidiu = False

            frear = False
            if not colidiu and not percurso.concluido:
                teclas = pygame.key.get_pressed()
                esquerda = teclas[pygame.K_a] or teclas[pygame.K_LEFT]
                direita = teclas[pygame.K_d] or teclas[pygame.K_RIGHT]
                acelerar = teclas[pygame.K_w] or teclas[pygame.K_UP]
                frear = teclas[pygame.K_s] or teclas[pygame.K_DOWN]
                ciclista.atualizar(delta_s, int(direita) - int(esquerda), acelerar, frear)
                ciclista.distancia_m = min(ciclista.distancia_m, COMPRIMENTO_PERCURSO_M)
                percurso.atualizar(delta_s, ciclista.distancia_m)
                perigo.atualizar(delta_s, ciclista.distancia_m, permitir_aviso=percurso.pode_iniciar_perigo)
                area_ciclista.centerx = ciclista.x
                if perigo.fase is FasePorta.ABERTA:
                    colidiu = area_ciclista.colliderect(perigo.area_porta(ciclista.distancia_m))

            tela.fill(FUNDO)
            desenhar_pista(tela, ciclista.distancia_m)
            desenhar_marcos_percurso(tela, ciclista.distancia_m, fonte_texto)
            desenhar_perigo_porta(tela, perigo, ciclista.distancia_m, fonte_texto)
            desenhar_ciclista(tela, ciclista, frear)
            desenhar_painel(tela, ciclista, fonte_titulo, fonte_texto, fonte_velocidade, perigo.fase, colidiu, percurso)
            pygame.display.flip()
    finally:
        pygame.quit()


if __name__ == "__main__":
    executar()
