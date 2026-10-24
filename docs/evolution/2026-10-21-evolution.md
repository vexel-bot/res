# Evolução do sistema

## Pedido e prioridade

A primeira entrega desta etapa é tornar a evolução visível na aplicação. Os recortes enviados pelo usuário solicitam documentos .md e registro de novas funcionalidades, atualizações, correções, exclusões, análises e pendências.

## Como consultar

- Acesse Evolução na navegação principal ou pelo rodapé dos Studios.
- Pesquise por assunto e filtre por tipo ou situação.
- Abra um registro para ler seu documento completo, impacto, requisitos e referências.
- Baixe o .md para manter uma cópia do registro.

## Fonte dos registros

O catálogo em docs/evolution/catalog.json referencia arquivos .md desta mesma pasta. A API autenticada consulta apenas esse catálogo; não recebe caminhos de arquivos do navegador. Documentos técnicos citados são referências de evidência e não expõem arquivos arbitrários do servidor.

## Situações

- Integrado: consta na main com referência registrada. Isso não declara aprovação automática de todas as funções em produção.
- Implementado nesta branch: código disponível nesta entrega, ainda sem afirmar publicação na main.
- Em andamento: pesquisa ou implementação incompleta.
- Planejado: requisito registrado, ainda sem entrega operacional.

## Atualização do histórico

Cada mudança recebe um registro com data, tipo, situação, impacto e evidências. Correções e exclusões podem ser registradas como novos fatos, preservando o histórico. A validação do catálogo verifica IDs, caminhos, documentos e referências locais.

## Limites

Não há percentual artificial de conclusão, números de uso ou status inferidos apenas por um teste verde. As demandas de rosto, voz, personagens e pesquisa de materiais continuam abertas até serem demonstradas nos fluxos reais.
