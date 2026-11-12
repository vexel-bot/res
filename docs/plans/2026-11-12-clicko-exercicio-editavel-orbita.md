# ÓRBITA · exercício de edição e transferência

## Correção no EffectCraft

O exercício é uma cópia editável da revisão 3 de `1b295922-5884-411b-a54f-eebf1da83593`. O EffectCraft manteve o documento de origem e gravou a correção como revisão 4 de `514d3731-bbd2-42d3-a3dd-fcd50e76740b`. O job local `f969ec7f-91e6-441f-8d4b-1aca47e34f43` produziu um MP4 vertical de 17,75 s de imagem a 24 fps.

| Evidência | Observação |
| --- | --- |
| Recuo | O pico de variação da escala caiu de 734,2 para 226,5 pontos percentuais por segundo. A medição usa amostras por quadro do rig nativo. |
| Texto a 300 px | Em 2,625 s, a moldura libera a passagem com o texto fora da área. Em 3,375 s, a frase completa reaparece acima da tela. O motor resolve `Inter-Bold` como Inter Bold. O pedido anterior por `Inter-Black` caía em Inter Regular. |
| Áudio | A faixa editável ganhou 7 dB no trecho de referência. O fade ocupa 16,35–17,75 s. A janela 17,42–17,65 s ficou 27,03 dB abaixo do original no mesmo intervalo. |
| Clarão | A inspeção dos 426 quadros do export corrigido passou no detector de picos amplos de brilho. |

A ficha `orbita-reveal-protect-title` documenta a técnica e seus contraexemplos no repertório consultável. O editor pode inspecionar a fonte efetiva antes de montar. A retomada e o registro de aprendizado usam amostras da revisão em questão, com a origem do material e os pedidos repetidos tratados pelo histórico.

## Prova com a IA local

Executamos o SmolVLM-500M-Instruct em cache na GPU local. A pergunta de detecção permaneceu idêntica nos quatro quadros de 300 px. O modelo respondeu sim à colisão original e aos três controles limpos, inclusive o quadro sem texto. Acertou 1 de 4. A amostra é diagnóstica.

No briefing inédito Casa Lume, a abertura lateral das portas prepara o letreiro de uma biblioteca. Fixamos a escolha B como gabarito antes da inferência. Comparamos a regra escrita e a mesma regra acompanhada da demonstração escrita da ÓRBITA. Nos dois braços, o modelo viu o quadro do novo briefing e escolheu A, antecipando o nome e repetindo o zoom no título. Os dois renders resultaram em MP4s idênticos.

O EffectCraft também renderizou a escolha B como controle editorial. Aos 1,25 s, só a abertura ocupa o quadro. Aos 2,75 s, o nome aparece acima das portas abertas e a categoria já está legível. O ensaio usa escolha entre operações candidatas e um único briefing. A aprovação visual por espectadores e a edição autônoma a partir de exemplos permanecem em aberto.

## Reprodução e recibos

- [Script nativo do exercício](../../benchmarks/studios/orbita/recuo-reparo.jsx).
- [Criação, aplicação e render local](../../scripts/validation/clicko-orbita-exercise.py).
- [Verificação de movimento, fonte e áudio](../../scripts/validation/clicko-orbita-verify.py).
- [Briefing de transferência e alternativas](../../benchmarks/studios/orbita/transferencia-casa-lume-escolhas.json).
- [Inferência visual local](../../scripts/validation/clicko-orbita-local-vlm.py) e [aplicação das escolhas no EffectCraft](../../scripts/validation/clicko-orbita-transfer.py).

Os MP4s, projetos editáveis, quadros e recibos JSON estão em `output/clicko-orbita-exercicio-2026-11-12` no workspace OneDrive. Consumo total de API de **US$ 0**.
