# Auditoria estática aprofundada — onda 01

## Cobertura

- 42/42 repositórios com origem e commit registrados;
- 42/42 com finalidade específica, sem placeholder genérico;
- licença raiz, manifests, linguagens, resumo de README e sinais de GPU/container/testes registrados;
- 23 apresentam sinal estático de dependência GPU;
- 13 apresentam diretório de testes detectável;
- dois permanecem sem licença raiz detectada: `hyperframes-launch-video` e `qwen3`;
- decisões continuam provisórias até benchmark e revisão de licenças de pesos/datasets.

## Decisões arquiteturais

### Adopt

Ferramentas fundamentais com adapter, versão fixada e fixture determinística: FFmpeg, OpenCV, OpenTimelineIO, PySceneDetect e Remotion. `Adopt` não significa promoção automática do clone atual; significa que a categoria é compatível com a arquitetura após os testes definidos.

### Adapt

Modelos e componentes que precisam de isolamento e projeção para contratos Clicko, incluindo Supervision, WhisperX, SAM2, Depth Anything V2, RAFT, TapNet, Qwen3-VL, V-JEPA2 e componentes editoriais selecionados.

### Reference-only

- OpenMontage: AGPL-3.0; usar somente padrões reimplementados independentemente;
- modelos biométricos: nenhuma promoção antes da última fase autorizada;
- repositórios sem licença raiz ou papel ainda não demonstrado;
- produtos/editoriais completos usados como referência, não incorporados ao domínio.

## Bloqueios prioritários

1. revisar licença separada de código, pesos e dataset dos 23 candidatos com sinal GPU;
2. fechar licença de `hyperframes-launch-video` e `qwen3` ou rejeitá-los;
3. executar fixtures sem identidade pessoal para visão, edição, voz stock e geração;
4. medir VRAM/RAM, tempo, determinismo, qualidade e falhas;
5. validar PT-BR onde fala, transcrição, G2P ou lip sync estiverem envolvidos.

## Supervision

Permanece `adapt`: organiza boxes, masks, tracks, zonas e annotations. Não detecta sozinho e não “vê perfeitamente”. O adapter converte resultados para `VisionObservationV1`; nenhum tipo de terceiro é persistido.

## OpenMontage

Permanece `reference-only`, fixado no commit `cd9f3c1f03368be87b140af494914b8ee4e3c7a4`. Padrões úteis: manifests, skills, checkpoints, aprovação humana, decision logs, validação pré-composição e inspeção pós-render. A reimplementação não copia código AGPL.

