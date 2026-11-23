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

## Métricas de desempenho

Cada perigo (porta do carro ou ponto cego do ônibus) gera um resultado por tentativa, gravado em `resultados/sessao_AAAAMMDD_HHMMSS.csv` (separado por `;`, abre direto no Excel). Para identificar o participante de um teste, execute:

```powershell
.\.venv\Scripts\python.exe jogo.py --jogador "Participante 1"
```

O registro começa no aviso do perigo e acompanha, quadro a quadro, se o ciclista está em risco — em rota de colisão com a porta ou dentro do ponto cego. O **tempo de resposta** é o intervalo entre o aviso e o instante em que o ciclista saiu do risco pela última vez, ou seja, a ação que realmente resolveu a situação.

| Resultado | Critério |
|---|---|
| **Antecipação** | Resolveu o risco em até 1,0 s após o aviso da porta (antes de ela abrir) ou em até 1,4 s após o aviso do ônibus (primeira metade do aviso). Quem já estava em posição segura tem tempo de resposta 0. |
| **Reação tardia** | Resolveu o risco sem colidir, mas depois desses limites. |
| **Falha** | Colidiu com a porta ou com o ônibus, ou ficou no ponto cego quando o ônibus fechou. |

Os limites ficam em `src/configuracao.py` (`LIMITE_ANTECIPACAO_PORTA_S` e `LIMITE_ANTECIPACAO_PONTO_CEGO_S`). Batidas em veículos comuns da avenida não são perigos planejados e ficam contadas à parte. A função `RegistroDesempenho.resumo()` (em `src/metricas.py`) devolve os totais, o tempo médio de resposta e o tipo de erro mais comum.

## Testes

Instale as dependências de desenvolvimento e rode os testes automatizados na raiz do projeto:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

Os testes em `tests/test_porta.py` simulam o percurso quadro a quadro e conferem a colisão com a porta do carro estacionado: o contato com a porta aberta, a passagem segura ao frear ou mudar de faixa durante o aviso, a porta que só causa colisão quando está aberta e o reinício do percurso após uma colisão.

Os testes em `tests/test_metricas.py` conferem a classificação de cada perigo em antecipação, reação tardia ou falha, o tempo de resposta, a gravação em CSV por tentativa e o resumo de desempenho.
