# Comparação de desempenho em situações equivalentes

Relatório gerado por `comparar_desempenho.py` a partir dos resultados gravados pelo jogo.
Cada par compara o primeiro perigo de um tipo no trecho 1 (*Manhã tranquila*) com o último do mesmo tipo no trecho 3 (*Hora do rush*). As duas situações têm o mesmo aviso e nenhum veículo comum nas faixas usadas para evitar o perigo, então a diferença de desempenho vem do jogador, e não do cenário.

Arquivos analisados: `sessao_20261124_221157.csv`

O tempo médio de resposta considera só as situações resolvidas (antecipações e reações tardias).

## (sem nome)

### Porta do carro — melhorou

| Situação | Tentativas | Antecipações | Reações tardias | Falhas | Taxa de antecipação | Taxa de falha | Tempo médio de resposta |
|---|---|---|---|---|---|---|---|
| Início (`porta_1`) | 3 | 2 | 0 | 1 | 67% | 33% | 0,21 s |
| Fim (`porta_9`) | 1 | 1 | 0 | 0 | 100% | 0% | 0,00 s |

### Ponto cego do ônibus — igual

| Situação | Tentativas | Antecipações | Reações tardias | Falhas | Taxa de antecipação | Taxa de falha | Tempo médio de resposta |
|---|---|---|---|---|---|---|---|
| Início (`ponto_cego_1`) | 1 | 1 | 0 | 0 | 100% | 0% | 0,00 s |
| Fim (`ponto_cego_9`) | 1 | 1 | 0 | 0 | 100% | 0% | 0,00 s |
