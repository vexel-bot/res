# Clicko — Especificação do Radar de Oportunidades Contextuais

**Versão:** 0.1  
**Status:** fonte normativa para evolução do backend  
**Escopo:** sinais externos, contexto de marca, ranking, oportunidades, feedback e aprendizado  
**Baseline observado:** `radar-v1.1` em `backend/app/domain/radar/scoring.py`

---

## 1. Propósito

O Radar responde continuamente:

> Qual conteúdo esta marca deveria produzir agora, por que, durante qual janela e com qual risco?

Ele não deve apenas listar notícias ou tendências. Deve encontrar — ou rejeitar — uma ponte coerente entre:

- o que está acontecendo no mundo;
- o que importa naquele nicho;
- o que aquela marca vende e defende;
- o que seu público deseja ou teme;
- o que já funcionou ou foi rejeitado;
- o objetivo editorial e comercial atual.

O sistema precisa ser capaz de afirmar:

- “Esta oportunidade combina com sua marca e deve ser usada nas próximas 12 horas.”
- “O tema está crescendo, mas a conexão com seu produto seria forçada.”
- “Não há evidência atual suficiente; use uma oportunidade evergreen baseada na memória da marca.”

---

## 2. Hipótese de produto

Durante 8 a 12 semanas, uma inteligência que combina contexto vivo, conhecimento de nicho, memória privada da marca e resultados anteriores deve melhorar:

- qualidade da decisão editorial;
- tempo entre oportunidade e publicação;
- taxa de aprovação na primeira versão;
- consistência de marca;
- desempenho relativo ao histórico daquela marca;
- capacidade de criar variações sem produzir conteúdo genérico.

O teste não pergunta somente se “a IA gerou algo bom”. Ele compara o fluxo Clicko com o fluxo anterior do usuário.

---

## 3. Princípio de arquitetura

O Radar não é um único modelo de machine learning e não é um prompt.

Ele é um sistema híbrido:

```text
Fontes externas e internas
  → coleta
  → normalização
  → deduplicação e clustering
  → validação de evidência
  → entendimento do acontecimento
  → comparação com marca/nicho/público
  → scoring e gates
  → recomendação editorial
  → decisão humana
  → publicação e resultado
  → aprendizado
```

Componentes:

1. regras determinísticas para segurança e elegibilidade;
2. métricas observáveis para timing, momentum e saturação;
3. recuperação de informação com fontes;
4. análise semântica para encontrar pontes não literais;
5. LLM para síntese e explicação, nunca como única evidência;
6. personalização por marca;
7. aprendizado por resultado;
8. conhecimento agregado por cohort somente com governança.

---

## 4. Três camadas de contexto

### 4.1 Contexto permanente da marca

O Radar consome a revisão vigente da Brand Memory:

- empresa e posicionamento;
- produtos, serviços e ofertas;
- diferenciais e provas;
- público, personas, dores, desejos e objeções;
- pilares de conteúdo;
- tom de voz;
- identidade e códigos culturais;
- objetivos editoriais e comerciais;
- regiões e idiomas;
- claims permitidos;
- assuntos proibidos;
- riscos e limites jurídicos;
- concorrentes e referências;
- conteúdos aprovados/rejeitados;
- histórico de performance.

Toda oportunidade deve registrar qual revisão da marca foi utilizada.

### 4.2 Contexto vivo do mundo e do nicho

O sistema monitora e diferencia:

- notícias;
- pesquisa em crescimento;
- cultura e entretenimento;
- filmes, séries, música e lançamentos;
- esportes e grandes eventos;
- datas e acontecimentos locais;
- memes e conversas emergentes;
- alterações regulatórias;
- atualizações técnicas e acadêmicas;
- players e concorrentes;
- conteúdos públicos do nicho;
- dúvidas e comentários do próprio público;
- performance recente dos canais conectados.

Cada sinal precisa ter fonte, URL, data de publicação, data de coleta, região, idioma, tipo e expiração.

### 4.3 Motor de oportunidades

O motor transforma sinais em oportunidades ou rejeições explicáveis. Ele compara o acontecimento ao contexto privado sem misturar dados entre workspaces.

---

## 5. Tipos de conhecimento

Todo item recuperado deve ser classificado:

| Tipo | Exemplo | Uso |
|---|---|---|
| Atual factual | notícia, lançamento, resultado esportivo | timing e oportunidade. |
| Tendência quantitativa | busca ou conversa em crescimento | momentum e saturação. |
| Acadêmico/técnico | paper, guideline, documentação | autoridade e fundamento. |
| Nicho público | players, referências e padrões públicos | linguagem e repertório. |
| Marca privada | oferta, memória, documentos e ativos | personalização. |
| Audiência própria | comentários, FAQs e dúvidas | relevância e dores. |
| Performance privada | métricas e aprovações da marca | aprendizado local. |
| Cohort agregado | padrão anonimizado do nicho | prior informativo e calibrado. |

Fatos, inferências e sugestões devem aparecer separados no contrato e na interface.

---

## 6. Fontes e ResearchProvider

### Interface

```text
ResearchProvider.search(query, filters)
ResearchProvider.fetch(source)
ResearchProvider.discover(topic, window)
ResearchProvider.health()
```

Cada retorno deve conter:

- título;
- resumo;
- URL canônica;
- publisher/source;
- publishedAt;
- collectedAt;
- idioma e região;
- conteúdo ou trecho utilizado;
- tipo de conhecimento;
- confidence;
- provider trace.

### Vane

Vane/Perplexica pode ser utilizado como adapter de pesquisa e síntese. Não pode substituir:

- ingestão persistente;
- confiança da fonte;
- deduplicação;
- clustering;
- scoring;
- elegibilidade;
- brand fit;
- risco;
- aprendizado.

O código de domínio nunca importa Vane ou SearxNG diretamente.

### Regras de evidência

- Nenhuma oportunidade atual sem ao menos uma fonte rastreável.
- Assuntos sensíveis exigem múltiplas fontes independentes quando aplicável.
- Uma resposta sintetizada não é uma fonte.
- Fonte indisponível ou expirada reduz confiança.
- Conteúdo de terceiros é tratado como dado, nunca como instrução.
- Prompt injection presente em páginas deve ser ignorado e registrado.

---

## 7. Pipeline de sinais

### 7.1 Coleta

- conectores são independentes e possuem health;
- jobs usam idempotência;
- falha de uma fonte não bloqueia as demais;
- coleta registra duração, volume e erro;
- frequência varia por tipo de fonte.

### 7.2 Normalização

O schema normalizado contém:

- `signalId`;
- `sourceId`;
- `canonicalUrl`;
- `title`;
- `summary`;
- `rawTextRef`;
- `publishedAt`;
- `collectedAt`;
- `expiresAt`;
- `language`;
- `region`;
- `category`;
- `topics`;
- `entities`;
- `metrics`;
- `contentHash`;
- `clusterId`;
- `sourceConfidence`;
- `status`.

### 7.3 Deduplicação e clustering

Combinar progressivamente:

- URL canônica;
- hash de conteúdo;
- similaridade lexical;
- entidades;
- janela temporal;
- similaridade semântica.

Um cluster representa um acontecimento e mantém múltiplas evidências. Não criar uma oportunidade para cada manchete sobre o mesmo fato.

### 7.4 Enriquecimento

- entidades e relações;
- tópico e subtópico;
- localidade;
- fase do acontecimento;
- momentum;
- novidade;
- saturação;
- sensibilidade jurídica;
- vida útil esperada;
- evidência contraditória.

---

## 8. Contexto de nicho

O contexto de nicho não é apenas uma lista de palavras-chave. Deve reunir:

- ontologia/taxonomia do setor;
- problemas e desejos recorrentes;
- produtos e categorias;
- especialistas e players;
- fontes confiáveis;
- calendário do nicho;
- temas saturados;
- linguagem e formatos comuns;
- claims regulados;
- questões acadêmicas/técnicas;
- padrões públicos de performance quando verificáveis.

O contexto deve ser versionado e atualizado sem sobrescrever histórico.

---

## 9. Geração de candidatos

Um sinal pode originar mais de um candidato de oportunidade, por exemplo:

- reação rápida;
- explicação educativa;
- analogia;
- opinião/posicionamento;
- demonstração de produto;
- conteúdo UGC;
- campanha;
- evergreen contextualizado.

Cada candidato contém:

- acontecimento;
- audiência conectada;
- problema/interesse acionado;
- produto/oferta relacionada;
- ponte causal;
- formato;
- ângulo;
- hook inicial;
- objetivo;
- janela;
- evidências;
- riscos;
- hipótese de resultado.

Se a ponte depender apenas de trocadilho ou associação superficial, deve receber baixa naturalidade ou ser rejeitada.

---

## 10. Scoring versionado

### Dimensões positivas

- relevância para o público;
- conexão natural com produto/oferta;
- aderência ao posicionamento;
- atualidade/freshness;
- momentum;
- novidade;
- potencial de compartilhamento;
- adequação local;
- potencial de autoridade;
- potencial de conversão;
- qualidade/confiança das fontes;
- força da ponte causal;
- adequação ao objetivo atual;
- evidência histórica da marca;
- disponibilidade real de assets/execução.

### Penalidades

- saturação;
- risco jurídico;
- risco reputacional;
- assunto proibido;
- baixa confiança;
- fontes contraditórias;
- conexão forçada;
- janela expirada;
- ausência de direito de uso;
- distância excessiva da audiência;
- custo/tempo incompatível com a janela.

### Estrutura

```text
baseScore = soma(dimensão × peso)
penalties = soma(penalidade × fator)
localAdjustment = personalização limitada da marca
cohortPrior = prior agregado limitado e governado
finalScore = clamp(baseScore - penalties + localAdjustment + cohortPrior)
```

Regras:

- pesos possuem `scoreVersion`;
- breakdown é persistido;
- alterações de peso não reescrevem o passado;
- personalização nunca pode tornar elegível um item bloqueado por segurança;
- cohort não pode dominar evidência local;
- score não substitui explicação;
- thresholds precisam ser calibrados por avaliação humana.

### Gates de elegibilidade

Rejeitar ou bloquear quando:

- risco supera limite;
- assunto é proibido;
- janela expirou;
- não há ponte natural;
- evidência atual é insuficiente;
- direito de uso é incompatível;
- execução não cabe na janela;
- oportunidade contradiz posicionamento essencial.

---

## 11. Evolução do baseline atual

O `radar-v1.1` existente deve ser preservado e testado como baseline. Ele já possui:

- scoring versionado;
- relevância de audiência;
- conexão com produto;
- brand fit;
- freshness;
- momentum, novidade e saturação;
- risco;
- local fit;
- autoridade e conversão;
- feedback e ajuste limitado;
- oportunidades evergreen.

Lacunas observadas:

- matching predominantemente lexical;
- bridge textual genérica;
- métricas de momentum/saturação dependem do conector;
- pouca modelagem de confiança da fonte;
- clustering simples;
- sem análise semântica controlada;
- sem taxonomia de nicho;
- sem custo de execução versus janela;
- feedback com taxonomia limitada;
- cohorts ainda não implementados;
- avaliação offline ainda insuficiente.

A evolução deve ocorrer por novas versões e shadow mode, não substituindo `v1.1` de uma vez.

---

## 12. Contrato OpportunityV2

Campos mínimos:

```text
OpportunityV2
├── identity
│   ├── id, workspaceId, clusterId
│   ├── status, scoreVersion
│   └── createdAt, updatedAt, expiresAt
├── event
│   ├── title, summary, entities, topics
│   ├── factStatements
│   ├── inferenceStatements
│   └── evidenceRefs
├── bridge
│   ├── audienceInterest
│   ├── brandConnection
│   ├── productConnection
│   ├── causalExplanation
│   └── naturalness
├── recommendation
│   ├── angle, hook, format, objective
│   ├── windowLabel
│   ├── publishBy
│   └── executionEstimate
├── score
│   ├── total
│   ├── breakdown
│   ├── penalties
│   ├── confidence
│   └── explanation
├── risk
│   ├── level, reasons, guardrails
│   └── eligibility/rejectionReason
├── context
│   ├── brandMemoryRevision
│   ├── nicheContextVersion
│   └── preferenceProfileVersion
└── lineage
    ├── source/provider traces
    ├── derivedCampaignIds
    └── feedback/results
```

---

## 13. Resposta “o que devo postar hoje?”

A saída deve conter:

- oportunidade;
- o que aconteceu e quando;
- fontes;
- por que interessa ao público;
- por que combina com a marca;
- conexão com produto/oferta;
- melhor abordagem;
- formato sugerido;
- hook;
- janela de publicação;
- objetivo: alcance, autoridade ou conversão;
- confiança;
- saturação;
- riscos e cuidados;
- esforço estimado;
- ação `Criar campanha` ou `Criar conteúdo`.

Quando não recomendada:

- motivo objetivo;
- dimensão que falhou;
- possibilidade de monitorar;
- alternativa evergreen ou de nicho.

---

## 14. Feedback rápido e aprendizado local

### Pontos de feedback

- oportunidade exibida;
- direção sugerida;
- hook;
- formato;
- conteúdo gerado;
- edição assistida;
- review;
- resultado publicado.

### Interação

O usuário deve responder em 10–30 segundos:

- aprovar;
- salvar;
- rejeitar;
- ajustar preferência;
- escolher motivo;
- comentário opcional.

### Motivos sugeridos

Positivos:

- combina com o público;
- conexão natural com produto;
- timing forte;
- direção original;
- marca bem representada;
- fácil de executar;
- potencial comercial.

Negativos:

- conexão forçada;
- não interessa ao público;
- saturado;
- tarde demais;
- risco elevado;
- não parece com a marca;
- não temos assets/tempo;
- direção genérica;
- informação duvidosa;
- outro.

### Eventos

Registrar:

- objeto e versão avaliados;
- ação e motivo;
- usuário e papel;
- workspace;
- contexto e score version;
- momento da jornada;
- modelo/política utilizados;
- efeito posterior quando mensurável.

### Linguagem de valor

Exibir mensagens como:

> “Sua decisão calibra as próximas recomendações desta marca.”

Não afirmar que o sistema “aprendeu tudo” após poucos eventos.

---

## 15. Resultado e atribuição

Feedback explícito e métricas publicadas são sinais diferentes.

O sistema deve normalizar performance por:

- marca;
- canal;
- formato;
- tamanho da audiência;
- período;
- objetivo;
- investimento pago;
- baseline histórico.

Não atribuir causalidade a uma oportunidade com base em uma única publicação. Manter separação entre:

- hipótese;
- correlação observada;
- evidência repetida;
- aprendizado validado.

---

## 16. Cohorts de nicho

### Objetivo

Permitir que padrões agregados ajudem novas marcas sem compartilhar memória privada.

### Regras

- opt-in ou base legal/política definida;
- agregação e anonimização;
- tamanho mínimo do cohort;
- nenhuma referência a marca, pessoa, asset ou texto identificável;
- nenhuma cópia de conteúdo;
- somente estatísticas e padrões abstratos;
- auditoria e possibilidade de exclusão;
- limites de influência no score;
- fallback para zero quando não há massa suficiente.

### Exemplos permitidos

- formatos com melhor retenção relativa no nicho;
- janelas médias de oportunidade;
- temas saturados;
- tipos de hook com melhor aceitação;
- tempo de produção por formato.

### Exemplos proibidos

- usar briefing privado de outra marca;
- expor campanha vencedora identificável;
- reutilizar rosto, voz ou asset;
- copiar texto ou direção proprietária;
- inferir segredo comercial.

---

## 17. Avaliação e machine learning

### Dataset de avaliação

Criar conjunto versionado de sinais e julgamentos humanos:

- usar/não usar;
- relevância;
- naturalidade da ponte;
- risco;
- janela;
- formato;
- explicação.

Separar treino, validação e teste por tempo para evitar vazamento temporal.

### Métricas offline

- Precision@K;
- NDCG@K;
- taxa de oportunidade inelegível no topo;
- calibração da confiança;
- concordância humana;
- qualidade de fonte;
- cobertura de nicho;
- latência e custo.

### Métricas online

- taxa de abertura;
- salvar/escolher/rejeitar;
- motivo de rejeição;
- tempo até criar;
- taxa de conclusão;
- aprovação na primeira versão;
- performance relativa ao baseline;
- diversidade e repetição.

### Rollout

1. baseline `v1.1` ativo;
2. novo ranking em shadow mode;
3. comparação offline;
4. revisão humana das divergências;
5. pequena exposição controlada;
6. monitoramento e rollback;
7. aumento gradual.

Não treinar um modelo sofisticado antes de possuir labels e volume adequados. Começar com features auditáveis e aprender incrementalmente.

---

## 18. Etapas de implementação

### R0 — Baseline e contratos

- preservar testes do `radar-v1.1`;
- documentar pesos e thresholds;
- criar contratos versionados de fonte, cluster e score;
- adicionar dataset de avaliação inicial;
- instrumentar métricas.

### R1 — Evidência e fontes

- `ResearchProvider`;
- confiança da fonte;
- citações;
- health;
- múltiplas evidências;
- classificação de tipo de conhecimento.

### R2 — Clustering e contexto semântico

- canonical URL;
- cluster híbrido;
- entidades;
- embeddings atrás de provider;
- taxonomia de nicho;
- bridge estruturada.

### R3 — OpportunityV2 e scoring

- novas dimensões;
- gates;
- score versionado;
- confiança;
- custo de execução;
- shadow mode.

### R4 — Direção para os Studios

- formato, ângulo, hook, janela e objetivo;
- `OpportunityEvidenceRef` completo;
- criar campanha ou conteúdo sem perder contexto;
- alternativa quando oportunidade é rejeitada.

### R5 — Feedback rápido

- taxonomia;
- eventos versionados;
- mensagens de valor;
- ajustes locais limitados;
- painel de calibração da marca.

### R6 — Resultado em 8–12 semanas

- normalização das métricas;
- associação oportunidade → campanha → conteúdo → resultado;
- comparação com baseline;
- confiança e limites causais.

### R7 — Cohorts

- governança;
- anonimização;
- tamanho mínimo;
- priors limitados;
- auditoria;
- rollout separado.

---

## 19. Critérios de aceitação

- Nenhuma tendência inventada.
- Toda oportunidade atual possui fonte e horário.
- Fato, inferência e sugestão são separados.
- O score possui versão e breakdown.
- Risco e saturação podem bloquear recomendação.
- O sistema consegue dizer “não use”.
- Oportunidade expirada não aparece como urgente.
- Feedback é registrado em poucos segundos.
- Ajustes por marca são limitados e auditáveis.
- Dados privados não atravessam workspaces.
- Cohort não existe sem governança e volume mínimo.
- Vane pode ser removido sem alterar o domínio.
- Novo ranking pode rodar em shadow e sofrer rollback.
- Existe teste E2E: sinal → oportunidade → campanha/conteúdo → feedback → resultado.

---

## 20. Não objetivos imediatos

- Substituir o Radar por uma chamada de LLM.
- Usar Vane como banco de oportunidades.
- Raspar redes sem observar termos e direitos.
- Prometer previsão de viralização.
- Compartilhar conteúdo entre marcas.
- Treinar modelo próprio sem dados suficientes.
- Permitir que performance contorne regras de segurança.
- Inventar score de momentum quando a fonte não fornece evidência.
- Criar uma tela nova para cada componente interno do algoritmo.

---

## 21. Princípio final

A vantagem do Radar não está em saber que um assunto está em alta. Está em saber se aquela marca deve agir, qual ponte é legítima, como transformar o momento em conteúdo e quando é melhor não participar.
