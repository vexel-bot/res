# Consulta do último plano e investigação da inspeção — 05/10/2026

No original em `C:/Users/edugu/Downloads/res`, `latest_plan` agora filtra workspace, tipo de evento e documento no banco, ordena por timestamp persistido/ID e materializa somente o evento escolhido. A revisão mais alta e o relógio fornecido pelo cliente não escolhem o último plano de um documento. Um plano escolhido inválido continua falhando, sem retorno silencioso de um anterior. Não houve mudança de contrato, migração, cache, renderizador ou dados persistidos.

A projeção escalar real encontrou 95 eventos de planos e 186.948.201 caracteres de payload neste laboratório. O caminho anterior materializava todos esses eventos antes de filtrar em Python. Não executamos novamente essa leitura integral para cronometrá-la neste computador com pouca memória: não há percentual de aceleração nem comparação controlada antes/depois. O filtro JSON segue a API `as_string()` já usada no repositório ([documentação oficial SQLAlchemy](https://docs.sqlalchemy.org/en/20/core/type_basics.html#sqlalchemy.types.JSON.Comparator.as_string)); o banco ainda precisa avaliar o filtro. Materializar um evento não significa ler um único registro físico do banco.

## Evidência real da consulta

Referência: projeção de IDs/documentos/timestamps de todos os eventos, seleção equivalente em Python pela ordem persistida e validação do único payload selecionado. A função nova e a API direta retornaram a mesma representação canônica completa em três documentos V2 reais.

| Estudo | Função local | API direta | Eventos materializados na função |
| --- | ---: | ---: | ---: |
| Organização A | 1.698 ms | 2.759 ms | 1 |
| Comparação A | 1.237 ms | 2.067 ms | 1 |
| Interface A | 626 ms | 1.255 ms | 1 |

São uma amostra por estudo, com conexões locais e processo Python separado; não são p95 nem previsão de produção. Os hashes dos planos e metadados dos eventos estão em [latest-plan-observation.json](latest-plan-observation.json). A API própria foi reiniciada uma vez para ativar o código depois dos testes; processo anterior 3040 encerrado, novo processo 9520 confirmado pronto. Nenhum reinício foi motivado por timeout de observação.

Na sessão própria existente do navegador, uma navegação inicial ainda estava carregando ao terminar a observação de 20 s; [query-ui-initial.json](query-ui-initial.json) conserva esse resultado negativo. A reobservação da mesma página, sem reiniciar, mostrou cinco materiais e MP4 1080×1920/15 s decodificado. Depois de abrir Revisão, [query-ui-open.json](query-ui-open.json) mostrou painel, frame 0, gate editorial e respostas HTTP 200 do último plano e da inspeção. Nenhuma consulta de difusor local foi automática. Houve uma primeira requisição de último plano com status 0 e uma concluída com 200; não usamos interceptação nesta rodada. A chamada de clique sem aspas foi rejeitada pelo PowerShell/CLI antes de qualquer ação; a referência citada foi executada em seguida. A resposta concluída do último plano levou 20.271 ms e a inspeção 20.351 ms nesse contexto concorrente: a lentidão global **não foi resolvida**.

## Perfil da inspeção que ainda exige trabalho

[interface-a-profile.json](interface-a-profile.json) conserva o perfil anterior à mudança desta consulta: três frames, função local entre 1.175 e 1.330 ms, respostas HTTP diretas entre 2.897 e 4.044 ms. Cada resposta tinha 7.201.865 bytes. O perfil cumulativo local apontou cerca de 3.582 dos 3.759 ms em `_events`, principalmente hidratação/decodificação JSON. Tempos de cursor SQL excluem hidratação. O perfil é de processo separado com overhead de cProfile; não equivale ao tempo de CPU dentro do servidor.

`get_plan`, usado pelo vínculo da inspeção e pelos comandos, permanece byte a byte igual. Ele valida o histórico, escolhe a maior revisão e desempata pela ordem persistida. Cinco eventos deste plano somavam aproximadamente 24 milhões de caracteres; [event-sizes.json](event-sizes.json) registra comprimentos, sem duplicar payloads. A consulta corrigida aqui é `latest_plan`, chamada ao abrir a direção. Próxima investigação: custo de `get_plan` e do documento completo repetido por frame, preservando validação histórica, revisão, digests, seleção e compatibilidade dos leitores. Esta entrega não demonstra scrubbing interativo.

## Verificação e preservação

Passaram seis testes novos de seleção real em SQLite: escopo/tipo/documento e uma materialização; empate por timestamp/ID; ausência; último inválido; maior revisão/último empate em `get_plan`; histórico inválido em `get_plan`. Passaram quatro regressões existentes da API: comando/replay/undo, atomicidade na falha, revisão/identidade/autor e isolamento entre workspaces. Ruff passou no serviço e nos testes novos. Os testes usam o banco temporário isolado do conftest; não houve render novo nem chamada paga.

[preservation.json](preservation.json) confirma pela API que as composições e assets dos nove estudos são iguais aos snapshots originais, revisão 2/version 1. Os nove MP4s locais têm os hashes originais. As três comparações cegas continuam `not_assessed`, sem avaliação humana e com labels iguais. [sources.json](sources.json) fixa 85 fontes: as 80 anteriores intactas e cinco fontes adicionais. O backup conserva o arquivo sujo anterior completo, e o verificador comprova igualdade exata fora da função `latest_plan`.

[verification.json](verification.json) sela evidências desta rodada. Não há aprovação estética nem demonstração de autonomia. A limpeza antiga de clones continua pendente por rejeição automática anterior; não tentamos contorná-la nesta rodada.
