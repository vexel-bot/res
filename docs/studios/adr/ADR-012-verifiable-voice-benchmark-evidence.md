# ADR-012 — Evidência verificável para benchmark de voz PT-BR

**Status:** aceito; contratos e gates implementados, benchmark real não executado  
**Data:** 2026-08-25

## Contexto

A primeira política congelava candidatos, thresholds e nomes de evidências, porém aceitava no contrato um `BenchmarkRunV1` composto apenas por métricas agregadas. Um operador poderia declarar 180 notas humanas, MOS 4,0 e 60 casos sem fornecer casos, observações, blinding ou proveniência verificáveis. A mesma suite também misturava voz stock sintética com clonagem consentida, apesar de terem corpus, hardware, custo, risco e critérios distintos.

## Decisão

O gate `passed` passa a exigir três artefatos imutáveis e ligados por digest:

1. `studio.benchmark-policy.v1`: candidatos, cadeia de componentes, controles, evidências e thresholds congelados;
2. `studio.benchmark-corpus-manifest.v1`: casos privados por ID, locale, cenários, digest do roteiro e, em clone, pseudônimo, asset/checksum e evidência do consentimento;
3. `studio.benchmark-evidence-bundle.v1`: execução terminal por caso, job/provider, output/checksum, provenance, tempo/custo/recursos e observações brutas;
4. `studio.benchmark-license-manifest.v1`: revisão, digest do artefato e texto legal, permissão SaaS/comercial, obrigações e evidência por componente.

O avaliador valida identidade e digest dos quatro artefatos, recompõe cada agregação, exige unidade/evaluator/case-set corretos e verifica que os assets de evidência das observações aparecem no agregado. O manifesto legal deve cobrir exatamente a cadeia da policy e concordar em URL, revisão e licença declarada; componente extra não inventariado ou identidade divergente bloqueia. Para MOS, a política de voz exige candidato cegado, pelo menos três revisores pseudônimos distintos e três avaliações por caso. Ausência de corpus/bundle/license/digest é `incomplete`; adulteração, quebra de consentimento/isolamento, evidência trocada ou agregado divergente é `failed`.

Voz stock e clone deixam de compartilhar a mesma suite:

- `clicko.voice-stock.pt-br.v1`: Kokoro, corpus sintético, zero sujeitos, worker `speech_cpu`, RTF p95 ≤ 1,0 e custo ≤ US$ 0,03/min;
- `clicko.voice-clone.pt-br.v1`: Chatterbox V3/pt-BR e Kokoro+OpenVoice, 10 adultos consentidos, 60 casos e worker `speech_gpu`.

Misaki e eSpeak NG agora aparecem explicitamente na cadeia Kokoro+OpenVoice. Os candidatos Kokoro ficam `review_required` até a revisão das obrigações GPL de source/notices da imagem distribuída. Isso não reprova o algoritmo nem proíbe uso comercial; impede homologação jurídica por inferência.

## Evidência

- 14 testes de contrato cobrem políticas sem dados privados, passagem somente com corpus/bundle/license completos, agregado sem raw data, adulteração de agregado/casos/evaluator/evidência/licença, blinding e separação stock/clone;
- Ruff passou nos contratos, CLI e testes focados;
- digests atuais estão documentados no README de `benchmarks/studios/identity/`.

Nenhum peso, áudio, embedding, consentimento real ou GPU foi usado. Os thresholds continuam política pré-run, não resultado de qualidade. A VPS não foi acessada nem alterada.

## Próximo gate

Antes de executar motores: revisão jurídica explícita dos manifests de licença; aprovação de uma nova versão assinada das políticas; geração do corpus privado com consentimentos ativos; manifesto de worker `speech_cpu`/`speech_gpu`; imagens pinadas com SBOM; protocolo de recrutamento/blinding; storage privado e cleanup comprovável. Só então os quatro candidatos podem produzir resultados comparáveis.
