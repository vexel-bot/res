# A voz escolhida narra uma imagem ou um vídeo da marca

Estado: seleção, admissão e montagem nativa implementadas. A qualificação dos modelos reais de síntese/clonagem permanece pendente.

## Experiência nos Studios

No Studio de Vídeos, uma criação com voz selecionada e sem aparência de avatar pode usar uma imagem ou um vídeo da biblioteca. O cliente prepara a narração e pede a primeira montagem. Não é necessário animar uma pessoa para usar sua voz autorizada ou uma voz licenciada.

A interface explica o tratamento dos materiais antes da criação. A montagem tem a duração da fala final: uma imagem permanece em cena; um vídeo usa seu início e, quando for curto, mantém a imagem final até a narração terminar. O áudio original do vídeo não é misturado com a fala escolhida. O arquivo original continua intacto na biblioteca.

Ao mudar a seleção para uma combinação que não aceita imagem, o formulário limpa o material incompatível em vez de manter uma escolha escondida. Projetos de avatar também deixam o vídeo de apoio como opcional; a apresentação pode existir sozinha.

Escolher o formato Imagem continua produzindo uma imagem estática. A voz fica como material do projeto. Para produzir um arquivo com som a partir de uma imagem, o cliente escolhe o formato Vídeo e usa essa imagem como material.

## Ligação à voz e aos materiais

O servidor exige a narração final do próprio projeto, com a versão exata da voz selecionada. Confere origem do job, texto, grant, checksums e arquivos armazenados. Um rascunho posterior ainda não sintetizado não pode substituir silenciosamente o áudio. Cancelamento/revogação e regras de admissão das vozes continuam valendo.

O plano registra o áudio final, o job de narração, a imagem/vídeo original, durações medidas e a decisão de manter a imagem final. As contas de frame usam a taxa real da origem e a sequência de saída de 30 fps. Quando a duração visual de um vídeo não puder ser comprovada, o sistema recusa a montagem e informa a pendência; não usa a duração do áudio original como prova da duração da imagem.

Imagem e narração entram em trilhas separadas no FilmCraft. Ajuste ao quadro, corte e manutenção da imagem final usam os comandos nativos, preservando proporções. Não há renderizador alternativo por FFmpeg. Ele prepara mídia de teste e verifica a exportação; a montagem e a codificação são feitas pelo Craft.

O arquivo original e o projeto nativo permanecem preservados. Uma repetição do pedido recupera a montagem existente. O fluxo de criar outra montagem após uma entrega concluída continua pendente de versionamento próprio.

## Evidência e limites

Os testes HTTP/DB cobrem voz clonada e licenciada sobre imagem e vídeo, preservação das referências, separação de trilhas, repetição de pedidos, texto ainda não sintetizado, revogação e duração visual desconhecida. Os testes de interface cobrem a seleção de material compatível e mensagens de orientação.

O teste explícito com o FilmCraft real usa um tom de 440 Hz como narração e um tom de 880 Hz no vídeo de origem. Ele cobre vídeo curto, vídeo longo e imagens estáticas, com as duas classes de voz. Confere duração integral da narração, ausência do áudio original na montagem, imagem final do vídeo curto, correspondência entre prévia/exportação, referências de voz, checksums e preservação do arquivo original.

Esses sons e imagens são fixtures. Não demonstram naturalidade, sotaque, semelhança vocal, clonagem de uma pessoa, edição generativa de rosto ou qualidade de um avatar. Nenhum modelo, voz real ou cadastro biométrico foi aprovado automaticamente. A qualificação dos modelos e o equipamento necessário continuam pendentes.

Na rodada integrada passaram 46 testes de backend, incluindo as aceitações nativas de narração e avatar; oito testes de interface também passaram. TypeScript, Ruff e build passaram. A interface e uma imagem extraída da exportação foram inspecionadas. A geração real com modelos permanece fora do que esses testes demonstram.

## Evidências

- backend/app/services/studios/project_voiceover.py
- backend/app/routers/studio_department.py
- backend/tests/test_project_voiceover.py
- backend/tests/native_project_voiceover_acceptance.py
- src/studios/department/DepartmentStudio.tsx
- src/studios/department/ProjectNarration.tsx
- tests/team-sync/project-voiceover.spec.ts
