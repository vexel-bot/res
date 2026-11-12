---
name: clicko-video-editing
description: Planeja, monta ou revisa vídeos editáveis na Clicko. Use para escolher entre motion, filmagem, demonstração de interface e híbrido, aplicar técnicas do acervo e conferir uma prévia. Para tarefas de geração de mídia sem montagem, use o fluxo de produção correspondente.
---

# Editar vídeos na Clicko

Leia [o manual de edição](../../../docs/studios/knowledge/playbooks/clicko-motion.md) para escolher a linguagem, preparar uma passagem de trabalho ou revisar a prova. Consulte [as fichas versionadas](../../../backend/app/services/studios/motion_editorial_cards.v1.json) somente quando precisar selecionar uma técnica ou inspecionar a decisão tomada pelo projeto.

1. Fixe briefing, revisão, proporção, materiais e destino. Identifique a promessa e a ação que a comprova. Escolha a linguagem pela prova disponível.
2. Escreva cada trecho como objeto, estado inicial, evento, estado final e intervalo. Declare o que a imagem ou o áudio precisa mostrar e um contraexemplo. Registre de que ficha veio cada escolha e o nível de evidência.
3. Faça uma proposta editável com operações suportadas pela Clicko. Se uma operação ou material essencial estiver ausente, registre a lacuna. Na prova local, use os materiais fornecidos e mantenha o orçamento de API em zero.
4. Renderize a prévia. Confira emendas, ação, identidade, leitura em tamanho de celular e CTA. Examine os momentos importantes com áudio e sem áudio quando houver acesso. Separe execução técnica, interpretação editorial e compreensão por espectadores.
5. Registre problemas com intervalo e evidência. Autorize uma rodada localizada de correção no fluxo experimental. Preserve o original e confira a revisão de origem antes de aplicar.

Para revisar uma peça existente, comece pelo render e trace cada problema à operação ou ao material que o causou. Para avaliar uma técnica nova, leia o protocolo de prova do manual antes de comparar versões.


## Editar no motor nativo

Abra Motion Design no EffectCraft, a montagem de vídeo no FilmCraft e imagens no PhotoCraft. Converta projetos antigos apenas quando necessário e confira os avisos da conversão. A direção pela API direta da Anthropic consulta o catálogo do motor, aplica comandos numa cópia e inspeciona quadros antes de salvar. Consulte [a auditoria do fluxo nativo](../../../docs/plans/2026-11-10-clicko-craft-edicao-nativa.md) para os recursos e limites atuais.

Ao trabalhar a partir de referência, fixe o trecho observado, o que se viu e ouviu, e os estados visuais que precisam ser reproduzidos. Compare o render no tamanho de celular. Registre as operações executadas, o material de origem e qualquer diferença. Um quadro estático não comprova continuidade de movimento ou sincronismo com o som.

Se uma borda em movimento passa pela área de leitura, consulte a ficha `orbita-reveal-protect-title`. Veja o pico da passagem e a entrada do texto no render da mesma revisão. Confira família e peso com `inspect_motion_fonts` quando disponível. Confira o ganho do áudio exportado quando o fade fizer parte da direção. Use [o exercício da ÓRBITA](../../../docs/plans/2026-11-12-clicko-exercicio-editavel-orbita.md) para testar a regra em outra linguagem de revelação.
