# Dead Lane

**Dead Lane** é um *serious game* 2D em visão superior (top-down) focado no ensino e treino de pilotagem defensiva para ciclistas urbanos. O projeto foi desenvolvido para o Desafio P2 de Desenvolvimento de Jogos Digitais.

O objetivo do jogador é percorrer com segurança uma avenida movimentada de 2.250 metros dividida em 3 períodos com intensidades de tráfego crescentes, aprendendo a antecipar perigos críticos como a abertura repentina de portas de carros estacionados (*dooring*) e o ponto cego de ônibus em conversão (*angles morts*).

---

## Recursos e Funcionalidades

- **Sprites e Identidade Visual Própria**: Ciclista em visão zenital (com animação de frenagem), veículos de passeio com múltiplas variações de cor e faróis noturnos, ônibus urbano com setas dinâmicas e carros estacionados com pisca-alerta.
- **Sinalização Visual de Risco**:
  - Área demarcada de abertura de portas de carros estacionados.
  - Zona visual de ponto cego do ônibus com setas de recuo recomendando a frenagem preventiva.
  - Alerta pulsante na borda da tela com retículo de perigo nos cantos ao entrar em zonas críticas.
- **Tela de Instruções de Pilotagem**: Apresentada no início para introduzir os controles e ensinar o reconhecimento dos alertas antes de o ciclista entrar na via.
- **Boletim de Pilotagem Defensiva (Fim de Fase e Pausa)**:
  - Telemetria em tempo real com contagem de antecipações, reações tardias, colisões e tempo médio de resposta.
  - Classificação e Nota final com Patentes (Rank S, A, B ou C).
  - Comparativo de evolução pedagógica: desempenho no início (Trecho 1) vs. fim (Trecho 3).
  - Diagnóstico pedagógico e dica personalizada gerada a partir do padrão de erros do jogador.
  - Funciona também como menu de pausa durante a corrida (teclas `B`, `P` ou `Esc`), congelando tempo e tráfego e permitindo continuar, recomeçar ou sair.

---

## Controles de Pilotagem

| Tecla / Atalho | Ação | Descrição |
|---|---|---|
| **W / ↑** | Acelerar | Pedala para frente, aumentando a velocidade até o limite máximo. |
| **S / ↓** | Frear (Defensivo) | Reduz a velocidade; fundamental para sair do ponto cego e recuar. |
| **A / ←** e **D / →** | Mudar de Posição | Desloca o ciclista lateralmente entre as faixas da pista. |
| **B / P / Esc** | Pausa / Boletim | Congela o jogo e abre o Boletim de Pilotagem com telemetria parcial. |
| **H / I** | Instruções | Abre a tela de instruções e reconhecimento de perigos. |
| **R** | Reiniciar | Reinicia a tentativa imediatamente a partir do marco zero. |
| **Esc / Q** | Sair | Fecha o jogo (ou despausa se estiver no boletim de pausa). |

---

## Execução em Ambiente de Desenvolvimento

### Pré-requisitos
- Python 3.11 a 3.14 instalado.
- Ambiente virtual configurado.

### Configuração no Windows (PowerShell / Prompt)
```powershell
# 1. Criação do ambiente virtual
py -3.14 -m venv .venv

# 2. Instalação das dependências
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. Execução do jogo
.\.venv\Scripts\python.exe jogo.py
```

### Configuração no Linux / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python jogo.py
```

### Parâmetros de Linha de Comando
- `--jogador "Nome"`: Grava o nome do ciclista no CSV de telemetria e no cabeçalho do Boletim.
- `--sem-instrucoes`: Pula a tela inicial de instruções, iniciando direto na pedalada.

Exemplo:
```powershell
.\.venv\Scripts\python.exe jogo.py --jogador "Ciclista 1"
```

---

## Empacotamento para Windows (Standalone `.exe`)

O projeto já conta com o arquivo de especificação [`build_windows.spec`](build_windows.spec) e um script automatizado [`build_windows.bat`](build_windows.bat), configurados para empacotar o jogo em um único arquivo executável autossuficiente (`DeadLane.exe`), sem abrir terminal (`--windowed`) e incluindo a pasta `assets/` compatível com `sys._MEIPASS`.

### Método 1: Compilação Automática via `.bat` (Recomendado)
Basta dar um duplo-clique no arquivo **`build_windows.bat`** (ou executá-lo pelo terminal):

```cmd
build_windows.bat
```

O script cuidará de:
1. Verificar e configurar o ambiente virtual `.venv`.
2. Instalar as dependências e o PyInstaller.
3. Gerar e validar os assets PNG em `assets/`.
4. Compilar o executável final em `dist\DeadLane.exe`.

### Método 2: Compilação Manual via Terminal
Se preferir rodar passo a passo:

```powershell
# 1. Instale o PyInstaller no ambiente virtual
.\.venv\Scripts\python.exe -m pip install pyinstaller

# 2. Execute a compilação a partir da especificação
.\.venv\Scripts\pyinstaller.exe --clean build_windows.spec
```

Ao término, o executável estará pronto na pasta `dist\`:
```powershell
.\dist\DeadLane.exe
```

---

## Métricas de Desempenho e Telemetria

Os dados de cada partida são gravados na pasta `resultados/sessao_AAAAMMDD_HHMMSS.csv` (separado por `;`, abrindo direto no Microsoft Excel e LibreOffice Calc).

| Resultado | Critério Defensivo |
|---|---|
| **Antecipação** | O ciclista resolveu o perigo em até 1,0 s após o aviso da porta (antes de ela abrir) ou em até 1,4 s após o aviso do ônibus (primeira metade do tempo de aviso). Se já pedalava em faixa segura, o tempo de resposta é 0 s. |
| **Reação Tardia** | O ciclista evitou o perigo sem colidir, mas tomou a decisão evasiva após o tempo limite de antecipação. |
| **Falha / Colisão** | Houve colisão física com a porta aberta, permanência no ponto cego no momento do fechamento do ônibus, ou batida no tráfego da via. |

### Relatório Comparativo de Evolução
Para processar os CSVs gerados e comparar as situações equivalentes entre o início e o fim da fase:

```powershell
.\.venv\Scripts\python.exe comparar_desempenho.py
```
O resultado consolidado é gerado em `docs/comparacao-desempenho.md`.

---

## Testes Automatizados

O repositório possui uma suíte completa de testes com `pytest`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

- `tests/test_porta.py`: Colisões e janelas temporais de reação a portas de carros estacionados.
- `tests/test_metricas.py`: Classificação de antecipações, reações tardias e gravação de CSV.
- `tests/test_comparacao.py`: Validação das situações pareadas do início e fim do percurso.
- `tests/test_visual_instrucoes.py`: Renderização de sprites, alertas de borda, tela de instruções e boletim (modos fim e pausa).
