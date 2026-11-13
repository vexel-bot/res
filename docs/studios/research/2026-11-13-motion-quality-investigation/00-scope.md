# Escopo da investigação

Data de referência do cliente: 13/11/2026. Pedido: investigar se direção pelo Opus com execução híbrida Craft/Canvas pode alcançar o acabamento pretendido e entregar um plano de melhorias. Esta rodada produz pesquisa e planejamento; não implementa a arquitetura nem autoriza inferência ou geração paga.

## Objetivo e contexto preservados

- Produto Clicko: receber materiais do produto/serviço e do apresentador, desenvolver anúncio e exportar. Qualidade de anúncio é o foco atual; piloto não é a prioridade desta rodada.
- Três referências aceitas: @paulo.ia, Olise/bola dourada (`Dd5Md7NMj7P`); @creators, crédito @martsromero, matcha (`DdW0UoSxXsX`); @moonsol.design, colagem (`Dcys2J3MfYK`). São exemplares de dimensões diferentes, com análise visual amostrada e som ainda não auditado no registro.
- A ÓRBITA independente de 16 s foi considerada primeiro resultado positivo pelo usuário, ainda com trabalho a fazer. Hash do MP4 `040484f64c32e9d7d47aff43b5d1fe69626382dfc598ae0b217296ec7f490391`; falta áudio e a exportação foi recuperada por Codex após a sessão do Opus encerrar por orçamento.
- A direção conserva liberdade de duração, cenas, camadas e efeitos. Critérios de avaliação não definem uma cadência fixa ou uma estética universal.
- Não reintroduzir HyperFrames ou MCP como condição para a solução. Examinar o que já existe e alternativas concretas; novas ferramentas dependem de necessidade comprovada, condições de uso e validação.

## Fontes internas de partida

- `docs/studios/knowledge/orbita-quality-baseline.v1.json`.
- `docs/studios/knowledge/playbooks/tres-referencias-storyboards-2026-11-12.md`.
- `docs/plans/2026-11-12-clicko-gargalos-e-orbita-independente.md`.
- `docs/plans/2026-11-12-clicko-orbita-effectcraft-mcp.md`.
- `backend/app/services/studios/craft_agent.py`, `craft_direction.py`, `craft_review.py`, `craft_learning.py`, `craft_material_search.py`, `craft_swarm.py`, `ad_copy_workflow.py`, `ad_materials.py` e seus testes.
- `third_party/craft/effectcraft/docs/` e `workers/craft/sources.lock.json` delimitam o build integrado; documentação do upstream atual não deve ser confundida com ele.
- Fontes do resultado independente em `C:/Users/edugu/Downloads/clicko-orbita-independent-20261112/src`; render e recibos em `C:/Users/edugu/OneDrive/Documentos/res/output/clicko-orbita-independente-2026-11-12`.
- Capturas de referência em `.codex-runtime/clicko-dev/orbita-target-reference`; a folha `paulo-contact.jpg` foi invalidada anteriormente por seek pausado com pixels desatualizados. Usar `paulo-contact-play.jpg` e as capturas `paulo-play-*`.

## Método e passagens de trabalho

Classificação: avaliação técnica (UC-001) e decisão de arquitetura/investimento (UC-002). O diagnóstico segue pergunta → método → desenho; a execução separa código/desempenho, fontes de pesquisa, procedência das referências e alternativas. A revisão de confiabilidade antecede a revisão dos vieses de decisão. As atribuições e os pareceres ficam identificados por arquivo; não se presume consenso.

Nenhuma hipótese de qualidade recebe probabilidade de sucesso ou PPV numérico sem base. Uma limitação documentada não é automaticamente a causa de um defeito visto. Uma simulação de resposta valida a integração, não o julgamento criativo do Opus.

## Contexto financeiro anterior

A auditoria financeira anterior permanece no relatório local privado `output/auditoria-saldo-2026-11-13`. O saldo exato da Anthropic está pendente de conferência pelo usuário; estimativa local, reservas e gasto verificável não são a mesma coisa. Esta investigação não reconsulta saldo nem consome esses créditos. Um orçamento de experimentos apresentado no plano será proposta futura, não autorização automática. Não publicar os recibos privados de conta com o dossiê técnico.
