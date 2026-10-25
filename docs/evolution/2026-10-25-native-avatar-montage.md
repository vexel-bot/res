# Apresentação e material da marca em uma montagem nativa

Estado: sequência e verificação de mídia implementadas. Os modelos de rosto e voz continuam pendentes de qualificação real.

## Problema encontrado no teste real

O primeiro teste com FilmCraft identificou que os dois vídeos eram inseridos na posição inicial da timeline. O material da marca podia encobrir a apresentação, e a exportação terminava com aproximadamente 2,8 segundos, embora os materiais somassem quatro segundos. O retorno da exportação também deixava a duração vazia.

A checagem anterior, que substituía o adaptador por uma fixture, provava o envio dos dois IDs e não sua colocação temporal ou o conteúdo exportado. Ela foi complementada por um teste com o motor Rust, os arquivos nativos e a mídia decodificada.

## Comportamento implementado

Antes da montagem, o servidor confere marca, estado, checksum e arquivos armazenados; mede a duração dos materiais com FFprobe e verifica a presença do áudio na apresentação. O plano registra cada clipe, seu checksum, posição e duração. As posições seguintes começam em limites de frame de uma sequência de 30 fps, sem colocar outro vídeo ou áudio sobre a fala selecionada.

O FilmCraft importa cada clipe na posição explícita e executa seu próprio comando de ajuste ao quadro. A imagem mantém a proporção e suas bordas; diferenças de formato podem deixar barras no quadro. A escala, a composição e a codificação continuam nos motores Craft. FFmpeg/FFprobe são usados para preparar fixtures e verificar a mídia, sem substituir o renderizador.

O documento preserva a duração do conjunto e o plano da montagem. Uma tentativa de trocar os materiais de uma montagem já criada é recusada; a versão anterior permanece preservada. O fluxo de novas versões de uma entrega existente continua sendo uma etapa posterior.

Exportações de vídeo passam por inspeção do contêiner e dos streams. A resposta informa largura, altura, fps, duração medida e presença de áudio. A reutilização de uma exportação confere o checksum e mede novamente o arquivo, inclusive com o motor offline. A autorização do elenco continua sendo verificada antes de reutilizar a saída.

## Aceitação audiovisual

O teste explícito usa um cartão de cor com bordas de enquadramento e um tom de 440 Hz como apresentação de 2,8 segundos. O material original da marca é outro cartão, com um tom de 880 Hz e duração de 1,2 segundo. Somente o adaptador de avatar e a síntese são fixtures: criação do documento, migração, comandos, arquivos `.fcproj`, reabertura, prévia, exportação, armazenamento e download são reais.

As verificações incluem:

- Quatro segundos de vídeo; no resultado local, o contêiner mede 4,010 segundos por causa da duração codificada do áudio.
- Saída de 1080 × 1350, com a primeira imagem seguida do material da marca e sem corte das bordas do enquadramento.
- Tom de 440 Hz no começo e no fim da apresentação, seguido pelo tom de 880 Hz no material original, sem sobreposição entre os dois.
- Correspondência entre os frames da prévia nativa e da exportação, com tolerância para a codificação com perdas.
- Download com checksum correspondente, referências de aparência e voz preservadas e assets presentes no manifesto nativo.
- Reutilização da exportação com o motor offline e bloqueio de nova prévia após a revogação da autorização.
- Rejeição de mídia alterada, apresentação sem áudio, duração incompatível e arquivo com apenas um cabeçalho de MP4 falso.

Essas verificações demonstram o funcionamento da montagem com mídia de teste. Não demonstram clonagem de rosto ou voz, naturalidade, semelhança de uma pessoa ou sincronismo labial de um modelo. Os runtimes e pesos reais continuam sujeitos às suas admissões e à validação em equipamento compatível.

A rodada de aceitação e regressão passou com 40 testes, incluindo o cenário com o motor nativo e os testes de projetos, ciclo de vida e armazenamento dos Crafts. Uma checagem final também passou para os casos de erro de leitura e o catálogo de Evolução. O teste nativo foi acrescentado à CI em uma etapa própria, com arquivos de evidência; isso não declara aprovação da execução completa da CI no GitHub.

## Evidências

- backend/app/services/studios/project_montage.py
- backend/app/routers/studio_department.py
- backend/app/services/studios/craft.py
- backend/tests/native_project_avatar_acceptance.py
- backend/tests/test_project_montage.py
- .github/workflows/studios-craft.yml
