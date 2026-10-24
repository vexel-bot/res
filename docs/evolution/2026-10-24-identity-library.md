# Biblioteca de rostos, vozes e personagens

## Implementado nesta branch

A rota /library/identities apresenta duas coleções reais da marca: pessoas e personagens; vozes. A área de evolução pode ser acessada pela navegação do sistema e pelos Studios.

O cadastro permite enviar apenas um rosto, apenas uma voz, os dois juntos, um personagem ou uma voz licenciada. A autorização ou comprovante de direitos é um arquivo separado das amostras. O envio cria versões em preparação; não declara que uma voz foi clonada ou um personagem foi animado.

Os perfis, versões, consentimento e recibo do cadastro são salvos em uma única transação. Uma falha não deixa metade de um perfil criada. Repetir o mesmo pedido devolve o recibo existente; alterar seus dados usando a mesma chave gera conflito.

## Escolha em uma criação

O pedido dos Studios aceita uma aparência e uma voz separadamente, em imagens, carrosséis e vídeos. Só versões ativas, pertencentes à marca e com autorização válida são aceitas pelo servidor. O documento guarda a versão exata e o consentimento; uma versão nova não substitui a escolha silenciosamente.

Para imagens e carrosséis, o retrato de referência da versão escolhida é incluído como um asset na composição e encaminhado ao PhotoCraft. Isso é uma composição com o retrato existente, não geração de outra pose ou face swap. A voz pode ficar associada à imagem para uma futura versão narrada; o arquivo de imagem não carrega áudio.

Para vídeo, o pedido preserva o elenco escolhido, mas a produção com personagem animado ou voz sintetizada permanece pendente de motor validado. O sistema informa essa condição e não entrega uma montagem sem aplicar o elenco pedido.

## Autorizações e histórico

Uma autorização pode ser revogada na biblioteca. Os próximos usos são bloqueados. Prévias e exportações Craft verificam novamente as versões e o consentimento; os jobs recebem as referências usadas, permitindo relacionar revogação e execução. A aprovação editorial ou a composição de uma imagem não amplia o escopo da autorização.

As amostras são carregadas por uma rota autenticada somente quando solicitadas. Não são publicadas em URLs abertas pelo catálogo.

## Trabalho ainda em andamento

- Executar e comparar clonagem de voz com amostras autorizadas e avaliação de português brasileiro.
- Qualificar o runner de avatar com imagem, áudio final, sincronismo, qualidade e recursos de GPU.
- Produzir e qualificar personagens próprios com aparência e voz pré-selecionadas. Importar um personagem para avaliação não constitui esse catálogo final.
- Aplicar o personagem ou rosto a novas cenas/imagens com preservação de identidade, além da composição com o retrato existente.
- Encadear síntese de voz, performance do avatar e composição no FilmCraft/EffectCraft sem intervenção técnica do cliente.
- Validar o resultado final em imagem e vídeo no ambiente de execução escolhido.

## Evidências

- backend/app/routers/studio_identity_library.py
- backend/app/services/studios/casting.py
- backend/tests/test_studio_identity_library.py
- src/studios/identity/IdentityLibrary.tsx
- tests/craft/identity-library.spec.ts

A pesquisa de candidatos, suas fontes e limitações está no registro de personagens, rosto e voz de 21/10/2026. Esta entrega da biblioteca não conclui a integração dos modelos generativos.

## Validação local em 24/10/2026

Passaram 56 testes direcionados de backend (incluindo publicação e revogação da voz de um narrador independente), 20 testes de interface, TypeScript, Ruff e build de produção. A aceitação nativa executou migração e exportação reais no PhotoCraft, reabertura do documento e bloqueio de prévia após revogação. O arquivo de teste é um bitmap de cor conhecida; ele não mede fidelidade facial ou qualidade de clonagem.

A interface de evolução e o formulário da biblioteca foram inspecionados no build de produção com API autenticada. O localhost principal foi iniciado pelo script existente, com web na porta 3000, API na 8000, Redis dedicado e worker conectado. Os serviços temporários de QA foram encerrados. A VPS não recebeu alterações.
