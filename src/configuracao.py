LARGURA_JANELA = 1280
ALTURA_JANELA = 720
FPS_ALVO = 60
TEMPO_MAXIMO_QUADRO_S = 0.05

CENTRO_PISTA_X = 440
LARGURA_PISTA = 420
FAIXAS_PISTA = 3
CICLISTA_TELA_Y = 512
MEIA_LARGURA_CICLISTA = 18
MARGEM_BORDA_PISTA = 10
CICLISTA_MIN_X = CENTRO_PISTA_X - LARGURA_PISTA / 2 + MARGEM_BORDA_PISTA + MEIA_LARGURA_CICLISTA
CICLISTA_MAX_X = CENTRO_PISTA_X + LARGURA_PISTA / 2 - MARGEM_BORDA_PISTA - MEIA_LARGURA_CICLISTA

VELOCIDADE_INICIAL_MPS = 8.0
VELOCIDADE_MAXIMA_MPS = 12.0
ACELERACAO_MPS2 = 3.0
FRENAGEM_MPS2 = 6.0
VELOCIDADE_LATERAL_PXPS = 270.0
ESCALA_PISTA_PX_POR_M = 30.0

LARGURA_COLISAO_CICLISTA = 24
ALTURA_COLISAO_CICLISTA = 52
LARGURA_CARRO_ESTACIONADO = 56
COMPRIMENTO_CARRO_ESTACIONADO = 100
ALTURA_PORTA = 24
ALCANCE_PORTA = 68
POSICAO_PORTA_M = 28.0
DISTANCIA_AVISO_PORTA_M = 13.0
DURACAO_AVISO_PORTA_S = 1.0
DURACAO_PORTA_ABERTA_S = 0.8

COMPRIMENTO_TRECHO_M = 750
NOMES_TRECHOS = ("Manhã tranquila", "Horário de almoço", "Hora do rush")
INTERVALO_PONTO_CONTROLE_S = 2.0
COMPRIMENTO_PERCURSO_M = COMPRIMENTO_TRECHO_M * len(NOMES_TRECHOS)

LARGURA_FAIXA = LARGURA_PISTA / FAIXAS_PISTA
CENTROS_FAIXAS_X = tuple(
    CENTRO_PISTA_X - LARGURA_PISTA / 2 + LARGURA_FAIXA * (faixa + 0.5)
    for faixa in range(FAIXAS_PISTA)
)

LARGURA_CARRO = 56
COMPRIMENTO_CARRO = 104
LARGURA_ONIBUS = 78
COMPRIMENTO_ONIBUS = 220

VELOCIDADE_CARRO_MIN_MPS = 5.2
VELOCIDADE_CARRO_MAX_MPS = 6.8
VELOCIDADE_ONIBUS_MPS = 4.8

MARGEM_SPAWN_TRAFEGO_FRENTE_M = 24.0
MARGEM_REMOCAO_TRAFEGO_ATRAS_M = 14.0
MARGEM_REMOCAO_TRAFEGO_FRENTE_M = 42.0
DISTANCIA_SEGURA_MESMA_FAIXA_M = 6.5
INTERVALO_TRAFEGO_PADRAO_M = 88.0
MAX_VEICULOS_AMBIENTE_PADRAO = 4

POSICAO_PONTO_CEGO_M = 140.0
ANTECEDENCIA_ENTRADA_ONIBUS_M = 14.0
DISTANCIA_ENTRADA_ONIBUS_M = 20.0
DISTANCIA_AVISO_PONTO_CEGO_M = 9.5
DURACAO_AVISO_PONTO_CEGO_S = 2.8
DURACAO_PONTO_CEGO_ATIVO_S = 1.5
LARGURA_PONTO_CEGO = 175.0
DESLOCAMENTO_FECHAMENTO_ONIBUS_PX = 26.0

# Métricas: o risco resolvido até este tempo após o aviso conta como antecipação; depois, como reação tardia.
LIMITE_ANTECIPACAO_PORTA_S = DURACAO_AVISO_PORTA_S
LIMITE_ANTECIPACAO_PONTO_CEGO_S = DURACAO_AVISO_PONTO_CEGO_S / 2
PASTA_RESULTADOS = "resultados"

# Situações equivalentes comparadas no início (trecho 1) e no fim (trecho 3) do percurso.
# Cada par usa o mesmo tipo de perigo, com o mesmo aviso, e sem tráfego comum por perto.
SITUACOES_COMPARAVEIS = {
    "porta": ("porta_1", "porta_9"),
    "ponto_cego": ("ponto_cego_1", "ponto_cego_9"),
}
# Trecho sem geração de tráfego comum em volta das situações comparáveis (metros antes, metros depois).
MARGEM_SEM_TRAFEGO_COMPARAVEL_M = (80.0, 50.0)

CONFIG_TRECHOS = (
    {
        "nome": NOMES_TRECHOS[0],
        "rotulo_densidade": "Tráfego leve",
        "intervalo_trafego_m": 135.0,
        "max_veiculos_ambiente": 2,
        "perigos": (
            ("porta", 95.0),
            ("ponto_cego", 260.0),
            ("porta", 435.0),
            ("ponto_cego", 605.0),
        ),
    },
    {
        "nome": NOMES_TRECHOS[1],
        "rotulo_densidade": "Tráfego moderado",
        "intervalo_trafego_m": 90.0,
        "max_veiculos_ambiente": 3,
        "perigos": (
            ("porta", 830.0),
            ("ponto_cego", 945.0),
            ("porta", 1065.0),
            ("ponto_cego", 1180.0),
            ("porta", 1295.0),
            ("ponto_cego", 1410.0),
        ),
    },
    {
        "nome": NOMES_TRECHOS[2],
        "rotulo_densidade": "Tráfego intenso",
        "intervalo_trafego_m": 62.0,
        "max_veiculos_ambiente": 5,
        "perigos": (
            ("porta", 1575.0),
            ("ponto_cego", 1660.0),
            ("porta", 1745.0),
            ("ponto_cego", 1830.0),
            ("porta", 1915.0),
            ("ponto_cego", 2000.0),
            ("porta", 2085.0),
            ("ponto_cego", 2165.0),
        ),
    },
)
