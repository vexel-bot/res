# Relatório canônico — inteligência criativa e fábrica audiovisual

**Data:** 2026-09-01  
**Workspace:** `C:\Users\edugu\Downloads\res`  
**Estado:** piloto R1 e taxonomia V1.1 aprovados pelo responsável do workspace.

## Resumo executivo

O plano foi implementado até o primeiro gate que exige autoridade humana. Existem doze análises completas de máquina e doze mapas temporais com cobertura integral, uma taxonomia corrigida, pacote de revisão e gate fail-closed. Nenhum vídeo novo, rosto, voz ou cenário foi gerado.

A estrutura das 900 unidades existe como manifesto: 200 creators, 300 roteiro, 100 direção, 100 montagem e 200 crafts complementares. **Zero das 900 foi fingida como anotada.** As doze unidades R1 são calibração e permanecem pendentes de aprovação. Noventa slots estão predeterminados para segunda revisão.

Os trinta ecossistemas de roteiro têm os seis artefatos estruturais, porém estão honestamente marcados `seed_evidence_only`. Eles só viram modelos operacionais após análise de dez obras/unidades, falhas, colaboradores e teste inédito.

## Evidências R1

Os creators demonstraram cinco padrões especialmente transferíveis:

1. **demonstração incorporada:** a transformação visual executa o argumento, em vez de apenas ilustrar uma palavra;
2. **processo observável:** entrada, transformação intermediária e saída tornam tutorial auditável;
3. **metalinguagem temporal:** timeline e rótulos revelam a estrutura no instante correspondente;
4. **progressão por escala/estado:** arquivo escolhido por origem, obstáculo, prova e consequência supera B-roll genérico;
5. **cenário funcional:** ambiente estabiliza mudança, produz cobertura, carrega regra ou serve como prova.

O contraexemplo mais claro é o diagrama estático de 9,43 segundos: muita informação espacial, nenhuma rota temporal de leitura e ausência de voz/personagem. Ele será preservado como falha instrutiva, não descartado.

As sequências abertas reforçaram que ação e descoberta dependem de objetivo, geometria, escala, reação e som. `Charge` usa um prop-objetivo e o ambiente industrial para criar opções/obstáculos. `Sprite Fright` usa indício, aproximação, mudança de escala, reação de ensemble e falsa segurança.

## Correção metodológica

Detecção de cena por pixels não equivale a montagem. Faíscas, face replacement, motion e movimento de câmera geram falsos cortes. `shots.json` registra claramente candidatos, speech units e necessidade de conferência. O schema persiste confiança e proveniência.

## Pesquisa de roteiro

A biblioteca parte de fontes institucionais e primárias:

- [Writers Guild Foundation — Screenplay Primers](https://www.wgfoundation.org/screenplay-primers);
- [Writers Guild Foundation — Archive](https://www.wgfoundation.org/archive);
- [BAFTA — Screenwriters’ Lecture Series](https://www.bafta.org/programmes/screenwriters-lecture-series);
- [DGA Visual History](https://www.dga.org/Craft/VisualHistory);
- [Michael Arndt — Endings](https://www.pandemoniuminc.com/endings-video) e [WGA East OnWriting](https://www.wgaeast.org/onwriting/michael-arndt-endings/);
- [Scriptnotes / John August e Craig Mazin](https://johnaugust.com/2022/scriptnotes-episode-532-mistakes-of-yes);
- [Television Academy — showrunners com Shonda Rhimes](https://www.televisionacademy.com/video/series-showrunners-0);
- [Making The Wire — painel](https://www.movingimagesource.us/files/dialogues/3/50252_programs_transcript_pdf_309.pdf);
- [Paul Schrader — BAFTA](https://www.bafta.org/media-centre/press-releases/bafta-screenwriters-lecture-series-paul-schrader/);
- [Céline Sciamma — BAFTA](https://www.bafta.org/media-centre/press-releases/screenwriters-lecture-series-2019-celine-sciamma/);
- [Park Chan-wook — BAFTA transcript](https://static.bafta.org/uploads_pre_202411/transcripts/sls_-_park_chan-wook.pdf);
- [Mike Leigh — BAFTA](https://www.bafta.org/stories/mike-leigh-screenwriters-lecture/).

Materiais que exigem consulta presencial, assinatura ou autorização aparecem como lacuna. A biblioteca não afirma ter lido uma obra integral que não foi legalmente acessada.

## Auditoria técnica

Foram inventariados 42 repositórios: os 40 clones, Supervision e OpenMontage. A inspeção registrou origem, commit, licença raiz, manifests, linguagens, riscos, decisão provisória e benchmark. Uma auditoria de máquina não promove provider.

`OpenMontage` foi clonado somente da origem oficial `calesthio/OpenMontage`, commit `cd9f3c1f03368be87b140af494914b8ee4e3c7a4`. A licença detectada é AGPL-3.0; decisão `reference-only`. Manifests, skills, checkpoints, human gates, decision logs e inspeção pós-render serão reimplementados independentemente. Código não entra no backend sem revisão jurídica.

`supervision`, commit `5f25aa0ee6dc22891415b6e3d2e1689ce7a32952`, é `adapt`: organização de detecções atrás de adapter. Seus tipos nunca atravessam domínio, banco ou API.

## Contratos implementados

O backend agora contém `KnowledgeClaimV1`, `CreativeCouncilDecisionV1`, `CopyBriefV1`, `CharacterBibleV1`, `WorldBibleV1`, `PerformancePlanV1`, `SceneBlueprintV1`, `VisionObservationV1`, `GenerativeShotSpecV1`, `AssetPlanV1`, `RepositoryCapabilityV1`, `ProductionRunV1` e `CreativeResearchGateV1`.

Os testes provam que:

- inferência sem base é rejeitada;
- evidência proibida não sustenta claim;
- pessoa e ambiente reais exigem grants;
- asset aprovado exige direitos liberados;
- estados não pulam gates nem se autoaprovam;
- aprovação do R1 libera somente expansão de pesquisa, nunca geração cara.

## Pipeline

O pipeline canônico está materializado em `playbooks/production-pipeline.yaml`, com rotas real, fictícia e híbrida, contratos separados para copy/roteiro e revisão de montagem/motion/som. A fábrica 12/24/64 já existente continua sob seus gates; o manifesto de avatar/voz está explicitamente bloqueado até os 100 vídeos não biométricos e 24 casos privados autorizados.

## Estado verificável

| Item | Estado |
|---|---|
| R1 analyses | 12/12 geradas e aprovadas por humano |
| R1 temporal maps | 12/12 válidos e aceitos no gate R1 |
| Taxonomia | V1.1 aprovada |
| Corpus 900 | 900 planejadas; 0 anotadas no corpus principal |
| Revisão dupla | 90 slots reservados |
| Mentes de roteiro | 30 scaffolds; 0 promovidas |
| Repositórios | 42 inventários; decisões provisórias |
| Geração de vídeo | bloqueada |
| Avatar/voz | bloqueado, última etapa |

## Próxima decisão humana

Revisar [R1_HUMAN_REVIEW_PACKET.md](R1_HUMAN_REVIEW_PACKET.md) e a taxonomia. Somente depois de decisões registradas o gate pode abrir a seleção e anotação das 900 unidades. Rejeições retornam à unidade proprietária e preservam versão e motivo.
