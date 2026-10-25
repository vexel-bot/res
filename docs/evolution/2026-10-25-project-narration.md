# Narração ligada à voz escolhida no projeto

Estado: fluxo de software implementado; modelos de voz e avatar ainda dependem de qualificação real.

## Experiência no Studio

Projetos com uma voz escolhida apresentam uma área de narração após a entrada na direção editorial. O cliente pode revisar e salvar o texto, fechar e reabrir o projeto, pedir a geração, acompanhar a fila e cancelar o pedido. O texto pode ser salvo mesmo quando não há um motor de voz disponível, sem criar um job de geração.

Quando a geração é concluída por um provedor admitido, o áudio é carregado pela rota autenticada da marca e pode ser ouvido ou baixado. O texto do último áudio é exibido separadamente do rascunho em edição. Uma falha de rede preserva a identidade do pedido; a consulta de estado recupera um envio aceito sem gerar outro job.

Em imagem e carrossel, a narração é um material do projeto para uma versão narrada; o arquivo de imagem não carrega áudio. Em vídeo, a fala final é uma etapa anterior à animação do personagem e à composição. Esta entrega não demonstra nem conclui essas duas etapas.

## Ligação com a voz

O servidor usa a versão exata selecionada na biblioteca e confere novamente sua autorização. Uma voz clonada produz um job de clonagem com sua amostra autorizada; uma voz licenciada usa o provedor e o timbre registrados na versão revisada. A seleção automática desse fluxo considera somente adaptadores locais presentes e admitidos, sem contratar um serviço remoto como alternativa.

A narração editorial por trechos também respeita a voz do documento. Ela não a substitui pelos antigos parâmetros de voz padrão. Ao retomar um job ou usar um áudio já produzido, o código confere voz, texto, consentimento, checksum e origem do asset. A duração do áudio é medida antes da composição. Uma produção que exige áudio não pode ignorar a voz escolhida ao mudar para uma avaliação somente visual.

O job e sua ligação ao projeto são gravados na mesma transação, com controle de revisão. Repetições do mesmo pedido não duplicam o job; um pedido antigo não substitui silenciosamente uma narração posterior. A revogação impede novos usos, mas não impede o responsável de cancelar o trabalho pendente.

## Validação e limites

Os testes de backend cobrem clonagem e voz licenciada nos formatos imagem e vídeo, salvamento e reabertura, idempotência, conflitos, isolamento entre marcas, revogação, cancelamento e origem do áudio. Testes específicos da rotina editorial usam a voz escolhida apesar de parâmetros padrão diferentes e medem os WAVs de fixture com FFprobe.

Os testes de interface cobrem salvar texto com geração indisponível, recuperar uma resposta perdida sem reenviar a geração, cancelar e obter o arquivo pela rota privada. Os testes usam vozes, modelos e áudios de fixture, incluindo WAVs silenciosos. Eles não medem semelhança vocal, naturalidade, pronúncia em português ou sincronismo de avatar.

Nesta etapa passaram 11 testes de narração do projeto, seis testes de execução de síntese, três de interface e dois de evolução. TypeScript, Ruff e build passaram. O painel foi inspecionado a partir da captura do teste no aplicativo local reiniciado.

Nenhum cadastro real foi aprovado automaticamente e nenhum provedor foi promovido por esta implementação. Continuam pendentes a instalação/configuração dos runtimes admitidos, a validação real dos modelos e o encadeamento da fala final com LongCat e a montagem Craft. A geração com elenco no botão principal de produção continua protegida enquanto esse caminho não estiver concluído.

## Evidências

- backend/app/routers/studio_project_narration.py
- backend/app/services/studios/cast_speech.py
- backend/app/services/studios/production_narration.py
- backend/tests/test_project_narration.py
- src/studios/department/ProjectNarration.tsx
- tests/team-sync/project-narration.spec.ts
