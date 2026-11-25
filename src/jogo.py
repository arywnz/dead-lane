import argparse
import sys
from pathlib import Path

# Garante que a pasta dead-lane esteja no sys.path mesmo se executado de fora
pasta_raiz = Path(__file__).resolve().parent.parent
if str(pasta_raiz) not in sys.path:
    sys.path.insert(0, str(pasta_raiz))

import pygame

from src.boletim import desenhar_boletim_pilotagem
from src.cenario_visual import (
    AVISO,
    DESTAQUE,
    FUNDO,
    PERIGO,
    desenhar_alerta_borda,
    desenhar_cenario_avenida,
    desenhar_ciclista,
    desenhar_marcos_percurso,
    desenhar_painel,
    desenhar_perigo_ponto_cego,
    desenhar_perigo_porta,
    desenhar_tela_instrucoes,
    desenhar_veiculo,
)
from src.ciclista import Ciclista
from src.comparacao import Comparacao, comparar
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
from src.metricas import RegistroDesempenho, ResumoDesempenho, resumir
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
        return f"{motivo_colisao} (B para Boletim)", PERIGO
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


def criar_partida() -> tuple[Ciclista, Percurso, GerenciadorPerigos, GerenciadorTrafego]:
    """Cria o estado inicial do percurso; usado ao abrir o jogo e ao reiniciar com R."""
    return Ciclista(), Percurso(), GerenciadorPerigos.criar_padrao(), GerenciadorTrafego()


def executar(jogador: str = "", pular_instrucoes: bool = False) -> None:
    registro = RegistroDesempenho(jogador=jogador)
    tentativa_encerrada = False
    pygame.display.init()
    pygame.font.init()
    try:
        tela = pygame.display.set_mode((LARGURA_JANELA, ALTURA_JANELA))
        pygame.display.set_caption("Dead Lane")
        relogio = pygame.time.Clock()
        ciclista, percurso, perigos, trafego = criar_partida()
        motivo_colisao: str | None = None
        tempo_total_s = 0.0
        feedback_seguro_s = 0.0
        area_ciclista = pygame.FRect(0, 0, LARGURA_COLISAO_CICLISTA, ALTURA_COLISAO_CICLISTA)
        area_ciclista.centery = CICLISTA_TELA_Y

        fonte_titulo = pygame.font.SysFont("Segoe UI", 42, bold=True)
        fonte_subtitulo = pygame.font.SysFont("Segoe UI", 24, bold=True)
        fonte_texto = pygame.font.SysFont("Segoe UI", 20)
        fonte_menor = pygame.font.SysFont("Segoe UI", 17, bold=True)
        fonte_velocidade = pygame.font.SysFont("Segoe UI", 64, bold=True)

        estado_jogo = "jogando" if pular_instrucoes else "instrucoes"
        modo_boletim = "fim"  # "pausa" ou "fim"
        resumo_boletim: ResumoDesempenho | None = None
        comparacoes_boletim: list[Comparacao] = []
        tempo_vitoria_boletim: float = 0.0
        botoes_boletim: dict[str, pygame.Rect] = {}

        def abrir_boletim(modo: str) -> None:
            nonlocal estado_jogo, modo_boletim, resumo_boletim, comparacoes_boletim, tempo_vitoria_boletim
            modo_boletim = modo
            if modo == "pausa":
                tentativa_atual = registro.tentativa
                regs = [r for r in registro.registros if r.tentativa == tentativa_atual]
                resumo_boletim = resumir(regs, colisoes_trafego=registro.colisoes_trafego)
                comparacoes_boletim = comparar(regs)
                tempo_vitoria_boletim = tempo_total_s
            else:
                tentativa_concluida = registro.tentativa - 1
                regs = [r for r in registro.registros if r.tentativa == tentativa_concluida]
                resumo_boletim = resumir(regs, colisoes_trafego=registro.colisoes_trafego)
                comparacoes_boletim = comparar(regs)
                tempo_vitoria_boletim = tempo_total_s
            estado_jogo = "boletim"

        while True:
            delta_s = min(relogio.tick(FPS_ALVO) / 1000, TEMPO_MAXIMO_QUADRO_S)
            if estado_jogo == "jogando":
                tempo_total_s += delta_s
            mouse_pos = pygame.mouse.get_pos()

            # -----------------------------------------------------------------
            # 1. PROCESSAMENTO DE EVENTOS
            # -----------------------------------------------------------------
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    return
                if evento.type == pygame.KEYDOWN:
                    if estado_jogo == "instrucoes":
                        if evento.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                            estado_jogo = "jogando"
                        elif evento.key == pygame.K_ESCAPE:
                            return
                    elif estado_jogo == "boletim":
                        if modo_boletim == "pausa":
                            # No modo pausa: retomar jogo
                            if evento.key in (pygame.K_SPACE, pygame.K_b, pygame.K_p, pygame.K_c, pygame.K_ESCAPE):
                                estado_jogo = "jogando"
                            elif evento.key == pygame.K_r:
                                if not tentativa_encerrada:
                                    registro.encerrar_tentativa()
                                tentativa_encerrada = False
                                ciclista, percurso, perigos, trafego = criar_partida()
                                motivo_colisao = None
                                feedback_seguro_s = 0.0
                                tempo_total_s = 0.0
                                estado_jogo = "jogando"
                            elif evento.key == pygame.K_q:
                                return
                        else:
                            # No modo fim de corrida: reiniciar ou sair
                            if evento.key in (pygame.K_r, pygame.K_RETURN, pygame.K_KP_ENTER):
                                if not tentativa_encerrada:
                                    registro.encerrar_tentativa()
                                tentativa_encerrada = False
                                ciclista, percurso, perigos, trafego = criar_partida()
                                motivo_colisao = None
                                feedback_seguro_s = 0.0
                                tempo_total_s = 0.0
                                estado_jogo = "jogando"
                            elif evento.key in (pygame.K_ESCAPE, pygame.K_q):
                                return
                    else:  # estado_jogo == "jogando"
                        if evento.key in (pygame.K_b, pygame.K_p, pygame.K_ESCAPE):
                            abrir_boletim("pausa")
                        elif evento.key in (pygame.K_h, pygame.K_i):
                            estado_jogo = "instrucoes"
                        elif evento.key == pygame.K_r:
                            if not tentativa_encerrada:
                                registro.encerrar_tentativa()
                            tentativa_encerrada = False
                            ciclista, percurso, perigos, trafego = criar_partida()
                            motivo_colisao = None
                            feedback_seguro_s = 0.0
                            tempo_total_s = 0.0
                elif evento.type == pygame.MOUSEBUTTONDOWN:
                    if estado_jogo == "instrucoes":
                        estado_jogo = "jogando"
                    elif estado_jogo == "boletim":
                        if modo_boletim == "pausa":
                            if botoes_boletim.get("continuar") and botoes_boletim["continuar"].collidepoint(mouse_pos):
                                estado_jogo = "jogando"
                            elif botoes_boletim.get("recomecar") and botoes_boletim["recomecar"].collidepoint(mouse_pos):
                                if not tentativa_encerrada:
                                    registro.encerrar_tentativa()
                                tentativa_encerrada = False
                                ciclista, percurso, perigos, trafego = criar_partida()
                                motivo_colisao = None
                                feedback_seguro_s = 0.0
                                tempo_total_s = 0.0
                                estado_jogo = "jogando"
                            elif botoes_boletim.get("sair") and botoes_boletim["sair"].collidepoint(mouse_pos):
                                return
                        else:
                            if botoes_boletim.get("jogar_novamente") and botoes_boletim["jogar_novamente"].collidepoint(mouse_pos):
                                if not tentativa_encerrada:
                                    registro.encerrar_tentativa()
                                tentativa_encerrada = False
                                ciclista, percurso, perigos, trafego = criar_partida()
                                motivo_colisao = None
                                feedback_seguro_s = 0.0
                                tempo_total_s = 0.0
                                estado_jogo = "jogando"
                            elif botoes_boletim.get("sair") and botoes_boletim["sair"].collidepoint(mouse_pos):
                                return

            # -----------------------------------------------------------------
            # 2. ATUALIZAÇÃO DA FÍSICA E REGRAS (SOMENTE EM MODO JOGANDO)
            # -----------------------------------------------------------------
            frear = False
            ciclista_no_ponto_cego = False
            ciclista_em_risco_porta = False

            if estado_jogo == "jogando":
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
                    zonas_sem_trafego = perigos.zonas_sem_trafego(ciclista.distancia_m)
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

                    porta_destaque = perigos.porta_em_destaque()
                    ciclista_em_risco_porta = (
                        porta_destaque is not None
                        and porta_destaque.ciclista_em_rota_de_colisao(
                            area_ciclista,
                            ciclista.distancia_m,
                            ciclista.velocidade_mps,
                        )
                    )

                    registro.atualizar(
                        tempo_total_s,
                        perigos,
                        area_ciclista,
                        ciclista.distancia_m,
                        ciclista.velocidade_mps,
                    )
                    colisao_perigo = perigos.verificar_colisao_detalhada(area_ciclista, ciclista.distancia_m)
                    if colisao_perigo is not None:
                        motivo_colisao, id_evento = colisao_perigo
                        registro.registrar_colisao(perigos, id_evento, motivo_colisao)
                        registro.encerrar_tentativa()
                        tentativa_encerrada = True
                    else:
                        for veiculo in trafego.veiculos:
                            if area_ciclista.colliderect(veiculo.area_colisao(ciclista.distancia_m)):
                                motivo_colisao = "Colisão com veículo na avenida. R para reiniciar."
                                registro.registrar_colisao_trafego()
                                registro.encerrar_tentativa()
                                tentativa_encerrada = True
                                break

                    # VERIFICAÇÃO DE CONCLUSÃO (LINHA DE CHEGADA): ABRE O BOLETIM IMEDIATAMENTE
                    if percurso.concluido:
                        registro.encerrar_tentativa(tempo_vitoria_s=tempo_total_s)
                        tentativa_encerrada = True
                        abrir_boletim("fim")

            # -----------------------------------------------------------------
            # 3. RENDERIZAÇÃO: CONTROLE TOTAL DO ESTADO
            # -----------------------------------------------------------------
            if estado_jogo == "instrucoes":
                desenhar_tela_instrucoes(
                    tela,
                    tempo_total_s,
                    fonte_titulo,
                    fonte_texto,
                    fonte_menor,
                    fonte_subtitulo,
                )
            elif estado_jogo == "boletim":
                botoes_boletim = desenhar_boletim_pilotagem(
                    tela,
                    resumo=resumo_boletim or registro.resumo(),
                    comparacoes=comparacoes_boletim,
                    tempo_percurso_s=tempo_vitoria_boletim,
                    jogador=jogador,
                    tempo_animacao_s=tempo_total_s,
                    mouse_pos=mouse_pos,
                    em_pausa=(modo_boletim == "pausa"),
                )
            else:
                tela.fill(FUNDO)
                desenhar_cenario_avenida(tela, ciclista.distancia_m, percurso.indice_trecho)
                desenhar_marcos_percurso(tela, ciclista.distancia_m, fonte_texto)
                for porta in perigos.portas:
                    desenhar_perigo_porta(tela, porta, ciclista.distancia_m, fonte_texto, tempo_total_s)
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

                porta_destaque = perigos.porta_em_destaque()
                ponto_cego_destaque = perigos.ponto_cego_em_destaque()
                em_risco_critico = (
                    ciclista_no_ponto_cego
                    or ciclista_em_risco_porta
                    or (ponto_cego_destaque is not None and ponto_cego_destaque.fase is FasePontoCego.ATIVO and ciclista_no_ponto_cego)
                )
                em_aviso_perigo = (
                    (ponto_cego_destaque is not None and ponto_cego_destaque.fase is FasePontoCego.AVISO)
                    or (porta_destaque is not None and porta_destaque.fase is FasePorta.AVISO)
                )
                desenhar_alerta_borda(tela, em_risco_critico, em_aviso_perigo, tempo_total_s)

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
        if not tentativa_encerrada:
            registro.encerrar_tentativa()
        pygame.quit()
        if registro.caminho_csv.exists():
            print(f"Resultados salvos em {registro.caminho_csv}")


def _ler_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dead Lane: serious game sobre percepção de riscos no trânsito.")
    parser.add_argument("--jogador", default="", help="nome ou código do participante, gravado nos resultados")
    parser.add_argument("--sem-instrucoes", action="store_true", help="inicia direto na partida pulando a tela de instruções")
    return parser.parse_args()


if __name__ == "__main__":
    args = _ler_argumentos()
    executar(args.jogador, pular_instrucoes=args.sem_instrucoes)
