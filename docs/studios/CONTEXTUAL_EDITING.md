# Motor de edição contextual — implementação inicial

O estúdio possui um caminho de edição contextual separado do fluxo UGC anterior. A entrada continua sendo um `CreativeDocument` com materiais e timeline. A direção editorial produz um plano persistido; o vídeo é renderizado pela fila existente e fica disponível para revisão. Não existe publicação automática nem aprovação humana fabricada.

## Uso no estúdio

Abra o estúdio de vídeo e a aba **Revisão → Edição com intenção**. Informe objetivo, ritmo e prioridade. Em **Direção por cena**, relacione materiais de apoio que já estão no documento e, opcionalmente, texto. **Criar vídeo com esta direção** planeja, verifica, aplica e solicita o render quando não há impedimentos.

A direção por cena também oferece transcrição, legendas da fala, início/fim na origem, ordem das cenas, máscara do apoio e referência do repertório. O catálogo inclui fichas importadas no workspace. Campos de intervalo vazios preservam o trecho atual.

Quando faltar um recurso ou material, as alternativas aparecem antes da aplicação. Escolher aguardar mantém o bloqueio. Remover um complemento requer escolha explícita; o sistema não descarta operações silenciosamente. Problemas de direitos ou orçamento não podem ser ignorados.

Quando reduzir a resolução for suficiente para caber no orçamento, o sistema oferece as dimensões alternativas. Só a escolha do cliente aplica essa redução; duração e conteúdo permanecem preservados.

A prévia da timeline existente continua sendo uma prévia dos materiais. O MP4 na aba de renderização é a referência para avaliar camadas, máscaras, áudio e texto final.

## Interfaces

Prefixo: `/api/v1/studios/v1`. Todas as operações exigem autenticação; documentos e conhecimento permanecem restritos ao workspace.

| Método e caminho | Comportamento |
| --- | --- |
| `GET /editing/capabilities` | Capacidades e limites do adaptador contextual local |
| `GET /editing/repertoire?workspace_id=…&query=…` | Fichas iniciais e busca no conhecimento existente |
| `POST /editing/observations?workspace_id=…` | Ingestão manual de técnica, fonte, timestamps e métricas datadas; acesso de governança |
| `POST /documents/{id}/editing-plans` | Cria plano com revisão esperada e `Idempotency-Key` |
| `GET /documents/{id}/editing-plans/latest` | Recupera o plano mais recente, incluindo após recarregar a página |
| `POST /documents/{id}/editing-plans/{plan}/choices` | Registra a escolha de uma alternativa com revisão esperada |
| `POST /documents/{id}/editing-plans/{plan}/feedback` | Ajusta as cenas selecionadas |
| `POST /documents/{id}/editing-plans/{plan}/apply` | Aplica somente plano viável sobre o documento original vinculado |
| `POST /video-renders` | Aceita `provider=builtin.ffmpeg-contextual-v1` e `contextualPlanId` aplicado |

Exemplo de planejamento:

```json
{
  "expectedDocumentRevision": 3,
  "intent": {
    "objective": "Mostrar o detalhe do produto enquanto explico sua utilização",
    "format": "tutorial",
    "script": "Texto original, incluindo ressalvas.",
    "lockedFacts": ["Texto que deve permanecer factual"],
    "emphasis": "auto",
    "pacing": "calm",
    "reducedMotion": false,
    "preserveMessage": true
  },
  "beats": [{
    "id": "demonstracao",
    "clipId": "clip-existente",
    "purpose": "Permitir observar o detalhe explicado",
    "supportAssetId": "material-existente-no-documento",
    "supportSourceStartMicroseconds": 0,
    "onScreenText": "Detalhe de utilização"
  }],
  "requiredTechniques": []
}
```

O planejador atual é determinístico e conservador. A prioridade `auto` reconhece um vocabulário limitado de objetivos; os demais casos preservam a mensagem. Não é um modelo de compreensão universal de roteiros. Ele preserva trechos completos, não gera diálogo e não remove palavras de uma fala. Roteiro e fatos ficam registrados no plano; não há certificação automática da verdade das afirmações ou da qualidade narrativa.

O apoio visual precisa estar associado à cena. A presença de uma fotografia de rosto não constitui vídeo de apresentador. Materiais gerados são admitidos apenas com resultado de job correspondente e verificações de origem/consentimento, sem relabelar a origem como upload.

### Seleção, ordem e transcrição

`clipOrder` aceita uma permutação completa dos clips da trilha principal. A montagem exige uma trilha principal contínua e desbloqueada; os elementos vinculados inteiramente a cada cena acompanham a nova posição. Faixas que atravessam cenas e não podem ser remapeadas com segurança geram impedimento. A ordem é uma direção explícita do cliente, não uma inferência automática de relações narrativas.

Cada beat pode usar `transcriptId`, `transcriptRevision`, `captionFromTranscript` e `sourceDecisions`. As decisões reutilizam `EditDecisionV1` (`keep`, `remove`, `marker`). O caminho contextual valida sua execução como política de rascunho; não muda decisões sugeridas para aceitas nem fabrica revisão humana.

Seleções de origem exigem transcrição previamente revisada e um intervalo contíguo que retenha integralmente todos os segmentos falados do trecho original. A implementação pode encurtar margens sem fala transcrita; não escolhe automaticamente frases dispensáveis. Remover negação, ressalva ou outro segmento transcrito bloqueia o plano. A alternativa **Manter a montagem original** conserva os intervalos e a ordem sem descartar os complementos independentes.

As legendas usam os tempos dos segmentos ou palavras disponíveis, convertidos conforme origem, posição e velocidade do clip. Nenhum texto novo é inferido. Segmentos incompletos e tempos que não cabem na precisão da timeline geram impedimento. Transcrições ficam vinculadas por workspace, asset, revisão e digest; alterações posteriores invalidam aplicação e render.

Exemplo de campos adicionais de um beat:

```json
{
  "id": "explicacao",
  "clipId": "clip-existente",
  "purpose": "Preservar a explicação e sua ressalva",
  "transcriptId": "transcricao-existente",
  "transcriptRevision": 2,
  "captionFromTranscript": true,
  "sourceDecisions": [{
    "id": "intervalo",
    "operation": "keep",
    "startMicroseconds": 200000,
    "endMicroseconds": 1800000,
    "status": "suggested"
  }]
}
```

## Composição executável

O novo adaptador usa FFmpeg para composição/codificação e Pillow para rasterização de texto. HyperFrames permanece disponível no caminho já existente; não foi substituído nem ganhou capacidades novas implicitamente.

| Recurso | Implementação e limite |
| --- | --- |
| Cortes e ordem | Intervalos e posição dos clips na timeline canônica; não há reescrita automática da fala |
| Múltiplas trilhas | Vídeo e imagens em trilhas `video`/`overlay`; ordem das trilhas determina a sobreposição |
| Áudio original | `video.muted` desliga somente áudio embutido; a imagem continua visível |
| Enquadramento | `fit=cover/contain`, posição, dimensões, escala, rotação fixa e crop proporcional |
| Máscaras | `MaskTrackV1` com imagem estática em escala de cinza; uma máscara por trilha, no espaço do clip |
| Keyframes | Contrato `MotionTrackV1` em `clip.keyframes`, posição X/Y, interpolação `linear` ou `hold`; frames relativos ao clip |
| Transições | Efeito `fade` com `inFrames`/`outFrames`; dissolve por sobreposição dos clips |
| Congelamento | Efeito `freeze`; mantém o frame no início do intervalo de origem |
| Velocidade | `playbackRate`, entre 0,5x e 2x; áudio usa ajuste de tempo |
| Cor | Efeito `color` com exposição, contraste e saturação |
| Texto e legendas | Camadas de texto/retângulo e `CaptionTrackV1`; texto rasterizado, overflow impede render |
| Mixagem | Ganho, pan, fades; papéis `dialogue`, `narration`, `ambience`, `effect`, `music` |
| Música durante fala | Compressão por sidechain; normalização de referência para -16 LUFS e teto de -1,5 dBTP |
| Silêncio | Faixa silenciosa quando não há áudio; sua adequação exige revisão editorial |

Exemplos de parâmetros em um clip:

```json
{
  "effects": [
    {"kind": "color", "exposure": 0.2, "contrast": 1.05, "saturation": 0.9},
    {"kind": "fade", "inFrames": 8, "outFrames": 8}
  ],
  "keyframes": [{
    "trackId": "entrada",
    "targetLayerId": "id-do-clip",
    "property": "position_x",
    "unit": "pixels",
    "keyframes": [{"frame": 0, "value": -20}, {"frame": 12, "value": 0}]
  }]
}
```

Perfil inicial: um canvas, MP4/H.264/AAC, dimensões pares até 3840, até 60 fps, até 100 clips/camadas ativos e 500 cues de legenda. A duração máxima aceita é 30 minutos, mas isso é um limite de admissão, não uma garantia de tempo, memória ou qualidade para qualquer composição. O benchmark automatizado usa vídeos curtos; capacidade de produção exige medição no worker de destino.

Tracking, rotoscopia, máscaras temporais, rampas de velocidade, estabilização e 3D continuam indisponíveis neste adaptador. Easing e propriedades de animação fora do subconjunto descrito também geram impedimento. A lista de capacidades é um registro de implementação, não uma promessa de suporte universal.

Na versão 1.1.0, máscaras multiplicam o alpha original pela máscara: áreas transparentes da imagem e do ajuste `contain` continuam transparentes. Os testes verificam os pixels dessas bordas, além da área mascarada.

## Repertório e atualização

As fichas iniciais cobrem continuidade, demonstração, profundidade, revelação por estados, movimento dirigido, texto, prioridade da fala e pausa. Os exemplos de Instagram preservam fonte e intervalos observados; áudio não verificado permanece identificado assim.

`KnowledgeDocument`/`KnowledgeChunk` e a busca híbrida existentes são reutilizados. Este caminho usa busca lexical, sem chamadas de embeddings ou LLM. Cada conteúdo tem hash de deduplicação; observações de métricas ficam datadas e preservadas separadamente dos chunks. Ingestões repetidas não duplicam a mesma observação.

Não há monitor automático dos perfis nem conector oficial ativo nesta entrega. A coleta é manual. `lastSuccessfulIngestAt` descreve ingestão no sistema; não significa que o perfil foi consultado naquele momento. `lastObservedAt` identifica a observação importada. Métricas não são evidência causal de que um efeito gerou desempenho. Ingestão não é treinamento de modelo.

Fontes técnicas: [filtros do FFmpeg](https://ffmpeg.org/ffmpeg-filters.html). As observações visuais remetem diretamente aos posts nas fichas. Princípios editoriais incorporados são políticas conservadoras desta implementação, sem alegação de validação experimental pelos posts.

`referenceTechniqueIds` seleciona referências explícitas. Uma ficha pode declarar `compositionProfile`, com proporções do apoio e entrada `none`, `fade` ou `slide`. Só esses parâmetros tipados alteram a composição; texto recuperado nunca é executado. Um perfil se adapta às dimensões do projeto e respeita movimento reduzido. Perfis incompatíveis, materiais ausentes e capacidades não utilizadas geram alternativas antes do render.

`editorialEvidence` diferencia referências solicitadas de resultados apenas recuperados, registra digest, fontes e idade da observação. A etiqueta `recent` usa uma janela operacional de 30 dias; ela não prova que a técnica está em tendência. Registros mais antigos são históricos. Uma nova observação de métricas não altera a ordem das versões de uma ficha, definida pela criação da versão.

## Persistência, custos e revisão

Planos e alterações são eventos versionados na infraestrutura já existente. Não há nova tabela ou migração. A aplicação exige vínculo com documento, revisão, conteúdo e checksums. Renderização revalida o vínculo antes e depois de processar; uma edição concorrente impede promover um resultado obsoleto como o resultado atual.

O worker cruza as operações com os IDs de camadas, legendas e faixas de áudio relatados pelo compilador. Cobertura incompleta impede aceitar o resultado. Cada operação recebe um registro em `operationChecks`; isso verifica execução e omissões autorizadas, sem afirmar que a intenção editorial foi comprovada por análise perceptual do MP4. O arquivo também passa pela verificação técnica existente.

O plano aplicado continua sendo rascunho. A revisão final do estúdio permanece vinculada ao arquivo renderizado. As três ações de feedback operam nas cenas selecionadas e nas camadas criadas pelo planejador; não alteram a faixa original de fala. Uma correção não resolve silenciosamente um impedimento diferente.

Configurações novas, em centavos:

```dotenv
STUDIO_EDITING_MONTHLY_BUDGET_CENTS=50000
STUDIO_EDITING_INFRASTRUCTURE_RESERVE_CENTS=15000
STUDIO_EDITING_ESTIMATED_CENTS_PER_MINUTE=50
```

O teto é compartilhado pela instalação. A estimativa considera duração, resolução e composição. Não é preço aferido de um provedor nem medição de toda a fatura: os R$150 são uma reserva configurável para infraestrutura. Não há chamadas pagas externas nesta edição. A reserva é conservadora, transacional e idempotente; tentativas repetidas do mesmo job não geram nova reserva. Reservas não consumidas não são liberadas automaticamente nesta versão. Tempos efetivos de render e tamanho do arquivo ficam no resultado para calibrar a estimativa.

O novo renderizador limita decodificação e codificação a duas threads, além de uma thread de composição. O pipeline não chama GPT em produção nem introduz serviço permanente de GPU.

## Validação

`backend/tests/test_contextual_editing.py` cobre contratos, API, isolamento entre workspaces, revisão concorrente, idempotência, orçamento, ingestão de métricas e execução real com FFmpeg. Os testes de render inspecionam pixels de máscara/posição e frequências do áudio para conferir a redução da música durante fala. Incluem formatos quadrado, vertical e horizontal, legenda, congelamento, velocidade, cor e fades.

`tests/e2e/contextual-editing.spec.ts` verifica no navegador que uma alternativa precisa ser escolhida antes da aplicação/renderização do rascunho. A integração real com o worker é testada separadamente no backend.

Os testes de backend existentes recriam o banco de testes do diretório corrente. Execute-os em um diretório temporário, com `PYTHONPATH` apontando para `backend`, para preservar bancos locais já existentes. Execute navegador e renders em sequência em máquinas com pouca memória.

Ainda é necessária avaliação humana com entrevistas, aulas, anúncios e narrativas reais antes de declarar qualidade editorial geral. Os sinais técnicos e as decisões registradas tornam essa avaliação rastreável; não a substituem.

### Verificação local em 05/09/2026

- 25 testes do novo motor passaram, incluindo renderização real e rejeição de cobertura incompleta.
- A bateria de regressão de render UGC, áudio natural, revisão editorial, HyperFrames e contratos de inteligência passou, com um teste ignorado.
- O teste Chromium de escolhas e resposta assíncrona antiga passou. Uma tentativa anterior falhou por `ERR_INSUFFICIENT_RESOURCES`; a repetição isolada passou.
- `npx tsc --noEmit --pretty false`, Ruff dos arquivos novos e `npm run build` passaram. O build continua emitindo aviso de bundle acima de 500 kB.

Esses resultados não qualificam tracking, rotoscopia, análise semântica automática de falas ou monitoramento contínuo dos perfis. Também não representam medição de capacidade mensal no ambiente de produção.

### Galeria técnica reproduzível

`backend/scripts/qualify_contextual_editing.py --output <diretorio-vazio>` gera sete composições curtas, os MP4s, documentos canônicos, relatório JSON e galeria HTML. Execute com `PYTHONPATH` apontando para `backend`. Não acessa APIs, não usa materiais de clientes e não modifica o banco.

Os cenários exercitam layouts de apresentação, tutorial de tela, entrevista, demonstração, narrativa com arquivo, fotografias e vídeo sem fala. São padrões visuais e tons sintéticos, com durações de 2 a 4 segundos, não entrevistas ou apresentações humanas. Tempo medido é o de render local desse material; não extrapole volume mensal, custo de produção ou qualidade de voz a partir dele. A avaliação humana de narrativa, clareza e adequação permanece pendente.

### Fechamento técnico em 06/09/2026

- 51 testes passaram e 1 foi ignorado na bateria de edição contextual, transcrições/decisões, UGC, HyperFrames e jobs de render. Destes, 32 pertencem ao motor contextual.
- O teste Chromium passou com `npx playwright test --config=playwright.contextual.config.ts`. Ele compila o componente real e simula a API, sem iniciar o backend ou HMR. A integração real com a fila e o worker está coberta no backend, inclusive seleção de origem com legendas e recibo de operações.
- A configuração isolada evita o consumo dos servidores completos: as tentativas anteriores no ambiente de desenvolvimento falharam por falta de memória e reinicialização de conexão antes de exercitar o componente.
- Ruff dos arquivos de edição, verificação TypeScript e `npm run build` passaram. O build mantém o aviso de bundle acima de 500 kB.
- A galeria final está em `artifacts/validation/contextual-gallery-20260906/index.html`, com `report.json`, sete documentos e sete MP4s. Essa geração usa o renderizador 1.1.0 e substitui a galeria técnica anterior à correção de alpha.
- Os sete renders levaram de 1.219 a 2.312 ms nesta execução local, com R$0 em APIs externas. O relatório separa tempo medido de reserva estimada.

Esta entrega fecha o caminho de composição contextual e revisão com seleção conservadora, transcrição vinculada, referências parametrizadas e execução verificada. Compreensão semântica universal, seleção automática de frases dispensáveis, conectores sociais oficiais e as técnicas avançadas listadas continuam fora das capacidades qualificadas. Não são silenciosamente usados como fallback nem tratados como concluídos por estes testes.
