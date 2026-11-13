# Auditoria de confiabilidade da investigação

Ioannidis, Tier 2, 13/11/2026. Parecer sobre métodos, relato, reprodutibilidade, avaliação e incentivos. Não é manifestação do pesquisador real. Esta revisão não executa novas inferências, renders ou testes de produção. **Estado: concluído após a conclusão dos cinco relatórios Tier 1, preservando a ordem Tier 1 → confiabilidade → decisão.**

## Escopo e critério de confiança

Examinei [pergunta](01-question.md), [método](02-method.md), [desenho](03-design.md), [auditoria técnica](10-backend-audit.md), [evidência primária](11-primary-evidence.md), [manifesto de fontes](11-sources.json), [interpretação causal](12-causal-editorial-analysis.md), [procedência](13-reference-and-provenance.md) e [alternativas de investimento](14-options-and-investment.md). Conferi diretamente os trechos de revisão sonora, ligação de composições, orçamento e contexto editorial no código, e li o recibo do probe Canvas. Não repeti o experimento nem ouvi os anúncios.

Confiança aqui distingue **rastreabilidade do fato**, **replicação do comportamento** e **validade da inferência**. Fonte primária ou código legível não equivale a eficácia criativa demonstrada. PPV, poder estatístico, efeito e intervalo de confiança são **não identificáveis**: faltam parâmetros justificáveis e comparação controlada. Preenchê-los com suposições produziria precisão fictícia. A adaptação qualitativa é explícita; não satisfaz uma exigência formal de PPV numérico da distribuição do squad.

## Julgamentos por alegação

| Alegação | Julgamento e limite |
|---|---|
| O híbrido permitirá atingir a meta. | **Não demonstrada.** Viabilidade arquitetural plausível; efeito sobre qualidade e contribuição de cada componente permanecem abertos. Aceitar somente como hipótese com portões de decisão. |
| EffectCraft é a causa principal dos anúncios fracos. | **Não sustentada.** A mudança independente alterou mídia, ferramentas, contexto e execução. Comparar a mesma operação pelo mesmo build dentro/fora da integração antes de atribuir culpa ao motor. |
| Faltam mecanismos concretos no fluxo ativo. | **Rastreabilidade alta nos trechos auditados.** O modelo recebe texto/imagens e medidas de áudio; `composition.link` aceita EffectCraft → FilmCraft; orçamento depende do modo. Código confirma alcance, não a frequência com que cada lacuna prejudicou anúncios. |
| O Canvas é reaproveitável. | **Suporte pontual.** O recibo registra oito solicitações, seis tempos distintos, repetições iguais e igualdade em página nova. Alfa 255 sustenta cena opaca nessas amostras; não demonstra animação inteira, transparência, paridade ou qualidade percebida. |
| O repertório já ensinou o sistema. | **Não demonstrada como transferência.** Cadastro e recuperação estão documentados; as fichas continuam candidatas. Exigir execução adequada em briefing novo e recusa no contraexemplo. Zero correspondências dos hashes específicos não prova ausência de toda imagem equivalente. |
| A ÓRBITA é progresso positivo. | **Sustentada como preferência do proprietário vinculada ao arquivo.** Não é aprovação comercial, compreensão populacional ou autonomia: o arquivo é silencioso e a exportação foi recuperada por intervenção humana. |

## Cinco pilares e ameaças principais

**Métodos:** a revisão de escopo serve para localizar mecanismos e planejar provas. Não estima causalidade. Materiais, referência visual, revisão, runtime e delegação são intervenções distintas; testar o pacote completo primeiro permitiria apenas uma conclusão sobre o pacote. A comparação por cena deve fixar especificação visual, sem exigir comandos idênticos entre motores.

**Relato:** os documentos distinguem observado, declarado e hipótese. A cobertura continua restrita: folhas amostradas não verificam easing, cortes completos ou som; artigos foram examinados no resumo; o processo do Matheus depende de registro histórico, com acesso atual malsucedido. Essas restrições precisam acompanhar a conclusão, não ficar apenas no apêndice. Não contabilizar relatórios derivados do mesmo Reel ou teste como replicações independentes.

**Reprodutibilidade:** links locais dos oito Markdown presentes nesta conferência resolveram sem ausências. O código foi conferido estaticamente; o probe é recibo do coordenador, não réplica independente. Seu script/resultado vivem em diretório ignorado e o renderer está fora do repositório: arquivar fonte, hashes, configuração, versão de navegador/runtime, fontes e condições de captura antes de apresentá-lo como pacote reproduzível. Não extrapolar 4,26 s de amostragem para custo de exportação completa.

**Avaliação:** separar integridade técnica, sentido, percepção e conclusão. Um arquivo decodificável não prova anúncio bom; RMS não prova inteligibilidade; imagens não provam fluidez. Calibrar o avaliador com pares corretos/defeituosos e registrar falsos positivos. O proprietário define preferência editorial; compreensão exige participantes e gabarito prévios. Sem coleta, registrar inconclusivo.

**Incentivos:** há risco de confirmar o híbrido já proposto, selecionar o primeiro avanço e defender investimento anterior. Documentação de fornecedor e processo de estúdio têm interesses comerciais; procedência primária não elimina esse viés. Benchmarks externos não são prognósticos da Clicko. Conservar resultados negativos e uma opção de permanecer no Craft se ele passar nas operações necessárias.

## Condições para a síntese

O plano pode recomendar preparação, referências visuais recuperáveis, runtime reutilizável, revisão audiovisual e interoperabilidade por etapas. Deve preservar o baseline, declarar o que já existe, fixar provas discriminantes antes do gasto e manter alternativas reversíveis. A sequência A como controle, B como candidato e C apenas após lacuna necessária, proposta por Gilad, é coerente com a incerteza atual; não prova que B vencerá. Não pode prometer equivalência aos criadores, domínio de qualquer gênero, vantagem de um enxame ou um saldo faturado a partir de estimativa local.

**Gate de confiabilidade: aprovado para planejamento condicional, com as condições acima.** Nenhum erro factual bloqueante foi identificado nos achados centrais examinados. A evidência é insuficiente para promover o híbrido como melhoria validada, iniciar gasto ou certificar qualidade. Encaminhar a Kahneman para auditoria da decisão; a síntese final ainda precisa incorporar estas condições. O parecer audita os relatórios disponíveis, não uma implementação ou plano final ainda inexistente.
