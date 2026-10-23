# Clicko — validação final e preparação para integração de IA

Data de consulta e execução: **21/10/2026**, America/Sao_Paulo. Checkout: `C:/Users/pedro/Downloads/res`.

Referências: [auditoria F01–F21 de 20/10](IMAGE_VIDEO_TECHNICAL_AUDIT_2026-10-20.md) e [recuperação estrutural](MEDIA_RECOVERY_2026-10-21.md).

## A. Diagnóstico executivo

**Há uma base local funcional para edição e exportação de vídeo. Ainda não há comprovação de uma fábrica audiovisual autônoma ou de geração profissional por IA.** Nesta etapa, uma publicidade de referência de 18 segundos atravessou as APIs reais de projeto, upload, timeline, job, renderização, biblioteca e download. FFmpeg/FFprobe, banco, arquivos e validações de pixels/áudio foram reais. Briefing, roteiro e decisão editorial foram escritos manualmente no teste. Não houve geração de cenas por IA.

Em imagens, criação de projeto, importação autorizada, preservação do original, proporção, checksum, vínculo, armazenamento privado e recuperação foram comprovados sem fornecedor. **Composição/edição/exportação de um novo bitmap pelo PhotoCraft permanece bloqueada pelo runtime ausente.** Baixar o original não foi contado como edição. Geração/edição Gemini não foi executada nesta etapa e continua sem homologação de qualidade.

Express e FastAPI identificam corretamente a prontidão do perfil local. O ambiente é SQLite/arquivos/pool local, não um cluster PostgreSQL/Redis/Celery qualificado. PhotoCraft, FilmCraft e EffectCraft informam indisponibilidade. A suíte global Python e dependências pendentes impedem declarar a Clicko inteira pronta para produção.

### Funciona e foi exercitado

- Persistência de documentos e revisões; autenticação e isolamento de cliente/workspace.
- Timeline canônica com cortes de materiais reais, sobreposição, texto rasterizado, keyframes, fades, ganho e áudio.
- Exportação MP4 H.264/AAC, resolução/duração verificadas, download privado, Range e replay idempotente.
- Referência de imagem 960×1200, prova de uso obrigatório, vínculo ao documento e download byte a byte sem alterar o original.
- Negativas explícitas para capacidades ausentes e rotas antigas sem edição verdadeira.
- Conexões LLM administrativas existentes, armazenamento cifrado de credenciais e seleção de modelo por projeto; seus testes de transporte usam doubles, não inferência real.

### Não comprovado / indisponível

- Geração, preservação de produto/pessoa, qualidade artística e edição remota com Gemini/Runway/Veo.
- Runtime nativo/WASM Craft, ASR, voz/avatar e workers especializados que exigem artefatos externos.
- Planejamento autônomo completo com inspeção audiovisual, seleção de geradores, correção iterativa e entrega sem intervenção.
- Infraestrutura distribuída, desempenho sob carga, conciliação de faturas e custos reais de hardware/armazenamento.

## B. Revalidação dos achados F01–F21

Critério: **resolvido** significa que a causa delimitada do achado foi corrigida e tem evidência; não certifica recursos externos não exercitados. **Parcial** indica correção local com parte ainda incompleta. **Bloqueado** exige infraestrutura ou autorização ausente. **Pendente** continua sem implementação/qualificação suficiente.

| ID | Estado | Evidência e limite atual |
| --- | --- | --- |
| F01 | Resolvido | `server/studios/legacyEditing.ts` e testes Node: edição legada retorna 410 sem arquivo fictício nem cobrança. Nenhum novo executor foi inventado. |
| F02 | Resolvido | Express `/api/ready` depende da saúde FastAPI. Perfil local respondeu 200; queda controlada na etapa anterior respondeu 503. `readiness.test.ts` revalidado. |
| F03 | Parcial | Bundles ausentes retornam 404 JSON, nunca HTML SPA; descoberta nativa e builder corrigidos. Os três motores continuam `available:false`, sem Docker/Rust/bundles nesta máquina. |
| F04 | Resolvido | Crítica normaliza `craft_render` e `timeline_render`, exigindo vídeo, revisão e checksum. `test_studios_recovery.py` cobre ambos; não é crítica remota real. |
| F05 | Resolvido | `studio_routes.py` compartilhado; testes comparam rotas de `app.main` e ponte. Autenticações próprias preservadas. |
| F06 | Bloqueado | Flags/credenciais de geração permanecem desligadas; runtimes e modelos especializados não provisionados. Catálogo não é serviço operacional. |
| F07 | Parcial | Reservas duráveis e limites mensais global/empresa/membro, inclusive entre clientes e retomadas em outro mês. Fatura real, tarifas multimodais completas e conciliação administrativa continuam pendentes. |
| F08 | Resolvido | Gate Gemini exige flags de outbound/vídeo e teto; testes de admissão/execução recusam limites nativos inválidos antes de submissão. |
| F09 | Parcial | Política confirmada: somente cenas geradas por IA consomem minutos. Medidas de processamento/saída/armazenamento reais; publicidade local registra geração=0. Tarifas comerciais de CPU/armazenamento não foram inventadas. |
| F10 | Parcial | `aspectRatio` e `imageSize` nativos e validação da saída têm testes de contrato. Referência local 4:5 comprovada; resposta de fornecedor real ainda não qualificada. |
| F11 | Bloqueado | Preservação de identidade/produto continua hipótese de benchmark, nunca garantia por prompt. Exige bateria autorizada com referências e avaliação humana. |
| F12 | Resolvido | Limite efetivo configurável até 16.384 no planejador Gemini, sem corte oculto para 8.192. É limite deliberado da aplicação, não o máximo do modelo. |
| F13 | Parcial | Resolução comum FFmpeg/FFprobe e detecção libopenh264/libx264. Renderização e áudio locais reais passaram; edição generativa remota não foi exercitada. |
| F14 | Parcial | Gating por operação/modelo e limites de duração já implementados. Veo Preview tem retirada iminente; disponibilidade de conta e todas as modalidades não estão homologadas. |
| F15 | Parcial | IA pode aplicar `timeline.replace` validado no executor canônico; aplicação/replay reais com resposta LLM double. O planejador universal continua recebendo contexto textual, não percepção completa do filme. |
| F16 | Parcial | Contratos legados ajustados, testes direcionados, TypeScript e build reexecutados. Suíte Python global não está verde; testes nativos usam doubles em parte e não certificam motores. |
| F17 | Parcial | Jobs locais fora do HTTP, pool limitado, claim atômico, recuperação e limites Celery por perfil. Sem homologação de broker/worker distribuído ou teste de carga. |
| F18 | Bloqueado | Manifests, políticas, benchmarks e modelos de workers ausentes continuam impedindo vários testes globais. Não criados arquivos de qualificação fictícios. |
| F19 | Pendente | Ainda há leituras amplas e custos de rasterização. A nova medição é funcional, não benchmark de escala; paginação, retenção, índices e carga precisam de etapa própria. |
| F20 | Parcial | Startup, validação, logging, headers e rate limiting compartilhados. Topologia de produção, Redis e failover não homologados nesta máquina. |
| F21 | Resolvido | `/api/ai/generate-image` antigo retorna 410; não alega fallback inexistente. Fluxo canônico exige admissão e recibo de cota. |

Resumo: **7 resolvidos, 10 parciais, 3 bloqueados e 1 pendente**. Não transformar esse placar em percentual de funcionalidades prontas: os achados têm escopos e riscos diferentes.

## C. Testes funcionais e evidências

### C1. Produção publicitária local de 18 segundos

Arquivo: `C:/Users/pedro/Downloads/res/.codex-runtime/final-validation-2026-10-21/publicidade-local-18s.mp4`.

| Etapa | Execução / evidência |
| --- | --- |
| Briefing | Apresentar o estúdio e convidar criadores a iniciar uma produção. Definido manualmente no teste. |
| Roteiro e cenas | 0–6 s: “Sua ideia merece ganhar forma.”; 6–12 s: “Imagem. Movimento. Criatividade.”; 12–18 s: “Crie seu próximo conteúdo com a Clicko.” |
| Materiais | Vídeo-fonte procedural de 24 s, PNG geométrico próprio e trilha harmônica sintetizada localmente. Não usa material de clientes nem uma logo oficial recriada. |
| Edição | Três intervalos de 6 s extraídos de pontos distintos do vídeo-fonte. Timeline tipada persistida pela API em revisão 2. |
| Transições | Fades de entrada/saída através do preto; não foi alegado um efeito de transição não implementado. |
| Elementos | PNG composto em camada independente, escala animada; títulos próprios com deslocamento Y e fades. |
| Áudio | Trilha PCM importada, ganho −6 dB, fades e exportação AAC. É trilha sintética de QA, não composição por IA nem validação de mixagem profissional. |
| Saída | 18 s, 1280×720, 30 fps, H.264 + AAC; checksum da entrega confere. |
| Qualidade técnica | Frames decodificados nas três cenas contêm o gráfico e textos; amostras reais de áudio são audíveis e respeitam fade inicial. Não é avaliação artística automatizada. |
| Persistência | Biblioteca, download, Range, isolamento contra outro cliente, replay sem segundo job e leitura em novo TestClient. |

Teste: `backend/tests/test_media_final_validation.py::test_real_eighteen_second_advertising_reference`.

`evidence.json` no mesmo diretório registra briefing, roteiro, IDs, métricas e saída FFprobe. `scene-1.png`, `scene-2.png` e `scene-3.png` são frames extraídos do MP4 verdadeiro, não mockups. O banco de teste é temporário; o arquivo/evidência foi retido fora dele. A sessão de desenvolvimento usa outro banco de QA.

**Conferência pela interface real:** o arquivo de 18 s foi importado no Studios e reproduzido até `ended=true`, sem erro de mídia. Um novo projeto de QA, `QA · Validação final · 18s`, foi criado pela interface, salvo, reaberto e recuperado após reinício do serviço. A primeira tentativa revelou que o backend recusava o campo `originalAudioEnabled` enviado pelo editor. A correção está descrita na seção D; a nova tentativa concluiu como **“MP4 validado”**, revisão 2, com download e reprodução reais. O MP4 baixado foi conferido com FFprobe: **1920×1080, 30 fps, 18,000 s, H.264/AAC, 3.075.636 bytes**. Essa segunda passagem reexporta a montagem já produzida, não prova edição multipista adicional nem geração por IA. Aumentar a resolução de saída não cria detalhe de fonte novo.

Evidência visual: `.codex-runtime/final-validation-2026-10-21/browser-export-validado.jpg`. Arquivo baixado: `C:/Users/pedro/Downloads/QA · Validação final · 18s · revisão 2.mp4`. Asset do ambiente local: `1caa3b8e-d514-4f57-9c5a-f9df2de34814`, distinto dos IDs do banco temporário dos testes. A sessão existente foi preservada; não houve bypass de autenticação.

**Onde a automação para:** a solicitação foi traduzida manualmente em roteiro/timeline. Não existiu LLM real escolhendo cenas, produzindo mídia nova ou avaliando/corrigindo o filme. O gerador remoto permanece desligado e produções autônomas sem recibo comercial estão bloqueadas. Trocar o LLM, isoladamente, não fecha essas lacunas.

### C2. Imagens reais disponíveis, sem inferência

Teste: `test_reference_image_import_storage_download_and_explicit_native_block`.

1. Criou documento visual 960×1200 e uma referência procedural própria 4:5.
2. Fez upload e recuperação autenticados; dimensões, bytes e SHA-256 conferem; outro cliente recebe 404.
3. Tentativa de vincular upload genérico sem prova de uso recebeu `resource_usage_evidence_required`. Isso é proteção correta, não erro a contornar.
4. Reimportou pelo contrato de recursos com prova de uso própria e vinculou a referência ao projeto, preservando o arquivo.
5. Tentou a prévia de composição pelo endpoint real `/craft/preview`. Sem projeto/runtime nativo, recebeu erro controlado, sem gerar imagem falsa. Original permaneceu idêntico.

Artefato retido: `reference-4x5.png`. Não houve crop, retoque, nova composição ou exportação PhotoCraft real. Os testes Gemini existentes usam HTTP doubles para verificar proporção/resolução, falhas, revisão e persistência; são evidência de contrato, não de inferência ou qualidade.

### C3. Infraestrutura

- Perfil local real: Express 3018 → FastAPI 8018, SQLite, arquivos e pool de duas threads. `/api/ready` e `/health/ready` conferidos.
- FFmpeg/FFprobe 9.0, encoder libopenh264 e AAC disponíveis. Capabilities listam os filtros e limites efetivamente suportados.
- PostgreSQL/Redis/Celery distribuídos não estavam provisionados. Testes de transporte/fila não substituem uma execução real desse cluster.
- PhotoCraft/FilmCraft/EffectCraft: indisponibilidade detectada; linhagem upstream revalidada, fontes preservados. Docker/Cargo não encontrados no PATH.
- Logs HTTP incluem correlação, método, rota, status e latência; não houve implantação de observabilidade centralizada/SLO.
- Recuperação de jobs, replays, isolamento, revisão, cotas e orçamento reexercitados nos testes direcionados. A falha de um recurso não altera artificialmente o status de outro.

### C4. Resultado automatizado

- Rodada selecionada final: **96 coletados, 78 aprovados, 18 pulados, zero falhas/erros**, 88,757 s. XML: `.codex-runtime/final-validation-selected.xml`. Inclui os dois casos reais de áudio original ligado/desligado.
- `npm run lint` (TypeScript), `npm run build` e `npm test` passaram novamente **após** instalar Vite 6.4.5; **229 testes Node/Vite aprovados**.
- `pip check`: sem incompatibilidades de requisitos instalados; não é auditoria de CVEs Python nem prova de modelos instalados.
- Ruff nos arquivos Python alterados nesta etapa: aprovado.
- Suíte completa Python: **1.227 coletados, 836 aprovados, 279 falhas, 112 pulados, zero erros**, 890,347 s. Evidências: `.codex-runtime/final-validation-full.xml` e `.codex-runtime/final-validation-full.log`. Os 279 IDs de falha já existiam na rodada anterior de recuperação; não surgiu ID novo. A base anterior tinha 282 falhas; três deixaram de falhar nesta rodada. Isso é comparação delimitada de testes, não comprovação de ausência de toda regressão.
- A coleta global precedeu a última correção de `originalAudioEnabled` e os dois testes novos desse contrato. Por isso não é uma execução global do snapshot final: essa correção foi verificada pela rodada direcionada de 96 casos e pela exportação real no navegador, sem repetir os 15 minutos de toda a suíte. **O CI global continua não aprovado.** Há bloqueios de manifests/modelos/benchmarks e contratos legados, já inventariados na recuperação; não foram suprimidos ou marcados como aprovados.
- Após os últimos ajustes equivalentes de formatação, os **seis casos novos** foram repetidos: **6 aprovados, zero falhas/pulados**, 25,521 s (`.codex-runtime/final-validation-new.xml`). A referência de 18 s foi regenerada nessa execução. Ruff dos cinco arquivos Python desta etapa e `git diff --check` dos arquivos rastreados revisados passaram.

Reprodução do ensaio e retenção de artefatos: comandos em [README — Verificação](../../README.md#verificação). Os testes de FFmpeg exigem as ferramentas reais; se faltarem, serão pulados, e esse resultado não deverá ser apresentado como aprovação de renderização. A execução local de 21/10 contou com FFmpeg e não pulou os seis casos novos.

## D. Correções implementadas nesta etapa

| Arquivo | Mudança | Verificação |
| --- | --- | --- |
| `backend/app/providers/studios/universal_llm.py` | Normalização Gemini soma tokens de candidatos e raciocínio, uma única vez, no uso de saída compartilhado. | Dois testes distinguem uso bruto e normalizado. |
| `backend/app/services/studios/gemini_editing.py` | Estimativa por tarifa inclui `thoughtsTokenCount` quando o uso ainda não está normalizado. Reservas conservadoras continuam separadas de fatura. | Testes de orçamento existentes e regressão nova. |
| `backend/app/domain/studios/timeline_editor.py` | Contrato `VisualMotion` aceita `originalAudioEnabled` como booleano estrito, com padrão verdadeiro. Antes, uma timeline normal do frontend era recusada como campo extra. | Dois testes reais reproduzem o payload do editor; a exportação da interface deixou de falhar no preflight. |
| `backend/app/providers/studios/timeline_ffmpeg.py` | Respeita o sinalizador ao incluir o áudio do vídeo-fonte. Trilhas de áudio independentes e mute existente preservados. Formatação/imports normalizados com Ruff. | Vídeo-fonte real com áudio: PCM audível quando habilitado e silêncio quando desabilitado; MP4 da interface contém AAC. |
| `backend/tests/test_media_final_validation.py` | Referência publicitária real de 18 s, imagens privadas/autorizadas, regressões de tokens e áudio original. | Arquivo real, pixels, áudio, checksum, download e persistência. |
| `package.json`, `package-lock.json` | Vite atualizado da instalação 6.4.3 para 6.4.5, preservando a linha 6 e as demais dependências. Mínimo solicitado `^6.4.4`. | Auditoria npm deixou de apontar severidades alta/crítica; build/testes repetidos. |
| `README.md`, `CHANGELOG.md` e este relatório | Reprodução da validação sem chamadas pagas, resultados, diferenças entre contrato/execução real, limites e próximos gates. | Comandos e referências aos artefatos locais. |

Motivação de tokens: o contrato Google distingue candidatos e raciocínio; a tabela cobra saída incluindo thinking. [UsageMetadata oficial](https://ai.google.dev/api/generate-content#UsageMetadata). A conta continua **estimativa por tarifa**, não fatura. Cache, ferramentas, mídia e combinações de modalidades ainda exigem tarifação específica; não se pode aplicar uma única tarifa textual a toda mídia e chamá-la de custo real.

Motivação Vite: correção de segurança Windows publicada para 6.4.4 ou superior. [Advisory oficial](https://github.com/advisories/GHSA-587h-7wmj-h5pm). `npm install --ignore-scripts --no-audit --prefer-offline` alterou um pacote instalado, sem scripts de instalação.

Auditoria npm após correção: **0 críticas, 0 altas, 3 moderadas**, correspondentes à cadeia `mammoth → argparse → sprintf-js`. `sprintf-js` não tem patch publicado; npm sugere downgrade incompatível de Mammoth para 0.3.29, não aplicado. O import encontrado de argparse no Mammoth é o CLI; os testes da extração DOCX continuam passando. Isso reduz a exposição conhecida nesse caminho, mas não permite declarar risco global inexistente. [Advisory](https://github.com/advisories/GHSA-hp3w-g68c-fv3c).

## E. Modelos, acesso e custo potencial

### E1. Identificadores e contratos conferidos

**Consulta pública não comprova acesso da conta nem desempenho.** Não foram enviados prompts de geração, cadastradas chaves, ativadas conexões ou cobradas inferências.

| Função | Modelo/endpoint | Adequação e integração existente |
| --- | --- | --- |
| Direção complexa | `anthropic/claude-opus-5.5`; `POST https://openrouter.ai/api/v1/chat/completions` | ID encontrado no catálogo público real `GET /api/v1/models`, com `response_format`, `structured_outputs` e tools declarados. A conexão universal existente suporta esse protocolo. Ainda precisa qualificação de JSON, limites, latência, privacidade e qualidade de direção. |
| Planejamento econômico | `gemini-3.8-flash`; `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent` | Multimodal na API, saída textual e structured outputs. Na Clicko, conexões universais recebem hoje contexto textual; percepção visual não surge só por selecionar o modelo. O limite interno de 16K é deliberadamente menor que o máximo documentado. |
| Imagem econômica | `gemini-3.1-flash-lite-image`; mesmo endpoint GenerateContent por ID | Adapter existente, 1K, subset de proporções aceito e validado. Não promete 2K/4K nem fidelidade absoluta. |
| Imagem com maior resolução | `gemini-3.1-flash-image`; GenerateContent | Adapter existente aceita 1K/2K/4K. Acesso, latência e preservação ainda não testados ao vivo. |
| Vídeo Google | `gemini-omni-1.1-flash`; `POST .../v1beta/interactions` | Transporte existente; documentado para geração/edição, saída 3–10 s. Primeiro candidato Google a qualificar na próxima etapa, não ativado aqui. |
| Veo | `veo-3.1-lite-generate-preview` / `veo-3.1-fast-generate-preview`; `:predictLongRunning` | IDs ainda referenciados, mas **desligamento anunciado para 22/10/2026** na Gemini Developer API. Não iniciar investimento novo nesses previews. Veo GA em plataforma Google empresarial exige outro projeto/credenciais/adaptador e análise própria. |
| Vídeo Runway | `gen4.5`; `/v1/text_to_video` e `/v1/image_to_video` em `https://api.dev.runwayml.com` | Adapter existente, versão `2024-11-06`, tarefas assíncronas e download seguro. Subset Clicko 2–10 s e 1280:720/720:1280. `aleph2` é a integração separada de edição, não um substituto silencioso. |

Fontes por função: [Claude no OpenRouter](https://openrouter.ai/anthropic/claude-opus-5.5/providers), [catálogo público](https://openrouter.ai/api/v1/models), [endpoint OpenRouter](https://openrouter.ai/docs/quickstart), [Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash), [Lite Image](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite-image), [Flash Image](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-image), [Omni](https://ai.google.dev/gemini-api/docs/models/gemini-omni-flash), [retirada Veo](https://ai.google.dev/gemini-api/docs/models/veo-3.1-generate-preview), [modelos Runway](https://docs.dev.runwayml.com/guides/models/).

O cadastro de conexão LLM não implica habilitar um gerador de imagens/vídeos. Permissão, modelo, preço, conteúdo autorizado, orçamento e recibo comercial continuam independentes. Saldo, localização, nível de conta, quotas, revisão de políticas e credenciais reais precisam ser conferidos pelo operador antes do piloto.

### E2. Comparação de preços verificados

**USD, tarifas Standard consultadas em 21/10/2026; sem impostos, câmbio, taxas de pagamento ou infraestrutura.** Não são faturas da Clicko.

| Provedor/modelo | Unidade / tarifa de referência |
| --- | --- |
| Opus 5.5 / OpenRouter | Entrada US$4; saída US$20 por milhão de tokens. |
| Gemini 3.8 Flash | Entrada US$0,75; saída US$3,75 por milhão, até 31/12/2026; tabela anuncia US$1,50/US$7,50 a partir de 01/01/2027. |
| Lite Image | Saída 1K: US$0,0336/imagem; entrada US$0,25/milhão. |
| Flash Image | Saída 1K/2K/4K: US$0,067 / 0,101 / 0,151 por imagem; entrada US$0,50/milhão. |
| Omni Flash | Vídeo 720p: 5.792 tokens/s × US$17,50/milhão = **US$0,10136/s**; entrada US$1,50/milhão. |
| Veo 3.1 Lite / Fast | 720p: US$0,05 / 0,10 por segundo; apenas referência histórica de opção em retirada. |
| Runway Gen-4.5 | 12 créditos/s × US$0,01/crédito = **US$0,12/s**. |
| Runway Aleph2 | 28 créditos/s, mínimo de 56 créditos; edição deve ser orçada separadamente. |

Fontes: [OpenRouter modelo](https://openrouter.ai/anthropic/claude-opus-5.5/providers), [Google preços](https://ai.google.dev/gemini-api/docs/pricing), [Runway preços](https://docs.dev.runwayml.com/guides/pricing/). Imagens também podem produzir texto/thinking faturável; entrada visual e reprocessamentos não estão incluídos no valor unitário de saída. Resolução maior não é upscale gratuito.

OpenRouter Standard cobra taxa de 5,5% na compra de créditos, separada do preço da inferência. Não confundir saldo adquirido com gasto por projeto. Mínimos de recarga, tributos e meio de pagamento precisam ser conferidos no checkout; nenhuma compra foi realizada. [Preço do serviço](https://openrouter.ai/pricing).

### E3. Piloto proposto — NÃO autorizado / NÃO executado

Base aritmética, não promessa de consumo: 10 mil tokens de entrada e 2 mil de saída por chamada de planejamento; sem cache, grounding ou ferramenta paga.

| Lote | Cálculo de saída/planejamento | Estimativa base |
| --- | --- | --- |
| 20 planejamentos Opus | 20 × (10.000×4 + 2.000×20)/1.000.000 | US$1,60 |
| 20 planejamentos Flash | 20 × (10.000×0,75 + 2.000×3,75)/1.000.000 | US$0,30 |
| 10 imagens Lite 1K | 10 × 0,0336 | US$0,336 + entradas |
| 10 imagens Flash 1K | 10 × 0,067 | US$0,67 + entradas |
| 4 cenas Runway de 5 s | 20 × 0,12 | US$2,40 |
| 4 cenas Omni de 5 s | 20 × 0,10136 | US$2,0272 + entradas |

Total base **US$7,3332**, antes das entradas de mídia, texto adicional, taxas, falhas/repetições e infraestrutura. Proposta de **teto de inferência de US$15**, em duas liberações: até US$5 para planejamento/imagens, até US$10 para cenas. Trata-se de proposta para autorização futura, não de aumento aplicado nos limites do sistema.

As reservas conservadoras da Clicko podem bloquear o lote antes do gasto esperado; isso é intencional. Definir limite de tokens/bytes por chamada, duração, resolução, máximo de tentativas e subtetos por fornecedor. Não reduzir artificialmente reservas para caber nessa estimativa. Uma repetição integral dobra a base; resultados desconhecidos não devem ser reenviados automaticamente. Se a reserva faltar, reduzir a quantidade de ensaios, não ultrapassar o teto. O piloto não deve usar o Veo Preview em retirada.

**Render/armazenamento:** o ensaio local mede tempo de processo, bytes e segundos de saída. Não há tarifa oficial do hardware desta máquina, nem serviço de armazenamento contratado para converter essas métricas em USD. Preencher posteriormente `CPU-h × tarifa`, `GB-mês × tarifa`, tráfego, banco/Redis, logs, backups e retenção. Não registrar US$0 como custo total só porque não houve chamada externa.

## F. Painel administrativo e segurança de configuração

| Controle | Existe hoje | Lacuna |
| --- | --- | --- |
| LLMs | `CraftModelPicker` e `/craft/llm-connections`: endpoint, protocolo, IDs, modelo selecionado, ativar/desativar, tokens e preço por milhão. | Não descobre acesso real da conta nem homologa capacidade só pelo catálogo. |
| Chaves LLM | Campo de senha administrativo; cifragem Fernet no servidor vinculada à conexão; API pública retorna `hasCredential`, não o segredo. | Exige chave-mestra no backend, rotação/backup seguro. Não foi cadastrado segredo nesta etapa. |
| Permissão | Somente Owner/Admin grava/desativa; leitura isolada por workspace; testes de papéis e revisão concorrente existentes. | Ainda não é um painel operacional global de todos os fornecedores. |
| Modelos imagem/vídeo | Configuração de ambiente e catálogo/flags no backend; seleção por função já separada. | Credenciais, tarifas, resoluções e ativação de geradores não têm CRUD administrativo unificado equivalente ao LLM. Hoje exigem configuração/reinício no servidor; IDs ainda possuem allowlists/fixos. |
| Consumo/custos | Quotas comerciais, reservas, métricas e jobs auditáveis. | Falta painel de USD por cena/tentativa/cliente, custo de falhas, comparação de qualidade e conciliação com faturas. |
| Histórico | Jobs, operações, revisões e biblioteca. | Falta visão integrada de produção, estados externos desconhecidos e ação administrativa de conciliação. |

**Conclusão:** trocar LLM de planejamento pode dispensar edição de código usando a conexão existente. Trocar qualquer gerador arbitrário, suas capacidades e sua política de cobrança ainda não. Não colocar chaves em frontend, localStorage, logs ou Markdown; a edição administrativa usa apenas o backend e configuração cifrada.

## G. Próxima implementação em fases

1. **Consolidar a base antes de investir.** Manter testes reais desta etapa, resolver o inventário ausente e testes globais, qualificar Docker/Craft em ambiente apropriado. Provisionar PostgreSQL/Redis/workers com backup e testar reinício, perda de worker, carga e storage. Corrigir dependência moderada quando houver solução compatível.
2. **Catálogo por função e configuração administrativa.** Evoluir o cadastro existente para provedores de mídia: versões de capacidades/tarifas, IDs oficiais, fim de vida, modos suportados e limites; cifragem e RBAC existentes. Desativado por padrão. Aprovação de configurações e logs sem segredos.
3. **Planejador validado.** Usar Flash econômico como referência e Opus como comparação em briefings idênticos; saídas separadas de roteiro, cena, referências e operações. JSON Schema/limites/preservação de IDs; medir tokens, reasoning, latência, rejeições e qualidade humana. Sem shell/código ou URL arbitrária produzidos pelo modelo.
4. **Aquisição controlada de mídia.** Vincular cada imagem/cena a recibo comercial assinado, reserva financeira e job filho da produção; resolver permissões dos materiais. Qualificar Gemini Image e Runway/Omni com matriz pequena. Persistir IDs de operação externa antes de polling; falha desconhecida exige conciliação, nunca POST duplicado.
5. **Observação e execução.** Entregar ao planejador evidências reais de frames/áudio/transcrição autorizados, não somente nomes de clipes. Aplicar exclusivamente ferramentas suportadas pelo motor; montagem FFmpeg existente continua independente da geração. Preservar aprovação humana, versão e rollback.
6. **Revisão e correção limitadas.** Inspeção técnica determinística + avaliação humana; chamada visual externa com orçamento próprio. No máximo um número explícito de correções por cena, cada tentativa rastreável. Alteração aprovada volta ao executor, não só a uma explicação textual.
7. **Entrega operacional.** Consolidar arquivo validado, armazenamento/retensão, permissões de download, custo estimado/real separado e histórico por projeto. Somente depois qualificar qualidade profissional, SLO e operação de produção.

### Critérios de liberação

Um modelo só passa de “configurado” para “qualificado” depois de resposta real autorizada, identidade confirmada, custo/uso registrado, arquivo decodificável, formato/resolução/duração conferidos, permissões/revisão preservadas e repetibilidade em referências representativas. O pipeline completo só é aprovado se executar **interpretação → cenas → materiais → ferramentas → validação → correção limitada → entrega**, com cada interrupção visível e sem simulação.

Nenhuma chave, serviço pago, fornecedor ou teto foi ativado. Sem alteração de produção, migração destrutiva, deploy, commit ou push. Alterações anteriores do checkout foram preservadas.
