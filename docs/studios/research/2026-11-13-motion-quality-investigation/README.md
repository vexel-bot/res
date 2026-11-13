# Investigação da qualidade de edição da Clicko

13/11/2026. Entrega: investigação e plano, sem mudança de produção, nova geração de anúncio ou uso pago de API. A arquitetura híbrida permanece uma proposta condicionada às provas.

**Conclusão:** reutilizar o Canvas pode ampliar a execução, mas o fluxo precisa também entregar evidências visuais ao diretor, preparar materiais/copy/som, permitir revisão temporal e sonora e concluir a exportação. Os ensaios disponíveis não isolam a causa da melhora nem permitem prometer equivalência às referências.

## Entrega principal

- [Plano de melhorias, etapas, contratos e indicadores](../../../plans/2026-11-13-clicko-qualidade-motion-roadmap.md).
- [Prova local, fonte arquivado e instruções de reprodução](probes/README.md).

## Diagnóstico e método

1. [00 — Escopo e contexto](00-scope.md).
2. [01 — Pergunta e comparação](01-question.md), papel Sackett.
3. [02 — Método de pesquisa](02-method.md), papel Booth.
4. [03 — Desenho experimental](03-design.md), papel Creswell.

## Investigação por responsabilidade

- [10 — Código, integração e execução](10-backend-audit.md), papel Forsgren: oito achados com rastreabilidade, capacidades existentes e provas propostas.
- [11 — Evidências primárias](11-primary-evidence.md) e [manifesto de fontes](11-sources.json), papel Cochrane: literatura/documentação e limites de aplicação.
- [12 — Análise editorial e explicações concorrentes](12-causal-editorial-analysis.md), papel Klein: cinco hipóteses, crítica visual e experimentos discriminantes.
- [13 — Referências e procedência](13-reference-and-provenance.md), papel Higgins: três alvos, cobertura, pacote recuperável e acesso limitado ao processo do Matheus.
- [14 — Alternativas e investimento](14-options-and-investment.md), papel Gilad: Craft como controle, híbrido reversível e ferramenta especializada somente após necessidade comprovada.

## Revisão sequencial

- [20 — Confiabilidade](20-validity-audit.md), papel Ioannidis, depois da conclusão dos cinco relatórios de investigação.
- [21 — Decisão e vieses](21-decision-audit.md), papel Kahneman, depois de 20 e do plano inicial.

Os papéis são lentes especializadas de agentes, não manifestações das pessoas reais. Revisões separadas usam parte das mesmas fontes; sua concordância não equivale a replicação empírica. Os auxiliares tiveram interrupções de disponibilidade, retomaram e concluíram os pareceres.

As correções finais do plano incorporam a revisão: integração dependente de utilidade demonstrada; cobertura audiovisual ou dimensão não comparável; preparação de materiais podendo começar antes/junto da integração. O gate é para **planejamento condicional**, não validação de implementação, qualidade artística ou gasto.

## Cobertura e lacunas

- Código e build: inspeção estática, com mecanismos e limites localizados. Não foram repetidos os testes históricos nem implementados os adaptadores propostos.
- Referências: reexame de folhas válidas e registros anteriores; observação amostrada. Som e movimento fino integral continuam sem auditoria nesta rodada.
- Baseline: feedback positivo do proprietário, não aprovação final. Arquivo de 16 s silencioso, exportado por recuperação humana.
- Pesquisa externa: fontes primárias com cobertura declarada; os artigos científicos foram consultados no resumo, sem reprodução dos resultados. Não foi realizada revisão sistemática exaustiva.
- Prova nova: repetibilidade de quadros selecionados do Canvas e verificação do pacote arquivado; sem novo anúncio, áudio ou comparação controlada entre motores.
- Sem espectadores, tamanho de amostra, compreensão populacional, IC, PPV ou probabilidade de sucesso calculável. Critérios futuros não são resultados obtidos.

## Fontes adicionais consultadas pelo coordenador

Complementam as fontes do manifesto 11; não contam como replicações independentes.

| Fonte primária | Cobertura e utilidade | Limite |
|---|---|---|
| [Anthropic — engenharia de contexto](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents) | Página de orientação de engenharia; recuperação seletiva, ferramentas e contexto. | Não compara a qualidade dos nossos anúncios. |
| [Anthropic — agentes efetivos](https://www.anthropic.com/research/building-effective-agents) | Orientação sobre padrões simples e trade-offs de agentes. | Publicação de 2024; usada como princípio, não inventário atual de produto. |
| [Auto-Director](https://arxiv.org/abs/2610.28346) | Resumo do preprint de outubro/2026; proposta de planejamento/edição/revisão com ferramentas. | Não reproduzido; não prova que um enxame seja necessário para a Clicko. |
| [EffectCraft upstream](https://github.com/storytold/effectcraft) | README e descrição de capacidades do projeto independente. | Upstream atual não é o build integrado. Percentuais autoatribuídos de cobertura não são medida de paridade ou qualidade. |
| [MDN — Canvas API](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API) | Documentação da API de desenho e sua distinção de WebGL. | Primitivas gráficas não fornecem automaticamente materialidade ou direção. |
| [FFmpeg — filtros](https://ffmpeg.org/ffmpeg-filters.html) | Trechos de composição/overlay e tratamento de alfa. | Não qualifica o intercâmbio específico da Clicko sem execução. |
| [Anthropic — Vision](https://platform.claude.com/docs/en/build-with-claude/vision) | Documentação de imagens e limitações. | Não usada para concluir uma proibição universal de áudio/vídeo; a ausência de escuta aqui foi localizada no código da integração. |

A documentação Adobe de fundamentos de animação foi aberta como triagem, sem cobertura suficiente do conteúdo técnico para apoiar uma alegação desta síntese. O processo do Matheus não pôde ser reaberto; seu uso é histórico e qualificado no parecer 13.
