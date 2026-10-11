# Catálogo leve e leituras de materiais/qualidade — 05/10/2026

O snapshot global da aplicação agora usa um catálogo explicitamente resumido dos assets. Os 46 registros do laboratório chegaram pela API em **34.200 bytes**, com IDs, títulos/tipos/tags, escopo, URLs privadas, MIME, tamanhos, checksums e timestamps preservados. A listagem antiga continua integral; o novo detalhe por asset também retorna o `AssetOut` completo. Não apagamos/regravamos metadata, evidências ou projetos.

## O que causava o volume

[payload-sizes.json](payload-sizes.json) encontrou 175.307.305 caracteres de metadata em 46 assets ativos. [metadata-fields.json](metadata-fields.json) identificou `contextualEditing` como campo dominante, cerca de 156,5 milhões de caracteres, enquanto as partes usadas pelo catálogo e pela qualidade são pequenas. Essa é uma medida dos dados armazenados, **não** uma medição do tamanho HTTP antigo. Evitamos baixar novamente a listagem integral desse volume.

`editing_resources.catalog` usava somente `editingResource`, `visualReview` e `generationJobId`, mas materializava metadata inteira de todos os assets. A qualidade fazia a mesma leitura integral; a comparação fresca dos estudos também entrava em `_reference`, embora precisasse apenas de bindings, fontes, QC, direção e recibo específicos. Essas leituras agora usam views de leitura sem identidade ORM parcial.

## Compatibilidade e preservação semântica

[COMPATIBILITY.md](COMPATIBILITY.md) foi salvo antes das mudanças. Novo `AssetCatalogItemV1` adiciona schema `studio.asset-catalog-item.v1`, `metadataDetail=summary` e `fullMetadataPath`. `GET /assets/catalog` mantém tenant/active/ordem e preserva `sourceAssetId`, único campo de metadata lido pelo snapshot global atual (inventário completo de ocorrências em src). Nenhum campo desse resumo representa autorização de direitos ou QC. O cartão de derivação continua pendente quando há sourceAssetId.

`GET /assets/{asset_id}` lê um asset ativo com membership filtrada no banco antes da hidratação; devolve a mesma representação completa do serializer original. O corpo de `GET /assets`, upload, derivação, exclusão e conteúdo permaneceu igual por AST. Todos os schemas anteriores permaneceram iguais; há somente um modelo novo. Produto/renderer continuam usando o documento e leitores canônicos existentes.

No SQLite, a projeção lê valores/type markers das paths solicitadas. A implementação final usa `json_extract` com a path inteira para não reconstruir/citar um pai enorme numa consulta nested. Booleanos são preservados como booleanos, null é diferente de chave ausente, e valores que podem perder precisão (inteiro oversized/zero real com possível sinal) voltam ao leitor original. Containers inválidos, outros dialects ou sessão que já contém assets ORM também usam o caminho anterior. Nested mutations ainda não salvas conservam sua semântica anterior. Não há cache de rights/reviews. Fonte primária: [SQLite JSON — tipos e extração](https://www.sqlite.org/json1.html#the_json_type_function).

As views não são `LibraryAsset` e não entram na identity map. `_reference` mudou apenas o lookup do asset; checks de documento/revisão, escopo, lifecycle, MIME, checksum, job/snapshot/fontes/rights, formato/duração/áudio/QC e cálculo de digests/recibo ficaram iguais por AST. Importar/anexar materiais continua lendo os assets integrais.

## API real

Antes de recarregar a API, foram salvas duas respostas integrais pequenas do backend antigo. A API final retornou valores **idênticos** para recursos e qualidade, incluindo fases, bloqueios, revisão humana, orçamento e comparações cegas. [api-observation-final.json](api-observation-final.json) registra os checks; respostas anteriores/finais foram conservadas. O catálogo foi conferido por campos contra projeção escalar + serializer original, e o detalhe integral de uma fonte WOFF2 real foi comparado ao registro original.

| Consulta | API antiga desta rodada | API final | Bytes finais |
| --- | ---: | ---: | ---: |
| Catálogo explícito novo | não existia | 4.261 ms | 34.200 |
| Recursos | 7.568 ms | 3.454 ms | 16.700 |
| Qualidade | 6.488 ms | 3.592 ms | 24.195 |

Uma amostra sequencial por endpoint e por fase, não randomizada, não p95 ou garantia de aceleração. A primeira candidata, usando índices JSON nested genéricos, também foi conservada: catálogo 1.741 ms, recursos 1.462 ms e qualidade 5.674 ms. A variação entre amostras impede atribuir um percentual causal a cada alteração. O tamanho reduzido/seleção de campos e a igualdade de respostas são verificações exatas; CPU/RSS/IO de todo o sistema não foram medidos.

Houve dois reinícios próprios justificados por mudanças de fonte, após testes: API antiga 740 → candidata 20752 → final 7232. Nenhum ocorreu por timeout ou para ressuscitar job. A checagem anterior ao primeiro mostrou zero jobs queued/running/retrying. Não submetemos novos jobs, compras ou chamadas pagas.

## Interface real

No navegador próprio existente, a navegação nova mostrou cinco materiais e o MP4 1080×1920/15 s decodificado na primeira observação. O snapshot usou `/assets/catalog`, sem chamada à listagem bulk antiga. A linha `title` manteve target `ed2-895c9ff7a0a9ce1cb92ec080`. Nos frames 0/244/449, foram conferidos valor do input, texto do frame calculado, seleção, vídeo pausado sem seek pendente e tempos 0/8,133333/14,966666 s dentro de meio frame.

Recibos: [catalog-ui-initial.json](catalog-ui-initial.json), [catalog-ui-open.json](catalog-ui-open.json), [catalog-ui-frame244.json](catalog-ui-frame244.json), [catalog-ui-frame449.json](catalog-ui-frame449.json). [Captura do frame 449](catalog-ui-frame449.png) foi inspecionada visualmente. Nessa navegação, catálogo ~2.170/5.902 ms em duas chamadas, recursos ~4.676/6.181 ms, qualidade ~5.690 ms; inspeção 0/244/449 ~3.791/836/419 ms. A duplicação de leituras/concurrência continua visível e deve ser investigada. Não houve pedidos de 80–158 s nessa navegação, mas uma navegação não demonstra eliminação global da lentidão, scrubbing realtime ou qualidade comercial.

## Testes e fontes

Passaram 32 casos na fonte final: dez de catálogo/projeção/valores/acesso, seis guardas de referência com recibos **sintéticos** (não prova de render), e 16 regressões existentes de recurso/qualidade/estudos. TypeScript e Ruff passaram. A primeira execução ampliada apontou um arquivo de teste inexistente e não rodou casos; o comando foi corrigido usando os arquivos reais. Um lint de linha longa foi corrigido, sem enfraquecer assertions. A extração direta por path justificou repetir a matriz final; esse resultado é o qualificado. [validation-commands.json](validation-commands.json) registra os comandos/terminais.

Backups exatos de seis fontes sujas foram retidos antes da mudança. [sources.json](sources.json) fixa 109 fontes: 96 anteriores intactas e 13 adicionais; as seis modificadas não estavam na lista anterior e têm backups próprios. [preservation.json](preservation.json) confirma pela API composição/assets dos nove documentos iguais aos snapshots, revisão 2/version 1 e os nove MP4s originais por hash. As três comparações continuam `not_assessed`, review null e labels iguais. [verification.json](verification.json) sela esta rodada.

Revisão estética/humana, três briefs autônomos e limpeza de clones anteriormente recusada ainda estão pendentes. Não repetimos a exclusão por outro mecanismo. Nenhuma capacidade estética foi promovida por esses checks de software.
