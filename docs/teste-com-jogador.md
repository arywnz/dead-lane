# Teste com jogador de fora do grupo

Roteiro para conduzir o teste do Dead Lane com alguém que não participou do desenvolvimento e registrar o que foi observado. Os números vêm do próprio jogo. As observações são anotadas por quem conduz o teste.

## Antes do teste

1. Confira se o jogo abre: `.\.venv\Scripts\python.exe jogo.py`.
2. Escolha um código para o participante (ex.: `P1`). Não use o nome completo.
3. Explique só os controles (W/↑ acelera, S/↓ freia, A D/← → mudam de posição, R reinicia). **Não explique** os perigos nem como evitá-los: o objetivo é ver se a pessoa reconhece os avisos sozinha.

## Durante o teste

1. Inicie o jogo com o código do participante:

   ```powershell
   .\.venv\Scripts\python.exe jogo.py --jogador P1
   ```

2. Deixe a pessoa jogar até completar o percurso ou por cerca de 10 minutos. Ela pode reiniciar quantas vezes quiser.
3. Observe sem ajudar e anote na tabela abaixo:
   - se a pessoa percebeu o aviso da porta e o do ônibus;
   - o que fez ao ver cada aviso (freou, mudou de faixa, não reagiu);
   - comentários espontâneos, dúvidas e momentos de confusão.
4. Ao fechar o jogo, o terminal mostra onde o arquivo `resultados/sessao_….csv` foi salvo.

## Depois do teste

1. Pergunte:
   - "O que você entendeu que precisava fazer quando o carro estacionado ficou com o contorno amarelo e o aviso '! Porta'?"
   - "E quando o ônibus ligava a seta?"
   - "Alguma coisa ficou confusa?"
2. Gere a comparação entre o início e o fim do percurso:

   ```powershell
   .\.venv\Scripts\python.exe comparar_desempenho.py
   ```

   O relatório sai em `docs/comparacao-desempenho.md`.
3. Copie o CSV do participante para `docs/dados/` (a pasta `resultados/` não vai para o Git) e preencha as seções abaixo.

## Registro do teste

| Campo | Valor |
|---|---|
| Data | |
| Participante (código) | |
| Experiência com jogos | |
| Anda de bicicleta na cidade? | |
| Tentativas jogadas | |
| Completou o percurso? | |

### Observações durante o jogo

| Momento (trecho / perigo) | O que aconteceu | O que a pessoa fez ou disse |
|---|---|---|
| | | |
| | | |
| | | |

### Respostas às perguntas finais

- Porta do carro:
- Ponto cego do ônibus:
- Pontos confusos:

### Comparação início × fim

Resumo de `docs/comparacao-desempenho.md` (melhorou, piorou ou igual em cada par, e por quê):

- Porta do carro:
- Ponto cego do ônibus:

### Conclusões

- O que o jogo ensinou bem:
- O que precisa melhorar:
