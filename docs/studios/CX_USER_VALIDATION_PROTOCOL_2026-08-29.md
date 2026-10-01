# Protocolo de validação CX — Clicko Studios

## Objetivo e gate

Validar se pessoas novas no produto encontram e concluem os caminhos críticos sem treinamento. O gate CX-0 é objetivo: no mínimo 8 de 10 participantes devem acertar, no primeiro clique, cada um dos destinos `Criar`, `Editar vídeo`, `Editar imagem`, `Revisar` e `Publicar`. A média agregada não pode esconder um destino abaixo de 80%.

## Amostra

- 10 participantes que não tenham participado do design ou da implementação;
- 6 criadores/editores de conteúdo, 2 revisores/gestores de marca e 2 operadores de publicação;
- pelo menos 3 pessoas que trabalhem principalmente em tela de até 390 px;
- registrar familiaridade com Canva, CapCut, editores NLE e ferramentas de avatar, sem usar isso como filtro de resultado;
- não coletar rosto, voz, documento ou biometria real neste estudo.

## Condições

- protótipo canônico: [Clicko — página 10, Prototype Tests](https://www.figma.com/design/9qNitJb73bJt4nwQ5zlhft/Clicko?node-id=324-2), sincronizado exclusivamente via MCP;
- iniciar cada jornada pelo cartão correspondente no índice `324:2`; não usar frames `LEGACY` ou a página `99 — Archive`;
- contas e workspaces de teste novos, com dados sintéticos claramente rotulados;
- metade inicia no desktop 1440×900; metade no mobile 390×844;
- ordem das tarefas alternada entre participantes para reduzir efeito de aprendizagem;
- moderador lê o enunciado literalmente, não aponta navegação e não explica nomes do produto;
- gravar somente tela, cliques e áudio da entrevista mediante consentimento específico;
- qualquer falha de infraestrutura é marcada `invalid_run` e repetida, nunca convertida em falha de UX.

## Parte A — tree test

Apresentar somente a hierarquia textual dos cinco destinos globais e seus filhos. Para cada tarefa, pedir onde a pessoa começaria:

1. criar um anúncio novo a partir de uma oferta;
2. reutilizar um arquivo aprovado da marca;
3. continuar uma campanha em andamento;
4. revisar uma peça enviada por outra pessoa;
5. agendar uma peça já aprovada;
6. editar um vídeo existente;
7. editar uma imagem sem alterar o original;
8. verificar a origem e os direitos de um asset.

Registrar primeiro destino, caminho completo, tempo e confiança de 1 a 5. Não revelar a resposta correta até concluir todas as tarefas.

## Parte B — first-click

Usar o build canônico atual ou o protótipo Figma sincronizado via MCP. Registrar qual superfície foi usada e reiniciar no ponto inicial antes de cada tarefa.

| ID | Enunciado | Primeiro clique esperado | Sucesso final esperado |
| --- | --- | --- | --- |
| FC-1 | “Crie um conteúdo novo para esta campanha.” | `Criar` | Create Hub/Direção |
| FC-2 | “Você recebeu um MP4 e precisa cortar e legendar.” | `Editar vídeo`/Vídeo | Video Studio |
| FC-3 | “Ajuste esta foto sem perder o arquivo original.” | `Biblioteca` ou `Editar imagem` contextual | Image Lab com source preservado |
| FC-4 | “Decida sobre a versão que chegou para aprovação.” | `Revisar`/pendência de revisão | Review Room com versão fixada |
| FC-5 | “Agende esta peça que já foi aprovada.” | `Publicar` | Preflight/Calendário |

Um clique conta como correto somente quando abre o destino esperado ou um passo intermediário previsto no grafo canônico. Busca global, voltar e tentativa subsequente não corrigem o first-click, embora possam concluir a tarefa.

## Parte C — seis jornadas-mãe

Executar duas jornadas por participante, distribuídas de forma balanceada:

1. oportunidade → direção → peça → revisão → publicação;
2. post → Visual/Carrossel → revisão;
3. asset → Image Lab/Video Studio → derivação → retorno;
4. mídia real → ingestão → cortes/captions → render/QC → review;
5. identidade stock ou demonstração sintética → Presenter → Video Studio;
6. conteúdo vencedor → Reuse → Factory → review.

Não usar identidade humana real. No Presenter, o resultado esperado sem provider/direitos é compreender o bloqueio e a próxima ação — nunca contornar o gate.

## Métricas

- `first_click_success`: booleano por tarefa;
- `task_success`: `success`, `assisted`, `failed` ou `invalid_run`;
- tempo até primeiro clique e tempo total;
- número de retornos, cliques mortos e desvios de rota;
- SEQ de 1 a 7 após cada jornada;
- entendimento do estado: `demo`, `privado`, `em revisão` ou `publicável`;
- entendimento de preservação: original, derivação, versão e lineage;
- problemas observados classificados por severidade 0–3 e vinculados a route/action/screen ID.

## Acessibilidade manual

Nas cinco tarefas de first-click, executar ao menos uma rodada integral somente por teclado e uma com leitor de tela. Verificar:

- ordem e visibilidade do foco;
- skip link, landmarks, heading hierarchy e nomes acessíveis;
- anúncio de loading, sucesso, erro recuperável, conflito e bloqueio;
- dialogs com foco contido e devolvido ao gatilho;
- zoom de 200% sem perda da tarefa;
- contraste WCAG 2.2 AA em texto, foco e estados, sem depender apenas de cor;
- `prefers-reduced-motion` sem perda de informação ou controle.

## Roteiro de entrevista final

1. “O que este produto parece produzir?”
2. “Qual é a diferença entre Biblioteca, Projeto e Studio?”
3. “Onde você esperaria editar foto, vídeo, movimento e voz?”
4. “Em que momento uma saída se torna publicável?”
5. “O que você acredita que aconteceu com o original?”
6. “Qual foi o ponto mais confuso ou arriscado?”

## Registro por participante

```json
{
  "participantId": "P01",
  "segment": "creator",
  "viewport": "desktop",
  "taskId": "FC-3",
  "firstClick": "HOME-OPEN-LIBRARY",
  "firstClickSuccess": true,
  "taskResult": "success",
  "timeToFirstClickMs": 0,
  "taskTimeMs": 0,
  "seq": 0,
  "stateUnderstood": "private",
  "notes": [],
  "issues": []
}
```

Usar IDs anônimos. Notas livres não devem conter nome, e-mail, imagem, voz ou identificadores de clientes.

## Decisão

- `pass`: todas as cinco tarefas FC têm pelo menos 8/10 no primeiro clique, nenhuma falha de severidade 3 e as jornadas críticas são concluídas por teclado;
- `conditional`: gate quantitativo passa, mas existe problema de severidade 2 repetido por três ou mais participantes;
- `fail`: qualquer tarefa FC abaixo de 80%, falha de severidade 3, gate biométrico contornável ou jornada crítica impossível por teclado;
- após correção, repetir apenas tarefas afetadas com cinco novos participantes; não reutilizar participantes treinados para declarar recuperação do first-click.

## Evidências a anexar

- versão/commit do build e URL local de teste;
- file key `9qNitJb73bJt4nwQ5zlhft`, node inicial `324:2` e data da sessão;
- matriz anonimizada por participante e tarefa;
- lista de issues com screen/action/route IDs;
- cálculo do gate por tarefa;
- decisão assinada por Produto, Design e Engenharia.
