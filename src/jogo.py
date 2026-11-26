from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Garante que a pasta dead-lane esteja no sys.path mesmo se executado de fora
pasta_raiz = Path(__file__).resolve().parent.parent
if str(pasta_raiz) not in sys.path:
    sys.path.insert(0, str(pasta_raiz))

import pygame

from src.assets import carregar_icone
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
    ESCALA_PISTA_PX_POR_M,
    FPS_ALVO,
    LARGURA_COLISAO_CICLISTA,
    LARGURA_JANELA,
    TEMPO_MAXIMO_QUADRO_S,
)
from src.metricas import RegistroDesempenho, ResumoDesempenho, resumir
from src.percurso import Percurso
from src.perigos import FasePontoCego, FasePorta, GerenciadorPerigos
from src.som import GerenciadorSom
from src.trafego import GerenciadorTrafego


def _obter_mensagem_status(
    motivo_colisao: str | None,
    percurso: Percurso,
    perigos: GerenciadorPerigos,
    distancia_ciclista_m: float,
    ciclista_no_ponto_cego: bool,
    feedback_seguro_s: float,
    feedback_texto: str = "Saiu do ponto cego com segurança!",
) -> tuple[str, str] | None:
    if motivo_colisao:
        return f"{motivo_colisao} (B para Resultados)", PERIGO
    if percurso.concluido:
        return "Vitória! Percurso concluído.", DESTAQUE
    if percurso.intervalo_restante_s > 0.0:
        return f"Checkpoint {percurso.indice_trecho} · Proteção ({percurso.intervalo_restante_s:.1f} s)", DESTAQUE

    ponto_cego = perigos.ponto_cego_em_destaque(distancia_ciclista_m)
    if ponto_cego is not None:
        if ponto_cego.fase is FasePontoCego.ATIVO:
            return f"Ônibus fechando à {ponto_cego.lado}! Afaste-se.", PERIGO
        if ciclista_no_ponto_cego:
            return "Você está no ponto cego! Freie para sair.", PERIGO
        return "Ponto cego do ônibus. Freie ou desvie.", AVISO

    porta = perigos.porta_em_destaque(distancia_ciclista_m)
    if porta is not None:
        if porta.fase is FasePorta.ABERTA:
            return f"Porta aberta na faixa {porta.lado}!", PERIGO
        return f"Aviso de porta à {porta.lado}. Freie ou mude de faixa.", AVISO

    if feedback_seguro_s > 0.0:
        return feedback_texto, DESTAQUE
    return None


def _piloto_em_risco_iminente(
    ciclista: Ciclista,
    area_ciclista: pygame.FRect,
    perigos: GerenciadorPerigos,
    trafego: GerenciadorTrafego,
) -> bool:
    """Verifica se há risco imediato (porta, ponto cego ou fechada/traseira de veículo) para validar o parry do Dash."""
    area_ciclista.centerx = ciclista.x
    if perigos.em_risco_iminente(area_ciclista, ciclista.distancia_m, ciclista.velocidade_mps):
        return True

    meia_alt_piloto_m = (ALTURA_COLISAO_CICLISTA * 0.5) / ESCALA_PISTA_PX_POR_M
    for v in [*trafego.veiculos, *perigos.onibus_ativos(ciclista.distancia_m)]:
        folga_frente_m = (v.distancia_m - v.comprimento_m * 0.5) - (ciclista.distancia_m + meia_alt_piloto_m)
        alinhado_lateral = abs(v.x - ciclista.x) <= (v.largura + LARGURA_COLISAO_CICLISTA) * 0.5 + 8.0
        vel_rel = ciclista.velocidade_mps - v.velocidade_mps
        if alinhado_lateral and 0.0 <= folga_frente_m <= 6.5:
            if folga_frente_m <= 2.4 or (vel_rel > 0.5 and folga_frente_m / vel_rel <= 1.25):
                return True
        if (
            v.seta_direcao != 0
            and abs(v.distancia_m - ciclista.distancia_m) <= v.comprimento_m * 0.5 + meia_alt_piloto_m + 1.5
            and abs(v.x - ciclista.x) <= (v.largura + LARGURA_COLISAO_CICLISTA) * 0.5 + 42.0
            and v.seta_direcao * (ciclista.x - v.x) > 0
        ):
            return True
    return False


def criar_partida(*, aleatorio: bool = False) -> tuple[Ciclista, Percurso, GerenciadorPerigos, GerenciadorTrafego]:
    """Cria o estado inicial do percurso; usado ao abrir o jogo e ao reiniciar com R."""
    return (
        Ciclista(),
        Percurso(),
        GerenciadorPerigos.criar_padrao(aleatorio=aleatorio),
        GerenciadorTrafego(aleatorio=aleatorio),
    )


def executar(jogador: str = "", pular_instrucoes: bool = False) -> None:
    registro = RegistroDesempenho(jogador=jogador)
    tentativa_encerrada = False
    pygame.display.init()
    pygame.font.init()
    try:
        tela = pygame.display.set_mode((LARGURA_JANELA, ALTURA_JANELA))
        pygame.display.set_caption("Dead Lane")
        pygame.display.set_icon(carregar_icone("icone_jogo"))
        relogio = pygame.time.Clock()
        som = GerenciadorSom()
        ciclista, percurso, perigos, trafego = criar_partida(aleatorio=True)
        motivo_colisao: str | None = None
        tempo_total_s = 0.0
        feedback_seguro_s = 0.0
        feedback_texto = "Saiu do ponto cego com segurança!"
        ultimo_alerta_sonoro = ""
        ultimo_trecho_sonoro = 0
        veiculos_sonoros: set[int] = set()
        area_ciclista = pygame.FRect(0, 0, LARGURA_COLISAO_CICLISTA, ALTURA_COLISAO_CICLISTA)
        area_ciclista.centery = CICLISTA_TELA_Y
        area_ciclista.centerx = ciclista.x

        fonte_titulo = pygame.font.SysFont("Bahnschrift", 44, bold=True)
        fonte_subtitulo = pygame.font.SysFont("Bahnschrift", 24, bold=True)
        fonte_texto = pygame.font.SysFont("Bahnschrift", 19)
        fonte_menor = pygame.font.SysFont("Bahnschrift", 17, bold=True)
        fonte_velocidade = pygame.font.SysFont("Bahnschrift", 64, bold=True)

        estado_jogo = "jogando" if pular_instrucoes else "instrucoes"
        modo_boletim = "fim"  # "pausa" ou "fim"
        derrota_boletim = False
        resumo_boletim: ResumoDesempenho | None = None
        comparacoes_boletim: list[Comparacao] = []
        tempo_vitoria_boletim: float = 0.0
        parries_boletim: int = 0
        botoes_boletim: dict[str, pygame.Rect] = {}

        def reiniciar_partida() -> None:
            nonlocal tentativa_encerrada, ciclista, percurso, perigos, trafego
            nonlocal motivo_colisao, feedback_seguro_s, tempo_total_s
            nonlocal ultimo_alerta_sonoro, ultimo_trecho_sonoro, estado_jogo
            if not tentativa_encerrada:
                registro.encerrar_tentativa()
            tentativa_encerrada = False
            ciclista, percurso, perigos, trafego = criar_partida(aleatorio=True)
            area_ciclista.centerx = ciclista.x
            motivo_colisao = None
            feedback_seguro_s = 0.0
            tempo_total_s = 0.0
            ultimo_alerta_sonoro = ""
            ultimo_trecho_sonoro = 0
            veiculos_sonoros.clear()
            estado_jogo = "jogando"

        def abrir_boletim(modo: str, *, derrota: bool = False) -> None:
            nonlocal estado_jogo, modo_boletim, derrota_boletim, resumo_boletim
            nonlocal comparacoes_boletim, tempo_vitoria_boletim, parries_boletim
            modo_boletim = modo
            derrota_boletim = derrota
            if modo == "pausa" and not tentativa_encerrada:
                tentativa_alvo = registro.tentativa
            else:
                tentativa_alvo = registro.tentativa - 1
            regs = [r for r in registro.registros if r.tentativa == tentativa_alvo]
            resumo_boletim = resumir(
                regs,
                colisoes_trafego=registro.colisoes_trafego_da_tentativa(tentativa_alvo),
            )
            comparacoes_boletim = comparar(regs)
            tempo_vitoria_boletim = tempo_total_s
            parries_boletim = ciclista.parries_realizados
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
                                reiniciar_partida()
                            elif evento.key == pygame.K_q:
                                return
                        else:
                            # No modo fim de corrida: reiniciar ou sair
                            if evento.key in (pygame.K_r, pygame.K_RETURN, pygame.K_KP_ENTER):
                                reiniciar_partida()
                            elif evento.key in (pygame.K_ESCAPE, pygame.K_q):
                                return
                    else:  # estado_jogo == "jogando"
                        if evento.key in (pygame.K_b, pygame.K_p, pygame.K_ESCAPE):
                            abrir_boletim("pausa")
                        elif evento.key == pygame.K_SPACE:
                            teclas_agora = pygame.key.get_pressed()
                            dir_dash = int(teclas_agora[pygame.K_d] or teclas_agora[pygame.K_RIGHT]) - int(
                                teclas_agora[pygame.K_a] or teclas_agora[pygame.K_LEFT]
                            )
                            em_risco_dash = _piloto_em_risco_iminente(ciclista, area_ciclista, perigos, trafego)
                            if ciclista.acionar_dash(dir_dash, em_risco=em_risco_dash):
                                som.tocar_dash()
                        elif evento.key in (pygame.K_h, pygame.K_i):
                            estado_jogo = "instrucoes"
                        elif evento.key == pygame.K_r:
                            reiniciar_partida()
                elif evento.type == pygame.MOUSEBUTTONDOWN:
                    if estado_jogo == "instrucoes":
                        estado_jogo = "jogando"
                    elif estado_jogo == "boletim":
                        if modo_boletim == "pausa":
                            if botoes_boletim.get("continuar") and botoes_boletim["continuar"].collidepoint(mouse_pos):
                                estado_jogo = "jogando"
                            elif botoes_boletim.get("recomecar") and botoes_boletim["recomecar"].collidepoint(mouse_pos):
                                reiniciar_partida()
                            elif botoes_boletim.get("sair") and botoes_boletim["sair"].collidepoint(mouse_pos):
                                return
                        else:
                            if botoes_boletim.get("jogar_novamente") and botoes_boletim["jogar_novamente"].collidepoint(mouse_pos):
                                reiniciar_partida()
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
                    protegido_checkpoint = percurso.intervalo_restante_s > 0.0
                    perigos.atualizar(
                        delta_s,
                        ciclista.distancia_m,
                        area_ciclista,
                        permitir_aviso=percurso.pode_iniciar_perigo,
                        velocidade_mps=ciclista.velocidade_mps,
                    )

                    onibus_perigo = perigos.onibus_ativos(ciclista.distancia_m)
                    for v_som in [*trafego.veiculos, *onibus_perigo]:
                        vid = id(v_som)
                        dist_v = v_som.distancia_m - ciclista.distancia_m
                        if -2.0 <= dist_v <= 24.0 and vid not in veiculos_sonoros:
                            veiculos_sonoros.add(vid)
                            som.tocar_passagem_veiculo(eh_onibus=(v_som.tipo.name == "ONIBUS"))
                        elif dist_v < -10.0 and vid in veiculos_sonoros:
                            veiculos_sonoros.discard(vid)
                    zonas_bloqueadas = perigos.zonas_bloqueadas_faixa_direita(ciclista.distancia_m)
                    zonas_bloqueadas_esq = perigos.zonas_bloqueadas_faixa_esquerda(ciclista.distancia_m)
                    zonas_sem_trafego = perigos.zonas_sem_trafego(ciclista.distancia_m)
                    trafego.atualizar(
                        delta_s,
                        ciclista.distancia_m,
                        zonas_bloqueadas=zonas_bloqueadas,
                        zonas_bloqueadas_esquerda=zonas_bloqueadas_esq,
                        veiculos_externos=onibus_perigo,
                        indice_trecho=percurso.indice_trecho,
                        zonas_sem_trafego=zonas_sem_trafego,
                        pausar_spawn=protegido_checkpoint,
                    )

                    if percurso.indice_trecho > ultimo_trecho_sonoro:
                        ultimo_trecho_sonoro = percurso.indice_trecho
                        som.tocar_vitoria()

                    ponto_cego_destaque = perigos.ponto_cego_em_destaque(ciclista.distancia_m)
                    ciclista_no_ponto_cego = (
                        ponto_cego_destaque is not None
                        and ponto_cego_destaque.ciclista_na_zona(area_ciclista, ciclista.distancia_m)
                    )

                    porta_destaque = perigos.porta_em_destaque(ciclista.distancia_m)
                    if ponto_cego_destaque is not None and ponto_cego_destaque.fase is FasePontoCego.AVISO:
                        if ultimo_alerta_sonoro != ponto_cego_destaque.id_evento:
                            ultimo_alerta_sonoro = ponto_cego_destaque.id_evento
                            som.tocar_alerta()
                    elif porta_destaque is not None and porta_destaque.fase is FasePorta.AVISO:
                        if ultimo_alerta_sonoro != porta_destaque.id_evento:
                            ultimo_alerta_sonoro = porta_destaque.id_evento
                            som.tocar_alerta()
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
                    if not protegido_checkpoint:
                        colisao_perigo = perigos.verificar_colisao_detalhada(area_ciclista, ciclista.distancia_m)
                        if colisao_perigo is not None:
                            motivo_colisao, id_evento = colisao_perigo
                            som.tocar_colisao()
                            registro.registrar_colisao(perigos, id_evento, motivo_colisao)
                            registro.encerrar_tentativa()
                            tentativa_encerrada = True
                            abrir_boletim("fim", derrota=True)
                        else:
                            for veiculo in trafego.veiculos:
                                if area_ciclista.colliderect(veiculo.area_colisao(ciclista.distancia_m)):
                                    motivo_colisao = "Colisão com veículo na avenida."
                                    som.tocar_colisao()
                                    registro.registrar_colisao_trafego()
                                    registro.encerrar_tentativa()
                                    tentativa_encerrada = True
                                    abrir_boletim("fim", derrota=True)
                                    break

                    if motivo_colisao is None:
                        # Valida o parry somente depois de confirmar que o piloto sobreviveu e saiu do risco.
                        if ciclista.dash_parry_pendente:
                            ainda_em_risco = _piloto_em_risco_iminente(ciclista, area_ciclista, perigos, trafego)
                            ciclista.resolver_parry_dash(ainda_em_risco=ainda_em_risco)

                        saiu_pc = perigos.consumir_feedback_seguro() is not None
                        ganhou_parry = ciclista.consumir_bonus_dash()
                        if ganhou_parry:
                            feedback_texto = "Escapada no limite! Bônus de Dash"
                            feedback_seguro_s = 1.8
                            som.tocar_vitoria()
                        elif saiu_pc:
                            feedback_texto = "Saiu do ponto cego com segurança!"
                            feedback_seguro_s = 1.6
                        else:
                            feedback_seguro_s = max(0.0, feedback_seguro_s - delta_s)

                    # VERIFICAÇÃO DE CONCLUSÃO (LINHA DE CHEGADA): ABRE O BOLETIM IMEDIATAMENTE
                    if percurso.concluido and not tentativa_encerrada:
                        som.tocar_vitoria()
                        registro.encerrar_tentativa(tempo_vitoria_s=tempo_total_s)
                        tentativa_encerrada = True
                        abrir_boletim("fim", derrota=False)

            som.atualizar_ambiente(delta_s, estado_jogo == "jogando" and motivo_colisao is None and not percurso.concluido)

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
                    resumo=resumo_boletim or registro.resumo(apenas_tentativa_atual=True),
                    comparacoes=comparacoes_boletim,
                    tempo_percurso_s=tempo_vitoria_boletim,
                    jogador=jogador,
                    tempo_animacao_s=tempo_total_s,
                    mouse_pos=mouse_pos,
                    em_pausa=(modo_boletim == "pausa"),
                    derrota=derrota_boletim,
                    parries_dash=parries_boletim,
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
                desenhar_ciclista(
                    tela,
                    ciclista,
                    frear,
                    protecao_s=percurso.intervalo_restante_s,
                    tempo_s=tempo_total_s,
                )

                porta_destaque = perigos.porta_em_destaque(ciclista.distancia_m)
                ponto_cego_destaque = perigos.ponto_cego_em_destaque(ciclista.distancia_m)
                em_risco_critico = percurso.intervalo_restante_s == 0.0 and (
                    ciclista_no_ponto_cego
                    or ciclista_em_risco_porta
                    or (ponto_cego_destaque is not None and ponto_cego_destaque.fase is FasePontoCego.ATIVO and ciclista_no_ponto_cego)
                )
                em_aviso_perigo = percurso.intervalo_restante_s == 0.0 and (
                    (ponto_cego_destaque is not None and ponto_cego_destaque.fase is FasePontoCego.AVISO)
                    or (porta_destaque is not None and porta_destaque.fase is FasePorta.AVISO)
                )
                desenhar_alerta_borda(tela, em_risco_critico, em_aviso_perigo, tempo_total_s)

                mensagem_status = _obter_mensagem_status(
                    motivo_colisao,
                    percurso,
                    perigos,
                    ciclista.distancia_m,
                    ciclista_no_ponto_cego,
                    feedback_seguro_s,
                    feedback_texto,
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
