# Rostos, vozes, personagens e evolução no localhost

## Iniciar o produto

Após a atualização do time de 24/10, o perfil de desenvolvimento usa a sessão
atual do Clicko e a ponte autenticada para o backend dos Studios. No PowerShell,
com as dependências instaladas e o ambiente Python em `.venv`:

```powershell
$env:PORT = '3000'
$env:CLICKO_LOCAL_STUDIO_PORT = '8000'
node scripts/dev-local.mjs
```

O perfil mantém dados privados em `.codex-runtime/clicko-dev`, recusa portas
ocupadas e não herda autorização de gasto. O status e o encerramento usam
`node scripts/dev-local.mjs status` e `node scripts/dev-local.mjs stop`.
O log fica em `.codex-runtime/clicko-dev/service.log`.

O launcher anterior `scripts/craft/start_local.ps1` continua disponível para
execução com worker e broker dedicados. Ele não deve ser iniciado por cima do
perfil DEV. Os dados anteriores, o `.env` e as chaves permanecem locais.

## Acessos

- /evolution: documentos completos, pesquisa, filtros e download dos .md.
- /library/identities: pessoas, personagens, vozes, versões e autorizações.
- /studios: pedido, escolha de direção e revisão da entrega.

É necessário entrar na conta do workspace. A área de evolução é um catálogo
versionado de documentos; os registros não representam conclusão automática de
uma integração ou aprovação de um modelo.

## Cadastro e uso

Rosto, voz, rosto e voz, personagem e voz licenciada são modos independentes de
cadastro. A autorização/comprovante é separado da amostra. As versões começam
em preparação. A avaliação e a revisão existentes continuam obrigatórias.

Uma aparência e uma voz ativas podem ser escolhidas no pedido para imagem,
carrossel ou vídeo. O servidor confere workspace, versão e consentimento. Em
imagem, o PhotoCraft compõe o retrato existente; a voz é uma referência para
uma futura versão narrada. Isso não é face swap nem clonagem sintetizada.

A exportação de uma imagem com retrato foi exercitada com o motor Rust real,
reabertura do documento e bloqueio de prévia após revogação. A fixture usada é
uma imagem de teste, não prova de qualidade de um modelo de identidade.

## Inferência de voz e avatar

O transporte LongCat 1.5 e os candidatos de voz existem em workers separados.
Os parâmetros STUDIO_LONGCAT_AVATAR_* estão documentados em .env.example. A
flag permanece false até o runner, os pesos e o ambiente serem qualificados.
Configurar endpoint e token não instala um modelo nem qualifica sua saída.

O contrato de avatar V2 admite aparência e narrador independentes. O campo
`consentGrantId` representa a autorização da aparência, ou a da voz quando a
aparência é sintética; se ambos forem personagens/vozes licenciados, pode ser
nulo. As autorizações próprias são resolvidas pelas versões e congeladas em
`executionBinding.cast`. O contrato V1 conserva as regras anteriores.

Uma versão de voz stock só pode ser usada para síntese identificada quando
possui `pronunciationProfile.synthesisBinding` com `provider` e `voiceKey`
correspondentes ao pedido. Esse vínculo pertence à versão revisada, não ao
texto que o cliente fornece. Áudios sintetizados sem versão vinculada não
podem ser apresentados como a voz de um perfil escolhido.

Neste computador, a RTX 2050 tem aproximadamente 4 GB de VRAM. Os manifests
atuais de avatar não admitem este host para os perfis GPU selecionados. O pedido
de vídeo preserva o elenco e informa a pendência da produção generativa.

A clonagem Kokoro + OpenVoice ganhou uma alternativa CPU, com adaptador, fila e
configuração próprios. A execução real com referência sintética e o cancelamento
foram verificados localmente. Isso não qualifica a semelhança com vozes humanas.
O arquivo privado `speech-runtimes.json` pode conter o kind
`kokoro-openvoice-cpu-docker`; configuração e builds não criam aprovações. Veja
`docs/studios/LOCAL_SPEECH_RUNTIMES.md` e o registro de evolução
`openvoice-cpu-project` para o estado e a cobertura dos testes.

O inventário da VPS Oracle de agosto registra uma máquina sem GPU e com menos
de 1 GiB de RAM. Esse registro é histórico; não constitui uma inspeção atual.
O usuário pediu concluir primeiro a configuração do localhost. Não houve
acesso, instalação ou alteração na VPS nesta etapa.

## Validação reproduzível

- TypeScript: npm run lint.
- Build: npm run build.
- Interface: npx playwright test --config playwright.craft.config.ts.
- API: com PYTHONPATH=backend, executar pytest para test_product_evolution.py,
  test_studio_identity_library.py e test_studio_department.py.
- Vínculo de geração: test_avatar_independent_cast.py,
  test_avatar_video_job_boundary.py e test_speech_synthesis_execution.py.
- PhotoCraft real: com PYTHONPATH=backend e o runtime Craft construído,
  python -m pytest backend/tests/native_identity_acceptance.py.

O teste nativo substitui apenas o transporte de fila para execução síncrona;
migração, composição, pixels e exportação são executados no runtime Rust.
Os testes da interface interceptam a API e não qualificam inferência de IA.
