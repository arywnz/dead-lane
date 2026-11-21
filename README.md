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

Na raiz, execute `.\.venv\Scripts\python.exe jogo.py`.

- **W / ↑** acelera.
- **S / ↓** freia até parar.
- **A / ←** e **D / →** movem o ciclista para os lados enquanto ele avança.
- **R** reinicia o percurso.
- **Esc** encerra a janela.

O carro estacionado à direita avisa antes de abrir a porta. Veículos e ônibus seguem na avenida no mesmo sentido do ciclista, e os ônibus de evento sinalizam a área de ponto cego à direita antes de fechar a trajetória — freie ou ultrapasse pela esquerda para evitar a zona de risco.

O percurso tem três trechos de 750 m (*Manhã tranquila*, *Horário de almoço* e *Hora do rush*), com perigos isolados no início e intervalos progressivamente menores junto ao aumento do tráfego nos trechos seguintes. Os checkpoints de 750 m e 1.500 m deixam o ciclista avançar e bloqueiam novos avisos de perigo por 2 segundos. Aos 2.250 m, o jogo mostra a vitória. Pressione **R** para voltar ao início.
