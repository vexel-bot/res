# Clicko AI Studios

Frontend React/TypeScript com Express como BFF autenticado e FastAPI como serviço de projetos, mídia e jobs. A identidade e as permissões continuam pertencendo à sessão Clicko; o navegador não recebe chaves de provedores.

## Motion Gemini experimental · 24/10/2026

Integração DEV opcional, **desligada por padrão**. Reutiliza o transporte Gemini,
credenciais criptografadas, jobs/revisão do orquestrador e FFmpeg locais. Não
altera o modelo/chave da KLIC. Ative somente no supervisor local:

```powershell
$env:CLICKO_MOTION_GEMINI_EXPERIMENTAL='true'
npm run dev:local
```

Em Motion Design → Configurações do projeto → **IA Experimental — Gemini**,
cadastre uma chave própria. Ela não passa pela recuperação em localStorage.
“Testar conexão” lista modelos oficiais, **não comprova gratuidade**. Inferência,
inclusive o teste mínimo, permanece bloqueada sem recibo operacional privado de
Free Tier/faturamento desativado, quotas e autorização para a chave/modelo/usuário.
Não há checkbox no navegador que conceda essa admissão. Nada deve ser faturado.

Os modos A (regras locais) e B (Gemini) usam o mesmo editor e renderer; nenhum
plano se aplica/renderiza automaticamente. A comparação com inferência real foi
adiada pelo usuário para validação assistida; não foi simulada nem homologada.
Veja [relatório, limites e reversão](CLICKO_MOTION_GEMINI_EXPERIMENTAL_2026-10-24.md).
Publicação do código no GitHub autorizada em 25/10/2026. Isso não ativa o
experimento, não comprova inferência real e não realiza deploy.

## Revisão da experiência dos Studios · 24/10/2026

Navegação horizontal permanente em **Imagem / Vídeo / Publicidade / Ferramentas
adicionais**, com uma segunda linha de ferramentas. Até 1000 px, dois seletores
compactos substituem as linhas sem esconder o catálogo em “Alterar Studio”.
Criação com opções progressivas e editores de Motion/Imagem/Vídeo integrados à
janela. Materiais, prévia, propriedades contextuais e timeline redimensionável
compartilham os projetos,
serviços e contratos já existentes. Em telas menores, os painéis aparecem por
etapas. Projetos, histórico, recursos profissionais e editores nativos continuam
acessíveis; a KLIC usa a conversa global, sem outro chat ou mudança de modelo/voz.
Nos Studios, o acesso único fica no cabeçalho: a conversa ocupa uma faixa lateral
reservada a partir de 1440 px; em janelas menores, apresenta temporariamente a
vista de conversa, preservando o editor montado e restaurando-o ao fechar.
Gerar/Salvar/Exportar, inputs e timeline não ficam sob o balão. A lista de
projetos de vídeo não aguarda o preflight dos modelos de IA opcionais.

O navegador ficou disponível em 24/10: criação, importação, edição, versões,
PNG/MP4, reprodução e layouts claro/escuro foram exercitados com dados próprios
no DEV. Isso supera o bloqueio visual registrado na auditoria histórica abaixo,
mas **não homologa geração por IA, Craft ou produção comercial**.

Veja o [relatório desta revisão](CLICKO_REVISAO_EXPERIENCIA_STUDIOS_2026-10-24.md),
o [inventário anterior à revisão](docs/studios/UX_REVISION_INVENTORY_2026-10-24.md),
o [relatório do redesign anterior](CLICKO_REDESIGN_STUDIOS_2026-10-24.md), o
[inventário anterior às alterações](docs/studios/UX_INVENTORY_2026-10-23.md) e a
[arquitetura visual](docs/studios/UX_ARCHITECTURE_2026-10-24.md).
Nenhum push ou deploy foi realizado nesta etapa.

## Auditoria funcional e audiovisual · 23/10/2026

O [relatório de 23/10](CLICKO_AUDITORIA_FUNCIONAL_AUDIOVISUAL_2026-10-23.md) separa
renderização local de geração por IA e conformidade técnica de qualidade artística.
Novas provas reais cobrem motion de 15 s, comandos KLIC, montagem de material
próprio, áudio, PNG e recuperação pós-reinício no perfil DEV isolado.
O motion automático ainda é básico; Craft e geração IA permanecem indisponíveis.
Naquela auditoria, a homologação visual estava bloqueada pelo acesso ao navegador;
o bloqueio foi superado na revisão de 24/10 acima. A suíte Python global registrou
**888 aprovados / 277 falhas / 112 pulados**,
Ruff global tem 323 achados e `npm audit` reporta uma vulnerabilidade alta.
Node (245 + 11 complementares), TypeScript e build passaram.
Os scripts em `scripts/audits` mantêm evidências privadas em `.codex-runtime`;
não usam chamadas pagas nem publicam artefatos de QA.

## Modo desenvolvedor local · 23/10/2026

```powershell
npm run dev:local
# Outro terminal, no mesmo checkout:
npm run dev:status
```

Abra [Dashboard](http://127.0.0.1:3018/dashboard),
[Motion](http://127.0.0.1:3018/studios/video/motion),
[Vídeo](http://127.0.0.1:3018/studios/video/create) ou
[Imagem](http://127.0.0.1:3018/studios/image/edit). Não exige login comercial.
O supervisor configura explicitamente `CLICKO_DEV_MODE=true` apenas no processo
filho; não altera `.env`. Uma sessão opaca, emitida pelo servidor, expira em 8 h;
não é um bypass global. Não existe senha DEV ou chave de provedor no navegador.

O provisionamento idempotente usa Clicko Developer / Clicko DEV / Cliente DEV /
plano Desenvolvimento, com IDs reservados e permissões administrativas de teste.
O cliente também existe na governança e é validado na ponte JWT Express/FastAPI;
não foi removida a validação que causava “Cliente não encontrado neste ambiente”.

Os dados ficam em `.codex-runtime/clicko-dev`: governança, conversas, projetos,
SQLite, uploads, exports e logs. Reiniciar não apaga documentos. Reabra pela lista
de projetos ou por seu link `?document=<id>`. Preferências e rascunhos do navegador
continuam nas chaves existentes por conta/workspace DEV; para recuperá-los,
use o mesmo navegador/origem. Eles não substituem documentos salvos no servidor.
O indicador **DEV / Ambiente de Desenvolvimento** mostra serviços, ponte,
modelos configurados versus não homologados e bloqueios de custo.

Parar: `npm run dev:stop`. Para desativar, **pare primeiro o perfil DEV** e só então:

```powershell
$env:CLICKO_DEV_MODE='false'
npm run dev:local
```

Nesse perfil, login, cliente autorizado, licenças e permissões comerciais voltam
a ser exigidos. Seu diretório padrão é o QA histórico `.codex-runtime/stage1-local`,
não o banco DEV nem produção. `CLICKO_LOCAL_REQUIRE_LOGIN=true` é um alias de
compatibilidade. Para voltar ao DEV, pare esse perfil e remova as duas variáveis.
Use sempre o mesmo `CLICKO_LOCAL_DATA_DIR` para iniciar, consultar e parar um
perfil. Se mudou as flags antes de parar, informe explicitamente a pasta do
processo ainda ativo ao executar `dev:stop`.

Limpeza recuperável, somente se desejar recomeçar os testes:

```powershell
npm run dev:stop
npm run dev:reset -- --confirm=ARCHIVE_CLICKO_DEV
```

O comando exige marcador privado e servidor parado, e **arquiva** a pasta com
timestamp; não a exclui permanentemente. O próximo início cria um perfil novo.
Backups podem ser restaurados com os serviços parados, preservando o caminho
original do perfil. Não apague a pasta arquivada se precisar dos projetos.
O comando não limpa rascunhos/preferências do navegador; remova apenas as chaves
DEV, se necessário, sem apagar o armazenamento de contas comerciais.

Somente loopback direto: rejeita produção/bundle, listener público, origens
remotas, cabeçalhos de proxy e conexões cujo endereço real não é loopback.
Não publicar por túnel, proxy ou redirecionamento TCP. O plano DEV não autoriza
gastos: Node, TTS, geração remota Python, pagamentos e integrações externas ficam
bloqueados. Ferramentas acessíveis não equivalem a recursos homologados:
composição PNG, timeline FFmpeg e motion 2D são locais; geração IA, voz externa e
motores Craft continuam sujeitos à infraestrutura/configuração real.

Veja [o relatório do Modo DEV](CLICKO_MODO_DESENVOLVEDOR_2026-10-23.md) e a
auditoria funcional acima. Os relatórios abaixo descrevem etapas históricas.

## Etapa 3 · homologação técnica de 22/10/2026

Corrigidos o encaminhamento de desfazer pela KLIC, pedidos incompletos de cor/texto
e a prioridade do projeto aberto por link sobre rascunhos de outro documento.
O Motion recebeu recuperação de erro acionável e controles avançados sob demanda.
Novas provas geraram dois MP4s de 15 s, verificaram persistência após reinício e
reutilizaram um PNG entre Imagem, Motion e Vídeo, preservando o original.

Naquela etapa, a homologação autenticada do editor ficou **pendente por escolha do usuário**;
o acesso direto de prévia não a substitui. Na inspeção, o cliente local selecionado
não estava cadastrado no backend; não se retirou essa proteção.
Veja [o relatório da Etapa 3](CLICKO_ETAPA3_HOMOLOGACAO_STUDIOS_2026-10-22.md).

Reprodução técnica: `node --import tsx scripts/agents/stage2-live.ts --stage3`;
após reiniciar o perfil, `.venv\Scripts\python.exe scripts/agents/stage2-verify.py --stage3`.
As evidências ficam em `.codex-runtime/stage3-validation`, separadas das anteriores.

## Situação atual · revisão de conclusão de 22/10/2026

A produção local foi revalidada e as falhas de seleção/cor, duração de uma camada,
texto literal e metadados de cenas foram corrigidas. O backend passou a impor o
escopo das edições também na aplicação; perguntas não geram mudanças e recibos
comprometidos continuam idempotentes. `dev:status` não encerra silenciosamente
antes da checagem de saúde. Há testes adicionais de regressão e de controle local.

Veja o [parecer atualizado de conclusão](docs/audits/STAGE2_COMPLETION_REVIEW_2026-10-22.md).
O MVP local está validado tecnicamente, **não** totalmente homologado como IA
generativa: a homologação visual do editor, os modelos e os motores
Craft ainda são dependências. Não houve chamadas pagas, instalação pesada ou push.

Para repetir a prova sem sobrescrever os arquivos de QA anteriores:
`node --import tsx scripts/agents/stage2-live.ts --review`; após reiniciar o perfil,
`.venv\Scripts\python.exe scripts/agents/stage2-verify.py --review`.
Teste de controle local: `node --test scripts/dev-local-control.test.mjs`.

## Etapa 2 · criação e edição assistida local

Incremento sobre os agentes existentes: comandos podem usar a camada selecionada
ou uma cena específica, pedem esclarecimento quando ambíguos e preservam os demais
elementos. Motion oferece texto palavra por palavra, fonte do sistema regular/
negrito, gradiente, sombra 2D, controles completos de keyframes e duplicação com
undo/redo. A biblioteca reutiliza materiais do mesmo ambiente entre Studios.

Tarefas expõem responsável, seleção, histórico, limites e revisão aplicada.
O ensaio `node --import tsx scripts/agents/stage2-live.ts` usa o roteador real da
KLIC, a ponte assinada e o backend do perfil QA isolado para criar/renderizar duas
versões de 15 s. Não exige nem cria login no navegador. Depois de reiniciar o perfil,
`.venv\Scripts\python.exe scripts/agents/stage2-verify.py` confere persistência e mídia.
Esses scripts só aceitam `dev:local` pronto com `.codex-runtime/stage1-local`.

O ensaio é **determinístico**, sem inferência; o fallback de modelo do fixture
falha fechado e conta chamadas. Não prova Gemini nem um LLM local em operação.
Leia o [relatório da Etapa 2](docs/audits/STAGE2_AGENT_EXPERIENCE_2026-10-22.md).

## Agentes e produção local · 22/10/2026

Motion Design e Image Studio agora oferecem **Edição local**, com documentos,
camadas e versões canônicos. A KLIC encaminha criação/edição a dois especialistas
de backend; no perfil sem modelo, o planejamento é por regras explícitas.
Há MP4/PNG reais, keyframes/easing, composição e histórico. Gemini e os editores
nativos existentes permanecem disponíveis em seus caminhos, conforme a configuração.

Nenhum modelo ou runtime pesado foi instalado e nenhuma API paga foi usada.
Ollama local é configurável por papel, mas a inferência real continua pendente.
Consulte a [arquitetura e limites](docs/studios/LOCAL_MULTIAGENT_ARCHITECTURE_2026-10-22.md),
o [hardware/modelos e operação](docs/operations/LOCAL_AGENT_MODELS_2026-10-22.md)
e o [relatório da implementação](docs/audits/LOCAL_MULTIAGENT_IMPLEMENTATION_2026-10-22.md).

## Execução local, sem geração paga

### Etapa 1 · procedimento centralizado (21/10/2026)

Com as dependências abaixo instaladas, use `npm run dev:local`, `npm run dev:status`
e `npm run dev:stop`. Express/FastAPI usam loopback nas portas 3018/8018.
Desde 23/10/2026, o perfil padrão é o novo DEV com sessão do servidor e dados em
`.codex-runtime/clicko-dev`, descrito acima; o antigo bypass não é ativado.
O armazenamento histórico `.codex-runtime/stage1-local` foi preservado.
Chamadas pagas Node, TTS e Python permanecem desativadas. Não altera o `.env`,
autenticação de produção ou licenças comerciais. Não exponha publicamente.
Portas ocupadas não são encerradas à força.

Veja [o procedimento e os requisitos Craft/Redis/Celery](docs/operations/STAGE1_LOCAL_INFRASTRUCTURE.md)
e [a admissão financeira central](docs/operations/STAGE1_FINANCIAL_ADMISSION.md).
O perfil histórico `npm run dev` abaixo continua disponível para quem gerencia
seus próprios dados/serviços; não confunda as duas pastas de armazenamento.

Entrega e evidências: [relatório da Etapa 1](docs/audits/STAGE1_INFRASTRUCTURE_IMPLEMENTATION_2026-10-21.md).
Rodada geral: **860 aprovados, 292 reprovados, 113 pulados**, sem novos IDs de
falha frente à referência. Núcleo audiovisual/financeiro: 89 aprovados e 18 pulados;
regressão final de orçamento/recuperação: 21 aprovados. npm: 233 aprovados, mais
7 de estado Craft executados separadamente. Ruff, tipagem e build aprovados.
Não há homologação global ou distribuída; Craft e artefatos ausentes seguem bloqueados.

Pré-requisitos: Node/npm, Python 3.12 com o ambiente `.venv` e FFmpeg/FFprobe com H.264/AAC. As dependências estão em `package-lock.json`, `backend/requirements.txt` e `backend/requirements-dev.txt`. Não é necessário instalar modelos de IA para editar/exportar uma timeline canônica.

No PowerShell, na raiz do checkout:

```powershell
npm ci
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt
$env:PORT='3018'
$env:CLICKO_STUDIOS_ORIGIN='http://127.0.0.1:8018'
npm run dev
```

Em desenvolvimento, Express pode iniciar o FastAPI local em um endereço loopback explicitamente configurado. A configuração anterior ignorava esse endereço e deixava o Studios parado. O perfil automático utiliza SQLite, arquivos locais e um pool de duas threads, com oito trabalhos admitidos no máximo. Os provedores pagos de mídia são desativados nesse perfil. `CLICKO_STUDIOS_AUTOSTART=false` permite gerenciar o serviço separadamente.

Os dados normais ficam em `.clicko-data/studios`. `CLICKO_STUDIOS_DATA_DIR` pode apontar para um diretório de QA separado. A validação desta etapa utilizou `.codex-runtime/studios-recovery`, sem migrar nem sobrescrever projetos de clientes. Não apague diretórios de runtime contendo arquivos que queira preservar.

Prévia: [Dashboard](http://127.0.0.1:3018/dashboard) e [Studios](http://127.0.0.1:3018/studios).
Com `npm run dev:local`, o acesso é direto; nos demais perfis, a sessão Clicko
continua necessária, salvo configuração explícita de desenvolvimento.

## Arquitetura e capacidade real

- `server/studios/proxy.ts`: sessão, RBAC, escopo de cliente, streaming e admissão comercial idempotente antes do FastAPI.
- `backend/app/studio_app.py`: autenticação pela ponte JWT do BFF. `app.main` conserva sua autenticação própria. Ambos reutilizam o mesmo catálogo de rotas de mídia e middleware HTTP.
- Timeline canônica: cortes, trim, sobreposição, texto/legendas fornecidas, fades, animações X/Y/escala/opacidade, rotação estática, áudio e MP4 H.264/AAC. A prévia é um arquivo realmente renderizado, não uma simulação de exportação.
- Projetos nativos: PhotoCraft, FilmCraft e EffectCraft são preservados. Precisam dos binários e/ou WASM compilados; não há substituição silenciosa por outro motor.
- IA: as conexões LLM existentes podem planejar comandos nativos ou uma timeline canônica. JSON Schema, tipos, revisões, referências, limites do renderizador e recibos de operação são conferidos antes da aplicação. O modelo não executa comandos de shell.
- Imagens: proporção e resolução são parâmetros nativos do adaptador. A proporção do arquivo recebido é validada. O canvas do projeto não equivale à resolução do gerador. Candidatos continuam sujeitos à revisão humana.

As rotas antigas Express `/api/ai/image-edit`, `/api/ai/video-edit` e `/api/ai/generate-image` retornam `410` com orientação de migração. As duas primeiras simulavam edição; a terceira contornava o fluxo durável de cotas. Projetos existentes não foram removidos.

## Saúde e processamento

`/api/health` é liveness do Express. `/api/ready` exige a prontidão real do Studios. `/health/ready` no FastAPI verifica banco, armazenamento, FFmpeg e processamento. Em modo Celery, exige Redis e consumidores das filas necessárias; em modo local, identifica explicitamente `local-thread-pool`. Falha em dependência obrigatória resulta em `503`.

O pool local não substitui uma fila durável de produção. Após reinício, trabalhos interrompidos ficam explicitamente recuperáveis; uma requisição externa de resultado desconhecido não é reenviada automaticamente. Entregas duplicadas não devem adquirir a mesma execução simultaneamente. Os limites de tempo de Celery acompanham o perfil de cada job, inclusive quando as filas isoladas não estão habilitadas.

Em produção: PostgreSQL, migrações não destrutivas aplicadas pelo operador, Redis, workers Celery e armazenamento configurado são requisitos externos. `ENVIRONMENT=production` valida essas restrições e proíbe execução eager. Não use o servidor de desenvolvimento como deploy de produção.

## FFmpeg e Craft

`FFMPEG_PATH` e `FFPROBE_PATH` explícitos têm prioridade. Um caminho inválido não provoca fallback silencioso. Sem configuração explícita, a descoberta utiliza PATH e, no checkout local, a instalação em `.codex-runtime/ffmpeg/*/bin`. O encoder H.264 disponível é detectado (`libopenh264` ou `libx264`).

Para os três motores nativos, siga [o guia Craft](workers/craft/README.md):

```powershell
.venv\Scripts\python.exe scripts/craft/provenance.py
.venv\Scripts\python.exe scripts/craft/build.py
.venv\Scripts\python.exe scripts/craft/build.py --wasm
```

O builder deste projeto exige Docker com engine Linux. Na máquina auditada, Docker/Rust e os bundles compilados não estão disponíveis. A compilação permanece bloqueada, não aprovada. URLs de bundles ausentes retornam `404` JSON, nunca HTML da SPA.

## Governança financeira e comercial

São mecanismos diferentes:

1. **Imagens:** uma unidade por solicitação aceita, inclusive falha/cancelamento. Replay HTTP e retry do mesmo job não cobram uma segunda unidade.
2. **Vídeo:** conforme confirmação do usuário, somente cenas geradas por IA consomem minutos. Edição, prévia e exportação locais não consomem essa cota. Reserva prévia protege o limite; resultado validado concilia segundos. Resultado desconhecido mantém a reserva.
3. **Financeiro USD:** reserva conservadora antes de submissões externas, estimativa por tarifa configurada separada de custo informado pelo provedor. Sem fatura conciliada, `providerReportedCostUsd` permanece nulo.
4. **Métricas:** segundos de processamento, segundos de saída/geração e bytes de ativos persistidos. Essas medições não inventam uma tarifa de CPU nem equivalem a uma cobrança comercial de armazenamento.

Limites financeiros mensais, todos explicitamente positivos para admitir chamadas pagas:

```text
STUDIO_EXTERNAL_MONTHLY_BUDGET_USD
STUDIO_EXTERNAL_WORKSPACE_MONTHLY_BUDGET_USD
STUDIO_EXTERNAL_USER_MONTHLY_BUDGET_USD
STUDIO_EXTERNAL_MODEL_MONTHLY_BUDGETS
```

Continuam válidos os limites e flags específicos de Gemini/Runway e o teto próprio das conexões LLM. Credenciais e tarifas precisam ser provisionadas pelo operador; esta etapa não habilitou nenhuma chamada paga. A ponte exige recibo comercial assinado para geração/edição de imagem e geração de vídeo. Rotas genéricas e produções internas não podem contornar essa admissão; aquisição autônoma de mídia sem recibo fica bloqueada até a integração própria.

KLIC/Gemini Node e Google Cloud TTS agora exigem reserva e claim no mesmo ledger
USD do Python, antes do SDK. Sem `CLICKO_NODE_OUTBOUND_ENABLED`,
`STUDIO_NODE_OUTBOUND_ENABLED`, tarifa Node versionada/válida e limites, a operação
falha fechada. Idempotency-Key deve ser reaproveitada nos reenvios. Resultado
desconhecido mantém reserva; estimativa de tokens não é fatura. O adaptador Python
antigo sem escopo financeiro não pode contornar a admissão canônica. Não se afirma
conciliação automática de extratos externos ou homologação de chamadas pagas.

A identidade financeira usa a empresa e o membro SaaS originais, não a partição de banco do cliente selecionado. Trocar de cliente não multiplica o orçamento. O período da reserva também é considerado quando uma tarefa antiga é retomada; registros históricos sem vínculo financeiro verificável exigem conciliação, nunca uma identidade escolhida pelo navegador.

Para futuros testes de Claude via OpenRouter, utilize a conexão LLM existente com protocolo Chat Completions, endpoint oficial, modelo explicitamente cadastrado, credencial cifrada no servidor, tarifas e orçamento. Nenhuma conta, chave ou modelo foi ativado nesta etapa.

## Verificação

```powershell
npm test
npm run lint
npm run build
$env:PYTHONPATH='backend'
$env:GEMINI_OUTBOUND_ENABLED='false'
$env:GEMINI_VIDEO_GENERATION_ENABLED='false'
$env:STUDIO_GEMINI_ENABLED='false'
.venv\Scripts\python.exe -m pytest backend/tests/test_studios_recovery.py backend/tests/test_image_frontend_contract.py backend/tests/test_video_timeline_real.py
```

Os testes Python utilizam banco/armazenamento temporários. Testes de protocolo com doubles não comprovam qualidade de geração dos provedores. Os testes reais de timeline utilizam FFmpeg, verificam pixels/áudio, arquivo, checksum, download e isolamento.

### Referência audiovisual real de 18 segundos

Para repetir a validação gratuita, com banco temporário e materiais procedurais próprios:

```powershell
$env:PYTHONPATH='backend'
$env:GEMINI_OUTBOUND_ENABLED='false'
$env:GEMINI_VIDEO_GENERATION_ENABLED='false'
$env:STUDIO_GEMINI_ENABLED='false'
$env:CLICKO_VALIDATION_ARTIFACT_DIR=Join-Path (Get-Location) '.codex-runtime/final-validation-2026-10-21'
.venv\Scripts\python.exe -m pytest -q backend/tests/test_media_final_validation.py
```

Essa pasta retém MP4, PNGs e `evidence.json`, fora do banco temporário. O ensaio monta três cenas, títulos, gráfico, fades e áudio pelo backend real; não faz inferência e não comprova produção autônoma por IA. Na conferência de 21/10, o MP4 de 18 s também foi importado, reproduzido e reexportado pela interface em 1920×1080. O sinalizador `originalAudioEnabled` do frontend é aceito e respeitado pelo renderizador; áudio original ligado/desligado tem testes PCM reais.

Registro histórico anterior à Etapa 1: 78 aprovados e 18 pulados na rodada direcionada; TypeScript, build e 229 testes frontend aprovados com Vite 6.4.5. A execução Python global daquela rodada registrou 836 aprovados, 279 falhas conhecidas e 112 pulados; precedeu a correção de áudio, verificada depois nos testes direcionados e navegador. Não representa a contagem atual nem aprovação global de produção. Os resultados e bloqueios da nova execução estão no relatório específico da Etapa 1. Auditoria npm: zero altas/críticas e três moderadas remanescentes na cadeia Mammoth, sem downgrade inseguro aplicado.

Consulte [a validação final e preparação de IA](docs/audits/FINAL_MEDIA_VALIDATION_2026-10-21.md), [a recuperação anterior](docs/audits/MEDIA_RECOVERY_2026-10-21.md), [a auditoria de referência](docs/audits/IMAGE_VIDEO_TECHNICAL_AUDIT_2026-10-20.md) e [o histórico](CHANGELOG.md). Há testes legados e runtimes ainda não qualificados; build aprovado não significa plataforma inteira aprovada para produção.
