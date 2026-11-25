"""Ponto de entrada oficial do jogo Dead Lane."""

import argparse
import sys
from pathlib import Path

# Garante que o diretório base do projeto esteja no sys.path
pasta_raiz = Path(__file__).resolve().parent
if str(pasta_raiz) not in sys.path:
    sys.path.insert(0, str(pasta_raiz))

from src.jogo import _ler_argumentos, _obter_mensagem_status, criar_partida, executar

if __name__ == "__main__":
    args = _ler_argumentos()
    executar(args.jogador, pular_instrucoes=args.sem_instrucoes)
