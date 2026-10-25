# Limpeza dos arquivos temporários na execução de avatar

Estado: implementação de software testada; geração real do modelo ainda pendente.

## Mudança

O worker do LongCat agora tem exclusão autenticada por execução e varredura de retenção. Imagem de referência, fala, arquivos normalizados, quadros intermediários e logs são removidos quando a execução termina. O vídeo final fica disponível por até uma hora por padrão, ou até o backend pedir sua exclusão após recebê-lo. Os arquivos originais da biblioteca da marca, os pesos e os repositórios permanecem fora desse ciclo temporário.

O backend confere o contrato de ciclo de vida antes de enviar imagem ou áudio. Também pede a exclusão quando há falha de transporte, divergência de checksum, timeout ou cancelamento. Receber uma solicitação de exclusão e concluir a remoção são fatos distintos, registrados separadamente. Uma falha nessa confirmação não provoca automaticamente outra inferência.

Uma execução em andamento recebe cancelamento antes de perder seus arquivos. Sem execução viva associada, os temporários são removidos. Uploads interrompidos, recibos corrompidos e execuções interrompidas no reinício também entram na limpeza. A varredura periódica funciona enquanto a API está ativa.

Os padrões são: até três horas por execução; uma hora para o vídeo temporário após conclusão; um dia para o recibo mínimo de exclusão; varredura a cada minuto. A configuração aceita somente limites positivos e finitos. Se o sistema operacional impedir a remoção de um arquivo, a exclusão continua pendente, o vídeo deixa de ser servido e a varredura tenta novamente.

Depois da exclusão, resta temporariamente um recibo com identificadores, digest do pedido, data e motivo. Ele não contém imagem, áudio, roteiro ou log do modelo. O recibo evita reutilizar uma execução já consumida; também expira. As tentativas efetivas de geração têm identificadores próprios, enquanto a idempotência do pedido e os resultados já salvos continuam sob responsabilidade do backend.

## Verificação e limites

Os testes do worker usam filesystem e HTTP reais, incluindo remoção de arquivos, links para diretórios externos, exclusão durante execução, expiração, arquivos bloqueados, reinício e varredura em segundo plano. A preparação e exportação de mídia usam FFmpeg real; a inferência é substituída por fixtures.

Os testes de transporte usam respostas simuladas para conferir envio, exclusão e comportamento quando a conexão falha. Os testes de elenco conferem reutilização de resultado salvo e bloqueios de revogação. Nenhum desses testes comprova clonagem de voz, fidelidade facial, qualidade visual ou sincronismo do LongCat.

Nesta etapa passaram 20 testes do worker, 18 de contrato/transporte LongCat, 13 de elenco independente e dois do catálogo de evolução. Ruff também passou. O novo documento foi consultado pela sessão autenticada do localhost com checksum disponível.

O worker não foi habilitado no localhost. Ainda faltam pesos/configurações completos, dependências CUDA e imagem imutável qualificadas, ensaio de interrupção abrupta e limpeza da árvore de processos nessa imagem, permissões de armazenamento e avaliação audiovisual. O encadeamento da produção com elenco na interface continua em desenvolvimento.

## Evidências

- workers/longcat-avatar/api.py
- workers/longcat-avatar/tests/test_runner.py
- workers/longcat-avatar/README.md
- backend/app/providers/studios/longcat_avatar.py
- backend/tests/test_longcat_avatar_integration.py
- backend/tests/test_avatar_independent_cast.py
