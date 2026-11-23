"""Gera o relatório de comparação início × fim a partir dos CSVs em resultados/."""

import argparse
import sys
from pathlib import Path

from src.comparacao import NOMES_TIPOS, comparar, gerar_relatorio, ler_registros
from src.configuracao import PASTA_RESULTADOS


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arquivos", nargs="*", type=Path, help=f"CSVs a analisar (padrão: todos em {PASTA_RESULTADOS}/)")
    parser.add_argument("--saida", type=Path, default=Path("docs/comparacao-desempenho.md"), help="arquivo Markdown gerado")
    args = parser.parse_args()

    arquivos = args.arquivos or sorted(Path(PASTA_RESULTADOS).glob("*.csv"))
    if not arquivos:
        print(f"Nenhum resultado encontrado em {PASTA_RESULTADOS}/. Jogue uma partida antes de comparar.")
        return 1

    comparacoes = comparar(ler_registros(arquivos))
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(gerar_relatorio(comparacoes, arquivos), encoding="utf-8")

    for comparacao in comparacoes:
        print(f"{comparacao.jogador} · {NOMES_TIPOS[comparacao.tipo]}: {comparacao.tendencia}")
    print(f"Relatório salvo em {args.saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
