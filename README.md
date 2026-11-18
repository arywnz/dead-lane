# Dead Lane

Serious game 2D sobre percepção de riscos no trânsito, desenvolvido para o Desafio P2 de Desenvolvimento de Jogos Digitais.

O protótipo inicial permite pedalar, acelerar, frear e mudar de posição na pista.

## Ambiente local

Com Python 3.14 instalado, execute na raiz do projeto no Windows:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Executar o protótipo

Na raiz, execute `.\.venv\Scripts\python.exe main.py`.

- **W / ↑** acelera.
- **S / ↓** freia até parar.
- **A / ←** e **D / →** movem o ciclista para os lados enquanto ele avança.
- **Esc** encerra a janela.
