# Clicko — Gemini experimental no Motion Design

24/10/2026. Pedido `09a1c7fc-7c26-4965-82e7-95e5847410e6`.

**Estado:** implementação local e contratos disponíveis; inferência e comparação
Gemini reais **pendentes da validação assistida escolhida pelo usuário**. Nenhuma
chave real foi lida ou cadastrada pelo agente, nem reutilizada da KLIC. Nenhum
modelo remoto foi inferido nesta etapa. Orçamento/custo externo realizado: zero.

## 1. Arquitetura utilizada

Inventário anterior às mudanças em
`docs/studios/MOTION_GEMINI_INVENTORY_2026-10-24.md`.
Fluxo: sessão DEV Express → claim assinado → FastAPI → configuração/credencial
privada → `agent_orchestrator.create_task` → `UniversalLLMPlanner` Gemini nativo →
schema/validação → revisão humana → `apply_task`/documento canônico → FFmpeg local.

Não há segunda arquitetura de agentes, editor, cliente conversacional ou
renderizador. `AudiovisualAgent` determinístico continua disponível. A flag
não altera os papéis globais ou as conexões da KLIC.

## 2. Frontend

`MotionGeminiSettings.tsx`, em Configurações do projeto do Motion: chave
transitória com colagem, mostrar/ocultar, cadastrar, remover, testar catálogo,
selecionar modelo retornado, ativar/desativar e teste mínimo após admissão.
Estado público somente Configurada/Não configurada, catálogo e disponibilidade.

O mesmo formulário de produção mostra A — regras locais / B — Gemini, duração,
Planejar com Gemini, resumo/JSON e Criar Motion Design após revisão. O plano
continua nos mesmos jobs e camadas; render/export permanecem ações explícitas.
Cancelar solicita o cancelamento do job já admitido. Uma requisição externa
já enviada pode terminar, mas seu plano cancelado não se aplica.

## 3. Backend

Novos módulos de domínio/configuração/rotas `motion_gemini`, usando as tabelas
existentes `StudioLLMConnection` e `StudioGenerationJob`, sem migração destrutiva.
Endpoints DEV em `/api/v1/studios/v1/agents/motion-gemini`: estado/configuração,
`/key`, `/test` (catálogo) e cancelamento de tarefa admitida. Planejamento e probe
usam a rota anterior de `agent-tasks`, com seleção explícita por requisição.

JSON usa `MotionAgentOutput`/`AgentOutput`, direção criativa estruturada e o
subset canônico. Renderer/estilos, identidade visual do workspace, duração,
proporção, assets do projeto e limitações 2D são enviados ao planejador; nenhum
binário, script, plugin, URL de mídia nova ou comando de shell é executável.
Seleção, locks, direitos/assets, revisão, tamanho e capacidades são revalidados.
O schema nativo enviado usa somente o subset documentado do
[GenerateContent](https://ai.google.dev/api/generate-content); o schema completo
continua no contexto e na validação Pydantic após a resposta. O gate admite
somente documentos de Motion local, não qualquer montagem de Vídeo.

## 4. Proteção da chave

- Correção de compatibilidade em 24/10: o cadastro não exige mais o formato
  legado AIza/39 caracteres, e o input não trunca em 100 caracteres. Chaves são
  tratadas como credenciais opacas (20–8192 caracteres seguros). Isso é somente
  validação básica de transporte; o Google ainda deve autenticar a credencial.
  Referência: [standard e authorization keys](https://ai.google.dev/gemini-api/docs/api-key).
- Criptografia Fernet do sistema universal, com binding de conexão/workspace/
  endpoint/protocolo e seleção experimental por `created_by`.
- Chave de criptografia DEV persistente em arquivo privado do supervisor quando
  uma chave de criptografia existente não estiver configurada. Não é chave KLIC.
- A conexão experimental é excluída das listagens genéricas e não pode ser usada,
  editada ou removida pelos caminhos universais genéricos de outro consumidor.
- Input em memória, limpo no cadastro; não usa `LocalRoom.write`, pending/recovery,
  localStorage/sessionStorage, query string, logs de payload ou export de projeto.
- Backend chama somente HTTPS oficial, chave no header, sem redirects, trust_env
  ou retries. Erros não retornam corpos do provedor. Navegador nunca recebe a
  chave cadastrada; remover apaga o ciphertext e desativa o experimento.
- Feature flag, Modo DEV, claim assinado e módulo Vídeo são exigidos. Produção
  e requisição sem autoridade DEV são recusadas, inclusive com flag isolada.

## 5. Modelos verificados

**Nenhum modelo verificado com credencial real nesta etapa.** Não há ID fixo de
modelo de produção no experimento. `models.list` pagina e filtra modelos Gemini
com `generateContent`, excluindo variantes de imagem/áudio/live. Catálogo é
candidato de texto; suporte estruturado e gratuidade ainda exigem verificação.
IDs fictícios nos testes são apenas fixtures, não ofertas de modelos reais.
Referência oficial: [API Models](https://ai.google.dev/api/models).

## 6. Estado da modalidade gratuita

**Não comprovada para uma conta real. Inferência bloqueada.** A listagem de
modelos não informa o faturamento nem o saldo de quota. O Google mostra plano
e limites no AI Studio; não se interpreta uma chave válida como uso ilimitado.
Fontes: [Billing](https://ai.google.dev/gemini-api/docs/billing) e
[Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits).

O gate aceita um recibo operacional revisado no servidor, não uma afirmação do
navegador/modelo. Exige: hash da chave própria, workspace/usuário, modelo exato,
projeto Google, tier free, faturamento desativado, suporte JSON confirmado,
autorização de inferência, referência da evidência, verificação/expiração (máximo
24 h), RPM/RPD/TPM e teto de saída. A quota real pode ser compartilhada por outros
clientes; 429 continua sendo falha, sem retry/fallback.

O caminho é configurado em `CLICKO_MOTION_GEMINI_FREE_TIER_EVIDENCE_FILE`, somente
dentro do diretório privado `CLICKO_LOCAL_DATA_DIR`. Não existe endpoint para
fabricar esse recibo ou ativar faturamento. Seu schema está em
`backend/app/domain/studios/motion_gemini.py`. **Não criamos uma evidência real ou
afirmamos verificá-la automaticamente.** Na etapa assistida, conferir no Google
o projeto da chave, Free Tier, ausência de billing e limites, antes de registrar
qualquer admissão. O operador deve revogar o recibo se o plano/billing mudar.

Admissão registra tentativas (inclusive resultado incerto/cancelado) no job
durável sob lock; conserva RPM/RPD/TPM e tokens de saída, com orçamento monetário
zero. Provedores pagos e reservas financeiras globais continuam bloqueados.

## 7. Testes de conexão

Sem chamada externa real. Contratos verificam cadastro criptografado, ausência
de chave em respostas/config, remoção, isolamento por usuário/workspace,
flag/produção/claim, paginação/header oficial, modelo desconhecido e erro de
chave. Navegador real verificou chave de formato inválido: rejeitada antes de
qualquer contato externo, campo limpo e estado Não configurada preservado.

Teste mínimo: após admissão válida e ação explícita, usa o mesmo job, saída
limitada a 128 tokens e schema `commands:[]/rationale`. Não envia o projeto,
não edita ou renderiza. Ainda não foi executado com uma chave real.

## 8. Estado do planejador Gemini

Integrado, mas **não homologado com inferência real**. Produz direção criativa
estruturada e operações existentes: conceito, narrativa/cenas, paleta,
tipografia, movimento/transições suportadas, ritmo e recomendações de áudio.
Camadas/keyframes/easing/cenas executáveis ficam no documento canônico.

Resposta inválida, comando incompatível, duração divergente, JSON malformado,
erro HTTP, timeout/transport, quota ou cancelamento não aplicam o plano nem
trocam silenciosamente para regras locais. Voltar a A é uma seleção explícita.
Áudio é recomendação, não síntese; o renderer é 2D, não perspectiva/3D real.

## 9. Testes de geração e validações

- **60 testes Python pertinentes aprovados** na rodada ampliada, sem falhas/
  erros/pulados. Após os últimos ajustes, **16 contratos experimentais** e
  **20 testes de conexões/transporte universal** passaram. O grupo experimental
  se sobrepõe à rodada ampliada: não somar as reexecuções como casos distintos.
- **273 testes Node/SSR/Vite aprovados** (271 + 2); tipagem e build aprovados.
- Ruff dos arquivos Python alterados: aprovado. `git diff --check`: aprovado.
- Revalidação para publicação em 25/10: 23 contratos experimentais (incluindo
  sete casos da correção de formato de chave), 20 testes de conexões/transporte,
  273 testes Node/SSR/Vite, tipagem, build e Ruff pertinente aprovados. São
  reexecuções das suítes, não aprovações adicionais a somar aos totais anteriores.
- Contratos com transporte falso exercitam resposta válida/malformada, rejeição
  de shell, zero custo, quotas/expiração, revisão, aplicação, cancelamento e
  renderização real via renderer local. Não são prova de inferência Gemini.
- QA real do painel no navegador DEV, seleção A/B e botão B bloqueado sem
  admissão; projeto A real criado, revisto/aplicado, renderizado e preservado.
- Dados de testes automatizados isolados do perfil DEV. Nenhum projeto de cliente
  foi alterado. UI usou somente projetos próprios de QA.

Logs/JUnit privados `.codex-runtime/motion-gemini-{final,node,types,build}.*`;
capturas `.codex-runtime/motion-gemini-settings-final.jpg`, `motion-gemini-phone.jpg`
e `motion-gemini-blocked.jpg`.
A suíte global histórica e o débito técnico documentado em outras auditorias
não foram declarados resolvidos por estes testes pertinentes.

## 10. Comparação A/B

Briefing solicitado: “Crie um Motion Design de 15 segundos sobre inteligência
artificial nas empresas, com tipografia dinâmica, elementos tecnológicos,
transições fluidas e estética premium.”

| Critério | A — planejador atual | B — Gemini real |
|---|---|---|
| Planejamento | Regras locais, três cenas de 5 s | Pendente da validação assistida |
| Elementos | Nove camadas editáveis: cartões/destaques/títulos | Não gerado |
| Composição/animação | Template 2D existente, fades/keyframes, sem IA | Não avaliado |
| Render | FFmpeg/Pillow, 1280×720, 24 fps, 15 s | Mesmo renderer previsto, não executado |
| Tempo render A observado | Aproximadamente 195 s entre admissão e conclusão nesta máquina | Sem medição |
| Tokens reais | Zero (sem LLM) | Zero nesta etapa (não houve inferência) |
| Custo externo realizado | Zero | Zero nesta etapa |
| Qualidade artística | Material para avaliação humana; não se afirma melhoria | Não comparável ainda |

Amostra A preservada: **QA · Gemini comparação A · 24-10**, documento
`f85b6591-49bf-4abb-a2b0-ba2d32ad10e6`, revisão 2, export da Biblioteca
`54e05979-155d-44ca-9600-694d5f5221ca`. A análise de desempenho não foi isolada de
outras tarefas da máquina. Amostra B não foi substituída por um mock/template.

## 11. Custos e tokens

Chamadas reais de inferência Gemini: **0**. Tokens reais Gemini utilizados: **0**.
Custo externo realizado: **R$ 0 / US$ 0**. Sem imagem/vídeo pagos, billing,
contratações ou mudança de credenciais KLIC. Tokens conhecidos das fixtures não
são consumo real. Uso recebido de uma chamada real futura será guardado no
resultado do job, incluindo thinking na contagem normalizada existente.

## 12. Limitações e próxima validação assistida

O usuário escolheu fazer a validação real depois. Próximos passos, sem enviar
chave no chat: cadastrar chave própria no painel; testar catálogo; conferir o
projeto/billing/Free Tier/quotas e suporte JSON; autorizar e registrar recibo
privado; executar solicitação mínima; criar B em novo projeto; revisar/aplicar;
exportar e comparar visualmente os dois arquivos com o mesmo renderer.

Se não houver comprovação confiável de operação gratuita, **não executar**.
Somente listar modelos não basta. Catálogo tem validade de uma hora; credencial,
modelo, flag, habilitação e recibo são rechecados antes da admissão. Não se promete
compatibilidade artística ou 3D que o motor atual não implementa. Prévia não é
deploy, e testes com transporte falso não homologam o serviço remoto.

Um reinício do processo Node registrou saída nativa Windows `0xC0000409`, sem
stack JavaScript; a causa não foi determinada. O supervisor foi iniciado
novamente, a prontidão Express/FastAPI/ponte foi confirmada e o projeto A reaberto
sem perda de dados. Não se atribui o incidente ao Gemini nem se declara resolvida
uma causa desconhecida. O ambiente foi deixado pronto para a validação assistida.

## 13. Reversão

No painel, **Restaurar planejador anterior** desativa o modo B; A permanece
disponível. **Remover chave** apaga a credencial experimental e desativa B.
Para desligar a feature, parar o supervisor e reiniciar sem a flag:

```powershell
npm run dev:stop
$env:CLICKO_MOTION_GEMINI_EXPERIMENTAL='false'
npm run dev:local
```

Remover também a configuração de evidência se foi adicionada. Não apagar os
projetos, exports ou o diretório de dados. Não é necessário reset, rollback de
documentos, mudança de modelo KLIC ou migração de banco. Flag desligada não
destrói o trabalho gerado.

### Publicação posterior — 25/10/2026

A instrução inicial de não fazer push foi substituída por pedido explícito do
usuário para atualizar o GitHub. O código e esta documentação serão publicados
na branch existente `codex/klic-atualizacao-20260823`, a partir de `1753221`.
Isso não é deploy, ativação de faturamento ou homologação da inferência real.
Credenciais, recibos privados, dados DEV, logs e capturas continuam fora do Git.

Na conferência de 25/10, painel e backend informaram chave experimental não
configurada, apesar do relato de recadastro. O ambiente foi reaberto sem reset
dos dados. Nenhuma inferência foi disparada nem amostra B foi criada; o
diagnóstico do cadastro e a verificação do Free Tier permanecem pendentes.
