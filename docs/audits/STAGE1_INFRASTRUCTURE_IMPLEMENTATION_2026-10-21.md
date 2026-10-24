# Clicko · Etapa 1 — estabilização da infraestrutura audiovisual

**Data:** 21/10/2026. **Checkout:** `C:\Users\pedro\Downloads\res`.
**Escopo:** implementação local, gratuita, com dados de QA próprios. Sem deploy,
migração destrutiva, ativação de fornecedor pago, compra, commit ou push.

## Conclusão executiva

Express e FastAPI Studios iniciam por um único comando, com persistência isolada,
prontidão real e encerramento dos processos próprios. O FFmpeg canônico foi
preservado; UGC/animatic passou a compartilhar sua descoberta de ferramentas e
seleção de encoder. Foi produzido um MP4 de 18 s e, pelo serviço HTTP em execução,
importado/reeditado/reexportado um MP4 de 16 s. Vídeo e imagem foram recuperados
após reinício com os mesmos checksums. O vídeo final reproduziu até o fim no navegador.

KLIC/Gemini Node e Cloud TTS agora exigem admissão no mesmo ledger financeiro
transacional do Python Studios. Não foi executada inferência nem síntese paga.
**Infraestrutura local comprovada não equivale a plataforma inteira homologada:**
Craft compilado, processamento distribuído, benchmarks ausentes e geração remota
permanecem com os bloqueios detalhados abaixo. A suíte global não está aprovada.

## A. Correções realizadas

### Inicialização e processos

- `scripts/dev-local.mjs`, `package.json`: comandos `dev:local`, `dev:status`,
  `dev:stop`; portas 3018/8018 loopback, verificação de ocupação, diretório privado
  de QA, segredos locais próprios, deadline de startup e IPC de encerramento.
- `server/studios/runtime.ts`, `backend/app/local_studio_server.py`, `server.ts`:
  processo Python com canal stdin de encerramento; falha de prontidão não é
  considerada sucesso; limpeza do processo próprio e Vite no encerramento/erro.
- `server/klic/store.ts`, `conversations.ts`, `server/radar/history.ts`: caminhos
  de armazenamento configuráveis para que o perfil isolado não escreva nos dados
  usuais. Nenhuma mudança de aparência ou regra de acesso nesses módulos.

### Processamento e contratos

- `backend/app/services/studios/ugc_acceptance.py`, `ugc_no_voice.py`: removidas
  buscas exclusivamente pelo PATH para FFmpeg/FFprobe; utilização de
  `media_runtime.resolve_tool` e `h264_encoder`. libopenh264 não recebe parâmetros
  exclusivos de libx264. Caminho explícito inválido continua falhando fechado.
- `backend/app/routers/editing_resources.py`: benchmark visual ausente gera 503
  com `visual_quality_baseline_unavailable`, não 500 nem aprovação inventada.
- Correções sem mudança funcional das 11 ocorrências Ruff em contratos,
  `editorial_production`, `image_edit`, `motion_canvas_projection`,
  `editorial_components` e `production_audit`.
- Fixtures dos testes de LLM passaram a declarar envelopes mensais/modelos
  explícitos. Seis testes unitários de alocação por categoria isolam a fronteira
  mensal com spy e verificam sua chamada; **não** são testes do ledger SQL.
  Esse ledger é exercitado separadamente com transações reais, concorrência,
  identidades distintas e passagem de mês. Nenhum benchmark fictício foi criado.

### Financeiro e preparação de IA

- `server/finance/admission.ts`, `gemini.ts`: contexto autenticado, JWT interno,
  reserva/claim antes do SDK, limites de saída e coleta de uso/estimativa.
- `server/klic/provider.ts`, `server.ts`: todos os caminhos Gemini dessas fábricas,
  incluindo streaming, transcrição e ferramentas antigas, usam o guard financeiro.
- `server/voice/providers/googleCloudTtsProvider.ts`, `server/voice/router.ts`:
  admissão antes da criação/chamada do cliente TTS, sem retry oculto; diagnósticos
  sem payload bruto do provedor. Crédito não é apresentado como USD.
- `backend/app/routers/internal_finance.py`, `studio_bridge_key.py`,
  `services/studios/external_policy.py`, `config.py`: mesma tabela/lock das reservas
  Studios, tetos positivos, modelo, tarifa versionada, claim único e retenção de
  submissões incertas, inclusive históricas `pending` na passagem de mês.
- `jobs.py`, `routers/studio_video.py`: recibos financeiros não executáveis por
  workers e excluídos da recuperação de jobs CPU. `server/studios/bridgeKey.ts` e
  `proxy.ts` compartilham a leitura segura da chave; audiência financeira é distinta.
- `server/klic/router.ts`: mensagem/anexos inválidos são recusados antes do consumo
  comercial do chat operacional.
- `backend/app/services/ai.py`, `routers/ai.py`: o adaptador Python antigo, que não
  recebe escopo financeiro durável, falha fechado. Não reabilitar só com API key.
- `services/studios/model_lifecycle.py`, `providers/studios/editing_ai.py`,
  `llm_catalog.py`: avisos oficiais de retirada, recusa de modelo aposentado e ID
  exato de Claude Opus via OpenRouter, sem ativação ou substituição automática.

Documentos e scripts de evidência: `scripts/craft/runtime_preflight.py`,
`scripts/video/stage1_acceptance.py`, `triage_stage1.py`, README, CHANGELOG e
os dois guias de operação em `docs/operations/`.

O checkout já continha muitas alterações de trabalhos anteriores. Elas foram
preservadas; o inventário acima descreve esta etapa, não atribui toda a diferença
Git a ela. Datas dos arquivos usuais de clientes permaneceram anteriores à execução.

## B. Infraestrutura

Perfil validado: `npm run dev:local`. Banco SQLite e arquivos em
`.codex-runtime/stage1-local`, separados de `.clicko-data`. Express em
`127.0.0.1:3018`; FastAPI em `127.0.0.1:8018`. Sessão/RBAC/licença normais continuam
obrigatórios no navegador; não foi usado bypass de login. O ensaio HTTP de mídia
usa a ponte serviço-a-serviço de QA e não homologa a assinatura comercial do BFF.

Evidências:

- `/api/ready` retornou 200 com `studios: ready` e armazenamento local identificado.
- Encerramento pelo supervisor produziu shutdown normal do Uvicorn.
- Uma segunda inicialização na porta ocupada foi recusada; a instância existente
  continuou pronta, sem matar processo alheio.
- Após queda deliberada do **processo FastAPI de QA identificado pela cadeia de
  processos**, Express retornou 503 e `studios: not_ready`.
- Reinício recuperou banco, revisão e bytes dos dois ativos. O perfil termina com
  os serviços principais prontos e todas as flags de geração paga desativadas.

Logs: `.codex-runtime/stage1-local-*-service.log`, `stage1-unavailable-evidence.json`,
`stage1-port-conflict.log`. Nenhum `.env` foi sobrescrito.

## C. Sistema de vídeos

**Comprovado localmente:** upload privado, projeto, timeline, trim/cortes,
texto, fades, keyframes suportados, trilha própria, áudio original ligado/desligado,
jobs, renderização H.264/AAC, validação de saída, download, isolamento e persistência.

1. `test_media_final_validation.py`: referência própria de 18 s, três cenas,
   títulos, gráfico animado e trilha harmônica PCM, com checagens técnicas/pixels/áudio.
2. `scripts/video/stage1_acceptance.py create`: upload dessa referência e de PNG,
   edição com dois cortes de 8 s e texto animado, renderização pelo executor local
   **real**, replay com o mesmo job e exportação dos arquivos.
3. O MP4 final tem **16,000 s, 1280×720, 30 fps, H.264, AAC 48 kHz**. Áudio e vídeo
   iniciam em 0,000 s e têm a mesma duração. Decode integral com FFmpeg terminou
   sem erro; o player HTML5 chegou a 16 s, `ended=true`, `readyState=4`, sem media error.
4. Reinício normal e posterior queda/reinício do serviço preservaram o checksum
   `fcf25fafda55a4acb0e72e4340df664d65639e97255e1865d7720184171fbf81` e a revisão 2.

Arquivos em `.codex-runtime/stage1-validation/`: `publicidade-local-18s.mp4`,
`live-export-16s.mp4`, `live-evidence.json`, `browser-evidence.json`,
`browser-playback-16s.png`. Decode/sincronismo técnico:
`.codex-runtime/stage1-decode-evidence.log`.

Isso é **edição determinística**, não geração de cenas por IA. A audição/avaliação
humana artística da trilha não foi certificada. FilmCraft nativo não foi substituído
pelo FFmpeg: são dois caminhos distintos, e o primeiro segue bloqueado por runtime.

## D. Sistema de imagens

Upload, validação de bytes, armazenamento privado, recuperação/exportação,
checksum, isolamento e persistência foram comprovados nas operações locais
disponíveis. O teste de imagem preserva a referência 4:5 de 960×1200; o teste
HTTP baixou o mesmo PNG depois de reiniciar o serviço.

`live-image-export.png`: SHA-256
`32842cae3e3ed8e6652f0614c7528386edbdedf42b6c8cfb3e683561aca14380`.
Proporção/resolução do adaptador Gemini, rejeição de candidato incompatível e
admissão comercial têm testes de contrato **offline**, não geração remota.
PhotoCraft compilado, remoção de fundo com modelo verificado e benchmark de
preservação de identidade não foram apresentados como disponíveis sem seus runtimes.

## E. Motores Craft

`scripts/craft/provenance.py` verificou inventário e hashes de todos os arquivos:

| Motor | Versão e revisão fixada | Fontes | Estado nesta máquina |
| --- | --- | --- | --- |
| PhotoCraft | 0.7.0 · `a7f26522ff84cd427c8a5d54b0e8ded7b56fb296` | 1.569 | Bloqueado: sem build nativo/WASM |
| FilmCraft | 0.6.0 · `0800a8b0aa4a703ba42172f415b45a61f8d8a5e1` | 1.236 | Bloqueado: sem build nativo/WASM |
| EffectCraft | 0.8.0 · `67434e90388b6dca4417555346fa6850b6f96033` | 1.016 | Bloqueado: sem build nativo/WASM |

Também verificados craft-libs (41 arquivos), craft-fonts (25) e FilmCraft compatível
antigo (951), sem trocar revisões ou licenças. Preflight confirmou Docker ausente;
`build.py` recusou execução antes de baixar/compilar. Rust/Cargo também não estão
no PATH. Faltam artefatos em `workers/craft/bin` e `public/craft`.

O guia de infraestrutura registra instalação **pelo operador** de Docker Desktop
oficial + WSL2/Linux, requisitos/licença, Rust 1.95.0 e wasm-bindgen 0.2.129 do builder,
comandos e validações posteriores. Não se afirma build reproduzido nesta máquina.
Não foram desabilitadas verificações de licença, manifestos, checksums ou consentimento.

## F. Testes e classificação

| Validação | Aprovados | Reprovados | Pulados | Resultado |
| --- | ---: | ---: | ---: | --- |
| Python geral, incluindo testes upstream Linux e subcasos unittest | **860** | **292** | **113** | Não aprovado globalmente; 654,15 s e 18 warnings |
| Núcleo audiovisual/financeiro de nove módulos extraído da rodada geral | **89** | **0** | **18** | Os pulos não são aprovações de motores ausentes |
| Reexecução final de financeiro + recuperação, após endurecer `pending` na troca de mês | **21** | **0** | **0** | SQL real, incluindo claim concorrente e resultado incerto |
| `npm test` (231 TypeScript/Node + 2 privacidade Vite) | **233** | **0** | **0** | Aprovado |
| Estado Craft, execução adicional fora da descoberta npm | **7** | **0** | **0** | Contratos/estado, não prova de engine compilada |

TypeScript (`npm run lint`), build Vite/esbuild, Ruff sobre `backend/app` e
`pip check`: aprovados; **zero ocorrências Ruff**. O supervisor MJS também passou
em `node --check` e nos ensaios de startup/status/stop/porta ocupada/quebra do serviço.

O núcleo acima contém `test_editing_ai_providers`, `test_editing_resources`,
`test_image_frontend_contract`, `test_media_final_validation`,
`test_studio_llm_connections`, `test_studios_recovery`, `test_video_frontend_contract`,
`test_video_timeline_real` e `test_internal_finance`. Não somar suas contagens às da
rodada geral: são subconjunto ou reexecuções. O ajuste final de retenção de
`pending`/sem ACK foi verificado na reexecução de 21 casos após a rodada geral.

Comparação com a referência de 847/294/113: **nenhum novo ID de teste falhou**;
os testes antigos do animatic real e do indicador visual foram resolvidos.
Os 13 aprovados adicionais são esses dois casos e 11 novos casos financeiros.
O total geral JUnit é 1.265, com subcasos unittest; a quantidade de itens coletados
não é igual a esse total, por isso os subcasos não foram omitidos.

Triagem das **292 falhas restantes**, mantendo os resultados originais:

| Causa primária observada | Falhas |
| --- | ---: |
| Arquivos de benchmark, manifests ou runtimes ausentes (FileNotFoundError) | 244 |
| Código de preflight de workers ou wheels verificados ausentes | 7 |
| Evidência ausente para read models de qualificação | 8 |
| Runtime Craft ausente | 3 |
| Packaging exclusivamente Linux executado no Windows | 15 |
| Lock de integridade divergente, não contornado | 1 |
| Helpers/motores/endpoints aposentados ou contrato nativo antigo | 10 |
| Divergências de código/contrato que ainda exigem revisão individual | 4 |
| **Total** | **292** |

Portanto, **278 casos reprovados estão bloqueados por dependências, plataforma ou
integridade**, 10 têm contrato antigo e quatro permanecem para diagnóstico/revisão.
“Bloqueado” é a classificação da causa **dentro** das reprovações, não um status
extra de pytest para somar ao total. Não foram convertidos silenciosamente em skip.
Os quatro últimos envolvem papéis de elementos/sequência com caminho e dois
fluxos antigos de revisão/exportação. Não se afirma que sejam geração/qualidade
aprovada ou que todos possam ser corrigidos sem os motores/evidências ausentes.

Evidências completas: `.codex-runtime/stage1-final-full.xml`,
`stage1-final-full.log`, `stage1-final-triage.json`, `stage1-finance-verified.xml`,
`stage1-node-verified.log`, `stage1-craft-state.log`, `stage1-tsc-final.log` e
`stage1-build-final.log`. O triador conserva ID, diagnóstico e comparação à base.

`npm audit`: **zero altas/críticas, três moderadas**, mesma cadeia
Mammoth → argparse → sprintf-js. O [advisory upstream](https://github.com/advisories/GHSA-hp3w-g68c-fv3c)
não indica patch publicado; o audit sugere downgrade incompatível de Mammoth para
0.3.29. Isso não foi aplicado. O uso de argparse foi localizado no CLI de Mammoth,
não no caminho de extração usado pelo app, mas essa inspeção não é prova universal
de inexequibilidade do advisory. O parser existente continua isolado/bounded em
worker; o risco permanece registrado, não eliminado por um relatório verde.

## G. Controle financeiro

Uma única autoridade SQL admite as chamadas pagas Node/Studios. Tetos globais,
por empresa/membro e modelo são verificados **antes** do POST. Recibo/fingerprint,
claim condicional, retries explícitos limitados e ausência de retries ocultos
protegem reenvios. Mudanças de tarifa, mês ou reserva com mais de 60 s impedem
reutilizar uma admissão Node antiga. Toda tentativa admitida tem seu registro.

Uso Gemini inclui candidatos + thinking uma única vez; TTS registra unidades,
não tokens fictícios. São reservas/estimativas por tarifas configuradas, não
garantia de faturamento máximo contratual do fornecedor. A configuração de preços
e limites reais do projeto precisa ser verificada pelo operador antes do piloto.
Valores não conciliados não são liberados como se uma estimativa fosse fatura.
Resultados `unknown`, `pending` ou sem ACK preservam responsabilidade financeira.

Cota comercial de imagem permanece uma solicitação aceita, incluindo falha ou
cancelamento; replay/retry do mesmo job não dobra a unidade. Vídeo só conta cenas
geradas por IA; edição/prévia/exportação local não consome minutos. KLIC credits
não foram convertidos artificialmente em USD.

Ainda falta importação/verificação de faturas, UI administrativa de reconciliação,
liberação controlada de reservas expiradas não utilizadas e homologação com conta
real. O fluxo legado Python sem escopo foi bloqueado, não falsamente protegido.
Higgsfield continua transporte experimental desativado, sem rota habilitada; não
deve ser exposto sem integrar a política central. Não há promessa de que um novo
adaptador futuro se torne protegido automaticamente por simplesmente existir.

Configurações e limitações detalhadas:
[admissão financeira](../operations/STAGE1_FINANCIAL_ADMISSION.md).

## H. Integrações de IA

| Papel/provedor | O que foi aproveitado | Situação |
| --- | --- | --- |
| OpenRouter / Claude Opus 5.5 | conexão LLM existente, Chat Completions, revisão, credencial cifrada/vinculada ao destino, teto próprio e mensal; ID `anthropic/claude-opus-5.5` | Preparado em contrato; conta/acesso/custo/qualidade real pendentes |
| Anthropic direto | protocolo Messages com cabeçalho de versão e normalização de uso | Preparado; nenhum envio real |
| Gemini planejamento/KLIC | transporte nativo existente, saída estruturada, limite de tokens, auditação e guard financeiro Node/Python | Testes offline aprovados; inferência não ativada |
| Gemini imagens | adaptador dedicado, tamanho/proporção nativos, candidato validado e revisão humana | Sem homologação remota/identidade visual |
| Gemini vídeo | caminho especializado separado do planejador, flags, limites e reserva | Não ativado; protocolo/modelo/conta devem passar pelo piloto real |
| Runway | adaptador nativo existente, `gen4.5` / `aleph2`, tarefas e download validado | Não ativado; credenciais e saídas reais pendentes |
| Google Cloud TTS | cliente atual reutilizado, MP3, timeout e admissão central | Nenhuma síntese paga; teste de bloqueio antes de criar cliente |

O LLM pode propor comandos/timeline; referências, schema, revisão e recursos do
renderizador são validados antes de aplicar. Não passa a gerar mídia por falar
JSON. Imagem, cenas e edição continuam serviços distintos, sem serviço duplicado.

Fontes oficiais conferidas nesta etapa:

- [OpenAI Deprecations](https://developers.openai.com/api/docs/deprecations): Sora 2 e Videos API removidos em **24/09/2026**. Permanecem aposentados.
- [Google Deprecations](https://ai.google.dev/gemini-api/docs/deprecations): Veo 3.1 Lite/Fast/standard Preview e Omni Flash Preview têm retirada indicada para **22/10/2026**, com aviso de prazo mínimo na página. Não são base recomendada de nova integração. Não houve troca automática de modelo.
- [Claude Opus 5.5 no OpenRouter](https://openrouter.ai/anthropic/claude-opus-5.5) e [API Runway](https://docs.dev.runwayml.com/api/): documentação não prova acesso da conta Clicko.

## I. Pendências e limites de homologação

1. Instalar/pré-validar Docker Linux/WSL2, compilar e testar os três motores Craft.
2. Provisionar PostgreSQL/Redis/workers Linux com manifestos reais e testar entrega,
   cancelamento, timeout, morte/reinício e concorrência distribuída. Não foi homologado.
3. Recuperar, da origem verificável, benchmarks, casebooks, manifests e modelos
   ausentes; não gerar arquivos falsos ou recalcular locks de integridade para
   ocultar divergências. Há testes Linux que precisam do ambiente Linux apropriado.
4. Concluir atualização dos contratos antigos de motores/revisões/preview e
   investigar divergências semânticas já existentes (papel visual e sequência com
   caminho). Essas falhas não foram declaradas aprovadas por o vídeo local funcionar.
5. Conciliar faturamento real e validar tarifas/limites por modelo. Um resultado
   desconhecido não é reenvio autorizado. Sem interface de reconciliação, manter
   flags desligadas é a postura segura.
6. Homologar acesso, qualidade de imagem/vídeo, sincronização de voz real e preservação
   de identidade com material autorizado; nenhuma dessas aprovações foi simulada.
7. npm mantém a cadeia Mammoth/argparse/sprintf-js com advisory moderado sem patch
   compatível aplicado. Não realizar downgrade destrutivo sugerido pelo audit.

## J. Próxima fase

Antes de testar Claude Opus, Gemini e um gerador de vídeo:

- Escolher IDs atuais e papel de cada modelo, confirmar documentação e acesso real
  na conta correta; não reaproveitar Sora aposentado ou Veo Preview em retirada.
- Provisionar credenciais privadas e chave de cifragem, verificar RBAC/isolamento,
  cadastro versionado, tarifas válidas e limites positivos em todos os níveis.
- Definir e **autorizar explicitamente** um teto de piloto. A proposta antiga de
  US$15 não é autorização aplicada e não foi gasta aqui.
- Começar por uma chamada pequena por provedor e conferir recibo, tokens/segundos,
  custo estimado e extrato; em resultado incerto, reconciliar antes de reenviar.
- Validar saída técnica, revisão humana e qualidade/identidade com mídia autorizada.
  Separar planejamento, geração de imagens/cenas e edição/exports na avaliação.
- Não promover produção antes de resolver gates de licença/integridade, filas,
  armazenamento, testes globais pertinentes, carga, backup e segurança.

O relatório não concede autorização para despesas, instalação administrativa,
contratação ou publicação. O próximo passo pode usar os serviços existentes;
não requer reconstruir os módulos nem inventar funções indisponíveis.
