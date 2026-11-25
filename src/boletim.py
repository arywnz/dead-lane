"""Tela de Boletim de Pilotagem: apresenta métricas de telemetria, patente/rank,
comparativo de evolução (início vs. fim) e diagnóstico pedagógico personalizado.
"""

from dataclasses import dataclass
import math
import pygame

from src.assets import carregar_icone
from src.comparacao import Comparacao, DesempenhoSituacao
from src.metricas import RegistroPerigo, ResultadoPerigo, ResumoDesempenho, resumir

# Cores da interface alinhadas à paleta de Dead Lane
FUNDO = "#121d1b"
ASFALTO = "#242c2d"
BORDA_PISTA = "#465451"
PAINEL = "#1b2824"
TEXTO_PRINCIPAL = "#edf1e6"
TEXTO_SECUNDARIO = "#aebdb4"
DESTAQUE = "#d8f975"
AVISO = "#ffcf70"
PERIGO = "#ff786f"
AZUL_CIANO = "#a5f3fc"
VERDE_ESMERALDA = "#6ee7b7"


@dataclass(frozen=True)
class PatenteDesempenho:
    rank: str
    titulo: str
    descricao: str
    cor: str
    pontuacao: int
    taxa_antecipacao: float


def calcular_patente(resumo: ResumoDesempenho) -> PatenteDesempenho:
    """Calcula a patente e rank (S, A, B, C) com base no desempenho defensivo."""
    total = resumo.total_perigos
    taxa_antecipacao = resumo.antecipacoes / total if total > 0 else 1.0
    total_colisoes = resumo.falhas + resumo.colisoes_trafego

    # Pontuação geral de 0 a 100
    pontos = 100
    pontos -= total_colisoes * 25
    pontos -= resumo.reacoes_tardias * 4
    pontuacao = max(0, min(100, pontos))

    # Regras de Rank
    if total_colisoes == 0 and taxa_antecipacao >= 0.85:
        rank = "S"
        titulo = "Especialista em Pilotagem Defensiva"
        descricao = "Excelente visão periférica! Você antecipou todas as ameaças antes que se tornassem críticas."
        cor = DESTAQUE
    elif total_colisoes == 0 and taxa_antecipacao >= 0.65:
        rank = "A"
        titulo = "Ciclista Defensivo Consciente"
        descricao = "Ótima conduta preventiva. Quase todos os riscos foram desarmados com antecedência e sem colisões."
        cor = VERDE_ESMERALDA
    elif total_colisoes <= 2 and taxa_antecipacao >= 0.40:
        rank = "B"
        titulo = "Ciclista em Desenvolvimento"
        descricao = "Bom domínio básico, mas com reações tardias que quase causaram incidentes em trechos movimentados."
        cor = AVISO
    else:
        rank = "C"
        titulo = "Piloto em Zona de Risco"
        descricao = "Postura vulnerável no trânsito. Muitas tomadas de decisão foram tardias ou resultaram em colisões."
        cor = PERIGO

    return PatenteDesempenho(
        rank=rank,
        titulo=titulo,
        descricao=descricao,
        cor=cor,
        pontuacao=pontuacao,
        taxa_antecipacao=taxa_antecipacao,
    )


def gerar_dica_personalizada(resumo: ResumoDesempenho) -> str:
    """Gera uma dica pedagógica direcionada a partir do tipo de erro mais comum."""
    if resumo.erro_mais_comum == "porta":
        return (
            "Dica Defensiva (Portas de Carros): Seu maior desafio foi o 'dooring'. "
            "Ao pedalar na faixa direita, mantenha pelo menos 1 metro de distância dos carros estacionados. "
            "Ao avistar o pisca-alerta ou a área hachurada na pista, mude preventivamente para a faixa central ou freie!"
        )
    if resumo.erro_mais_comum == "ponto_cego":
        return (
            "Dica Defensiva (Ponto Cego de Ônibus): Seu maior perigo foram os 'Angles Morts' de veículos pesados. "
            "Lembre-se: se você não vê os retrovisores do motorista, ele não vê você! "
            "Nunca permaneça na zona lateral demarcada quando o ônibus acionar a seta: freie imediatamente para ficar atrás ou ultrapasse com folga pela esquerda."
        )
    if resumo.colisoes_trafego > 0:
        return (
            "Dica de Fluxo e Espaçamento: Cuidado com os veículos à frente na avenida. "
            "Mantenha distância de seguimento e dose a aceleração com a tecla de freio (S / ↓) para antecipar paradas bruscas do trânsito."
        )
    if resumo.reacoes_tardias > 0:
        return (
            "Dica de Antecipação: Você conseguiu evitar colisões, mas agiu em cima da hora. "
            "Ao notar os alertas visuais (pisca do carro, setas do ônibus ou brilho da borda da tela), "
            "tome sua decisão imediatamente para não depender de reflexos de emergência."
        )
    return (
        "Dica de Excelência: Pilotagem impecável! Você previu todos os perigos urbanos com maestria e tempo de resposta zero. "
        "Continue aplicando essa postura defensiva preventiva na vida real pedalando sempre com atenção às zonas de risco."
    )


def desenhar_boletim_pilotagem(
    tela: pygame.Surface,
    resumo: ResumoDesempenho,
    comparacoes: list[Comparacao],
    tempo_percurso_s: float,
    jogador: str,
    tempo_animacao_s: float = 0.0,
    mouse_pos: tuple[int, int] = (0, 0),
    em_pausa: bool = False,
) -> dict[str, pygame.Rect]:
    """Renderiza a tela completa de Boletim de Pilotagem e retorna os botões clicáveis."""
    tela.fill(FUNDO)

    # Detalhes visuais de pista no fundo
    pygame.draw.rect(tela, ASFALTO, (0, 0, 1280, 10))
    pygame.draw.rect(tela, ASFALTO, (0, 710, 1280, 10))

    # Fontes do boletim
    fonte_titulo = pygame.font.SysFont("Segoe UI", 36, bold=True)
    fonte_subtitulo = pygame.font.SysFont("Segoe UI", 22, bold=True)
    fonte_secao = pygame.font.SysFont("Segoe UI", 18, bold=True)
    fonte_texto = pygame.font.SysFont("Segoe UI", 16)
    fonte_menor = pygame.font.SysFont("Segoe UI", 14)
    fonte_rank = pygame.font.SysFont("Segoe UI", 72, bold=True)
    fonte_numero = pygame.font.SysFont("Segoe UI", 36, bold=True)

    # 1. CABEÇALHO
    cx = 640
    titulo_texto = "CORRIDA PAUSADA · BOLETIM DE PILOTAGEM" if em_pausa else "BOLETIM DE PILOTAGEM DEFENSIVA"
    titulo = fonte_titulo.render(titulo_texto, True, AVISO if em_pausa else DESTAQUE)
    tela.blit(titulo, (cx - titulo.get_width() // 2, 22))

    nome_jogador = f"Ciclista: {jogador}" if jogador else "Ciclista Defensivo"
    tempo_fmt = f"{tempo_percurso_s:.1f} s"
    if em_pausa:
        info_cabecalho = f"Jogo Pausado · {nome_jogador} · Tempo Decorrido: {tempo_fmt} · Telemetria em Tempo Real"
    else:
        info_cabecalho = f"Percurso Urbano Concluído · {nome_jogador} · Tempo Total: {tempo_fmt}"
    sub = fonte_menor.render(info_cabecalho, True, TEXTO_SECUNDARIO)
    tela.blit(sub, (cx - sub.get_width() // 2, 66))

    # 2. CÁLCULO DA PATENTE
    patente = calcular_patente(resumo)

    # 3. LINHA SUPERIOR: CARD DO RANK (ESQUERDA) E 4 MÉTRICAS (DIREITA)
    y_linha1 = 96

    # --- CARD DO RANK / PATENTE ---
    card_rank = pygame.Rect(60, y_linha1, 350, 240)
    pygame.draw.rect(tela, PAINEL, card_rank, border_radius=18)
    pygame.draw.rect(tela, patente.cor, card_rank, width=2, border_radius=18)

    # Letra do Rank em destaque com brilho
    badge_rank = pygame.Rect(card_rank.x + 24, card_rank.y + 24, 90, 90)
    pygame.draw.rect(tela, "#16221f", badge_rank, border_radius=14)
    pygame.draw.rect(tela, patente.cor, badge_rank, width=2, border_radius=14)
    letra_render = fonte_rank.render(patente.rank, True, patente.cor)
    tela.blit(letra_render, (badge_rank.centerx - letra_render.get_width() // 2, badge_rank.centery - letra_render.get_height() // 2 - 2))

    # Título da Patente e Pontuação
    tela.blit(fonte_secao.render("Classificação Geral", True, TEXTO_SECUNDARIO), (card_rank.x + 126, card_rank.y + 24))
    nome_patente = fonte_secao.render(patente.titulo, True, patente.cor)
    if nome_patente.get_width() > card_rank.width - 138:
        nome_patente = pygame.transform.smoothscale(nome_patente, (card_rank.width - 138, 18))
    tela.blit(nome_patente, (card_rank.x + 126, card_rank.y + 50))

    score_txt = f"Nota: {patente.pontuacao} / 100"
    score_render = fonte_subtitulo.render(score_txt, True, TEXTO_PRINCIPAL)
    tela.blit(score_render, (card_rank.x + 126, card_rank.y + 78))

    pygame.draw.line(tela, BORDA_PISTA, (card_rank.x + 20, card_rank.y + 128), (card_rank.right - 20, card_rank.y + 128), 1)

    # Descrição da patente
    desc_render = fonte_texto.render(patente.descricao, True, TEXTO_SECUNDARIO)
    if desc_render.get_width() > card_rank.width - 40:
        desc_render = pygame.transform.smoothscale(desc_render, (card_rank.width - 40, 16))
    tela.blit(desc_render, (card_rank.x + 20, card_rank.y + 142))

    # Barra visual de índice de antecipação
    rotulo_barra = fonte_menor.render(f"Índice de Antecipação: {patente.taxa_antecipacao * 100:.0f}%", True, TEXTO_PRINCIPAL)
    tela.blit(rotulo_barra, (card_rank.x + 20, card_rank.y + 176))
    pygame.draw.rect(tela, BORDA_PISTA, (card_rank.x + 20, card_rank.y + 202, card_rank.width - 40, 10), border_radius=5)
    larg_progresso = round((card_rank.width - 40) * patente.taxa_antecipacao)
    if larg_progresso > 0:
        pygame.draw.rect(tela, patente.cor, (card_rank.x + 20, card_rank.y + 202, larg_progresso, 10), border_radius=5)

    # --- 4 CARDS DE TELEMETRIA ---
    x_metricas = 430
    larg_col_metrica = 190
    espaco_col = 16
    altura_metrica = 240

    metricas_cards = (
        ("Antecipações", str(resumo.antecipacoes), DESTAQUE, "Resolvidos no aviso", "Decisões seguras e preventivas"),
        ("Reações Tardias", str(resumo.reacoes_tardias), AVISO, "Resolvidos no susto", "Ações evasivas de última hora"),
        ("Falhas / Colisões", str(resumo.falhas + resumo.colisoes_trafego), PERIGO, "Incidentes na via", "Batidas em portas ou tráfego"),
        (
            "Tempo de Resposta",
            f"{resumo.tempo_medio_resposta_s:.2f} s" if resumo.tempo_medio_resposta_s is not None else "0.00 s",
            AZUL_CIANO,
            "Média até a saída",
            "Tempo médio de reação",
        ),
    )

    for idx, (titulo_m, valor_m, cor_m, sub1, sub2) in enumerate(metricas_cards):
        xm = x_metricas + idx * (larg_col_metrica + espaco_col)
        card_m = pygame.Rect(xm, y_linha1, larg_col_metrica, altura_metrica)
        pygame.draw.rect(tela, PAINEL, card_m, border_radius=18)
        pygame.draw.rect(tela, "#283b35", card_m, width=2, border_radius=18)

        # Barra colorida superior
        pygame.draw.rect(tela, cor_m, (card_m.x + 18, card_m.y + 14, 28, 4), border_radius=2)

        # Título da métrica
        tm = fonte_menor.render(titulo_m, True, TEXTO_SECUNDARIO)
        tela.blit(tm, (card_m.x + 18, card_m.y + 28))

        # Valor numérico em tamanho grande
        vm = fonte_numero.render(valor_m, True, cor_m)
        tela.blit(vm, (card_m.x + 18, card_m.y + 60))

        pygame.draw.line(tela, "#263531", (card_m.x + 16, card_m.y + 120), (card_m.right - 16, card_m.y + 120), 1)

        # Legendas explicativas
        s1 = fonte_menor.render(sub1, True, TEXTO_PRINCIPAL)
        tela.blit(s1, (card_m.x + 16, card_m.y + 138))

        s2 = fonte_menor.render(sub2, True, TEXTO_SECUNDARIO)
        if s2.get_width() > card_m.width - 32:
            s2 = pygame.transform.smoothscale(s2, (card_m.width - 32, 13))
        tela.blit(s2, (card_m.x + 16, card_m.y + 164))

    # 4. LINHA INFERIOR: COMPARATIVO INÍCIO VS. FIM (ESQUERDA) E DICA PERSONALIZADA (DIREITA)
    y_linha2 = 356

    # --- CARD COMPARATIVO DE EVOLUÇÃO ---
    card_comp = pygame.Rect(60, y_linha2, 570, 240)
    pygame.draw.rect(tela, PAINEL, card_comp, border_radius=18)
    pygame.draw.rect(tela, "#283b35", card_comp, width=2, border_radius=18)

    tela.blit(fonte_secao.render("Evolução: Início vs. Fim da Fase", True, TEXTO_PRINCIPAL), (card_comp.x + 22, card_comp.y + 16))
    tela.blit(
        fonte_menor.render("Compara situações idênticas no Trecho 1 (Manhã) e Trecho 3 (Rush):", True, TEXTO_SECUNDARIO),
        (card_comp.x + 22, card_comp.y + 42),
    )
    pygame.draw.line(tela, BORDA_PISTA, (card_comp.x + 22, card_comp.y + 66), (card_comp.right - 22, card_comp.y + 66), 1)

    # Extrai as comparações de porta e ponto cego
    comp_porta = next((c for c in comparacoes if c.tipo == "porta"), None)
    comp_ponto_cego = next((c for c in comparacoes if c.tipo == "ponto_cego"), None)

    def formatar_desempenho(desemp: DesempenhoSituacao) -> tuple[str, str]:
        if desemp.falhas > 0:
            return "Falha (Colisão)", PERIGO
        if desemp.antecipacoes > 0:
            tempo = f" ({desemp.tempo_medio_resposta_s:.2f} s)" if desemp.tempo_medio_resposta_s is not None else ""
            return f"Antecipação{tempo}", DESTAQUE
        if desemp.reacoes_tardias > 0:
            tempo = f" ({desemp.tempo_medio_resposta_s:.2f} s)" if desemp.tempo_medio_resposta_s is not None else ""
            return f"Reação Tardia{tempo}", AVISO
        return "Sem dados", TEXTO_SECUNDARIO

    def formatar_tendencia(tend: str) -> tuple[str, str]:
        if tend == "melhorou":
            return "Melhorou ▲", DESTAQUE
        if tend == "piorou":
            return "Piorou ▼", PERIGO
        if tend == "igual":
            return "Constante ▬", TEXTO_PRINCIPAL
        return "Sem dados", TEXTO_SECUNDARIO

    # Linha Perigo de Porta
    y_cp = card_comp.y + 80
    tela.blit(carregar_icone("icone_porta"), (card_comp.x + 20, y_cp))
    tela.blit(fonte_secao.render("Porta de Carro Estacionado", True, TEXTO_PRINCIPAL), (card_comp.x + 76, y_cp + 2))

    if comp_porta is not None:
        txt_ini, cor_ini = formatar_desempenho(comp_porta.inicio)
        txt_fim, cor_fim = formatar_desempenho(comp_porta.fim)
        txt_tend, cor_tend = formatar_tendencia(comp_porta.tendencia)

        tela.blit(fonte_menor.render(f"Início (Trecho 1): {txt_ini}", True, cor_ini), (card_comp.x + 76, y_cp + 24))
        tela.blit(fonte_menor.render(f"Fim (Trecho 3): {txt_fim}", True, cor_fim), (card_comp.x + 76, y_cp + 42))

        # Badge de tendência
        badge_tend = pygame.Rect(card_comp.right - 145, y_cp + 12, 125, 28)
        pygame.draw.rect(tela, "#16221f", badge_tend, border_radius=6)
        pygame.draw.rect(tela, cor_tend, badge_tend, width=1, border_radius=6)
        lbl_tend = fonte_menor.render(txt_tend, True, cor_tend)
        tela.blit(lbl_tend, (badge_tend.centerx - lbl_tend.get_width() // 2, badge_tend.centery - lbl_tend.get_height() // 2))

    pygame.draw.line(tela, "#263531", (card_comp.x + 22, card_comp.y + 152), (card_comp.right - 22, card_comp.y + 152), 1)

    # Linha Ponto Cego de Ônibus
    y_pc = card_comp.y + 164
    tela.blit(carregar_icone("icone_ponto_cego"), (card_comp.x + 20, y_pc))
    tela.blit(fonte_secao.render("Ponto Cego do Ônibus (Angles Morts)", True, TEXTO_PRINCIPAL), (card_comp.x + 76, y_pc + 2))

    if comp_ponto_cego is not None:
        txt_ini_pc, cor_ini_pc = formatar_desempenho(comp_ponto_cego.inicio)
        txt_fim_pc, cor_fim_pc = formatar_desempenho(comp_ponto_cego.fim)
        txt_tend_pc, cor_tend_pc = formatar_tendencia(comp_ponto_cego.tendencia)

        tela.blit(fonte_menor.render(f"Início (Trecho 1): {txt_ini_pc}", True, cor_ini_pc), (card_comp.x + 76, y_pc + 24))
        tela.blit(fonte_menor.render(f"Fim (Trecho 3): {txt_fim_pc}", True, cor_fim_pc), (card_comp.x + 76, y_pc + 42))

        badge_tend_pc = pygame.Rect(card_comp.right - 145, y_pc + 12, 125, 28)
        pygame.draw.rect(tela, "#16221f", badge_tend_pc, border_radius=6)
        pygame.draw.rect(tela, cor_tend_pc, badge_tend_pc, width=1, border_radius=6)
        lbl_tend_pc = fonte_menor.render(txt_tend_pc, True, cor_tend_pc)
        tela.blit(lbl_tend_pc, (badge_tend_pc.centerx - lbl_tend_pc.get_width() // 2, badge_tend_pc.centery - lbl_tend_pc.get_height() // 2))

    # --- CARD DICA PERSONALIZADA ---
    card_dica = pygame.Rect(650, y_linha2, 570, 240)
    pygame.draw.rect(tela, PAINEL, card_dica, border_radius=18)
    pygame.draw.rect(tela, "#283b35", card_dica, width=2, border_radius=18)

    tela.blit(fonte_secao.render("Diagnóstico Pedagógico Personalizado", True, TEXTO_PRINCIPAL), (card_dica.x + 22, card_dica.y + 16))
    tela.blit(fonte_menor.render("Feedback gerado com base no seu padrão de erros nesta partida:", True, TEXTO_SECUNDARIO), (card_dica.x + 22, card_dica.y + 42))
    pygame.draw.line(tela, BORDA_PISTA, (card_dica.x + 22, card_dica.y + 66), (card_dica.right - 22, card_dica.y + 66), 1)

    # Texto da dica formatado em bloco acolchoado
    dica_texto = gerar_dica_personalizada(resumo)
    caixa_dica = pygame.Rect(card_dica.x + 20, card_dica.y + 80, card_dica.width - 40, 140)
    pygame.draw.rect(tela, "#152420", caixa_dica, border_radius=12)
    pygame.draw.rect(tela, "#2a3d36", caixa_dica, width=1, border_radius=12)

    # Quebra de linhas suave para a dica
    palavras = dica_texto.split(" ")
    linhas_dica: list[str] = []
    linha_atual = ""
    for palavra in palavras:
        teste = f"{linha_atual} {palavra}".strip()
        if fonte_texto.size(teste)[0] < caixa_dica.width - 32:
            linha_atual = teste
        else:
            linhas_dica.append(linha_atual)
            linha_atual = palavra
    if linha_atual:
        linhas_dica.append(linha_atual)

    y_d = caixa_dica.y + 16
    for l_txt in linhas_dica[:5]:
        tela.blit(fonte_texto.render(l_txt, True, TEXTO_PRINCIPAL), (caixa_dica.x + 16, y_d))
        y_d += 24

    # 5. BOTÕES DE AÇÃO NO RODAPÉ
    botoes: dict[str, pygame.Rect] = {}
    altura_btn = 52
    y_btn = 620

    if em_pausa:
        # Quando pausado durante a corrida: 3 botões (CONTINUAR, RECOMEÇAR, SAIR)
        larg_btn_pausa = 260
        gap = 20
        larg_total = 3 * larg_btn_pausa + 2 * gap
        x_inicio = cx - larg_total // 2

        # 1. Botão Continuar Corrida
        rect_cont = pygame.Rect(x_inicio, y_btn, larg_btn_pausa, altura_btn)
        hover_cont = rect_cont.collidepoint(mouse_pos)
        cor_fundo_cont = "#2a423a" if hover_cont else "#1f332c"
        pygame.draw.rect(tela, cor_fundo_cont, rect_cont, border_radius=14)
        pygame.draw.rect(tela, DESTAQUE if hover_cont else "#3d574d", rect_cont, width=2, border_radius=14)

        txt_cont = fonte_subtitulo.render("CONTINUAR", True, DESTAQUE if hover_cont else TEXTO_PRINCIPAL)
        sub_cont = fonte_menor.render("[ESPAÇO] ou [B] / [P]", True, TEXTO_SECUNDARIO)
        tela.blit(txt_cont, (rect_cont.centerx - txt_cont.get_width() // 2, rect_cont.y + 8))
        tela.blit(sub_cont, (rect_cont.centerx - sub_cont.get_width() // 2, rect_cont.y + 30))
        botoes["continuar"] = rect_cont

        # 2. Botão Recomeçar
        rect_rec = pygame.Rect(x_inicio + larg_btn_pausa + gap, y_btn, larg_btn_pausa, altura_btn)
        hover_rec = rect_rec.collidepoint(mouse_pos)
        cor_fundo_rec = "#383c27" if hover_rec else "#272a1d"
        pygame.draw.rect(tela, cor_fundo_rec, rect_rec, border_radius=14)
        pygame.draw.rect(tela, AVISO if hover_rec else "#4e5436", rect_rec, width=2, border_radius=14)

        txt_rec = fonte_subtitulo.render("RECOMEÇAR", True, AVISO if hover_rec else TEXTO_PRINCIPAL)
        sub_rec = fonte_menor.render("[R]", True, TEXTO_SECUNDARIO)
        tela.blit(txt_rec, (rect_rec.centerx - txt_rec.get_width() // 2, rect_rec.y + 8))
        tela.blit(sub_rec, (rect_rec.centerx - sub_rec.get_width() // 2, rect_rec.y + 30))
        botoes["recomecar"] = rect_rec

        # 3. Botão Sair
        rect_sair = pygame.Rect(x_inicio + 2 * (larg_btn_pausa + gap), y_btn, larg_btn_pausa, altura_btn)
        hover_sair = rect_sair.collidepoint(mouse_pos)
        cor_fundo_sair = "#3d2222" if hover_sair else "#261919"
        pygame.draw.rect(tela, cor_fundo_sair, rect_sair, border_radius=14)
        pygame.draw.rect(tela, PERIGO if hover_sair else "#573535", rect_sair, width=2, border_radius=14)

        txt_sair = fonte_subtitulo.render("SAIR DO JOGO", True, PERIGO if hover_sair else TEXTO_PRINCIPAL)
        sub_sair = fonte_menor.render("[Q] ou [ESC]", True, TEXTO_SECUNDARIO)
        tela.blit(txt_sair, (rect_sair.centerx - txt_sair.get_width() // 2, rect_sair.y + 8))
        tela.blit(sub_sair, (rect_sair.centerx - sub_sair.get_width() // 2, rect_sair.y + 30))
        botoes["sair"] = rect_sair
    else:
        # Quando concluído (fim de percurso): 2 botões (JOGAR NOVAMENTE e SAIR)
        larg_btn = 320

        # Botão Jogar Novamente
        rect_jogar = pygame.Rect(cx - larg_btn - 20, y_btn, larg_btn, altura_btn)
        hover_jogar = rect_jogar.collidepoint(mouse_pos)
        cor_fundo_jogar = "#2a423a" if hover_jogar else "#1f332c"
        pygame.draw.rect(tela, cor_fundo_jogar, rect_jogar, border_radius=14)
        pygame.draw.rect(tela, DESTAQUE if hover_jogar else "#3d574d", rect_jogar, width=2, border_radius=14)

        txt_jogar = fonte_subtitulo.render("JOGAR NOVAMENTE", True, DESTAQUE if hover_jogar else TEXTO_PRINCIPAL)
        sub_jogar = fonte_menor.render("[R] ou [ENTER]", True, TEXTO_SECUNDARIO)
        tela.blit(txt_jogar, (rect_jogar.centerx - txt_jogar.get_width() // 2, rect_jogar.y + 8))
        tela.blit(sub_jogar, (rect_jogar.centerx - sub_jogar.get_width() // 2, rect_jogar.y + 30))
        botoes["jogar_novamente"] = rect_jogar

        # Botão Sair
        rect_sair = pygame.Rect(cx + 20, y_btn, larg_btn, altura_btn)
        hover_sair = rect_sair.collidepoint(mouse_pos)
        cor_fundo_sair = "#3d2222" if hover_sair else "#261919"
        pygame.draw.rect(tela, cor_fundo_sair, rect_sair, border_radius=14)
        pygame.draw.rect(tela, PERIGO if hover_sair else "#573535", rect_sair, width=2, border_radius=14)

        txt_sair = fonte_subtitulo.render("SAIR DO JOGO", True, PERIGO if hover_sair else TEXTO_PRINCIPAL)
        sub_sair = fonte_menor.render("[ESC]", True, TEXTO_SECUNDARIO)
        tela.blit(txt_sair, (rect_sair.centerx - txt_sair.get_width() // 2, rect_sair.y + 8))
        tela.blit(sub_sair, (rect_sair.centerx - sub_sair.get_width() // 2, rect_sair.y + 30))
        botoes["sair"] = rect_sair

    return botoes
