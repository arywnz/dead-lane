# Dead Lane

**Dead Lane** é um jogo 2D em visão superior (top-down) focado no ensino e treino de pilotagem defensiva para motociclistas e condutores de motos elétricas no trânsito urbano. O projeto foi desenvolvido para a P2 de Desenvolvimento de Jogos Digitais.

O objetivo do jogador é percorrer com segurança uma avenida movimentada de 2.250 metros dividida em 3 períodos com intensidades de tráfego crescentes, aprendendo a antecipar perigos críticos como a abertura repentina de portas de carros estacionados nas laterais (*dooring*) e o ponto cego de ônibus em conversão (*angles morts*).

> **Nota sobre execução:** A forma oficial de executar o jogo é diretamente pelo Python (veja as instruções abaixo). Optamos por não distribuir um executável `.exe` empacotado porque binários gerados sem assinatura digital são frequentemente bloqueados pelo Controle Inteligente de Aplicativos / Smart App Control do Windows 11.

---

## Recursos e Funcionalidades

- **Sprites e Identidade Visual Própria**: Piloto em visão zenital (com luz de freio, rastro de Dash e pulso de escapada no limite), veículos de passeio com variações de cor, troca de faixa com seta e faróis noturnos, ônibus urbano com setas dinâmicas e carros estacionados nas duas laterais com pisca-alerta.
- **Sinalização Visual de Risco**:
  - Área demarcada de abertura de portas de carros estacionados nos lados direito e esquerdo da pista.
  - Zona visual de ponto cego do ônibus com setas de recuo recomendando a frenagem preventiva.
  - Alerta pulsante na borda da tela com retículo de perigo nos cantos ao entrar em zonas críticas.
  - Proteção de 2 segundos ao cruzar cada checkpoint, com escudo visual e pausa no surgimento de tráfego.
- **Tela de Instruções de Pilotagem**: Apresentada no início para introduzir os controles e ensinar o reconhecimento dos alertas antes de o piloto entrar na via.
- **Tela de Resultados (Fim de Fase e Pausa)**:
  - Telemetria em tempo real com contagem de antecipações, reações tardias, colisões, escapadas no limite (Dash) e tempo médio de resposta.
  - Classificação e Nota final com Patentes (Rank S, A, B ou C).
  - Comparativo de evolução pedagógica: desempenho no início (Trecho 1) vs. fim (Trecho 3).
  - Diagnóstico pedagógico e dica personalizada gerada a partir do padrão de erros do jogador.
  - Funciona também como menu de pausa durante a corrida (teclas `B`, `P` ou `Esc`), congelando tempo e tráfego e permitindo continuar, recomeçar ou sair.

---

## Controles de Pilotagem

| Tecla / Atalho | Ação | Descrição |
|---|---|---|
| **W / Seta Cima** | Acelerar | Acelera para frente, aumentando a velocidade até o limite máximo (58 km/h). |
| **S / Seta Baixo** | Frear (Defensivo) | Reduz a velocidade; fundamental para sair do ponto cego e recuar. |
| **A / D ou Setas** | Mudar de Faixa | Desloca o piloto lateralmente entre as faixas da pista. |
| **Espaço** | Dash | Desvio lateral rápido (com A/D) ou impulso para frente (sem direção lateral). Escapar de um risco iminente reduz a recarga. |
| **B / P / Esc** | Pausa / Resultados | Congela o jogo e abre a Tela de Resultados com telemetria parcial. |
| **H / I** | Instruções | Abre a tela de instruções e reconhecimento de perigos. |
| **R** | Reiniciar | Reinicia a tentativa imediatamente a partir do marco zero. |
| **Esc / Q** | Sair | Fecha o jogo (ou despausa se estiver na tela de pausa). |

---

## Como Executar (Qualquer Versão do Python 3)

### Pré-requisitos
- Qualquer versão recente do **Python 3** instalada (**Python 3.9 ou superior** — compatível com 3.9, 3.10, 3.11, 3.12, 3.13 e 3.14).

### Configuração no Windows (PowerShell ou Prompt de Comando)
Abra o terminal dentro da pasta do jogo e execute os comandos abaixo (eles usam automaticamente a versão do Python instalada no computador):

```powershell
# 1. Criação do ambiente virtual (use "py -m venv .venv" se o comando "python" não existir)
python -m venv .venv

# 2. Instalação das dependências (pygame-ce compatível com o seu Python)
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. Execução do jogo
.\.venv\Scripts\python.exe jogo.py

# Ou sem janela de terminal (Windows):
.\.venv\Scripts\pythonw.exe jogo.py
```

> **Dica se copiou a pasta de outro PC:** se já existir uma pasta `.venv` antiga criada em outro computador (ou com outra versão do Python), apague-a antes do passo 1 com `Remove-Item -Recurse -Force .venv` e recrie com `python -m venv .venv`.

### Configuração no Linux / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python jogo.py
```

### Parâmetros de Linha de Comando
- `--jogador "Nome"`: Grava o nome do piloto no CSV de telemetria e no cabeçalho da Tela de Resultados.
- `--sem-instrucoes`: Pula a tela inicial de instruções, iniciando direto na corrida.

Exemplo:
```powershell
.\.venv\Scripts\python.exe jogo.py --jogador "Piloto 1"
```

---

## Métricas de Desempenho e Telemetria

Os dados de cada partida são gravados na pasta `resultados/sessao_AAAAMMDD_HHMMSS.csv` (separado por `;`, abrindo direto no Microsoft Excel e LibreOffice Calc).

| Resultado | Critério Defensivo |
|---|---|
| **Antecipação** | O piloto resolveu o perigo em até 0,55 s após o aviso da porta ou em até 1,10 s após o aviso do ônibus. Se já trafegava em faixa segura, o tempo de resposta é 0 s. |
| **Reação Tardia** | O piloto evitou o perigo sem colidir, mas reagiu após o tempo limite de antecipação (ou atravessou a zona de ponto cego em velocidade). |
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

- `tests/test_porta.py`: Colisões e janelas temporais de reação a portas de carros estacionados nos dois lados da pista.
- `tests/test_metricas.py`: Classificação de antecipações, reações tardias, parry do Dash, proteção de checkpoint, prevenção de sobreposição de tráfego e gravação de CSV.
- `tests/test_comparacao.py`: Validação das situações pareadas do início e fim do percurso.
- `tests/test_visual_instrucoes.py`: Renderização de sprites, alertas de borda, tela de instruções e Tela de Resultados (modos fim e pausa).
