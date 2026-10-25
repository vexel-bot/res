# Runner de avatar com fala final: implementação e qualificação pendente

Data: 24 de outubro de 2026.
Estado: em andamento. Não habilita geração de avatar neste computador.

Após atualizar o localhost com o trabalho do time, foi retomada a execução
isolada do LongCat-Video-Avatar 1.5. O código upstream foi clonado integralmente,
sem clone raso, e fixado em `6b3f4b8582a8bc3f20f795735f5383716c4ba794`. Os pesos
não foram baixados. O checkout local fica em `.candidate-build/longcat-source`.

O runner adapta o demo oficial por checksum, preservando o checkout original.
Ele usa a fala final já limpa, sem executar o separador vocal do demo, respeita
a seed escolhida e mantém o retrato completo por enquadramento com margens.
Uma referência de áudio em 16 kHz alimenta o modelo; a exportação usa o áudio
original e é cortada na duração da fala.

O serviço implementa fila limitada, recibos atômicos, consulta de progresso,
cancelamento, identificação de interrupções e download autenticado. O backend
envia o pedido completo, confere o vínculo da resposta, baixa o arquivo por
streaming e solicita cancelamento ao atingir o limite de espera.

Passaram dez testes de serviço e mídia com FFmpeg real e nove testes de contrato
e transporte no backend. Para a etapa de modelo, os testes usam quadros de cor
e respostas simuladas. Isso não demonstra clonagem de rosto, qualidade de voz,
sincronismo em português ou atuação de um avatar.

Continuam pendentes o lock de dependências CUDA, a imagem imutável do worker,
o inventário completo de pesos e configurações e a qualificação visual. O ciclo
de retenção foi implementado posteriormente e está descrito no registro
“Limpeza dos arquivos temporários de avatar”; sua qualificação no host CUDA
continua pendente. O preflight continua indisponível, e os
provedores generativos não foram promovidos nem habilitados no localhost.

Referências e fontes:

- [Demo oficial fixado](https://github.com/meituan-longcat/LongCat-Video/blob/6b3f4b8582a8bc3f20f795735f5383716c4ba794/run_demo_avatar_single_audio_to_video.py)
- `workers/longcat-avatar/README.md`
- `workers/longcat-avatar/runner.py`
- `workers/longcat-avatar/tests/test_runner.py`
- `backend/tests/test_longcat_avatar_integration.py`
