# Radar Contextual V2 — implementação segura em shadow

Data da verificação: 2026-08-23.

## Resultado

O `radar-v1.1` continua sendo o único ranking ativo e sua resposta pública não foi substituída. A evolução contextual foi implementada como uma trilha V2 aditiva, desligada por padrão, com contratos, gates, persistência de comparação, avaliação offline e rollback por flag.

## Fronteiras implementadas

| Responsabilidade | Implementação |
| --- | --- |
| Fonte/evidência | `SourceEvidenceV2` preserva URL, publicação, coleta, expiração, confiança opcional, tipo de conhecimento e provider trace. |
| Cluster | `SignalClusterV2` representa um acontecimento e remove URLs duplicadas. |
| Matching | port `SemanticMatcher`; baseline determinístico `builtin.lexical-jaccard`. |
| Pesquisa/embedding | ports `ResearchProvider` e `EmbeddingProvider`; nenhum provider externo foi adotado. |
| Scoring | `radar-v2.0-shadow`, dimensões `observed/derived/unknown`, pesos positivos, penalidades e gates independentes. |
| Explicação | `OpportunityCandidateV2` contém o que postar, por quê, formato, hook, objetivo, janela, confiança, risco/saturação quando conhecidos, evidências, esforço e lineage. |
| Shadow | `RadarShadowEvaluation` guarda baseline, candidato, delta, mudança de elegibilidade, revisão da marca e provider trace. |
| Feedback | `feedback.v2` registra score version e versão do objeto quando disponível. |
| Avaliação offline | `radar-eval-v1` calcula precision@K, recall@K, NDCG@K, duplicação de cluster e concordância de elegibilidade. |

## Regras de honestidade

- momentum, novidade, saturação e risco só recebem valor quando o conector fornece a métrica normalizada;
- ausência de métrica vira `unknown`, nunca um número substituto;
- menos de duas evidências independentes bloqueia a alegação de tendência e orienta o uso de evergreen fundamentado na marca;
- janela expirada, assunto proibido, conexão forçada ou risco alto bloqueiam independentemente do score;
- resposta sintetizada, inferência e sugestão não são tratadas como fonte factual;
- uma única avaliação shadow é persistida para o representante mais recente de cada cluster por execução.

## Flags e rollout

```text
RADAR_CONTEXTUAL_V2_ENABLED=false
RADAR_CONTEXTUAL_V2_SHADOW_MODE=false
```

1. `SHADOW_MODE=true`: executa V2 ao lado do rank ativo e persiste comparações; não muda oportunidades exibidas.
2. `ENABLED=true`: libera a consulta autenticada `/api/v1/radar/shadow-evaluations` para auditoria interna.
3. Ativação futura como score principal exige dataset julgado, métricas offline, análise dos deltas, thresholds aprovados e rollout por workspace. Essa ativação não foi implementada neste slice.

Rollback: desligar ambas as flags. Nenhuma tabela antiga, oportunidade `radar-v1.1` ou feedback histórico é removido.

## Persistência e migrations

- `0012_radar_contextual_v2` adiciona metadata versionada aos sinais, metadata de versão ao feedback e `radar_shadow_evaluations`.
- A migration é aditiva e passou em upgrade/downgrade/upgrade junto à cadeia completa até `0013`.

## Evidência de testes

- candidato com uma única fonte: gate `evidence_sufficiency=block`;
- métricas ausentes: momentum, novelty e saturation permanecem `unknown`;
- duas manchetes equivalentes: um cluster e uma avaliação V2 shadow;
- ranking retornado ao usuário continua com `scoreVersion=radar-v1.1`;
- auditoria shadow respeita tenant isolation;
- feedback escolhido preserva `feedback.v2` e `opportunityScoreVersion=radar-v1.1`;
- avaliação offline retorna métricas reproduzíveis e versionadas;
- suite backend completa: 50 testes;
- E2E completo: 15 testes.

## Limitações e gates reais

- O baseline `radar-v1.1` ainda possui defaults históricos para novelty/saturation. Eles foram preservados para não alterar silenciosamente o baseline; o V2 corrige essa semântica em shadow. Uma futura promoção exige nova versão, nunca mutação escondida de `v1.1`.
- Não existe provider semântico ou de pesquisa aprovado; Vane/Perplexica continua apenas candidato encapsulável.
- Não há dataset humano suficiente para promover thresholds V2.
- Cohorts não foram implementados. Exigem consentimento, política, anonimização, tamanho mínimo e testes de isolamento.
- Aprendizado continua local por workspace e limitado; nenhuma memória, texto, asset, rosto, voz ou resultado identificável cruza marcas.
