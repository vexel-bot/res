# Estúdio de vídeo — front-end, 17/10/2026

## Escopo e integração

Somente `/video` ganhou a nova experiência. `ClickoStudioView` encaminha `create-video` para `VideoStudio`, carregado sob demanda; Imagem não precisa carregar o código/CSS da nova interface. O fluxo de Imagem continua usando `DepartmentStudio` / `CraftStudio`. Não houve alteração de banco, autenticação, contratos, filas, provedores, governança ou regras de negócio. CSS e tipografia estão restritos a `.vs-root`.

Arquivos novos:

- `src/studios/video/VideoStudio.tsx`: navegação Criar com IA / Editor / Motion / Anúncios, briefing compartilhado, catálogo, upload, disponibilidade, fila e exportação.
- `src/studios/video/VideoEditor.tsx`: monitor, transporte, painel de mídia, inspetor por categoria, projeção multifaixa, seleção, movimentação, corte e divisão por comandos nativos confirmados.
- `src/studios/video/LegacyVideoProjects.tsx`: consulta e continuidade dos pedidos antigos sem criar cópias.
- `src/studios/video/VideoProjectTools.tsx`: histórico, importação/download nativo, atualização de build, avisos de fidelidade, recuperação de composição e revisão editorial, reutilizando os serviços existentes.
- `src/studios/video/videoModel.ts`: modelos de apresentação, construção dos contratos existentes, validação, projeção da timeline, comandos e presets nativos de motion.
- `src/studios/video/videoUsability.ts`: organização das capacidades confirmadas, parâmetros principais/avançados, controle nativo de ganho, avisos da revisão correta e orientação contextual.
- `src/studios/video/video-studio.css`: painéis, estados, desktop/tablet/mobile, tema claro/escuro e redução de movimento.
- `src/studios/video/videoModel.test.ts`: 11 testes de validação, contratos, revisão, tempo nativo, presets e confirmação de saída.
- `src/studios/video/videoUsability.test.ts`: 6 testes de ferramentas confirmadas, preservação de schemas, áudio, orientação de fluxos e isolamento dos avisos de conversão.
- `backend/tests/test_video_frontend_contract.py`: 3 testes de compatibilidade HTTP, usando banco temporário isolado. Nenhuma lógica do backend foi modificada.

Arquivo de integração modificado: `src/studios/ClickoStudioView.tsx`.

## Funcionamento real

- As quatro áreas compartilham o documento aberto e o briefing; trocar de área não cria outro projeto.
- Projetos são listados, criados, reabertos e atualizados por `productApi.studioDocuments/createStudioDocument/replaceStudioDocument`. O catálogo não contém exemplos fictícios.
- A gravação de metadados mantém composição e estado nativo intactos. O servidor continua sendo autoridade sobre revisão, aprovação e acesso.
- Reabrir um projeto busca o documento atual no servidor antes de preencher o formulário; abrir novamente o projeto atual não restaura o briefing antigo do catálogo. Uma confirmação de salvamento não limpa a indicação de alterações digitadas depois do envio.
- Proporção/duração/idioma são definidos na criação e preservados no contrato extensível existente. Depois de salvar, a configuração estrutural usa o motor nativo; o PUT de briefing não tenta reescrever uma timeline protegida.
- Materiais são enviados por `craftApi.uploadAsset` e lidos por `studioAssetBlob`, com os headers de módulo/cliente e a sessão já implementados. Os mesmos IDs são usados na biblioteca e no documento.
- Uma criação com resultado de transporte desconhecido é reconciliada por `correlationId` antes de qualquer novo POST. Não há reenvio automático de criação potencialmente persistida.
- A reprodução da mídia original usa o navegador e está identificada como **original, sem efeitos da montagem**. A duração vem do arquivo carregado quando disponível.
- A montagem usa `useCraftStudio`, suas revisões, recuperação local existente, idempotência, undo/redo, migração, comandos, salvamento e exportação. Não foi criado um segundo motor JavaScript de edição.
- A prévia da montagem usa WASM quando disponível ou o endpoint nativo de quadros; não é uma imagem mock. A reprodução de quadros WASM é visual, sem mixagem de áudio; a saída renderizada possui a mixagem do pipeline. O processamento de quadros é sequencial e para ao sair do editor.
- Timeline agrupa os clipes e as camadas realmente retornados pela inspeção. Faixas vazias são explicitamente vazias, não exemplos de conteúdo.
- Reposicionamento usa `timeline.move`, cortes usam `timeline.trim`, divisão usa `timeline.razor`, silenciamento usa `timeline.setTrack`. Os comandos aparecem/habilitam somente quando confirmados pela versão do motor. FilmCraft usa 254.016.000.000 ticks por segundo.
- Texto, áudio, legendas, efeitos, transições e keyframes são acessíveis pelas capacidades e schemas reais do inspetor. Parâmetros complexos possuem edição JSON avançada; não se inventam operações que o motor não expõe.
- O ganho rápido usa `clip.audioGain` com seleção nativa, modo `set` e faixa de −60 a +12 dB. Histórico e arquivos nativos reutilizam `loadVersions/loadNative/saveNative`; bundles de múltiplas páginas preservam a extensão ZIP. Atualização de build reutiliza `upgradeBuild`.
- Avisos de migração/fidelidade não são escondidos pela nova interface. A recuperação de camadas do original usa `recoverEffects` e só abre a composição depois de receber seu ID do servidor. Também é possível guardar uma cópia JSON da recuperação local existente.
- A revisão editorial reutiliza `EditorialReviewPanel` e `studio.review`. Envio exige conteúdo já vinculado, gate da mesma revisão, exportação atual confirmada e ausência de lote pendente. Um projeto independente de biblioteca não ganha um vínculo editorial fictício.
- Motion oferece três presets de títulos: abertura, identificação e CTA. Quando disponíveis, aplicam `engine.batch` atômico com `layer.newText` e quatro `prop.addKey` de opacidade. IDs são referências de resultado do motor (`$1.layer`), não IDs adivinhados. A composição pode ser vinculada a uma montagem nativa existente por `linkComposition`.
- Anúncios possuem caminhos de vídeo próprio e montagem de mídias, com oferta, benefício, público, tom, roteiro e CTA persistidos nos campos existentes do briefing.
- Montagem assistida usa o `CraftModelPicker` e `applyAI` existentes. Isso significa comandos de edição sobre o projeto; **não** significa geração integral de filmagens por prompt.
- Exportação acompanha os estados reais de job, cancelamento e retry admitido pelo servidor. Download só aparece com status `succeeded` e asset confirmado. Uma saída de revisão anterior não substitui a prévia da revisão atual. Progresso respeita a escala 0–100 do backend.

## Complemento de identidade e usabilidade

- Tipografia de sistema sem fontes externas; superfícies neutras, coral/tangerina para ações da Clicko e azul `#6EB8F5` restrito à assistência por IA. Alterações continuam restritas ao módulo de Vídeo.
- A orientação inicial distingue projeto vazio, rascunho salvo e motor disponível. Os quatro caminhos explicam como começar sem confundir briefing, mídia original, montagem e saída renderizada.
- Ferramentas frequentes têm botões diretos, derivados das capacidades realmente retornadas. O catálogo completo permanece em “Todas as ferramentas”. Não foram removidos schemas, defaults, limites ou parâmetros técnicos.
- Conexão/modelo de IA, disponibilidade dos serviços, parâmetros avançados, histórico/arquivos e revisão editorial ficam sob demanda. Foram reaproveitados `CraftModelPicker`, `useCraftStudio`, `useCraftBrowser`, `EditorialReviewPanel`, `ClickoSelectMenu`, `productApi`, `craftApi` e `departmentApi`, sem serviços duplicados.

## Dependências e limites — não apresentar como pronto

1. **Runtime nativo ausente neste ambiente**: FilmCraft/EffectCraft e codecs precisam ser compilados/provisionados conforme `workers/craft/README.md` e `scripts/craft/build.py` (Docker com engine Linux no runner Windows). A evidência histórica de outro checkout em `docs/studios/CRAFT_INTEGRATION_STATUS.md` não comprova runtime instalado nesta máquina. Assim, os fluxos reais de render, export, keyframes, cortes e mixagem não puderam ser exercitados com pixels aqui. Os testes de ciclo nativo existentes usam uma fronteira de motor isolada; não comprovam renderização audiovisual real.
2. **Edição WASM**: depende dos builds compatíveis em `public/craft` e dos limites de memória do mecanismo existente. Sem WASM, ainda é possível pedir quadros ao servidor, quando o runtime de servidor estiver operacional. Não se simula reprodução nativa em tempo real.
3. **Vídeo integral por IA**: o backend oferece scene-generation com preflight, modelos locais, plano contextual V2, vínculo de cena/requisito e admissão de candidato. O novo front-end consulta a disponibilidade, mas não cria esse plano especializado nem oferece um atalho que contorne as verificações. O caminho está marcado como não habilitado. É necessária uma integração futura específica com o planejador/admissão, além do serviço/modelo qualificado; credenciais sozinhas não bastam.
4. **Avatar/apresentador**: exige provider/modelo, identidade/voz, consentimentos e qualificação existentes. O fluxo guiado dessas aprovações não foi reconstruído neste módulo. O cartão é informativo e não habilitado, mesmo que um provedor isolado esteja apto. Não se promete clonagem de voz, lipsync ou remoção de fundo.
5. **Voz/transcrição automática**: ferramentas expostas pelo motor e upload de áudio podem ser usados quando disponíveis. Não há novo fluxo guiado de síntese, gravação de câmera/microfone ou importador dedicado de SRT neste trabalho; esses recursos dependem de integrações/contratos específicos e permissões de captura. Legendas manuais usam os comandos reais expostos.
6. **Personalização avançada**: algumas operações ainda dependem dos schemas técnicos/JSON do motor. Presets de motion foram conectados ao contrato nativo e testados como comandos, mas exigem uma rodada de QA no motor real após provisionamento.
7. **Miniaturas e consumo**: não há miniaturas renderizadas ou duração de mídia inventadas no catálogo. Ícones identificam o tipo de projeto; durações planejadas são lidas do documento. Não foi inventada estimativa de créditos/tempo.
8. **Pedidos anteriores incompletos**: o contrato anterior exige um vídeo de origem antes de produzir. Quando ele não existe, o pedido permanece visível/preservado, com o impedimento explicado; não se cria uma cópia automática.

## Validação

- `npm run lint` — TypeScript sem erros.
- `npm test` — 154 testes aprovados, incluindo 11 do modelo de vídeo e 6 de usabilidade/contratos de ferramentas.
- `node --import tsx --test tests/unit/craftState.test.ts` — 7 testes adicionais de recuperação, comandos e integração aprovados.
- `npm run build` — frontend, servidor e worker compilados.
- `PYTHONPATH=backend .venv/Scripts/python.exe -m pytest backend/tests/test_video_frontend_contract.py backend/tests/test_clicko_studio_bridge.py backend/tests/test_studio_department.py backend/tests/test_craft_studios.py backend/tests/test_craft_lifecycle.py -q` — 29 testes de contratos/ciclo, sem chamadas pagas.
- Persistência isolada: criar → ler → atualizar briefing → ler novamente; composição preservada; revisão obsoleta rejeitada (409); reescrita de composição rejeitada (422); cliente diferente rejeitado (404); usuário somente Imagem não cria Vídeo (403).
- Upload isolado: PNG real → biblioteca do workspace → referência no documento/timeline → releitura do asset original, sem duplicação.
- Verificação no navegador: quatro áreas, editor vazio honesto, validação de briefing, aviso de motor indisponível, recursos bloqueados corretamente, temas claro/escuro, desktop (largura padrão aproximadamente 1480), tablet 1024×768 e celular 390×844. Nas verificações móveis/tablet, `scrollWidth` da página ficou menor ou igual à viewport. Nenhum documento fictício foi criado no ambiente do usuário.
- Abertura limpa do módulo após a separação do bundle: sem erros/avisos no console. Tema e viewport originais foram restaurados. Os arquivos do teste de upload usam diretório temporário isolado, sem deixar materiais de teste no projeto do usuário.
- **Limite da rodada final do complemento:** a automação local do navegador passou a retornar “Local browser use is disabled in Work settings”. Portanto, a conferência visual descrita acima é da implementação anterior ao complemento de disclosure/ferramentas avançadas; esses últimos ajustes receberam TypeScript, testes e build, mas não uma nova inspeção visual. Não foi usado outro mecanismo para contornar a configuração do usuário.

## Próximo passo

Provisionar os runtimes/codecs e WASM existentes, configurar uma conexão de edição com IA aprovada e executar QA audiovisual com mídia de teste: corte, áudio, legendas, presets, vínculo de composição, exportação e cancelamento/retry. Somente então declarar geração/renderização ponta a ponta operacional. Os caminhos especializados de vídeo generativo e avatar precisam de implementação guiada adicional sobre os contratos existentes.
