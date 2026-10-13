# Substituição dos Studios por Craft

Estado em 13 de outubro de 2026: três motores integrados e ativados localmente
no projeto principal, com fontes completos, builds reais e exportação/cancelamento
pela fila de servidor validados. Os documentos anteriores foram migrados com
originais preservados. A revisão de fidelidade dos tratamentos avançados
permanece necessária; a inferência com LLM real foi adiada pelo usuário.

Checkout de integração: `C:/Users/edugu/Downloads/res-craft-integration`, branch
`codex/craft-studios`. O checkout principal em `C:/Users/edugu/Downloads/res`
foi ativado na branch `codex/craft-studios-active`. O estado anterior, incluindo
mudanças locais e arquivos não rastreados, está preservado na branch
`codex/pre-craft-activation-b30b5174a362` e no stash
`3750573789e3144ac8ffb8fcefe3184f11494f30`. Os 262 arquivos de saída criados após
a captura inicial foram restaurados. Configuração e bancos mantiveram seus
checksums durante a troca do código; as migrações posteriores têm backups próprios.
O commit de base registra as mudanças locais anteriores às importações.

## Fontes e procedência

| Fonte | Revisão fixada | Arquivos upstream conferidos |
|---|---|---:|
| PhotoCraft | `a7f26522ff84cd427c8a5d54b0e8ded7b56fb296` | 1.569 |
| FilmCraft | `0800a8b0aa4a703ba42172f415b45a61f8d8a5e1` | 1.236 |
| EffectCraft | `67434e90388b6dca4417555346fa6850b6f96033` | 1.016 |
| craft-libs | `5c874d51eeb3de70e735c8ce87a59a7dedd47675` | 41 |
| craft-fonts | `abb83316d96aa59c1cf64784289e378fe9fa5695` | 25 |
| FilmCraft exigido pelo EffectCraft | `2c5ba7a72619935f0481f99d59409e0d1844b234` | 951 |

Os três editores foram importados por subtree, com seus históricos. Os seis
inventários somam 4.838 arquivos e foram comparados aos blobs Git das revisões
fixadas. As interfaces originais, documentação, testes e recursos upstream
permanecem nos fontes. As adaptações Clicko ficam fora desses diretórios.

Os mirrors completos e bundles verificados ficam em
`.codex-runtime/craft/upstream`; preservam refs, branches, tags e histórico.
Os mirrors e bundles completos também estão no checkout principal, em
`.codex-runtime/craft/upstream`, com cópias independentes dos objetos Git.
O script `scripts/craft/mirror.py --bundle` reproduz esse material. O manifesto
`workers/craft/sources.lock.json` fixa árvores, blobs e checksums dos inventários.
Cada adaptador tem seu próprio `Cargo.lock`. O EffectCraft mantém a dependência
FilmCraft antiga, independentemente da montagem com o FilmCraft mais recente.

A auditoria integral está em `CRAFT_SOURCE_COMPLETENESS.json`. Ela confere todos
os arquivos, blobs e permissões contra as árvores upstream, rejeita clones
rasos/parciais e objetos emprestados, compara as referências anunciadas pelo
upstream e verifica os backups com histórico completo. Os quatro arquivos de
fontes externas e suas licenças também passaram. Foram restauradas as permissões
executáveis de seis scripts de empacotamento da cópia FilmCraft de compatibilidade;
o conteúdo desses arquivos permaneceu igual ao upstream. Cinco testes locais
de integridade passaram, incluindo a reprodução dessa perda de permissão.

As interfaces desktop/web originais, screenshots, temas, painéis e ícones estão
preservados nos fontes integrais. O índice dos screenshots com checksums está
na auditoria. O planejamento visual solicitado será feito depois desta etapa;
este fechamento não altera o desenho do frontend Clicko.

Os builds próprios incluem licenças, atribuições e checksums. As marcas e logos
upstream ficam nos fontes de referência; o frontend e executáveis distribuídos
pela integração usam Clicko. Bundles WASM incluem os avisos e licenças das fontes
e recursos, inclusive fontes tipográficas, em seus diretórios `licenses`.

## Implementação disponível

- Studio de Imagens com PhotoCraft; Studio de Vídeos com FilmCraft e área de
  composição e efeitos com EffectCraft. As entradas de edição, inclusive da
  biblioteca, chegam ao novo frontend React.
- Adaptadores Rust reais e previews WASM em Web Workers dedicados. Os modelos,
  comandos, renderizadores e formatos nativos pertencem aos projetos Craft.
- `NativeEditorStateV1`, projetos `.pcraft`, `.fcproj` e `.ecproj`, checksum de
  assets/fontes, páginas de carrossel, fontes originais e dependências vinculadas.
- Comandos manuais e por IA com o mesmo contrato, revisão esperada, idempotência,
  histórico, undo/redo, autosave e recuperação. A IA usa os provedores e controles
  de orçamento já existentes.
- Uploads por streaming, salvamento com conflito explícito, snapshots imutáveis
  de render, progresso/cancelamento, exportação, revisão e publicação vinculadas
  ao artefato e à versão aprovados.
- Migração para os modelos nativos com arquivo dos originais e pendências
  explícitas para operações que não podem ser convertidas com fidelidade.
  O relatório registra build e checksums do arquivo nativo e do original.
  Formas, cantos arredondados, tipografia e relações de parentesco não mapeadas
  recebem avisos específicos; valores neutros não acrescentam pendências.
- Recuperação das camadas visuais e motion graphs arquivados em composições
  EffectCraft editáveis, sem duplicar footage/áudio/legendas da montagem.
  A interface abre a composição e oferece seu retorno ao FilmCraft. Composições
  pendentes precisam ser vinculadas antes da exportação. Reabrir uma composição
  já recuperada mantém a revisão e as aprovações da montagem.
- O adaptador EffectCraft `1.0.1` converte grupos em camadas nulas nativas,
  mantém coordenadas locais, pivôs e animação e calcula a opacidade herdada.
  Ciclos, pais não representados, escala não uniforme com rotação e diferenças
  de composição de grupos com filhos sobrepostos geram avisos explícitos.
  Composições com grupos mantêm o documento canônico completo; a biblioteca
  guarda somente sua indicação de abertura no Studio, sem projetá-las no
  formato do editor retirado.
- Componentes, timelines, hooks e renderizadores exclusivos dos editores antigos
  retirados da execução. Os workers anteriores e testes específicos desses
  motores estão arquivados em `docs/studios/archive`, fora dos builds e imports.
  Flags de ambiente antigas não reativam esses motores. FFmpeg permanece como
  utilitário de mídia.

O frontend oferece operações conforme as capacidades reais dos builds. Fontes
externas e mídias acima dos limites locais usam o mesmo motor nativo no servidor
para a prévia. Nenhum editor antigo serve de alternativa.

## Evidência obtida

| Verificação | Resultado e limite |
|---|---|
| Integridade dos seis inventários upstream | Passou: 4.838 arquivos |
| Mirrors/bundles Git | `fsck` e verificação dos bundles passaram |
| Builds nativos Photo/Film/Effect | Concluídos; imagem `clicko-craft-runtime:local` gerada |
| WASM Photo/Film/Effect | Bundles gerados; execução real dos três em workers validada |
| Arquivo nativo → WASM → salvar/reabrir → PNG | Passou nos três motores; SHA-256 igual à referência nativa |
| EffectCraft: tempo de entrada/saída, alpha e reabertura | Passou no WASM real; canto transparente e centro vermelho verificados |
| API real dos três motores | Criação, migração, edição, histórico, conflito, reabertura e exportação passaram novamente nos builds finais |
| Áudio real em FilmCraft | Importação, mix e MP4 com áudio não silencioso passaram |
| EffectCraft → FilmCraft | WebM transparente, atualização da mesma composição, áudio preservado e bundle com `.ecproj`/WAV passaram |
| Prévia do frontend → exportação nativa | PNG do worker real da interface conferido por SHA-256 nos três motores |
| Imagem media CPU | Build concluído; usuário 10001, root somente leitura, sem rede na atestação e sete ferramentas verificadas |
| Inventário CycloneDX | 825 componentes instalados/registrados nos locks, com versões, imagem e checksums registrados |
| Fila HTTP/Redis/Celery real | Exportação MP4 e checksum passaram no worker atestado e isolado |
| Cancelamento nativo em execução | Passou novamente na imagem atualizada durante exportação real; nenhum artefato parcial publicado |
| Contratos de backend | 28 testes passaram, incluindo falha de commit, recuperação de efeitos, snapshots adulterados, criação com grupos, rejeição de carrossel inválido, avisos de fidelidade e impossibilidade de reativar motores antigos |
| Regressão selecionada do Studio | 63 testes de contratos, publicação, áudio e compilação editorial passaram; os quatro casos de avisos de conversão foram repetidos após os últimos ajustes |
| Criação com carrossel inválido | Rejeitada com `422` antes da persistência; nenhum documento criado. O caso antes retornava `500` |
| Regressões dos adaptadores Rust | Photo 2, Film 3 e Effect 12 testes passaram; transparência, hierarquia/pivôs, ciclos e reabertura verificadas |
| Hierarquia EffectCraft real | Posição, rotação, pivô e alpha herdado passaram na API e no WASM; SHA dos dois frames idêntico, reabertura preservada e pixels iguais na CLI upstream |
| Ensaio representativo de hierarquia | Um projeto existente reaberto em cópia privada: avisos EffectCraft caíram de 37 para 9; sete grupos e nove pendências de hierarquia/pivô resolvidos. Os demais avisos continuam em revisão |
| Ensaio completo de hierarquia `1.0.1` | 31 montagens e 29 composições reabertas; 120 arquivos nativos/originais com checksums conferidos. Avisos EffectCraft de 1.572 para 963; 384 avisos de hierarquia/pivô e 138 de camadas não suportadas resolvidos. Montagens nativas preservadas byte a byte |
| Recuperação real de camadas | Animação de opacity, fundo transparente, replay, CAS e composição vinculada passaram nos motores reais |
| Recuperação no frontend | Navegação para a composição, worker WASM, paridade de pixels e revisão da montagem preservada passaram |
| Referências CLI upstream PhotoCraft, FilmCraft e EffectCraft | Compilaram integralmente; executaram os arquivos Clicko sem rede e com fontes em montagem somente leitura. Interfaces desktop ainda não qualificadas |
| `.pcraft` Clicko → CLI PhotoCraft original → PNG | Abriu e converteu; pixels RGBA idênticos ao adaptador, com codificação PNG diferente |
| `.fcproj` Clicko → CLI FilmCraft original → PNG | Abriu e renderizou; pixels RGBA idênticos ao adaptador em 320 × 320 |
| `.ecproj` Clicko → CLI EffectCraft original → PNG | Abriu e renderizou; pixels RGBA idênticos ao adaptador, inclusive overlay transparente nos frames 0 e 10 da animação recuperada |
| Concorrência HTTP com motor real | Duas edições na mesma revisão: uma salva e uma `409`; revisão única, replay estável e undo restaurando os bytes originais |
| Testes unitários upstream `photocraft-engine` | 1.285 passaram, 12 ignorados e um falhou: `destructive_levels_dont_clip_in_32_bit`; suíte não aprovada |
| Integração upstream `photocraft-engine` | 45 executáveis concluídos: 129 testes passaram, cinco ignorados e nenhuma falha |
| Testes unitários upstream `filmcraft-engine` | 541 passaram, três ignorados e um falhou na conferência do preset APV pelo FFprobe; suíte não aprovada |
| Integração da CLI FilmCraft original | 11 testes passaram, incluindo presets de exportação, probe de mídia e execução de comandos |
| Testes upstream `effectcraft-engine` | 523 passaram, dois ignorados e nenhuma falha; inclui unitários e três executáveis de integração |
| Transporte Rust compartilhado | 6 testes passaram, incluindo frames e schemas de parâmetros |
| Runner isolado | 3 testes passaram |
| Estado e rotas TypeScript | 7 testes passaram |
| Interface Playwright | 7 testes passaram: edição, autosave, páginas, IA/undo, cancelamento, conflitos e recuperação |
| Compilação editorial de documentos | 27 testes passaram |
| Publicação e áudio | 8 testes passaram; binding a export nativo, pacote, revisão, agendamento e isolamento |
| Avatar, biblioteca, API, aprovações e workspace | 32 testes de regressão passaram |
| Ensaio do banco existente | 31 vídeos convertidos para arquivos FilmCraft válidos e reabertos; originais/versões arquivados e checksums conferidos numa cópia privada |
| Recuperação dos documentos existentes | 31 montagens nativas reabertas; 29 composições EffectCraft criadas e reabertas; dois vídeos sem camadas visuais. Ensaio somente em cópias privadas |
| Fidelidade desse ensaio | 30 dos 31 vídeos exigem revisão. Permanecem 1.267 avisos da montagem e 963 da composição no ensaio `1.0.1`; 14 composições excedem o orçamento automático de keyframes, quatro exigem revisão da composição de grupos e três de escala não uniforme. Máscaras e receitas avançadas também seguem pendentes. A reabertura não comprova fidelidade |
| TypeScript e build de produção | Passaram; build repetido com os três bundles WASM finais e workers |
| Coleção da suíte de backend | Sem erros de importação após arquivar testes exclusivos dos renderizadores retirados |
| Regressão ampla do backend | Não qualificada: execução interrompida após falhas no primeiro bloco; amostras diagnosticadas exigem fixture local de auditoria ausente e esperam acesso ao renderer Alight retirado |

Os testes de contrato usam doubles somente nas fronteiras de processo/provider.
Eles não comprovam fidelidade visual nem uma chamada a um provedor pago de IA.
As verificações de pixels descritas na tabela executaram os motores reais.
A suíte completa de regressão do sistema e as suítes completas upstream ainda
não foram qualificadas. As interfaces desktop upstream não foram recompiladas;
os seus fontes completos estão preservados.

Na revisão PhotoCraft fixada, o teste de níveis de 32 bits espera preto em zero,
mas obteve `-0.0796427`. O comentário do próprio teste descreve extrapolação em
32 bits; ainda é necessário resolver a divergência entre expectativa e resultado
antes de qualificar essa operação HDR. O fonte e o teste upstream permanecem
intactos. A falha está em `upstream-photo-engine-tests-retry.log` e não foi
contabilizada como sucesso dos testes Clicko.
Os testes de integração foram executados separadamente com `--test '*'`, pois
o Cargo encerrou a primeira execução após a falha unitária. O consolidado
`upstream-photo-tests-results.json` preserva os dois resultados, sem declarar
a suíte upstream aprovada.

O caso FilmCraft APV foi reproduzido separadamente: o motor exportou um arquivo
`apv1` de 320 × 320, e seu probe nativo identificou `APV 422-10`. O FFprobe
5.1.9 instalado retornou dimensões e tag, mas omitiu `codec_name`, causando a
falha da expectativa do teste. Essa incompatibilidade de verificação permanece
pendente, sem alterar ou ignorar o teste upstream. Logs estão em
`upstream-film-engine-tests.log`, `upstream-film-apv-ffprobe.log` e
`upstream-film-apv-native-probe.log`.

Os resultados agregados dos motores originais estão em
`upstream-photo-tests-results.json`, `upstream-film-tests-results.json` e
`upstream-effect-tests-results.json`: 2.489 testes passaram, 22 foram ignorados
e duas expectativas falharam. Isso cobre os pacotes descritos na tabela,
sem qualificar os demais crates, interfaces desktop ou corpus externos.

O Docker Desktop foi atualizado para 4.94.0 (241994), com Engine 29.8.2. O
problema anterior de inicialização deixou de bloquear os builds e jobs. Houve
uma interrupção posterior do daemon durante a qualificação upstream; o serviço
foi reiniciado e o último documento do ensaio foi repetido com sucesso em outra
cópia privada. A interrupção não foi contabilizada como aprovação dos testes.
Imagem media CPU validada nesta rodada:
`sha256:7fd63dfd80011cc997f4a94be878f41ed2930303922b16cbb8958dc91002a8f7`.
Esse identificador corresponde à imagem local; não houve publicação em registry.
Evidências estão em `media-worker-attestation.json`, `media-worker-sbom.cdx.json`
e `queue-acceptance-results.json`, no diretório de QA ignorado.

O teste de fila usa cópia do banco em volume Linux descartável. A primeira
tentativa identificou erro de I/O ao compartilhar SQLite simultaneamente entre
Windows e Linux por NTFS. A infraestrutura de QA foi corrigida, e o worker agora
recupera a transação antes de registrar uma falha SQLAlchemy. Projetos e banco
originais não foram usados para escrita nesse teste.

O ensaio de recuperação está registrado em
`migration-qa-567b7cd1d286/results.json`; o último documento, interrompido pelo
daemon, foi concluído em `migration-qa-9e51a24f9da7/results.json`. Ambos ficam em
`.codex-runtime/craft`, fora do Git, pois contêm informações de projetos locais.
O consolidado `existing-recovery-summary.json` registra os checksums das duas
evidências e a substituição do resultado interrompido pelo resultado repetido.
O script de ensaio aceita `--document-id` para repetir somente uma pendência,
sempre copiando o banco de origem em modo somente leitura; falhas retornam
código de saída não zero. As composições recuperadas continuam pendentes de
revisão e vínculo na montagem, sem promover a migração no banco original.

O primeiro ensaio do build `1.0.1` está em `migration-qa-1d2be2fadf2b/results.json`.
O conjunto completo foi repetido em `migration-qa-9e93982dcdf2/results.json`, sem
falhas: 31 montagens, 29 composições e dois vídeos sem camadas visuais. O resumo
`existing-hierarchy-full-summary.json` relaciona checksums das evidências,
builds reais, integridade de 120 assets e contagens anteriores/atuais. Nenhuma
montagem FilmCraft foi substituída e o banco original não recebeu alterações.
Essas contagens precedem os avisos adicionais de formas/tipografia introduzidos
na API nesta rodada; essa extensão recebe qualificação separada abaixo.
Não foi declarada fidelidade completa para o conjunto. `hierarchy-acceptance-results.json`,
`wasm-effects-results.json` e `hierarchy-cli-results.json` registram a validação
do fixture de hierarquia nos três ambientes.

Os avisos adicionais passaram em quatro casos de persistência/arquivo com
fronteira de processo simulada: PhotoCraft e EffectCraft, forma textual e forma
estruturada, parentesco, tipografia e ordem de camadas. Valores neutros não
geraram avisos. O projeto representativo foi repetido com os motores reais em
`migration-qa-adb47ecb538a/results.json`: dez avisos, incluindo a ordem `zIndex`
antes não informada, com checksums do original/arquivos nativos e builds
registrados. Não se contou esse aviso adicional como perda de uma operação
antes convertida. A redução de 37 para nove descreve o teste anterior.

O ensaio agora reconhece o motor nativo existente e materializa os arquivos da
composição vinculada, independentemente da ordem dos documentos. A repetição
da montagem e da composição já convertidas passou em
`migration-qa-b77a05fd9ea5/results.json`, com as duas identidades de motor
corretas, fontes de origem somente leitura e reabertura conferida.

A revisão upstream EffectCraft permanece `67434e90`; somente o adaptador Clicko
mudou para `1.0.1`. A identidade do build é conferida na abertura do projeto;
projetos vinculados a `1.0.0` não são trocados silenciosamente de motor.
O runtime e worker anteriores estão preservados localmente nas tags
`pre-hierarchy-1.0.0`; binário e WASM anteriores ficam em
`.codex-runtime/craft/previous-builds` e `browser-builds/effectcraft-1.0.0`.

## Pendências para o aceite final

1. Qualificar migrações de documentos reais com efeitos/receitas avançadas,
   concorrência, arquivos grandes, recuperação e cancelamento de exportações
   maiores. O cancelamento durante um fixture de 60 segundos já passou; faltam
   os casos reais de carga. Pendências de conversão preservam os originais.
2. A validação com um LLM real foi adiada explicitamente pelo usuário em
   13/10/2026. A implementação dos endpoints e a integração HTTP→comandos
   nativos foram qualificadas com endpoint local determinístico; isso não
   comprova a qualidade de planejamento de modelos reais. Não houve
   implantação na VPS nem publicação externa.

## Conclusão da implementação em 13/10/2026

O adaptador EffectCraft agora usa o build `clicko-effectcraft-1.0.2+67434e90`.
A instalação de animações amostradas ocorre em uma única transação do histórico
nativo, evitando copiar toda a composição para cada keyframe. O limite
protetor passou de 10.000 para 100.000 chaves; valores ou propriedades inválidos
não deixam uma sequência parcialmente convertida. Os fontes upstream não
foram modificados.

- Quatorze testes do adaptador EffectCraft passaram. Um fixture com 12.000
  quadros passou pela API real e pelo worker WASM, com SHA-256 idêntico nas
  transparências inicial, intermediária e final, incluindo salvar e reabrir.
- O novo ensaio completo converteu 31 documentos e reabriu 29 composições.
  Nenhum ficou bloqueado pelo orçamento antigo de keyframes. Trinta documentos
  continuam exigindo revisão de fidelidade; os originais permanecem arquivados.
  Os 1.129 avisos de EffectCraft são superiores aos 963 do ensaio anterior
  porque a interrupção por orçamento deixou de ocultar os avisos posteriores.
  Isso não representa fidelidade integral para formas, tipografia ou efeitos
  avançados que continuam explicitamente em revisão.
  A verificação adicional conferiu 149 arquivos nativos/originais por checksum
  e confirmou que as 31 montagens FilmCraft permaneceram idênticas em bytes.
- A atualização de projetos `1.0.0`/`1.0.1` para `1.0.2` exige operação explícita
  com revisão esperada e build alvo. Preserva o arquivo anterior no histórico.
  Um projeto antigo real passou por comparação de pixels com o runtime
  anterior, replay do recibo e undo. Outras combinações de build são rejeitadas.
- Quarenta e seis testes selecionados de persistência, protocolos de IA,
  permissões, cifragem, orçamento e manifesto do worker passaram; oito testes
  de interface passaram, incluindo recuperação de IA após resposta perdida
  sem uma segunda submissão. A suíte completa de backend e os dois casos
  upstream anteriormente descritos continuam com os limites registrados.
- O novo worker foi atestado como usuário 10001, raiz somente leitura e sem
  rede na atestação. Seu inventário CycloneDX tem 828 componentes. Exportação
  HTTP/Redis/Celery e cancelamento em execução passaram na imagem
  `sha256:f3f4a27e6b8cc233540278f079cd54a38fbf1699b2d3a71637a8e5dd69561ef8`.
- O provedor Pillow antigo, sem consumidores, foi removido da árvore executável
  e preservado em `archive/pillow_image_edit.py.source`.

O cadastro de IA oferece sete protocolos HTTP, treze presets de provedores e
25 sugestões de modelos. A edição usa o catálogo nativo validado e o mesmo
histórico da edição manual. Credenciais cifradas por workspace não são
retornadas à interface nem persistidas no navegador. Pedidos interrompidos
conservam a chave de idempotência; resultados desconhecidos continuam pendentes
até reconciliação. Não há reenvio automático com uma nova chave.
Veja [configuração e fontes dos provedores](LLM_PROVIDERS.md).

O teste HTTP real usou um endpoint local determinístico e PhotoCraft real:
uma submissão, pixel azul conferido, recibo reconciliado e undo com pixels
originais. O cadastro real na interface passou pela criação, leitura sem chave,
reabertura do formulário sem segredo e remoção da credencial. A produção
TypeScript/React compila. Essa evidência não é um teste de inferência de LLM.

O principal também passou pela conferência dos 4.838 arquivos upstream e pelo
build de produção. O proxy passou a transmitir projetos/exports com backpressure,
sem materializar toda a resposta na memória. Um teste com 16 MiB conferiu que
os primeiros bytes chegaram antes do término do upstream e verificou a
integridade de toda a transmissão. A nova migração de esquema `0027` foi aplicada
depois de um backup do banco com os 31 documentos originais.

`migrate_primary.py` exige `--apply`, banco e storage pertencentes ao checkout,
cria um backup SQLite antes de qualquer edição e registra cada conversão.
Verifica o checksum e a correspondência do arquivo histórico com o canvas e
as versões anteriores. Sua execução foi qualificada em dois documentos nativos
de uma cópia privada, incluindo composição dependente. A execução no principal
permanece registrada separadamente da evidência de ensaio.

As evidências privadas ficam em `.codex-runtime/craft`: `dense-motion-results.json`,
`wasm-dense-results.json`, `upgrade-build-results.json`,
`existing-bulk-motion-summary.json`, `migration-qa-0de1a60264f3/results.json`,
`llm-http-native-results.json`, `llm-connections-ui-results.json`,
`craft-llm-final-contracts-diagnostic.log`, `media-worker-attestation.json`,
`media-worker-sbom.cdx.json` e `queue-acceptance-results.json`.

## Retomada reproduzível

O principal está disponível em `http://127.0.0.1:3000`, com API em `8000`.
O broker próprio usa somente `127.0.0.1:6383`, com persistência em volume Docker.
O orquestrador Celery local usa Windows e as filas `celery,studio.media.cpu`;
os motores Rust continuam executando em containers limitados e sem rede.
Assim o banco SQLite não é compartilhado entre processos Windows e Linux.
A instalação local usa contexto de execução `embedded`, sem declarar a
atestação reservada ao worker Linux de produção. API, frontend e worker
foram ligados; o worker respondeu ao ping. O container HeyGem existente
permaneceu em execução.

Os 31 documentos do banco principal foram convertidos sem pendências técnicas,
e 29 composições EffectCraft `1.0.2` foram reabertas. São 60 projetos nativos
após a criação dessas composições. Trinta documentos têm avisos que exigem
revisão de fidelidade; suas composições ficam pendentes de aprovação e vínculo,
sem publicar ou descartar silenciosamente a edição original. O banco anterior
está preservado em `.codex-runtime/craft/primary-migration-*/database-before-native-migration.sqlite`.
O resultado real fica em `.codex-runtime/craft/primary-migration-latest.json`
no checkout principal. Os 35 testes selecionados de áudio, compilação de cenas
e revisão/publicação passaram após essa integração, além dos 46 contratos
descritos acima.

A conferência final no principal verificou 149 arquivos nativos/históricos por
checksum, 60 de 60 documentos com estado nativo e os 262 arquivos de saída
contra os blobs do stash anterior. A configuração privada permaneceu idêntica.
Os três workers WASM da versão de produção passaram por abertura, salvar e
reabrir com SHA-256 de pixels igual às referências da API nativa. Evidências:
`.codex-runtime/craft/primary-final-integrity.json` e
`.codex-runtime/craft/production-wasm-results.json`. A aplicação local respondeu
com `200`, assim como `/health/ready`; o worker de segundo plano respondeu ao ping.

Para retomar o ambiente local já compilado no checkout principal:

```powershell
./scripts/craft/start_local.ps1
./scripts/craft/start_local.ps1 -StatusOnly
```

O script usa janelas ocultas, registra os processos próprios e não para serviços
que estejam ocupando as portas. Configurações privadas existentes não são
reescritas. Logs e identificação dos processos ficam em
`.codex-runtime/craft/local`. A configuração de LLM real continua adiada.

Execute no checkout de integração. Use banco e storage isolados para QA.

```powershell
python scripts/craft/provenance.py
python scripts/craft/build.py
python scripts/craft/build.py --wasm
docker build --file workers/media-cpu/Dockerfile --tag clicko-media-cpu:craft .
npm run lint
npm run test:craft
npm run build
$env:PYTHONPATH = 'backend'
python -m pytest backend/tests/test_craft*.py backend/tests/test_worker_runtime.py backend/tests/test_creatives.py
npx playwright test --config=playwright.craft.config.ts
```

Com API de QA em `8018` e frontend em `3018`:

```powershell
python scripts/craft/acceptance.py
python scripts/craft/media_acceptance.py
python scripts/craft/recovery_acceptance.py
python scripts/craft/concurrency_acceptance.py
python scripts/craft/hierarchy_acceptance.py
python scripts/craft/worker_acceptance.py
docker pull redis:8.2.1-alpine
python scripts/craft/queue_acceptance.py
node scripts/validation/craft-browser-parity.mjs
node scripts/validation/craft-recovery-browser.mjs
node scripts/validation/craft-wasm-reference.mjs
node scripts/validation/craft-wasm-effects.mjs
```

Os dois últimos testes podem usar as referências nativas já salvas, mesmo com
Docker indisponível. Logs, projetos, PNGs, exports e credenciais de QA ficam em
`.codex-runtime/craft`, ignorados pelo Git. Essas verificações não substituem as
qualificações dos projetos reais e da implantação.
