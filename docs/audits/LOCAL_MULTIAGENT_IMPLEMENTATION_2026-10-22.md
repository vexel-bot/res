# Clicko · implementação de agentes e produção local

**Data:** 22/10/2026. **Checkout:** `C:\Users\pedro\Downloads\res`.
Orçamento externo efetivamente utilizado: **R$ 0**. Sem instalação de pesos ou
novas dependências, chamada generativa paga, alteração de credencial KLIC, dados
de clientes, migração destrutiva, deploy, commit ou push.

## 1. Estrutura implementada

Entregue um incremento operacional de produção determinística local sobre o
documento/timeline/ledger/armazenamento existentes. A KLIC encaminha pedidos para
especialistas de backend, recebe o projeto e o plano, e conserva uma única
conversa. Há revisão/aplicação, edição manual, snapshots e exportação reais.

Não foram instalados três modelos nem comprovada autonomia generativa. A máquina
não tem runtime/pesos locais instalados e não foi demonstrado acesso remoto
gratuito. Os agentes operam inicialmente com regras declaradas e ferramentas
locais. A conexão de inferência local está preparada e tem teste de contrato
simulado explicitamente separado das provas de mídia real.

| Fase solicitada | Resultado desta etapa |
| --- | --- |
| 1 · hardware | Levantamento real e script reproduzível concluídos |
| 2 · agentes | KLIC preservada; dois papéis especialistas implementados, com adaptadores locais/configuração independente |
| 3 · orquestrador | Contratos, tarefas, escopo, validação, delegação, revisão, idempotência e retorno à conversa |
| 4 · modelos gratuitos | Avaliação documentada; nenhum modelo instalado ou inferência real homologada |
| 5 · motion | Primeiro conjunto local real, editável e exportável; efeitos avançados/nativos ficam pendentes |
| 6 · vídeo | Editor canônico preservado, comandos estruturados e integração com as camadas locais |
| 7 · imagem | Composição/edição local em camadas e PNG; geração/segmentação ainda indisponíveis |
| 8 · linguagem natural | Subconjunto em português por regras; LLM local preparado, interpretação livre não comprovada |
| 9 · interface | Novos painéis integrados aos Studios, tokens/menus existentes e CSS responsivo; homologação visual pós-login pendente |
| 10 · validação | Testes de contrato, regressão, mídia real, reprodução e persistência executados |
| 11 · documentação | README, CHANGELOG, arquitetura, hardware/modelos, operação, limites e este relatório |

Principais arquivos desta implementação (o checkout já estava muito modificado;
não se atribui todo o `git diff` a esta etapa):

| Área | Arquivos |
| --- | --- |
| Contratos | `backend/app/domain/studios/agents.py`, `local_composition.py`, extensão de `timeline_editor.py` |
| Coordenação | `backend/app/services/studios/agent_orchestrator.py`, `local_agents.py` |
| Apresentação local | `backend/app/providers/studios/local_composition.py`, extensão de `timeline_ffmpeg.py` |
| API | `backend/app/routers/studio_agents.py`, inclusão em `studio_routes.py`, reconhecimento de `visual` na ponte `studio_app.py` |
| Persistência/execução reutilizada | `services/studios/timeline_editor.py`, `jobs.py` (plano não executável por worker) |
| Transporte de modelo | `providers/studios/universal_llm.py` (schema Ollama e descarregamento após execução local) |
| KLIC | `server/klic/localProduction.ts`, `conversationRouter.ts`; tipos/modos/contexto em `src/klic/`; evento do assistente flutuante |
| Studios | `src/studios/local/`, `ClickoStudioView.tsx`, `StudiosWorkspace.tsx`, tipo de áudio original em `canonicalTimeline.ts` |
| Testes | `backend/tests/test_local_agents.py`, `server/klic/localProduction.test.ts`, `src/studios/local/localModel.test.ts` |
| Aceitação | `scripts/agents/audit-environment.ps1`, `scripts/agents/acceptance.py` |

## 2. Agentes criados

**KLIC:** Gemini/texto/voz/histórico continuam no fluxo original. Pedido explícito
de criação audiovisual pode ser roteado ao caminho local; o modo Produção local
também o seleciona. Alterações seguem o documento em contexto ou o último projeto
vinculado na conversa. Pergunta informativa não vira criação automática.

**AudiovisualAgent:** planeja cenas de motion, tempos, títulos, cartões e operações
de edição. Solicita gráficos editáveis ao `ImageAgent`. A tarefa de motion registra
as delegações reais; mudança simples de duração/título não inventa uma chamada
ao especialista visual. Roteirização é um modelo por regras, não direção criativa
autônoma validada.

**ImageAgent:** planeja cartão/composição e fornece primitivas visuais editáveis;
coordena a edição local de arquivos próprios. O renderizador exporta PNG
reutilizável e permite que o mesmo asset seja referenciado pelo projeto de vídeo.

Não há três históricos ou chats separados. O documento, assets e tarefas são
consultados por ID e workspace; o BFF verifica os módulos e a ponte faz o
isolamento de cliente. A entrada `visual` agora é reconhecida como Imagem na
validação do formato, fechando essa ambiguidade de permissão.

## 3. Modelos utilizados

**Inferência efetiva nesta etapa: nenhuma.** O adaptador operacional usa regras
explícitas. `Ollama local_free` pode ser vinculado separadamente a Audiovisual e
Imagem, reaproveitando `StudioLLMConnection` e `UniversalLLMPlanner` existentes.
Antes do pedido exige loopback, modelo local instalado, ausência de credencial,
customização de destino ou modelo cloud; não faz download e não usa fallback pago.
Schema JSON e validação das operações são independentes do texto do modelo.

Levantamento: Windows 11, i7-12650H, aproximadamente 7,71 GiB de RAM visível e
0,8–1,3 GiB livre nas medições, Intel UHD integrada. `AdapterRAM=1 GiB` não é uma
medição de VRAM dedicada. Python 3.12.14/Node 24.15.0 e FFmpeg privado funcionam;
Ollama, Torch, Diffusers, Transformers, ONNX/DirectML, Docker e Rust não estavam
disponíveis. WSL tem comando do Windows, mas não uma instalação funcional.

Qwen3 0.6B quantizado é apenas candidato condicionado à liberação de RAM e
benchmark de JSON/latência. Não se recomenda carregar um LLM grande ou difusão
nesse estado. A seleção, licença e fontes oficiais estão no
[guia de modelos/hardware](../operations/LOCAL_AGENT_MODELS_2026-10-22.md).
Gemini gratuito precisa de comprovação da conta/tier; a chave não foi alterada ou
usada para presumir gratuidade.

## 4. Integrações realizadas

- Mesma sessão, permissões, identidade de cliente e JWT BFF→Studios.
- Mesmo documento canônico, histórico e armazenamento privado.
- `agent_plan` durável antes de inferência: replays não criam outro pedido;
  resultados incertos/interrompidos não são reenviados automaticamente.
- Aplicação vinculada à revisão do plano, com recibo idempotente, snapshot anterior
  e aprovação invalidada. Camadas/trilhas/clipes bloqueados são preservados.
- Ledger registra comandos/delegações; saídas arbitrárias, shell, parâmetros
  desconhecidos e assets de outro workspace são recusados.
- Planejador e execução são separados. Os comandos validados alimentam o mesmo
  compilador FFmpeg; texto do LLM não equivale a gerar mídia.
- Os guardas financeiros existentes de Gemini/TTS/integrações pagas permanecem.
  O encaminhamento local por regras não chama SDK remoto nem desconta crédito de
  inferência; conversa Gemini normal conserva seu fluxo comercial.

## 5. Vídeo

Mantidos cortes/trim, sobreposição, títulos/legendas de texto fornecido, áudio
original, ganho/fades, keyframes, cancelamento, job, biblioteca e MP4 H.264/AAC.
Importar mídia no painel local faz referência ao original; editor canônico permite
os ajustes de montagem existentes. Renderização inclui mídia e camadas locais.

Geração de cenas cinematográficas novas permanece separada e indisponível neste
perfil. Nenhum modelo de vídeo gratuito foi apresentado como operacional.

## 6. Imagem

Importar, crop normalizado, redimensionar pela camada, brilho/contraste/saturação,
textos/formas/ordem/rotação/opacidade e composição PNG são executados localmente.
O original não é sobrescrito. Exportação usa novo asset com checksum e revisão;
repetir sua chave retorna o mesmo resultado. Histórico/restauração preservam
versões e exportações anteriores.

Remoção automática de fundo e geração visual por modelo continuam indisponíveis.
Esses pedidos retornam limitação e nenhuma edição, conforme teste de contrato.

## 7. Motion design

Uma solicitação textual cria até três cenas no modelo local, cada uma com cartão,
destaque e título independentes, sem vídeo de referência. Camadas continuam
editáveis. Há keyframes X/Y/escala/opacidade/rotação, easing linear/ease-out/
ease-in-out, gradiente, cor e um sombreamento raster simples; não é iluminação 3D.
Textos fazem transição de opacidade; não se anuncia catálogo de transições nativas
arbitrárias ou composição 3D real.

Modelo de motion aceita 3–120 segundos. O renderer canônico mantém seus limites
próprios. Até 24 camadas locais, dentro do limite total de 32 itens de renderização;
saída até 1920 px. Motion com clipes/áudio exige ajustar duração no editor, em vez
de esticar silenciosamente os materiais.

PhotoCraft/FilmCraft/EffectCraft não foram substituídos. Seus caminhos e projetos
avançados permanecem; precisam dos artefatos/ambiente de build já bloqueados na
Etapa 1. Nenhum motor nativo foi declarado testado nesta entrega.

## 8. Recursos editáveis e interface

Rotas: `/studios/video/motion`, `/studios/image/edit` e
`/studios/tools/composition`, opção **Edição local**. Há seleção/criação de projeto,
briefing/comando, plano e aplicação, camadas, propriedades, timeline de camadas,
prévia de edição, importação, undo/redo de rascunho, histórico/restauração e exportação.
O botão KLIC abre o assistente existente com o documento em contexto.

CSS usa tokens atuais e fonte nativa; organiza colunas para desktop e reagrupa
em 1200/640 px. Alterações na composição precisam ser salvas antes de abrir a
montagem canônica, evitando exportar material anterior sem aviso. Recuperação
local e replays usam escopo de usuário/workspace/módulo. Rascunho recuperado não
é substituído automaticamente pelo parâmetro de URL.

A prévia Canvas local ajuda na edição das camadas e não é uma promessa de
equivalência pixel a pixel com Pillow. Clipes de vídeo e áudio são conferidos no
MP4 realmente renderizado. O backend disponibiliza still PNG exato de camadas,
inclusive com áudio separado, sem tentar desenhar clipes não suportados por ele.

**Limite de verificação:** build/tipagem e contratos HTTP foram verificados; a
nova interface completa não foi homologada manualmente após login em desktop,
mobile e ambos os temas. O perfil isolado não contém sessão autenticada/licença
de navegador; não foram criados bypass ou assinatura fictícia. A reprodução do
artefato em player HTML5 foi verificada separadamente e não substitui esse ensaio.

## 9. Testes e evidências

| Verificação | Aprovados | Falhas | Pulados |
| --- | ---: | ---: | ---: |
| Python direcionado, dez módulos audiovisuais/financeiros/agentes | **97** | **0** | **18** |
| Agentes, reexecução final com cancelamento de contrato simulado | **8** | **0** | **0** |
| Node/TypeScript descobertos por `npm test` | **234** | **0** | **0** |
| Privacidade Vite, parte do mesmo `npm test` | **2** | **0** | **0** |

Os oito casos de agentes são subconjunto/reexecução da rodada Python, não se
somam para inventar 105 aprovações. Os 18 pulos usam a fixture histórica
`FFmpeg integration runtime unavailable`: ela procura o executável pelo PATH e
gera mídia com libx264. O binário privado validado usa libopenh264; os testes
canônicos e de motion reais foram executados por sua descoberta centralizada.
Esses pulos não provam homologação das integrações antigas.

TypeScript, build Vite/esbuild, `ruff check backend/app` e `git diff --check`:
aprovados. Nenhum ID de falha foi ocultado alterando benchmark/licença/fixture.
A suíte Python global não foi reexecutada: a referência de 21/10 continua
860 aprovados/292 falhas/113 pulados. Não se declara aprovação global da plataforma.

Contratos incluem autenticação/isolamento/módulos, modelo remoto/cloud recusado,
revisão, replay, comandos arbitrários, referência inválida, bloqueio de camada,
remoção de fundo indisponível, retiming, imagem/original e dois renders reais.
O teste LLM usa resposta **simulada** para rejeição e cancelamento; não comprova
inferência/qualidade. O teste HTTP Node usa upstream de contrato **simulado** para
verificar conversa única, JWT e ausência de chamada paga. A mídia live abaixo usa
o backend/SQL/armazenamento/FFmpeg verdadeiros.

### Aceitação live

`scripts/agents/acceptance.py create` produziu, em partição QA própria:

1. Briefing textual de motion de 12 s → plano estruturado → nove camadas canônicas.
2. Aplicação, áudio próprio de teste, gradiente e rotação por keyframes → MP4 v1.
3. Novo comando textual alterando o título → MP4 v2, com documento/histórico anterior.
4. Importação de PNG próprio, crop/ajustes e texto → composição PNG nova; original intacto.
5. Decode integral FFmpeg e FFprobe: ambos MP4s **12,000 s, 640×360, H.264/AAC**.
6. Player HTML5 chegou a `currentTime=12`, `ended=true`, `readyState=4`, sem media error.
7. Após reinício dos serviços, `verify` recuperou as três entregas com os mesmos
   checksums e o documento na revisão **4**, com as nove camadas editáveis.

Arquivos em `.codex-runtime/stage2-validation/`:

- `motion-v1.mp4`: SHA-256 `2308459920fbb81d56ddce95ce51d5d799a0f644e242f8556cd40e1c1d612e7f`.
- `motion-v2.mp4`: SHA-256 `5c2770226db240ae01e746760e6f42c71d34952c86bc197eeba8aa098102ba4d`.
- `composition.png`: SHA-256 `62abf4a47b1c299ecd6a38dc05a1952512cfe75f1e561d80881c940f1f50b10a`.
- `document-v1.json`, `document-v2.json`, `image-document.json`, `plan-v1.json`,
  `plan-v2.json`, `versions.json`, `evidence.json`, `browser-evidence.json` e
  `browser-playback.png`. `rendered-frame.png` foi extraído do MP4, não gerado como
  substituto do vídeo. `own-source.png` é o material sintético próprio de QA.

Logs/relatórios: `.codex-runtime/stage2-core-verified.xml/.log`,
`stage2-agent-final.xml/.log`, `stage2-node-verified.log`,
`stage2-tsc-delivery.log`, `stage2-build-delivery.log`, `stage2-live-acceptance.log`.

## 10. Bloqueios restantes

- Runtime/pesos de LLM local e benchmark de interpretação/JSON/desempenho ausentes.
- Memória disponível pequena; geração local de imagens/vídeos por modelos não
  selecionada. Nenhuma velocidade de inferência foi inventada.
- Gemini Free Tier da conta não verificado, voz real remota não homologada neste
  orçamento, credenciais existentes preservadas.
- Craft nativo/WASM, distribuição Redis/Celery e artefatos de benchmarks globais
  continuam nas dependências da Etapa 1.
- Linguagem natural por regras é limitada; sem segmentação automática de fundo,
  câmera 3D ou efeitos nativos arbitrários.
- Planejamento de modelo é síncrono e limitado pelo timeout do transporte; pedido
  de cancelamento impede publicar plano aplicável ao retornar, mas não comprova
  interrupção imediata do compute do runtime. Isso deve ser homologado com Ollama real.
- Ensaios visuais/interativos autenticados completos da nova UI continuam pendentes.

## 11. Custos externos efetivos

**R$ 0; chamadas pagas de modelos/TTS: zero.** Não houve compra de crédito,
contratação, instalação pesada ou ativação remota. Pesquisa de documentação não
foi usada como prova de acesso gratuito da conta. O perfil final continua local,
com Express/FastAPI prontos e flags pagas desligadas. A demonstração usa apenas
materiais QA, e a data do arquivo usual de governança de clientes permaneceu
04/10/2026. Nenhum login/licença foi enfraquecido para produzir a evidência.

## 12. Próximas etapas

1. Fazer ensaio da UI com sessão legítima nos temas/tamanhos previstos, incluindo
   importação, edição concorrente, recuperação, exportação e download.
2. Liberar RAM e autorizar instalação de runtime/pesos específicos com origem,
   licença e checksum conferidos; começar por modelo pequeno e contexto curto.
3. Homologar os agentes com modelo real: qualidade, JSON, limites, cancelamento,
   referência de asset, memória e latência. Só então expandir interpretação livre.
4. Disponibilizar ambiente de build e artefatos Craft verificados antes de anunciar
   ferramentas avançadas. O FFmpeg/Pillow local continua independente deles.
5. Reavaliar geração especializada gratuita somente com capacidade, licença e
   custo comprovados. Provedores pagos futuros continuam sujeitos à admissão central.

Detalhes de contratos e operação:
[arquitetura](../studios/LOCAL_MULTIAGENT_ARCHITECTURE_2026-10-22.md) e
[hardware/modelos](../operations/LOCAL_AGENT_MODELS_2026-10-22.md).
