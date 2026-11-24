# Direção audiovisual autônoma v2

Implementação local de 15/11/2026. Não houve chamada paga, geração de vídeo ou alteração dos projetos de produção nesta etapa.

## Ativação e compatibilidade

O pedido nativo aceita `directionContract: "v2"`. Ausência do campo continua significando v1 e mantém o hash dos pedidos históricos. Na interface, a opção **Direção com comparação de versões** ativa v2 em novos pedidos. Ela começa desmarcada. O pedido de recuperação conserva a escolha original. Não há migração silenciosa de sessões em andamento.

O roteiro `clicko-autonomous-cinematic-review.py` aceita `--direction-contract v2` para novos pedidos. Uma retomada usa o contrato salvo no pedido original, independentemente dessa opção.

O modo sem teto continua sem teto financeiro, prazo total ou número máximo de iterações. Operações adicionais com cobrança exigem a sessão explicitamente sem teto; em sessões limitadas não são habilitadas até haver integração de reserva financeira. O diretor pode sempre consultar disponibilidade e usar operações gratuitas qualificadas.

## Comportamentos entregues

- **A — Histórico:** `sourceDocumentId`, `sourceRevision` e `branchReason` vinculam cópias novas à família comprovada. Guias aprovados e feedback dos ancestrais são recuperados com escopo; hipóteses continuam separadas. O script de revisão autônoma transmite esse vínculo. Não se infere parentesco por título ou semelhança.
- **B — Descoberta:** consultas por intenção em português/inglês classificam resultados por relevância. Nenhum resultado não significa operação inexistente. Manifesto separa disponibilidade, qualificação e registros de execução.
- **C — Observação:** revisão admite `sampling: "detail"`, `maximumSide` e recorte normalizado `[x,y,width,height]`. Detalhes estáticos não viram cobertura temporal. Referências podem registrar um arquivo temporal com hash; as referências atualmente só disponíveis em pranchas continuam declaradas como tal. Avaliações ficam vinculadas ao arquivo, ao plano e à revisão observados.
- **D — Direção:** plano estruturado e versionado, sem quantidade fixa de cenas ou efeitos, com intenções, alternativas, experimento e ações essenciais. O resumo sobrevive à compactação; o plano completo é consultável por ID.
- **E — Produção:** interface de provedores qualificados, submissão/poll com registro anterior à chamada e sem reenvio automático de resultado incerto. Materiais verificados podem ser preparados no projeto e inspecionados antes de importação. O registro conserva procedência e custo.
- **F — Comparação:** candidatos imutáveis, problemas persistentes, evidência das duas versões, comparação sonora original/equivalente quando comprovada, candidato preferido separado da aprovação humana. Promoção verifica revisão atual, cobertura e evidências. A conclusão revisada exige seleção comparativa do candidato atual.
- **G — Raciocínio:** v2 solicita esforço alto em todas as chamadas do diretor. São registrados parâmetros solicitados e efetivamente enviados pelo adaptador, modelo, etapa e consumo. Isso não demonstra por si só melhoria de raciocínio ou estética.

## Interfaces

Contratos: `craft.context.v2`, `craft.direction.v2`, `craft.capabilities.v2`, `craft.evidence.v2`, `craft.comparison.v2` e `craft.delivery.v2`.

Ferramentas: `inspect_direction`, `record_direction_plan`, `manage_direction_issue`, `record_revision_hypothesis`, `inspect_production_capabilities`, `request_direction_evaluation`, `request_direction_material`, `stage_direction_material`, `save_direction_candidate`, `compare_direction_candidates`, `review_reference`. Escritas usam `expectedVersion` e `payload`. `inspect_direction` oferece versão corrente e esquema completo do plano.

HTTP: `GET /studios/v1/documents/{id}/craft/director-context`; `POST .../craft/director-approval` requer usuário autenticado, revisão do documento, versão do estado, candidato, decisão e comentário. Claude não recebe ferramenta de aprovação humana.

Persistência usa o armazenamento de conhecimento existente com tipos `craft_lineage` e `craft_direction_v2`, segregados por workspace. Atualizações são comparadas pela versão e histórico é preservado. Não há alteração de schema SQL. Documentos antigos permanecem independentes até existir relação comprovada explicitamente registrada; nenhum dado vivo foi migrado.

`scripts/validation/clicko-director-link-lineage.py` valida recibos de cópias existentes contra workspace, revisão e hash da origem preservada. Por padrão apenas verifica; `--apply` é necessário para registrar os vínculos. A ferramenta rejeita famílias já divergentes ou estados v2 que precisariam de reconciliação e não altera composições.

## Qualificação de provedores e limites presentes

`DirectorProvider` é um adaptador de servidor com ID, versão, modalidade, recibo de qualificação, disponibilidade, execução, consulta de estado e declaração de cobrança. Seu registro não é uma ferramenta do Claude. O adaptador é responsável por credenciais, execução autorizada, reconciliação e cadastro dos ativos. `poll` não deve reenviar uma operação.

O registro vem vazio: **não foi inventado um avaliador que escuta nem ativado um gerador não qualificado**. Os serviços legados de geração contextual e detecção acústica não são automaticamente compatíveis com a sessão nativa. Sua ligação e qualificação operacional continuam necessárias antes de uso real. Sem avaliador audiovisual qualificado, a entrega permanece rascunho nas dimensões não observadas.

Avaliação aceita somente resultado de adaptador qualificado com hash consumido, intervalo, modalidade e achados. Comparação em volume equivalente exige ambos os hashes consumidos, método, ganhos aplicados e confirmação das duas audições. Os nomes das versões, custos e justificativas do autor são omitidos do pedido de avaliação. Critérios observáveis são fornecidos sem a defesa do autor.

Não há promessa de qualidade das referências, aprovação estética, vantagem de modelo mais potente ou qualificação do motor 3D. Essas conclusões dependem de avaliações reais posteriores. A infraestrutura fornece os contratos para esse trabalho e mantém lacunas explícitas.

## Verificação e ativação progressiva

Testes isolados usam banco temporário, adaptadores simulados e arquivos de fixture. Cobrem ancestralidade, isolamento, problemas omitidos, revisão parcial/desatualizada, hipótese persistida, falta de escuta, chamadas incertas, promoção, aprovação humana separada, contratos antigos e passagem por uma sessão nativa simulada. Não se apresentam esses testes como prova de qualidade visual.

O script `scripts/validation/clicko-director-evidence-audit.py` lê logs existentes, sem modelo ou renderizador, e relata cobertura, referências, buscas vazias e erros. Serve de base para comparação de processo, sem nota estética.

Próxima ativação operacional: qualificar adaptadores sobre evidências existentes, registrar materiais temporais verificáveis e calibrar achados com casos positivos e negativos. Somente depois avaliar a produção audiovisual completa em nova etapa autorizada. O retorno a v1 é feito em novos pedidos, sem alterar pedidos v2 já iniciados.


## Integração com Claude Opus 5.5 — 15/11/2026

A modalidade nativa oferece o avaliador `claude.opus55.visual` usando a conexão Anthropic da própria sessão. O contrato verifica workspace, modelo, revisão da conexão e recibo de qualificação antes da chamada. O servidor configura `STUDIO_CRAFT_CLAUDE_QUALIFICATION_FILE`. O recibo contém a identidade da conexão e evidência da execução. A troca de conexão ou revisão exige uma qualificação correspondente.

Claude escolhe intervalo, frequência e resolução por `request_direction_evaluation` com modalidade `visual` e `parameters.fps/maximumSide`. O adaptador envia imagens individuais com horários e conserva hashes dos quadros, consumo, identificador da chamada e parâmetros de raciocínio. São permitidos até 48 quadros por vídeo por chamada para respeitar o transporte. Claude pode dividir a observação em quantas chamadas forem necessárias. A comparação A/B omite custo, ordem de produção e justificativa do autor.

A API de Opus 5.5 recebe imagens e texto. Áudio e integração audiovisual permanecem inconclusivos. Os quadros amostrados também deixam acontecimentos entre as amostras desconhecidos. Este adaptador mantém essas limitações nos registros e recusa pedidos de modalidade sonora.

A criação de cenas, composição, animação e efeitos usa a rota `native_scene_generation` do EffectCraft, com `run_motion_script` e `edit_project` sob direção do Claude. A descoberta informa essa rota independentemente de síntese de materiais por modelos externos. O registro de operações concluídas e o build do motor delimitam a evidência técnica. Cada resultado ainda precisa de inspeção.

O comando `scripts/validation/clicko-claude-provider-qualification.py` realiza um teste visual controlado e uma observação de vídeo existente. Usa o banco da aplicação apenas para ler a conexão. O recibo e os resultados ficam fora dos projetos. Valores de consumo monetário deste adaptador são estimativas pela tarifa pública padrão de US$ 4/20 por milhão de tokens de entrada/saída, acompanhadas do uso devolvido pelo provedor.

## Continuidade e observação — 16/11/2026

O ciclo real autorizado de `Depois da última chuva` continua na mesma chave de execução, após recuperação de armazenamento. Projetos anteriores, candidatos preservados e exposição financeira incerta permanecem registrados. Esta execução posterior inclui chamadas pagas; a declaração de ausência de chamadas na abertura deste documento se refere apenas à implementação inicial de 15/11.

Nos ciclos com `compactEvidence`, a compactação conserva os dois últimos pares completos de chamadas/resultados públicos. Blocos assinados de raciocínio não são reinseridos após reescrever o prefixo. Pares incompletos são descartados; a mensagem original não é alterada. Prévia já presente nesses pares não é duplicada no checkpoint. A modalidade antiga conserva seu comportamento.

`inspect_direction` oferece `payload.kind=plan_schema` para obter o contrato completo e `payload.kind=observations` com paginação para recuperar identificadores antigos. A resposta compacta traz os últimos 24 registros e o total, sem impor limite ao histórico persistido. Consultas por ID continuam disponíveis.

Pedidos de avaliação aceitam `parameters` e o alias `sampling`, rejeitam conflito e campos desconhecidos e encaminham `questions`. A execução real confirmou 44 quadros a 10 fps/720 px na revisão do batch 12. Os recibos antigos mantêm sua densidade efetiva original. Justificativa do autor e custo continuam fora do avaliador independente.

Verificação: análise estática, seis suítes do backend (memória, finanças, direção v2, contexto do ciclo, avaliação Claude e cache), protocolo de pares compactados pela contagem de tokens da conexão real e respostas Messages posteriores válidas. A qualificação de protocolo não solicitou geração Messages. O build nativo permaneceu `clicko-effectcraft-1.0.5+67434e90`.

Esses resultados demonstram execução e continuidade. A qualidade das referências ainda não foi demonstrada; a prova continua sendo revisada pelo Claude. O relatório intermediário, os recibos e as cópias inalteradas dos experimentos estão em `C:\Users\edugu\OneDrive\Documentos\res\output\clicko-after-rain-2026-11-15`.

`record_revision_hypothesis` agora distingue explicitamente a proposta do plano vigente: retorna `planImpact.planChanged=false`, o ID do plano e a orientação de versioná-lo quando a intenção essencial mudar. Não altera cenas, não apaga evidência anterior nem muda a seleção. O teste de regressão demonstra que o plano fica idêntico e não surge aprovação humana. A sessão já em execução recebeu o mesmo esclarecimento por diagnóstico persistente, sem reiniciá-la ou escolher sua direção.

A comparação A/B usa o início e a duração do trecho da versão de comparação. Recibos de renderização que incluem também `endSeconds` continuam válidos. A conversão foi coberta pela validação real do adaptador em teste local. É possível registrar uma comparação entre candidatos preservados antes de existir um preferido formal. A promoção continua sujeita à revisão atual, às evidências exigidas e à comparação com o preferido vigente.
