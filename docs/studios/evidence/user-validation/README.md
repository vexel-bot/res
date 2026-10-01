# Pacote de validação real CX-0

Este diretório recebe somente dados anonimizados de sessões reais. Não adicionar nomes, e-mails, imagens, voz, documentos, dados de clientes ou gravações brutas ao repositório.

## Superfície de teste

- Figma: [Clicko — Prototype Tests](https://www.figma.com/design/9qNitJb73bJt4nwQ5zlhft/Clicko?node-id=324-2);
- file key: `9qNitJb73bJt4nwQ5zlhft`;
- índice: node `324:2`;
- build: registrar URL local e commit exato no arquivo de resultados.

## Como coletar

1. Duplicar `results.template.json` com um nome que inclua a data do estudo.
2. Criar dez participantes anônimos `P01` a `P10`.
3. Registrar uma execução válida de FC-1 a FC-5 para cada participante; repetir `invalid_run` causado por infraestrutura.
4. Registrar uma rodada integral por teclado e uma com leitor de tela.
5. Vincular cada issue a `screenId`, `actionId` ou `route` sempre que possível.
6. Executar `npm run audit:cx-user-validation -- <arquivo.json>`.

## Interpretação

- `pass`: cada tarefa tem ao menos 8/10 no primeiro clique, não há severidade 3 e as duas rodadas assistivas passam;
- `conditional`: o gate passa, mas uma issue de severidade 2 apareceu para pelo menos três participantes;
- `fail`: uma tarefa ficou abaixo de 80%, houve severidade 3 ou uma rodada assistiva crítica falhou;
- `incomplete`: a amostra ou a evidência obrigatória ainda não está completa.

O relatório do script é cálculo, não evidência primária. Preserve os resultados anonimizados e a decisão assinada por Produto, Design e Engenharia.
