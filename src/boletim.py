"""Tela de Boletim de Pilotagem: apresenta métricas de telemetria, patente/rank,
comparativo de evolução (início vs. fim) e diagnóstico pedagógico personalizado.
"""

from dataclasses import dataclass
import pygame

from src.assets import carregar_icone
from src.cenario_visual import (
    ASFALTO,
    AVISO,
    BORDA_PISTA,
    DESTAQUE,
    FUNDO,
    PAINEL,
    PERIGO,
    TEXTO_PRINCIPAL,
    TEXTO_SECUNDARIO,
    _quebrar_texto,
)
from src.comparacao import Comparacao, DesempenhoSituacao
from src.metricas import ResumoDesempenho

VERDE_ESMERALDA = "#34d399"


@dataclass(frozen=True)
class PatenteDesempenho:
    rank: str
    titulo: str
    descricao: str
    cor: str
    pontuacao: int
    taxa_antecipacao: float


def calcular_patente(resumo: ResumoDesempenho, *, derrota: bool = False) -> PatenteDesempenho:
    """Calcula a patente e rank (S, A, B, C) com base no desempenho defensivo."""
    total = resumo.total_perigos
    taxa_antecipacao = resumo.antecipacoes / total if total > 0 else 0.0
    total_colisoes = resumo.falhas + resumo.colisoes_trafego

    pontos = 100
    pontos -= total_colisoes * 25
    pontos -= resumo.reacoes_tardias * 4
    pontuacao = max(0, min(100, pontos))

    if derrota or total == 0:
        if derrota:
            pontuacao = min(pontuacao, 45)
            titulo = "Corrida encerrada por colisão"
            descricao = "Revise os sinais de alerta e mantenha margem lateral."
        else:
            pontuacao = 0
            titulo = "Em andamento"
            descricao = "Avance pela avenida para registrar eventos de risco."
        return PatenteDesempenho(
            rank="C",
            titulo=titulo,
            descricao=descricao,
            cor=PERIGO if derrota else TEXTO_SECUNDARIO,
            pontuacao=pontuacao,
            taxa_antecipacao=taxa_antecipacao,
        )

    if total_colisoes == 0 and taxa_antecipacao >= 0.85:
        rank = "S"
        titulo = "Pilotagem Defensiva Exemplar"
        descricao = "Você antecipou praticamente todas as ameaças antes de ficarem críticas."
        cor = DESTAQUE
    elif total_colisoes == 0 and taxa_antecipacao >= 0.65:
        rank = "A"
        titulo = "Piloto Defensivo Consciente"
        descricao = "Ótima leitura preventiva e nenhuma colisão no trajeto."
        cor = VERDE_ESMERALDA
    elif total_colisoes <= 2 and taxa_antecipacao >= 0.40:
        rank = "B"
        titulo = "Piloto em Desenvolvimento"
        descricao = "Bom controle geral, mas com reações tardias em trechos movimentados."
        cor = AVISO
    else:
        rank = "C"
        titulo = "Piloto em Zona de Risco"
        descricao = "Decisões tardias ou colisões comprometeram a segurança na via."
        cor = PERIGO

    return PatenteDesempenho(
        rank=rank,
        titulo=titulo,
        descricao=descricao,
        cor=cor,
        pontuacao=pontuacao,
        taxa_antecipacao=taxa_antecipacao,
    )


def gerar_dica_personalizada(resumo: ResumoDesempenho, *, derrota: bool = False) -> str:
    """Gera uma dica pedagógica direcionada a partir do tipo de erro mais comum."""
    if resumo.erro_mais_comum == "porta":
        return (
            "Dica Defensiva (Portas de Carros): Seu maior desafio foi o 'dooring'. "
            "Mantenha distância dos carros estacionados à direita e, ao notar o pisca-alerta, "
            "mude para a faixa central ou freie."
        )
    if resumo.erro_mais_comum == "ponto_cego":
        return (
            "Dica Defensiva (Ponto Cego de Ônibus): Atenção aos 'Angles Morts'. "
            "Nunca emparelhe na zona lateral quando o ônibus der seta: freie para recuar "
            "ou ultrapasse pela esquerda."
        )
    if resumo.colisoes_trafego > 0:
        return (
            "Dica de Fluxo e Espaçamento: Mantenha distância segura dos veículos à frente "
            "e use o freio (S / Baixo) ou o Dash (Espaço) para evitar colisões."
        )
    if resumo.reacoes_tardias > 0:
        return (
            "Dica de Antecipação: Você evitou colisões, mas reagiu em cima da hora. "
            "Ao ver o pisca-alerta ou a seta do ônibus, aja imediatamente."
        )
    if derrota:
        return (
            "Uma colisão encerrou a tentativa. Observe os avisos visuais na pista "
            "e reduza a velocidade nos trechos de tráfego mais intenso."
        )
    if resumo.total_perigos == 0:
        return (
            "Continue pilotando pela avenida para registrar sua leitura "
            "de portas de carros e pontos cegos de ônibus."
        )
    return (
        "Dica de Excelência: Pilotagem impecável! Você antecipou todos os perigos urbanos "
        "com folga e manteve o percurso seguro."
    )


def _formatar_desempenho(desemp: DesempenhoSituacao) -> tuple[str, str]:
    if desemp.falhas > 0:
        return "Colisão", PERIGO
    if desemp.antecipacoes > 0:
        tempo = f" ({desemp.tempo_medio_resposta_s:.2f}s)" if desemp.tempo_medio_resposta_s is not None else ""
        return f"Antecipação{tempo}", DESTAQUE
    if desemp.reacoes_tardias > 0:
        tempo = f" ({desemp.tempo_medio_resposta_s:.2f}s)" if desemp.tempo_medio_resposta_s is not None else ""
        return f"Tardia{tempo}", AVISO
    return "", TEXTO_SECUNDARIO


def desenhar_boletim_pilotagem(
    tela: pygame.Surface,
    resumo: ResumoDesempenho,
    comparacoes: list[Comparacao],
    tempo_percurso_s: float,
    jogador: str,
    tempo_animacao_s: float = 0.0,
    mouse_pos: tuple[int, int] = (0, 0),
    em_pausa: bool = False,
    derrota: bool = False,
) -> dict[str, pygame.Rect]:
    """Renderiza o Boletim de Pilotagem com visual limpo e hierárquico, sem poluição."""
    tela.fill(FUNDO)

    fonte_titulo = pygame.font.SysFont("Bahnschrift", 34, bold=True)
    fonte_subtitulo = pygame.font.SysFont("Bahnschrift", 22, bold=True)
    fonte_secao = pygame.font.SysFont("Bahnschrift", 19, bold=True)
    fonte_texto = pygame.font.SysFont("Bahnschrift", 18)
    fonte_menor = pygame.font.SysFont("Bahnschrift", 15, bold=True)
    fonte_tecla = pygame.font.SysFont("Consolas", 14, bold=True)
    fonte_rank = pygame.font.SysFont("Bahnschrift", 66, bold=True)
    fonte_numero = pygame.font.SysFont("Bahnschrift", 42, bold=True)

    margem_x = 64
    largura_total = 1280 - 2 * margem_x
    x_fim = 1280 - margem_x

    # 1. CABEÇALHO LIMPO
    icone_jogo = pygame.transform.smoothscale(carregar_icone("icone_jogo"), (48, 48))
    tela.blit(icone_jogo, (margem_x, 28))

    if em_pausa:
        titulo_texto = "CORRIDA PAUSADA"
        cor_titulo = AVISO
        status_cab = "Telemetria parcial"
    elif derrota:
        titulo_texto = "CORRIDA ENCERRADA"
        cor_titulo = PERIGO
        status_cab = "Colisão na via"
    else:
        titulo_texto = "PERCURSO CONCLUÍDO"
        cor_titulo = DESTAQUE
        status_cab = "Chegada segura"

    nome_jogador = jogador if jogador else "Piloto"
    tela.blit(fonte_titulo.render(titulo_texto, True, cor_titulo), (margem_x + 64, 24))
    tela.blit(
        fonte_texto.render(f"{status_cab}  ·  {nome_jogador}  ·  {tempo_percurso_s:.1f} s", True, TEXTO_SECUNDARIO),
        (margem_x + 64, 62),
    )

    pygame.draw.line(tela, BORDA_PISTA, (margem_x, 98), (x_fim, 98), 1)

    # 2. FAIXA PRINCIPAL: RANK + 4 MÉTRICAS EM UM ÚNICO BLOCO LIMPO
    patente = calcular_patente(resumo, derrota=derrota)
    y_hero = 120
    alt_hero = 186

    bloco_hero = pygame.Rect(margem_x, y_hero, largura_total, alt_hero)
    pygame.draw.rect(tela, PAINEL, bloco_hero, border_radius=4)
    pygame.draw.rect(tela, BORDA_PISTA, bloco_hero, width=1, border_radius=4)
    pygame.draw.rect(tela, patente.cor, (bloco_hero.x, bloco_hero.y, bloco_hero.width, 3))

    # Lado esquerdo do hero: Rank + Nota + Barra de Antecipação
    badge_rank = pygame.Rect(bloco_hero.x + 28, bloco_hero.y + 28, 92, 92)
    pygame.draw.rect(tela, ASFALTO, badge_rank, border_radius=4)
    pygame.draw.rect(tela, patente.cor, badge_rank, width=2, border_radius=4)
    letra_render = fonte_rank.render(patente.rank, True, patente.cor)
    tela.blit(
        letra_render,
        (badge_rank.centerx - letra_render.get_width() // 2, badge_rank.centery - letra_render.get_height() // 2 + 2),
    )

    x_info = badge_rank.right + 22
    tela.blit(fonte_subtitulo.render(f"Nota {patente.pontuacao} / 100", True, TEXTO_PRINCIPAL), (x_info, bloco_hero.y + 30))
    tela.blit(fonte_secao.render(patente.titulo, True, patente.cor), (x_info, bloco_hero.y + 60))
    for i_d, linha_d in enumerate(_quebrar_texto(fonte_texto, patente.descricao, 330)[:2]):
        tela.blit(fonte_texto.render(linha_d, True, TEXTO_SECUNDARIO), (x_info, bloco_hero.y + 88 + i_d * 20))

    # Barra fina de antecipação no rodapé esquerdo do bloco
    tela.blit(
        fonte_menor.render(f"Antecipação: {patente.taxa_antecipacao * 100:.0f}%", True, TEXTO_SECUNDARIO),
        (bloco_hero.x + 28, bloco_hero.bottom - 42),
    )
    barra_x = bloco_hero.x + 170
    barra_w = 290
    pygame.draw.rect(tela, ASFALTO, (barra_x, bloco_hero.bottom - 35, barra_w, 6), border_radius=2)
    larg_prog = round(barra_w * patente.taxa_antecipacao)
    if larg_prog > 0:
        pygame.draw.rect(tela, patente.cor, (barra_x, bloco_hero.bottom - 35, larg_prog, 6), border_radius=2)

    # Divisória vertical interna
    x_div_hero = bloco_hero.x + 492
    pygame.draw.line(tela, BORDA_PISTA, (x_div_hero, bloco_hero.y + 24), (x_div_hero, bloco_hero.bottom - 24), 1)

    # Lado direito do hero: 4 números limpos sem sub-caixas redundantes
    tempo_resp = f"{resumo.tempo_medio_resposta_s:.2f} s" if resumo.tempo_medio_resposta_s is not None else "—"
    metricas = (
        ("ANTECIPAÇÕES", str(resumo.antecipacoes), DESTAQUE),
        ("TARDIAS", str(resumo.reacoes_tardias), AVISO),
        ("COLISÕES", str(resumo.falhas + resumo.colisoes_trafego), PERIGO),
        ("TEMPO MÉDIO", tempo_resp, TEXTO_PRINCIPAL),
    )
    larg_m = (bloco_hero.right - x_div_hero - 36) // 4
    for idx, (rotulo_m, valor_m, cor_m) in enumerate(metricas):
        xm = x_div_hero + 28 + idx * larg_m
        tela.blit(fonte_menor.render(rotulo_m, True, TEXTO_SECUNDARIO), (xm, bloco_hero.y + 42))
        tela.blit(fonte_numero.render(valor_m, True, cor_m), (xm, bloco_hero.y + 74))

    # 3. ÁREA INFERIOR: 2 COLUNAS LIMPAS (SEM CAIXA DENTRO DE CAIXA E SEM "SEM DADOS")
    y_inf = y_hero + alt_hero + 26
    alt_inf = 270
    larg_col = (largura_total - 28) // 2

    # --- COLUNA ESQUERDA: DIAGNÓSTICO ---
    col_diag = pygame.Rect(margem_x, y_inf, larg_col, alt_inf)
    pygame.draw.rect(tela, PAINEL, col_diag, border_radius=4)
    pygame.draw.rect(tela, BORDA_PISTA, col_diag, width=1, border_radius=4)
    pygame.draw.rect(tela, cor_titulo, (col_diag.x, col_diag.y, 4, col_diag.height))

    tela.blit(fonte_secao.render("Diagnóstico da corrida", True, TEXTO_PRINCIPAL), (col_diag.x + 26, col_diag.y + 24))
    pygame.draw.line(tela, BORDA_PISTA, (col_diag.x + 26, col_diag.y + 56), (col_diag.right - 26, col_diag.y + 56), 1)

    dica_texto = gerar_dica_personalizada(resumo, derrota=derrota)
    y_d = col_diag.y + 76
    for linha in _quebrar_texto(fonte_texto, dica_texto, col_diag.width - 52)[:6]:
        tela.blit(fonte_texto.render(linha, True, TEXTO_SECUNDARIO), (col_diag.x + 26, y_d))
        y_d += 28

    # --- COLUNA DIREITA: EVOLUÇÃO (SÓ MOSTRA O QUE EXISTE, ZERO "SEM DADOS") ---
    col_comp = pygame.Rect(col_diag.right + 28, y_inf, larg_col, alt_inf)
    pygame.draw.rect(tela, PAINEL, col_comp, border_radius=4)
    pygame.draw.rect(tela, BORDA_PISTA, col_comp, width=1, border_radius=4)

    tela.blit(fonte_secao.render("Leitura por tipo de perigo", True, TEXTO_PRINCIPAL), (col_comp.x + 24, col_comp.y + 24))
    pygame.draw.line(tela, BORDA_PISTA, (col_comp.x + 24, col_comp.y + 56), (col_comp.right - 24, col_comp.y + 56), 1)

    itens_validos: list[tuple[str, str, Comparacao]] = []
    for tipo_p, icone_n, nome_p in (
        ("porta", "icone_porta", "Porta de carro"),
        ("ponto_cego", "icone_ponto_cego", "Ponto cego de ônibus"),
    ):
        comp = next((c for c in comparacoes if c.tipo == tipo_p), None)
        if comp is not None and (_formatar_desempenho(comp.inicio)[0] or _formatar_desempenho(comp.fim)[0]):
            itens_validos.append((icone_n, nome_p, comp))

    if itens_validos:
        y_c = col_comp.y + 74
        for idx_c, (icone_n, nome_p, comp) in enumerate(itens_validos):
            tela.blit(carregar_icone(icone_n), (col_comp.x + 24, y_c + 4))
            tela.blit(fonte_secao.render(nome_p, True, TEXTO_PRINCIPAL), (col_comp.x + 84, y_c))

            txt_ini, cor_ini = _formatar_desempenho(comp.inicio)
            txt_fim, cor_fim = _formatar_desempenho(comp.fim)

            if txt_ini and txt_fim:
                tela.blit(fonte_texto.render(f"Início: {txt_ini}", True, cor_ini), (col_comp.x + 84, y_c + 26))
                tela.blit(fonte_texto.render(f"Fim: {txt_fim}", True, cor_fim), (col_comp.x + 84, y_c + 48))
            elif txt_ini:
                tela.blit(fonte_texto.render(f"Trecho inicial: {txt_ini}", True, cor_ini), (col_comp.x + 84, y_c + 30))
            elif txt_fim:
                tela.blit(fonte_texto.render(f"Trecho final: {txt_fim}", True, cor_fim), (col_comp.x + 84, y_c + 30))

            if comp.tendencia in ("melhorou", "piorou", "igual"):
                mapa_tend = {
                    "melhorou": ("Melhorou", DESTAQUE),
                    "piorou": ("Piorou", PERIGO),
                    "igual": ("Constante", TEXTO_PRINCIPAL),
                }
                txt_t, cor_t = mapa_tend[comp.tendencia]
                badge_t = pygame.Rect(col_comp.right - 128, y_c + 14, 104, 28)
                pygame.draw.rect(tela, ASFALTO, badge_t, border_radius=3)
                pygame.draw.rect(tela, cor_t, badge_t, width=1, border_radius=3)
                lbl_t = fonte_menor.render(txt_t, True, cor_t)
                tela.blit(lbl_t, (badge_t.centerx - lbl_t.get_width() // 2, badge_t.centery - lbl_t.get_height() // 2))

            if idx_c == 0 and len(itens_validos) > 1:
                pygame.draw.line(tela, BORDA_PISTA, (col_comp.x + 24, y_c + 82), (col_comp.right - 24, y_c + 82), 1)
            y_c += 96
    else:
        msg_comp = (
            "Avance pelos trechos da avenida para comparar sua leitura "
            "entre o início (Manhã) e o fim do percurso (Hora do rush)."
        )
        y_msg = col_comp.y + 84
        for linha in _quebrar_texto(fonte_texto, msg_comp, col_comp.width - 48):
            tela.blit(fonte_texto.render(linha, True, TEXTO_SECUNDARIO), (col_comp.x + 24, y_msg))
            y_msg += 26

    # 4. RODAPÉ E BOTÕES
    y_rodape = 634
    pygame.draw.line(tela, BORDA_PISTA, (margem_x, y_rodape), (x_fim, y_rodape), 1)

    botoes: dict[str, pygame.Rect] = {}
    y_btn = y_rodape + 16
    alt_btn = 46

    def desenhar_btn(chave: str, rect: pygame.Rect, rotulo: str, atalho: str, cor_borda: str, destaque: bool = False) -> None:
        hover = rect.collidepoint(mouse_pos)
        if destaque:
            fundo_b = DESTAQUE
            cor_txt = FUNDO
            cor_sub = ASFALTO
        else:
            fundo_b = ASFALTO if hover else PAINEL
            cor_txt = cor_borda if hover else TEXTO_PRINCIPAL
            cor_sub = TEXTO_SECUNDARIO
        pygame.draw.rect(tela, fundo_b, rect, border_radius=4)
        pygame.draw.rect(tela, cor_borda if (hover or destaque) else BORDA_PISTA, rect, width=1, border_radius=4)

        lbl = fonte_menor.render(rotulo, True, cor_txt)
        sub = fonte_tecla.render(atalho, True, cor_sub)
        tela.blit(lbl, (rect.x + 18, rect.centery - lbl.get_height() // 2))
        tela.blit(sub, (rect.right - sub.get_width() - 16, rect.centery - sub.get_height() // 2))
        botoes[chave] = rect

    if em_pausa:
        desenhar_btn("sair", pygame.Rect(margem_x, y_btn, 220, alt_btn), "SAIR", "Q / ESC", PERIGO)
        desenhar_btn("recomecar", pygame.Rect(margem_x + 236, y_btn, 240, alt_btn), "RECOMEÇAR", "R", AVISO)
        desenhar_btn("continuar", pygame.Rect(x_fim - 320, y_btn, 320, alt_btn), "CONTINUAR", "ESPAÇO / B", DESTAQUE, destaque=True)
    else:
        desenhar_btn("sair", pygame.Rect(margem_x, y_btn, 220, alt_btn), "SAIR", "ESC", PERIGO)
        desenhar_btn("jogar_novamente", pygame.Rect(x_fim - 340, y_btn, 340, alt_btn), "JOGAR NOVAMENTE", "R / ENTER", DESTAQUE, destaque=True)

    return botoes
