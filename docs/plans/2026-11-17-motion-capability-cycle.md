# Qualificação local de motion

Este ciclo usa somente CPU, arquivos existentes, sinais sintéticos e o motor nativo em contêiner sem rede. Não submete solicitações a modelos, avaliadores pagos ou provedores de materiais; não produz um anúncio.

## Reprodução

- `scripts/validation/clicko-motion-native-proof.py --source PROJECT.ecproj --output NEW_DIRECTORY --all-frames`: verifica os 30 quadros da prova de um segundo. A medida da trajetória não mede FPS da interface nem aprova acabamento.
- `scripts/validation/clicko-motion-capability-suite.py --source PROJECT.ecproj --output NEW_DIRECTORY`: executa provas independentes de máscaras, opacidade, mistura, texto, gradiente, sombra, câmera, luz e perspectiva. Salva scripts, inspeções, hashes e quadros. `--cases` seleciona operações. Diferença de pixels não constitui aprovação estética.
- `scripts/validation/clicko-motion-audio-proof.py --source PROJECT.ecproj --output NEW_DIRECTORY --envelope`: verifica deslocamento temporal e dois ganhos diferentes no WAV exportado. Falha retorna código diferente de zero. Sem escuta.
- `scripts/validation/clicko-motion-compaction-replay.py --evidence JOB.json --output REPORT.json`: reproduz duas compactações dos dados salvos, compara campos presentes e preserva a origem. Não testa o raciocínio do modelo.

Sempre usar diretórios novos para provas nativas. Não sobrescrever projetos de produção. Os exemplos expostos ao diretor são vinculados à versão do motor e não liberam alegações de qualidade profissional.

## Defeito de áudio reproduzido

Na build 1.0.5 o mixador lê o ganho apenas no início do bloco. O exportador WAV fornece blocos de um segundo: dois sons que deveriam estar a -6 e -12 dB saem com o mesmo ganho. A correção avalia níveis animados/expressões no tempo de cada amostra, conserva a via rápida de níveis estáticos e evita descartar um bloco inteiro que começa silencioso mas cresce depois.

A correção é uma sobreposição de compilação com hash exato em `workers/craft/patches/effect-audio-levels.json`. A árvore importada é restaurada byte a byte após compilar, inclusive em falha. Fontes inesperadas recusam a aplicação; alterações concorrentes não são revertidas. A build do adaptador muda para 1.0.6. A imagem anterior é conservada para comparação. Não há edição ou reexportação dos filmes históricos.

## Briefing preparado, não executado

Claude permanece diretor. Objetivo da futura prova: demonstrar uma transformação visual compreensível com acabamento temporal consistente, usando referências externas escolhidas pelo diretor. Ele decide conceito, duração, materiais, cenas, movimento e linguagem sonora. Deve escolher a maior incerteza criativa, associar operações verificáveis e examinar todos os acontecimentos essenciais. Não há receita de montagem nem obrigação de usar todos os efeitos demonstrados.

Critérios de comparação: legibilidade e hierarquia; continuidade e trajetória; integração entre elementos; transições; profundidade e coerência de luz/sombra quando pertinentes; sincronismo técnico. Observar detalhes e movimento, registrar perdas e incertezas. Escuta continua pendente; planos espaciais não provam CGI volumétrico.

Uma prova criativa paga e um anúncio completo continuam suspensos por instrução do usuário. A próxima etapa local deve aprofundar acabamento nas capacidades exigidas por referências concretas, sem reativar provedores.
