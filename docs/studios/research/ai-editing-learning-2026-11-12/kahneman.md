# Auditoria de decisão · Clicko/ÓRBITA

Kahneman concluiu a etapa final de QA documental após [Ioannidis](ioannidis.md). Revisei o [desenho](pipeline.md), os achados de [Cochrane](cochrane.md) e [Higgins](higgins.md), a [síntese](sintese.md) e a [auditoria local](diagnostico-orbita.md). As verificações do vídeo e do motor são da auditoria local. O piloto comparativo e as avaliações humanas abaixo são propostas.

## Evidência que muda a decisão

- **Avanço observado.** O nome e a categoria estão legíveis na amostra de 4,58 s do novo corte. No anterior, a categoria aparece na amostra de 27,2 s. O Opus sozinho dirigiu, editou e solicitou a exportação do novo corte. Sonnet e Haiku tiveram zero chamadas e contribuições nessa execução. O Clicko/EffectCraft validou, salvou e renderizou. No anterior, Sonnet propôs edições, das quais duas entraram na timeline, e Haiku indexou o contexto. Mudaram briefing, duração e participação, portanto o contraste não estima o efeito de delegação ou de repertório.
- **Defeitos verificados.** O motor resolveu Inter-Black como Inter Regular. O fade prometido para 18,2–19,5 s não ocorreu no MP4, cuja relação de ganho com a faixa original permaneceu estável até o fim. A revisão deixou de observar a moldura cruzando o texto a 2,625 s. O primeiro achado é fidelidade de fonte, o segundo é divergência plano–render e o terceiro envolve cobertura temporal. A capacidade do revisor de reconhecer a colisão quando exposto a ela continua em aberto.
- **Uso da biblioteca.** O contexto inicial incluiu o índice e seis fichas. Não houve busca, consulta ou registro de lição durante a sessão. A presença das fichas permite influência, mas o registro não identifica seu efeito. Uma regra pode ter sido desconhecida, recuperada e ignorada, mal executada ou contrariada por uma limitação do motor. Essas hipóteses levam a correções diferentes.

## Checklist de decisão

| Pergunta | Risco observado e resposta |
|---|---|
| 1. Interesse próprio | Moderado para a literatura de fornecedores. Documentação serve para descrever o contrato. Exigir avaliação independente da eficácia. |
| 2. Apego à proposta | Alto se a solução vier pré-selecionada como “mais agentes” ou “mais repertório”. Incluir o fluxo atual e o diagnóstico de fidelidade. |
| 3. Dissenso | Alto na aprovação pelo próprio editor, que encerrou sem corrigir os defeitos identificados depois. Coletar notas cegas e independentes antes da discussão. |
| 4. Analogia saliente | Alto para generalizar a ÓRBITA ou o B-roll de EditDuet para motion, áudio e outros gêneros. Usar casos inéditos com demandas diferentes. |
| 5. Alternativas | Alto para atribuição causal. Isolar regra, demonstração, recuperação e revisão em comparações distintas. Tratar briefing e delegação como hipóteses separadas. |
| 6. Informação ausente | Alto. Faltam compreensão após uma exibição, preferência cega, cobertura da revisão, repetição e transferência. Medir cada uma. |
| 7. Âncoras numéricas | Alto. Duração, custo medido, raciocínio, quantidade de Béziers e taxas externas podem dominar a impressão. Registrar origem, comparador, incerteza e finalidade de cada número. |
| 8. Halo | Alto. O recuo até a sala e o render válido podem emprestar crédito ao acabamento inteiro. Julgar tipografia, ritmo, continuidade, som e cumprimento do briefing separadamente. |
| 9. Custo afundado | Possível. O investimento passado em biblioteca ou enxame não deve determinar o próximo braço. Usar esforço e valor incrementais prospectivos. |
| 10. Otimismo de planejamento | Alto para prometer ganho, tempo ou custo. Fixar teto e usar distribuição de execuções comparáveis antes de projetar orçamento de produção. A classe de referência ainda falta. |
| 11. Pior caso | Alto. O piloto pode recompensar memorização, falso alarme ou conformidade estética. Aplicar o premortem abaixo. |
| 12. Aversão à perda | Incerta. Usar o fluxo atual como controle e experimentar em cópias permite comparar melhorias sem apostar a produção. |

O System 1 pode explicar a melhora pela novidade do corte ou pela reputação do modelo. O teste de System 2 é perguntar se a mesma conclusão sobreviveria a um recorte que destaque apenas a colisão, o fade e a fonte. O veredito se mantém nas duas molduras: há melhora de comunicação observável e falhas locais, com efeito de cada intervenção indeterminado.

## Avaliações mediadoras

Pontuação documental de suporte para agir, por dimensão. **1** hipótese sem comparação local, **2** sinal local ou evidência indireta pertinente, **3** observação local com evidência rastreável. Esta é uma avaliação individual. Os julgamentos independentes serão coletados no piloto.

| Dimensão | Nota | Base |
|---|---:|---|
| Fidelidade do motor e do áudio entregue | 3 | Consulta de fonte e comparação da faixa exportada com a original. |
| Cobertura da revisão | 3 | A colisão fica fora das janelas temporais solicitadas. |
| Percepção da revisão | 1 | Falta mostrar o mesmo defeito em evidência equivalente e medir se o revisor o reconhece. |
| Efeito das demonstrações de ferramentas | 2 | EditDuet fundamenta a hipótese. O domínio e as medidas diferem do Craft. |
| Transferência editorial entre briefs e gêneros | 1 | Uma execução local, com mudanças simultâneas. |
| Previsibilidade de custo e tempo | 1 | Execuções diferentes, com exposição incerta e sem classe comparável. |

## Comparações refutáveis

Fixar versão do modelo, ferramentas, fontes efetivamente disponíveis, insumos, briefing por par, configuração de render e teto de tempo/custo/contexto. Rodar repetições, contrabalançar a ordem e ocultar autoria e condição dos avaliadores. Usar exemplos de ensino, casos de calibração e briefs inéditos sem sobreposição. Predefinir a menor melhora editorial útil e os limites aceitáveis de defeitos, retrabalho e custo.

| Hipótese | Comparação com uma mudança | Evidência que enfraquece a hipótese |
|---|---|---|
| Regras executáveis ajudam a escolher e aplicar técnicas | Fluxo atual × fluxo atual com uma regra condicional e seu contraexemplo. | O intervalo de resultados em briefs inéditos exclui a melhora mínima prevista para a habilidade-alvo. |
| Trajetórias ensinam a executar e reparar | Mesma regra textual × mesma regra acompanhada de trajetória nativa com estado, comando, erro, reparo e resultado. Igualar o teto de contexto e ferramentas. | O ganho fica restrito ao exercício mostrado ou há mais falhas técnicas sem melhora editorial útil. |
| A recuperação pertinente melhora a decisão | Mesmo corpus e orçamento, recuperação atual × recuperação guiada pela intenção do trecho. | Melhora a pertinência medida das fichas, mas o efeito útil na edição é excluído pelos resultados. |
| A cobertura temporal explica o defeito perdido | Mesmos MP4s, revisor e orçamento de evidência. Janelas livres × cobertura de ponta a ponta com amostragem densa nos eventos críticos. Incluir trechos íntegros e falhas anotadas independentemente. | O recall não melhora no critério pré-fixado ou o aumento de falsos positivos supera o tolerado. Separadamente, fornecer o trecho anotado a ambos os protocolos permite testar se o revisor percebe a falha quando ela está visível. |
| Crítica calibrada melhora o que vai ao ar | Mesma montagem inicial e mesmo orçamento de revisão/reparo. Autorrevisão × crítico calibrado que indica tempo, evidência e correção possível. | Mais críticas sem reparos confirmados, ou reparos acompanhados de regressão editorial julgada às cegas. |

Tipografia resolvida e envelope de ganho são checagens do artefato. Avaliar com pessoas legibilidade, hierarquia, continuidade, ritmo e som. Medir compreensão com espectadores após uma exibição. Relatar concordância, precisão, recall, reparos e custo separadamente. Uma comparação de modelo, IDE, motor ou delegação exigiria seu próprio controle. Resultado inconclusivo preserva a incerteza.

## Premortem e veredito

- **Regras, trajetórias e recuperação.** O piloto “venceu” no próprio recuo da ÓRBITA, mas repetiu o mesmo movimento em um brief cujo evento pedia outra solução. Um conjunto reservado com contraexemplos e critérios por intenção revela essa falha.
- **Cobertura e crítica.** O revisor passou a marcar qualquer cruzamento como defeito. O editor limpou o texto, mas destruiu o encaixe com a grade ou perdeu o acento musical. Pares íntegros, falso positivo medido e nova revisão do render após o reparo revelam essa falha.
- **Fidelidade.** O exercício validou nomes de fontes e animações no projeto, mas o MP4 final continuou com substituição e ganho estático. A fonte resolvida no motor e a comparação do envelope do áudio exportado são os critérios correspondentes.

**Prosseguir** com verificação explícita da fidelidade do render e preparar um piloto pequeno e reversível. **Revisar** qualquer conclusão de que repertório, modelo, agentes ou custo explicam a melhora do corte. **Rejeitar como conclusão desta coleta** promessa de domínio geral de edição ou superioridade arquitetural. O gate de decisão está concluído para síntese com esses limites. A execução do piloto, as avaliações humanas independentes e a referência de custo/tempo permanecem pendentes.
