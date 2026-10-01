# Edição contextual: implementação de 8 de setembro de 2026

## Comportamento entregue

O novo fluxo do painel usa `useSemanticCompositions=true`, preservando os contratos V1/V2 antigos. O planejador recebe o schema nativo do Gemini, exemplos parciais versionados e seis famílias registradas: evidência/anotação, comparação, sequência, repetição, foco e continuidade. Esses componentes são convertidos em elementos, keyframes, MotionGraph e manifesto existentes; nenhum código do modelo é executado.

As famílias aceitam identidade nos elementos e parâmetros de duração, eixo, margens, espaçamento, repetição e escala. O runtime compartilhado mede o texto após carregar fontes, mantém um piso de legibilidade de 12 px na apresentação de 300 px e vincula conectores aos centros dos alvos transformados. Overflow continua sendo falha, não aprovação automática. Anotações em regiões específicas e tracking temporal não estão qualificados por conectores de centro.

O modo visual mantém o roteiro para rastreabilidade sem exigir narração ou preservar áudio de origem. A seleção de materiais mantém prioridade de projeto/acervo, ordena candidatos antes da inspeção e conserva a lista durante tentativas. Filmagens são inspecionadas no intervalo solicitado, com até 18 amostras e amostragem adicional em mudanças de cena. A cobertura permanece amostral, sem certificar continuidade por leitura de frames.

O fluxo novo avança em worker. Jobs de inspeção incertos não são reenviados. Depois do animatic, a crítica e os checkpoints precisam estar vinculados ao arquivo; cobertura parcial ou problemas remanescentes impedem o avanço automático. Há até duas correções existentes por etapa. O vídeo final permanece sujeito à revisão humana.

## Interfaces

- `ContextualPlanRequestV2.executionScope` distingue execução visual de audiovisual; padrão audiovisual mantém clientes antigos.
- `EditorialSceneV2.compositions` contém operadores registrados, alvos estáveis, finalidade e resultado esperado. O compilador registra versão e decisões no manifesto.
- `MaterialInspectionRequestV1.sourceStartSeconds` e `maxSamples` vinculam o trecho e a cobertura solicitada; padrões preservam requisições antigas.
- `GET /api/v1/studios/v1/documents/{document_id}/production-runs/{run_id}/evidence` exporta ZIP autenticado com vídeos disponíveis, materiais, frames, plano, grafo/manifesto presentes no plano, histórico e consumo registrado. Checksum divergente bloqueia a exportação. Credenciais e parâmetros de URLs são omitidos.
- `POST .../external-review` registra texto externo com revisão do run e checksum do vídeo. Não altera edição nem aprovação humana.

Nenhuma migração destrutiva é necessária: os campos são aditivos nos contratos/JSON existentes. Reiniciar os workers é necessário para carregar a tarefa de continuação nova. O frontend e backend devem ser publicados juntos para expor o novo opt-in e os endpoints de evidências.

## Validação e limites

Testes de contratos, compilação, seleção após o centésimo candidato, intervalo de inspeção, fila, integridade de exportação, revisão localizada e modo visual. Teste do runtime em Chromium para medição de texto, transformação de grupo, conector e seek reversível. Banco de testes em diretório temporário, isolado do banco local. TypeScript e Ruff verificam a integração estática.

Não houve produção de peça pelo agente, entrega manual de materiais ao res nem chamadas pagas nesta implementação. A qualificação estética, os custos reais de uma nova produção e o comportamento dos provedores ao vivo permanecem pendentes do teste iniciado pelo usuário.

## Teste pelo usuário

1. Iniciar pelo res a peça de distribuição de 15–20 segundos, com montagem mista e avaliação somente visual. O res escolhe as cenas e busca materiais pelos conectores configurados.
2. Se acesso ou material estiver indisponível, registrar a pendência. Não substituir silenciosamente filmagem por gráficos nem contar ausência de credencial como sucesso de aquisição.
3. Avaliar clareza, pertinência, legibilidade e continuidade; exigir ao menos 4/5 em cada dimensão essencial, com evidências de execução das ações.
4. Solicitar revisão localizada mais calma e com menos texto, preservando a conclusão.
5. Repetir com outro tema/identidade; exportar o pacote e encaminhá-lo ao Gemini para análise externa.

Um MP4, um schema válido ou uma crítica favorável do modelo não qualificam edição universal. Os componentes e conectores mantêm limites explícitos; a entrega visual só será aprovada depois da avaliação dos vídeos reais.
