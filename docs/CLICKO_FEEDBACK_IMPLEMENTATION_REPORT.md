# Clicko — implementação do feedback

Status: concluído em 18 de agosto de 2026.

## Resultado por ponto de feedback

| Feedback | Implementação |
| --- | --- |
| Fábrica parecia um Kanban | Reconstruída como sistema de produção inteligente: entradas, receita estratégica, motor Clicko, formatos, gates humanos, decisões, variações, capacidade e destinos. |
| Projetos parecia uma tabela administrativa | Substituída por universos criativos visuais com peças, progresso, sinais, decisões, versões e próximos passos. |
| Rolagem horizontal e painéis cortados | Layouts de Conteúdo, Biblioteca, Calendário, Editorial, Visual, Projetos e Fábrica receberam contenção e breakpoints específicos. |
| Tipografia pequena e baixo contraste | Tipografia unificada nos tokens Clicko, mínimo de 12 px nas camadas finais e contraste secundário elevado. |
| Editores mal resolvidos | Visual recebeu marca/retorno, headline contida e faixa de slides recolhível; Editorial passou a usar uma hierarquia mais simples e um único fluxo de rolagem. |
| Logos genéricos | Integrações usam SVGs oficiais ou marcas reconhecíveis para Meta, Instagram, Google Drive, Dropbox, Canva e demais canais. |
| Presenter em “EXPLORATION” | Renomeado para “PRODUÇÃO APROVADA” e reorganizado em sistema, decisão humana e resultado. |
| Home dependente do prompt | Adicionadas prioridades proativas: oportunidades, decisões pendentes, saúde de campanha e reaproveitamento de vencedores. |
| Produto só demonstrado com Café Aurora | Adicionado workspace completo da Clínica Horizonte, acessível com `?brand=horizonte`. |

## Evidências

- Auditoria em 1280 px: 14 superfícies sem overflow horizontal, elementos cortados ou texto abaixo do mínimo.
- Auditoria em 1440 px: 14 superfícies com o mesmo resultado.
- Playwright: 14 jornadas aprovadas.
- Backend: 40 testes aprovados; Ruff sem erros.
- TypeScript, contrato visual e cobertura das 57 referências aprovados.
- Build de produção concluído.

Arquivos de auditoria: `artifacts/feedback-audit/final-1280.json` e `artifacts/feedback-audit/final-1440.json`.

## Execução local

- Produto: `http://localhost:3000`
- API: `http://localhost:8000`
- Saúde da API: `http://localhost:8000/health/live`

