# Pesquisa: como ensinar um agente a editar

Data: 12/11/2026. Projeto-alvo: Clicko/Craft; nenhuma chamada paga, geração ou substituição de renderizador autorizada nesta pesquisa.

## Governança e classificação

Lidos: SKILL de deep-research, config.yaml, README.md, .codex/team.json, definição do coordenador e workflows/wf-deep-research.yaml da raiz original `C:/Users/edugu/.codex/agents/squads/deep-research`. A ordem preservada é Sackett → Booth → Creswell → coleta paralela Cochrane/Higgins → Ioannidis → Kahneman → síntese. Papéis reais delegados pelos native_role do mapa. Escopo: Technical Deep Dive e evidência sobre mecanismos de aprendizagem; nomes de UC divergem entre config e definição do coordenador, portanto o escopo textual prevalece nesta documentação.

## Sackett — pergunta e medidas

P: agentes multimodais que editam anúncios curtos com tipografia, motion e áudio por ferramentas estruturadas Craft/Clicko. I: intervenções separáveis de regras executáveis derivadas de exemplares; demonstrações com estado e chamadas de ferramentas; prática com crítica calibrada; fine-tuning tratado separadamente. C: mesmo modelo, ferramentas, materiais, briefing e orçamento com o fluxo atual de índice e cartões iniciais. O: qualidade editorial cega, defeitos encontrados/corrigidos, sucesso técnico, tempo e custo. A rubrica separa legibilidade, hierarquia, ritmo, continuidade, som e aderência ao briefing.

Pergunta: essas intervenções melhoram tarefas inéditas em relação ao contexto inicial atual? Subpergunta: revisão com cobertura integral e inspeção de eventos críticos detecta mais defeitos anotados que janelas escolhidas pelo próprio agente? O caso ÓRBITA formula hipóteses; não identifica causa com uma execução.

Evidência preferida: experimentos comparativos com tarefas reservadas e avaliadores cegos; na coleta, papers com ablações, benchmarks reproduzíveis, documentação oficial e demonstrações completas. Demos são hipóteses operacionais, sem comprovação de generalização. Quantidade de camadas/chamadas não representa qualidade.

## Booth — método

Revisão de escopo delimitada, com busca documentada e avaliação crítica; não revisão sistemática exaustiva nem meta-análise. SALSA: buscar fontes primárias; avaliar desenho e acesso por tipo de fonte; sintetizar matriz temática; analisar evidência, limite de transferência, adaptação Clicko e teste refutável.

STARLITE: amostragem intencional diversa; 12–18 fontes finais e aproximadamente 3–5 tutoriais em vídeo; papers, benchmarks, documentação e demonstrações do autor; busca temática e encadeamento; 2022–12/11/2026, com fundamentos anteriores explicitados; português/inglês e acesso público sem serviços pagos; incluir edição de timeline/motion/legendas/áudio e aprendizagem genérica com transferência declarada; excluir difusão como evidência direta de edição, republicações sem origem e demos sem conteúdo inspecionável. Fontes: arXiv/anais oficiais, fornecedores oficiais, GitHub dos autores e canais/sites originais.

Consultas de protocolo: `(video editing agent OR motion design agent) AND (demonstration OR trajectory OR evaluation)`; `(agent skills OR context engineering) AND (examples OR retrieval OR evaluation)`; `(motion design OR video editing) AND (breakdown OR workflow OR tutorial)`.

## Creswell — desenho e handoffs

Síntese documental predominantemente qualitativa. Números dos estudos serão descritos com seus comparadores e condições; não se estima eficácia no Clicko. Programa posterior possível: QUAL → quan exploratório sequencial, mecanismos desta coleta orientando experimento futuro em briefs inéditos.

Cochrane recebe papers, benchmarks e documentação oficial: extrair formato dos exemplos/traços, mecanismos, comparadores, ablações, avaliação humana, tarefas reservadas e disponibilidade de código/dados. Higgins recebe criadores/workflows: autoria, procedência, etapas demonstradas e cobertura real de vídeo/transcrição/descrição/imagens/página. Documentação comprova contrato/orientação; demo isolada comprova possibilidade selecionada.

Integração: matriz por mecanismo com fonte/conteúdo acessado, método, limite, adaptação Craft e teste refutável. Não agregar benchmarks incompatíveis. Triangulação, trilha de auditoria e conferência contra PICO; divergências ficam visíveis. Detecção de defeitos, preferência estética e compreensão são resultados distintos. Regras e exemplares podem orientar decisões sem comprovar transferência.

## Gates

- QG-001: escopo pesquisável e factível com fontes públicas; limites de acesso devem ser explícitos.
- QG-002: concluído com PICO, revisão de escopo e desenho documental. Handoffs sequenciais reais concluídos; Cochrane e Higgins iniciados em paralelo.
- QG-003: concluído: Cochrane entregou nove fontes e Higgins seis (15 no total), incluindo três links de tutoriais com cobertura declarada. Dois vídeos encontrados apenas em mirrors foram excluídos. Nenhum tutorial foi reproduzido/escutado nesta coleta. Não há contradição substantiva entre os especialistas: ambos distinguem procedimento documentado de eficácia transferível.
- QG-004 concluído. Ioannidis verificou métricas e limites de transferência no artigo original e nas matrizes. Kahneman auditou a atribuição causal e propôs comparações separadas para ensino e cobertura de revisão. O valor preditivo da intervenção local segue indeterminado. [Ioannidis](ioannidis.md) · [Kahneman](kahneman.md)

## Entregas por agente

| Agente | Entrega verificável |
|---|---|
| Coordenador de pesquisa | Roteou os três diagnósticos, a coleta paralela e a primeira auditoria. Salvou este protocolo e a primeira síntese. Atingiu limite de execução na fase de QA. A raiz assumiu a continuidade, retomou a auditoria e integrou a síntese final. |
| Sackett | Formulou população, intervenções, comparador e indicadores para avaliar transferência. A entrega consta no protocolo. |
| Booth | Delimitou a revisão de escopo, fontes, critérios de inclusão e exclusão e trilha de busca. A entrega consta no protocolo. |
| Creswell | Definiu a síntese documental e como comparar o efeito das intervenções em ensaios separados. A entrega consta no protocolo. |
| Cochrane | Entregou nove fontes primárias, incluindo artigos, documentação e benchmarks. [Matriz](cochrane.md) |
| Higgins | Entregou seis fontes primárias de criadores e workflows, incluindo três links de tutoriais com cobertura textual. [Matriz](higgins.md) |
| Ioannidis | Conferiu números e atribuições e documentou limites da evidência. A primeira execução foi interrompida por limite de uso. A retomada concluiu a entrega. [Auditoria](ioannidis.md) |
| Kahneman | Auditou alternativas, viés e condições para decidir se a intervenção funciona. [Auditoria](kahneman.md) |
| Codex, agente principal | Examinou quadros, projeto e recibos, sondou a fonte e as curvas no motor e mediu o áudio. Consolidou o diagnóstico e as aplicações ao Craft. [Auditoria da ÓRBITA](diagnostico-orbita.md) |

As descrições H2 e H6 entram como exceções de idioma. Foi usada a documentação bilíngue acessível do repositório H2 e o conteúdo indexado em inglês para H6. H4 entrou como fundamento de animação com data editorial sem confirmação. A [síntese final](sintese.md) incorpora essas restrições.
