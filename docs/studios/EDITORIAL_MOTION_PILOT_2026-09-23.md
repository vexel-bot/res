# Piloto de motion editorial — Distribuição (23/09/2026)

## Resultado observado

O res produziu um animatic MP4 vertical de 11 segundos, 720×1280, 30 fps, a partir do briefing e da identidade neutra. O Codex não escreveu as cenas nem forneceu arquivos de imagem ao piloto. O diretor local de teste usou GPT-4.1; os ícones foram obtidos pelo componente Lucide do res e o vídeo foi exportado pelo caminho HyperFrames/FFmpeg.

**Estado: reprovado.** O arquivo final do piloto é `artifacts/validation/distribution-production-live/director-editorial-motion-v4-valid-schema-20260922/distribution.mp4`, SHA-256 `7906f47887bba0420a8315e6fbfa35a31b8f90de9fe8ac8cfec4e53c830d37c6`. A produção parou em `awaiting_review`, com `production_visual_correction_limit_reached`; os gates de adequação técnica e resultado observado falharam. Não houve avaliação humana 4/5 nem aprovação comercial.

A sequência mostra uma lâmpada, linhas e ícones de dispositivos, mas não mostra um objeto reconhecível percorrendo caminhos e chegando a destinos. A segunda cena contém um traço angular que se lê como rabisco. A ressalva final depende de texto pequeno. O primeiro ícone veio em um cartão com fundo próprio, porque a necessidade componível não exigia alfa. O áudio AAC está praticamente silencioso: média e pico de aproximadamente −91 dB na medição com FFmpeg.

## Causa técnica confirmada

1. O diretor declarou oito necessidades gráficas, mas o resolvedor consultava Pexels para componentes componíveis. A ordem foi corrigida: a biblioteca local é consultada primeiro e uma ausência de componente não se converte automaticamente em stock.
2. Três ícones da última cena não tinham necessidade vinculada. A recompilação do res criou um derivado e vinculou essas necessidades ao mesmo componente declarado no blueprint. Os oito materiais foram então resolvidos localmente.
3. A primeira exportação encontrou um erro de variável não inicializada na auditoria semântica. O mesmo job foi repetido com o código corrigido; não houve nova submissão de planejamento.
4. A afirmação `content_present` exigia conteúdo canônico, mas os ícones procedurais não tinham referência de conteúdo. O contrato anterior aceitava essa combinação impossível. O contrato agora a rejeita antes do render; uma ação puramente gráfica tem o tipo `visual_action`, cuja interpretação permanece pendente de revisão humana.
5. As duas correções automáticas não mudaram os pixels. Os três jobs de render retornaram o mesmo checksum. A primeira correção retirou parte da exigência semântica; a segunda alterou apenas propriedades sem efeito visual. O fluxo agora rejeita enfraquecimento de verificação e revisões sem alteração visual executável antes de renderizar outra vez.

## Custos e limites da evidência

Quatro tentativas de planejamento da **mesma peça** registraram US$0,316896, US$0,662652, US$0,104952 e US$0,601836, totalizando **US$1,686336 medidos**. Houve ainda uma chamada diagnóstica curta, não incluída nos recibos agregados; portanto o valor medido é um piso, não o gasto exato. Nenhuma chamada adicional é necessária para analisar este candidato. A execução ficou abaixo do teto de US$2 autorizado para a peça.

O contato de frames é uma amostra de um frame por segundo, não uma revisão temporal integral. Nenhum especialista humano atribuiu notas. A avaliação técnica não prova qualidade editorial.

## Critério para a próxima progressão

Antes de um novo piloto pago, o res precisa demonstrar localmente: um motivo reconhecível que permaneça entre cenas; conectores de origem a destinos, sem polilinha que se cruza; tipografia em hierarquia legível; layout e cor de ícones controlados pela identidade; som com função ou silêncio deliberado. Duas propostas devem ser **visualmente renderizadas** e escolhidas antes da peça completa. A saída deverá preservar rastreabilidade entre proposta, plano, manifestação executável, áudio e vídeo. Somente um novo MP4 assistido em velocidade normal e avaliado por pessoas poderá cumprir a meta de 4/5.
