# Rostos, vozes, personagens e evolução no localhost

## Iniciar o produto

No checkout do Clicko, execute npm run build e depois scripts/craft/start_local.ps1.
O script reutiliza o broker Redis dedicado, inicia o worker local, a API em
127.0.0.1:8000 e a aplicação em http://127.0.0.1:3000. Ele preserva serviços já
existentes e recusa reiniciar sobre portas ocupadas ou processos parciais.

Use scripts/craft/start_local.ps1 -StatusOnly para consultar os processos.
Os logs locais ficam em .codex-runtime/craft/local. O arquivo .env e as chaves
permanecem locais; não devem ser incluídos no Git.

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

Neste computador, a RTX 2050 tem aproximadamente 4 GB de VRAM. Os manifests
atuais não admitem este host para os perfis generativos selecionados. O pedido
de vídeo preserva o elenco e informa que a produção generativa está pendente,
em vez de entregar um vídeo sem a aparência ou voz escolhida.

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
- PhotoCraft real: com PYTHONPATH=backend e o runtime Craft construído,
  python -m pytest backend/tests/native_identity_acceptance.py.

O teste nativo substitui apenas o transporte de fila para execução síncrona;
migração, composição, pixels e exportação são executados no runtime Rust.
Os testes da interface interceptam a API e não qualificam inferência de IA.
