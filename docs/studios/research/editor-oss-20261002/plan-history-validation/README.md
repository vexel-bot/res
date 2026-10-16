# Validação do histórico por conteúdo — 05/10/2026

No original em Downloads, `get_plan` passou a reaproveitar fatos de validação de conteúdos idênticos. Continua lendo os eventos atuais e calculando SHA-256 do payload integral de cada um. Conteúdo novo ou alterado passa pelo parser completo; o plano escolhido é sempre decodificado/validado e devolvido como objeto novo. A maior revisão e o último evento persistido em empate continuam escolhendo o plano. Nenhum evento/avaliação/modelo de projeto foi migrado ou apagado.

[COMPATIBILITY.md](COMPATIBILITY.md) registra os invariantes antes da implementação. A memória por processo guarda somente parser/IDs/hash/revisão, até 1.024 fatos, com acesso protegido para threads; não guarda payloads nem modelos. Falha não é memorizada. Expulsão/reinício só exige validar outra vez. SHA é sobre bytes do texto integral, não apenas ID, número de revisão ou data. `_bound_plan` e os controles atuais de autorização/documento/digest continuam intactos.

Se a sessão já tem qualquer evento ORM carregado, ou plan_id é vazio, `get_plan` executa o corpo anterior. Isso preserva mudanças em JSON nested que existem só no objeto em memória e ainda não foram descarregadas no banco. A fonte anterior e o corpo desse fallback foram comparados por AST; as demais funções do serviço ficaram iguais.

O caminho sem objetos de evento usa [CAST documentado pelo SQLAlchemy](https://docs.sqlalchemy.org/en/20/core/sqlelement.html#sqlalchemy.sql.expression.cast) para receber texto, em vez de hidratar todos os JSONs como objetos ORM. O comportamento foi verificado no SQLite local. Execução em PostgreSQL não foi demonstrada. O banco ainda lê o histórico integral em cada chamada; esta mudança não torna o custo independente do tamanho do histórico.

## Comparação real e alcance

[observation.json](observation.json) compara somente a função anterior extraída do backup, o caminho novo frio e o novo aquecido, em sessões novas de um processo de diagnóstico separado. Todo o plano, incluindo avaliação integral, foi comparado por hash canônico nos três modos de cada estudo.

| Estudo | Anterior | Novo frio | Novo aquecido | Parsers anterior/frio/aquecido |
| --- | ---: | ---: | ---: | --- |
| Organização A | 522 ms | 539 ms | 351 ms | 3 / 4 / 1 |
| Comparação A | 568 ms | 602 ms | 242 ms | 3 / 4 / 1 |
| Interface A | 1.284 ms | 939 ms | 346 ms | 5 / 6 / 1 |

O caminho frio valida todos os eventos e novamente o escolhido; nos dois primeiros estudos custou ligeiramente mais nessa amostra. Depois, somente o escolhido passa pelo parser, com o mesmo resultado. Tempos excluem serialização/hash do plano. Uma sequência anterior→frio→aquecido por estudo, não randomizada; não é p95 ou garantia de aceleração. Não medimos RSS/CPU/memória de todo o processo; teto de fatos não prova teto do processo.

Na API própria atualizada, os frames 0/244/449 devolveram exatamente os mesmos hashes das respostas summary anteriores, com 41.758/41.790/41.764 bytes. Tempos HTTP diretos: 1.083/409/311 ms. A API foi reiniciada uma vez depois dos testes para ativar a fonte: processo anterior 27188, novo 740 confirmado pronto. Nenhum reinício ocorreu por timeout de observação. Nenhum job/render foi submetido; um registro antigo de cancelamento pendente fora do laboratório não foi alterado.

## Interface e lentidão restante

A seleção da linha `title` manteve o target `ed2-895c9ff7a0a9ce1cb92ec080`. Os recibos qualificados são [history-ui-open.json](history-ui-open.json), [history-ui-frame244-settled.json](history-ui-frame244-settled.json) e [history-ui-frame449-settled.json](history-ui-frame449-settled.json): frame calculado/input, query summary/HTTP 200, vídeo pausado e decodificado a 0/8,133333/14,966666 s, dentro de meio frame. Materiais e gate editorial continuaram disponíveis.

Os dois recibos iniciais de frames 244/449 expiraram aos 20 s e foram preservados como negativos. O orquestrador iniciou a próxima ação antes de observar o encerramento da primeira; a mudança de frame abortou o pedido 244 no navegador. Esse pedido foi servido no backend depois, mas não é evidência positiva de apresentação do frame 244. Reobservamos o mesmo pedido 449 sem reiniciar nem reenviar; depois solicitamos 244 novamente, aguardando o término antes de avançar. A segunda leitura do frame 244 levou 820 ms no navegador.

A abertura real continua muito lenta sob as consultas paralelas: inspeção inicial ~7.692 ms; pedido 449 ~53.056 ms. No mesmo registro, `/api/v1/assets` levou ~158.157 ms desde fetchStart, `/editing/resources` ~92.757 ms, `/visual-quality` ~86.844 ms e `/creative/replan-state` ~30.197 ms. Logs da API observados também mostraram mais de 80 s em materiais/qualidade e ~71,9 s no pedido 244 posteriormente abortado. Tempos de navegador incluem fila/transferência; não identificam sozinhos CPU ou causa. Esse resultado contradiz qualquer conclusão de lentidão global resolvida. Próxima investigação: tamanho/hidratação/serialização das listagens de assets, recursos e qualidade e sua concorrência, preservando evidências e contratos. Não foi demonstrado scrubbing realtime ou playback contínuo sob alterações rápidas.

## Verificações

Passaram oito casos novos: frio/quente/retorno independente, corrupção histórica depois de aquecer/falha não memorizada, bytes alterados no mesmo ID/novas revisões, nested JSON não descarregado, preservação de objeto ORM, expulsão limitada, escopo/ausência/rollback e leitores concorrentes. Passaram seis casos anteriores de consulta, nove de resumo/contrato/controle de acesso e três de comandos/replay/undo/atomicidade/compare-and-swap concorrente: 26 casos. Ruff passou. Frontend/tipos ficaram intactos nesta rodada.

[preservation.json](preservation.json) confere pela API nove documentos iguais em composição/assets aos snapshots originais, revisão 2/version 1, mais os nove MP4s por hash. As três avaliações cegas continuam `not_assessed`, review null e labels intactos. [sources.json](sources.json) fixa 96 fontes: 90 das 91 anteriores intactas, uma mudança esperada e cinco fontes novas. [verification.json](verification.json) sela as evidências.

O último poll adicional do processo de diagnóstico retornou handle desconhecido depois do término já observado; a observação concluída existe e foi verificada, sem reinício. Não houve chamada paga nem nova geração. Revisão humana, autonomia e a limpeza de clones anteriormente recusada continuam pendentes; não tentamos outra via de exclusão.
