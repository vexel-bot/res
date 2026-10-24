# Clicko · agentes e produção local

Implementação de 22/10/2026. Complementa a Etapa 1; não substitui os projetos,
conexões, histórico, autenticação ou motores existentes.

## Responsabilidades e execução

```mermaid
flowchart LR
  U[Conversa única da KLIC] --> B[BFF: sessão e permissões]
  B --> O[Orquestrador Studios]
  O --> A[Agente audiovisual]
  O --> I[Agente visual]
  A -->|Solicita cartões editáveis| I
  A --> P[Documento canônico versionado]
  I --> P
  P --> V[Revisão e aplicação de comandos]
  V --> F[Timeline FFmpeg: MP4]
  V --> R[Composição Pillow: PNG]
  F --> L[Biblioteca privada e exportações]
  R --> L
  O -->|Tarefa e projeto vinculados| U
```

- **KLIC:** mantém Gemini, conversas, arquivos, voz e permissões. Pedidos explícitos
  de criação de motion/vídeo/imagem e alterações de um projeto em contexto podem
  seguir para a produção local. O modo **Produção local** permite escolher esse
  caminho explicitamente. Perguntas informativas continuam na conversa normal.
- **AudiovisualAgent:** planeja cenas de motion e operações de edição. No adaptador
  por regras, solicita os cartões ao `ImageAgent` e registra as solicitações no
  ledger de eventos. Em um comando simples de título/cor/duração não registra
  falsamente uma delegação ao agente visual.
- **ImageAgent:** planeja composições e fornece formas editáveis ao audiovisual;
  usa assets do próprio workspace. Não depende de um gerador de fotografias.

Os dois especialistas têm bindings de modelo independentes por workspace.
`local_agents.py` contém adaptadores por regras e os papéis distintos;
`agent_orchestrator.py` decide o papel, limita as operações, registra e aplica o
resultado. **Adaptador por regras não é um LLM e não comprova autonomia de IA.**

## Reaproveitamento e contratos

Persistência permanece em `CreativeDocument`, `StudioDomainEvent`,
`StudioGenerationJob`, `StudioLLMConnection` e `LibraryAsset` existentes.
Não há banco de projetos paralelo, novo chat ou SDK de modelos duplicado.

O formato editável continua `CreativeDocumentV1`/`CreativeCompositionV1`, com
`CreativeLayerV1` e `MediaTimelineV1`. O perfil estrito
`studio.local-layer.v1` define propriedades executáveis de texto/forma/imagem;
não é um projeto nativo Craft e não reativa endpoints de edição aposentados.
O MP4 é uma exportação, nunca a representação do projeto.

Operações admitidas:

| Operação | Efeito validado |
| --- | --- |
| `composition.replace` | Subconjunto local completo, mantendo identidade e assets do documento |
| `layer.upsert` / `layer.remove` | Texto, forma ou imagem; camadas bloqueadas são preservadas |
| `project.background` | Cor hexadecimal explícita |
| `project.duration` | Reescala tempos e keyframes de motion sem clipes de mídia; mantém IDs |
| `timeline.replace` | Timeline canônica, com seus limites, referências e streams |
| `asset.attach` | Referência a arquivo privado existente do mesmo workspace |

Somente o backend aplica. Schema, dimensões, duração, quantidade de camadas,
keyframes, texto que cabe na caixa, checksums, acesso aos assets, bloqueios e
revisão atual são verificados. Não são aceitos scripts, plugins, filtros enviados
pelo usuário, URLs externas ou caminhos locais como comandos.

## Ciclo da tarefa e recuperação

1. Criar ou selecionar documento com a sessão normal.
2. Enviar briefing com revisão esperada e `Idempotency-Key`.
3. Registrar um `agent_plan` antes da execução do planejador. Replays retornam a
   mesma tarefa; uma submissão inconclusiva não dispara inferência automática.
4. Validar o plano, registrar a origem (`none`/`local_model`) e as delegações reais.
5. Mostrar operações/rationale para revisão. Planejar não altera a composição.
6. Aplicar sobre a revisão vinculada. A mesma aplicação retorna o recibo original;
   conflito com edição posterior é recusado.
7. Guardar snapshot anterior, incrementar versão/revisão e invalidar aprovação.
8. Renderizar com o job canônico existente. PNG local usa operação síncrona
   limitada/idempotente; MP4 conserva a fila, cancelamento e recuperação existentes.

`agent_plan` não é um job de mídia executável/repetível pelo worker. No reinício,
o mecanismo existente marca planos interrompidos como falhos, sem reenviar o
modelo. A interface conserva rascunho e operações sem confirmação no escopo
usuário/workspace/módulo; repetir confirmação reutiliza a chave original.

## Rotas autenticadas

Base `/api/v1/studios/v1`:

- `GET/PUT /agents/roles?workspace_id=...` (alteração exige proprietário/admin).
- `POST /agents/projects` (criação idempotente de projeto local vazio).
- `POST/GET /documents/{id}/agent-tasks`.
- `POST /documents/{id}/agent-tasks/{taskId}/apply`.
- `POST /documents/{id}/local-commands`.
- `GET /documents/{id}/local-preview?frame=...` (PNG exato de camadas locais;
  projetos com vídeo/sobreposições de mídia usam a exportação canônica).
- `POST /documents/{id}/local-image-export`.

MP4 usa `/video/documents/{id}/render-jobs`; histórico, restauração, importação e
conteúdo dos assets continuam nas rotas existentes. O BFF não aceita bearer de
browser para fingir sessão: revalida acesso e assina a mesma ponte Studios.
O escopo operacional geral da KLIC continua excluindo leitura ampla de mídia;
somente a referência do projeto selecionado cruza o novo encaminhamento.

## Capacidades e limites atuais

Motion: criação textual por modelo determinístico de até três cenas, cartões,
títulos, formas, camadas, cor/gradiente, posição, opacidade, escala e rotação,
keyframes e easing linear/ease-out/ease-in-out. Cenas de modelo aceitam 3–120 s.
O renderer canônico mantém seu limite geral de 600 s, 32 itens e até 1920 px;
camadas locais têm limite de 24 dentro desse total. O título continua texto
editável, mesmo sendo rasterizado temporariamente para o encoder.

Vídeo: preservados cortes, trim, texto/legendas fornecidos, fades, sobreposição,
áudio, ganho, áudio original, exportação e jobs do editor canônico. O comando
local de duração não estica arbitrariamente clipes/áudio; isso deve ser ajustado
no editor. A prévia Canvas de edição não é a prévia exata de todo o compositor de
vídeo; para mídia, a referência final é o MP4 do compilador FFmpeg.

Imagem: importação privada, crop normalizado, resize pela geometria da camada,
brilho/contraste/saturação, texto, formas, ordem/opacidade/rotação, composição e
PNG. Original imutável; arquivo exportado novo e versão anterior preservada.

Ainda indisponíveis: segmentação/remoção automática de fundo, geração de cenas
cinematográficas, fotogeração local, transcrição nova sem ASR operacional,
transições/effects nativos arbitrários, motion 3D real, câmera 3D e garantia de
qualidade de interpretação livre. PhotoCraft/FilmCraft/EffectCraft mantêm seus
projetos e caminhos avançados, mas continuam dependentes dos artefatos ausentes.

## Controle de custo

O caminho novo só admite ferramentas locais ou Ollama `local_free`, loopback,
sem credencial, cabeçalhos extras ou redirecionamento. Não aceita modelos `cloud`.
Antes de planejar, consulta `/api/show` para exigir metadados de pesos locais já
instalados; não chama `pull`. O adaptador UniversalLLM já existente envia schema
JSON, não usa streaming/retry oculto e descarrega o modelo após o pedido local.
O limite de entrada é 24 mil caracteres e a saída, até 3 mil tokens.

Uma conexão local não prova desempenho/qualidade: isso exige homologação com o
modelo real. Gemini gratuito não foi presumido nem habilitado. KLIC/TTS e
provedores pagos conservam a autoridade financeira da Etapa 1. Templates locais
não usam créditos de inferência; a conversa Gemini normal conserva sua regra.

## Incremento da Etapa 2

Na revisão de conclusão, a seleção passou a ser uma restrição de execução:
planos não podem modificar outra camada nem transformar a edição selecionada em
operação global. Essa validação é repetida antes de uma mutação nova. Recibos já
comprometidos e com fingerprint idêntico continuam apenas retornando o resultado
anterior, sem executar uma operação. Use o controle de desmarcar para alterar o
projeto inteiro. Duração da animação, título literal e cenas inexistentes têm
regras/testes próprios; perguntas informativas não são comandos de edição.

`AgentTaskRequest.selectedLayerIds` é opcional, limitado e validado no documento.
O mesmo contexto passa por painel/KLIC/backend; pedidos ambíguos não escolhem
automaticamente um título. Consulta individual de tarefa retorna responsável,
datas, limites, eventos e recibo da revisão aplicada. Replays antigos sem seleção
mantêm o fingerprint anterior.

O estilo `studio.local-layer.v1` aceita peso 400/700 e revelação por palavras,
com intervalo em quadros. Texto continua em uma camada canônica; Pillow e o
compilador FFmpeg compartilham layout, e a máscara temporal é aplicada antes das
transformações. O Canvas oferece a prévia de edição correspondente. Retiming
atualiza cenas, keyframes e intervalo das palavras. O canvas legado recebe uma
projeção compatível, sem modificar o documento canônico.

Veja o [relatório da Etapa 2](../audits/STAGE2_AGENT_EXPERIENCE_2026-10-22.md) para
comandos, biblioteca compartilhada, teste de conversa com backend real, dois MP4s
de 15 s e limites de homologação. Isso não constitui inferência real comprovada.
