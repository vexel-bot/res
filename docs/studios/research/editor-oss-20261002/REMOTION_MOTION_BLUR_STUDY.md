# Estudo do mecanismo de motion blur do Remotion

03/10/2026, `Downloads/res`. O pacote instalado e fixado é `@remotion/motion-blur` 4.0.527, sob licença MIT. A fonte local de `CameraMotionBlur` foi lida diretamente em `workers/remotion-benchmark/node_modules`; o estudo não baixa outro repositório nem copia o pacote para o produto.

O componente open source cria um grupo isolado, duplica os filhos em amostras temporais com `Freeze`, usa `mix-blend-mode: plus-lighter` e pondera cada amostra com `filter: opacity(1/N)`. O `TemporalExposure` nativo do res conserva esse mecanismo, mas adiciona uma política tipada: shutter centralizado e limitado ao intervalo, tempos efetivos por subárvore, pais externos no frame central e redução somente quando as entradas de desenho são idênticas.

Essa comparação confirma que a integração do mecanismo estudado está fiel ao runtime pinado. Os ensaios da mesma fonte mostram que a combinação com matte mundial e pai externo animado ainda produz divergências de pixels na acumulação; por isso a admissão continua `motion_recipe_temporal_matte_moving_external_ancestor_pending`. Não promover a capacidade apenas por reproduzir a implementação do pacote.

O recibo [remotion-motion-blur-study.json](remotion-motion-blur-study.json) congela versão, licença, caminhos e SHA-256 dos dois arquivos. A verificação pode ser refeita com `python scripts/validation/editor-remotion-motion-blur-study.py`.
