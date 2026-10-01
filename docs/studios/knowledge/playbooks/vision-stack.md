# Pilha de percepção e limite do Supervision

`supervision` organiza resultados; não é um modelo que “vê perfeitamente”. Seu adapter permanece no worker e projeta apenas contratos canônicos `VisionObservationV1`.

| Camada | Responsabilidade | Saída canônica |
|---|---|---|
| PySceneDetect | candidatos de plano/corte | eventos temporais com confiança |
| WhisperX | fala, palavras e timestamps | speech/OCR regions e provenance |
| OpenCV | geometria, cor e medidas | observações objetivas |
| SAM2 | máscaras e continuidade | mask tracks |
| Depth Anything V2 | profundidade monocular | depth artifact + confiança |
| RAFT/TapNet | fluxo e pontos | tracks |
| detector + Supervision | boxes, zonas e anotações | regiões normalizadas |
| Qwen3-VL/V-JEPA2 | descrição e relações temporais | inferências separadas |

Emoção, intenção, causalidade e plausibilidade física nunca entram como detecção objetiva. O sistema deve abster-se quando modelos discordarem ou a confiança ficar abaixo do limiar calibrado.

