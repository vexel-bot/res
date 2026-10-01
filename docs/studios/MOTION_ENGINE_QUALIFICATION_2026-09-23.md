# Qualificação local dos motores de motion — 23/09/2026

## Decisão atual

Motion Canvas está **integrado experimentalmente** ao render contextual do res, mantendo o documento, o MotionGraph, o armazenamento, os jobs e a mixagem FFmpeg. O padrão continua HyperFrames. Remotion foi testado somente como concorrente local; não foi registrado como provedor de produção. Nenhum motor recebeu aprovação estética ou comercial nesta rodada.

A comparação com o mesmo documento e grafo gerou uma composição muito parecida em HyperFrames e Motion Canvas. Motion Canvas foi mais rápido nesse caso simples (aproximadamente 4,4 s contra 13,3 s de render gráfico), mas esse tempo não prevê a velocidade de cenas mais complexas. Nos dois casos difíceis testados, Remotion também gerou imagens visualmente próximas às de Motion Canvas. Trocar o motor, por si só, não resolveu a direção de arte nem a coreografia do piloto reprovado.

## Evidência produzida

Os arquivos em `benchmarks/studios/motion-canvas/outputs/2026-09-23/` são **fixtures de engenharia**, produzidas com insumos sintéticos ou fonte local pelo mesmo contrato de documento e grafo. Não são vídeos planejados autonomamente a partir de briefing e não são uma demonstração de qualidade comercial.

| Caso | O que foi observado nos frames |
|---|---|
| Tipografia com acentos | Fonte carregada; palavras completas reveladas progressivamente |
| Câmera e grupos | O filho cresceu com a transformação do grupo |
| Recorte e oclusão | PNG com alfa ficou atrás da camada frontal |
| Caminho vinculado | A linha foi revelada entre origem e destino |
| Anotação de produto | O conector apareceu entre objeto e rótulo |
| Continuidade | Uma instância se deslocou sem ser substituída por outra |
| Proporção de imagem | `contain` preservou a imagem inteira; `cover` preencheu o quadro por recorte, sem deformação |

Um teste adicional atravessou `ContextualPlanRequestV2 → lower_compositions → compile_scenes → MotionGraph → Motion Canvas → MP4` com uma peça canônica. A fotografia e a headline permaneceram visíveis nos dois estados e a largura observada do material mudou. Essa peça também é fixture de engenharia, não o piloto autônomo de Distribuição.

Os testes agora examinam pixels nos estados relevantes, em vez de aprovar apenas a existência do MP4. O teste da imagem encontrou uma falha concreta: a primeira projeção esticava qualquer imagem ao tamanho da caixa. O adaptador agora verifica as dimensões do arquivo e aplica `contain`, `cover` ou `fill` explicitamente. Operações fora do subconjunto suportado são impedimentos, não conversões silenciosas.

## Limites do adaptador experimental

O worker aceita manifesto de dados validado, arquivos por checksum, camada de texto, forma, imagem, grupos, caminhos, keyframes, blur e corte/dissolve. A LLM não entrega código TypeScript. A prévia e os frames de exportação usam o mesmo runtime gráfico. A API contextual foi conectada por configuração, desligada por padrão.

Máscara avançada, vídeo dentro do grafo, spans tipográficos, blend modes, sombra e wipe ainda não são executáveis neste adaptador. Esses usos bloqueiam a compilação. Os testes de imagens e texto são estruturais; não demonstram legibilidade em todos os tamanhos, pertinência editorial, ritmo, som ou compreensão humana. A auditoria visual existente precisa continuar sendo aplicada ao MP4 final.

O benchmark Remotion usa as mesmas manifestações de recorte e continuidade. A primeira renderização levou cerca de 55,6 s, incluindo preparação do bundle; a segunda, com cache, cerca de 6,2 s. Não é uma comparação robusta de desempenho. A licença de Remotion permite avaliação, mas uso comercial por um produto automatizado exige decisão e verificação específicas antes da integração. Ver [licença oficial](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md) e [preços oficiais](https://www.remotion.dev/pricing).

## Próximo gate de qualidade

O resultado atual qualifica operações isoladas. O próximo teste precisa partir apenas de briefing, identidade e duração, produzir duas propostas **em movimento** pelo res, registrar a escolha visual e exportar a peça completa. É necessário medir continuidade, hierarquia, ritmo, legibilidade e som em reprodução normal, com notas humanas associadas ao checksum do MP4. Até isso ocorrer, Motion Canvas permanece experimental e nenhum piloto está visualmente aprovado.

O After Effects poderá servir de referência e, após hardware adequado, de candidato a worker separado. Sua instalação no computador não altera esta qualificação nem substitui o contrato de cenas do res.

## Replay de um plano produzido pelo diretor do res

Também renderizamos pelo Motion Canvas o plano `0a5a81c9-0761-48c9-8dea-360c41aff44d`, criado anteriormente pelo diretor do res para Distribuição. O replay leu o `draftDocument`, o MotionGraph e os oito arquivos do catálogo do piloto. O novo render não chamou LLM, não escolheu cenas ou materiais e não alterou o banco. Os checksums de plano, materiais e MP4 estão em `artifacts/validation/distribution-production-live/director-editorial-motion-v4-valid-schema-20260922/distribution-motion-canvas-replay-v4.receipt.json`.

O MP4 tem 11 segundos, 720×1280 e vídeo H.264 sem áudio. É um **teste de integração com uma direção já produzida pelo sistema**, não um novo piloto autônomo. A versão HyperFrames do mesmo plano tem áudio e aparência muito semelhante. O Motion Canvas inicialmente quebrou “Uma ideia nasce.” em duas linhas; ajustamos o texto à caixa com medição da fonte no runtime e registramos tamanho original (45 px) e efetivo (42,59 px). Ambos os motores ainda colocam o título sobre a base da lâmpada. Os ícones e textos posteriores continuam pequenos, e a progressão visual não ficou profissional.

## Recompilação com componente de sequência corrigido

A versão `distribution-motion-canvas-recompiled-v6.mp4` foi gerada pela ferramenta `backend/scripts/recompile_motion_canvas_plan.py`. Ela leu a direção armazenada e recompilou os elementos com `res.scene-compiler.v2.14` e `res.editorial-components.v2.20`, sem alterar o plano persistido, escolher novos assets ou chamar um modelo. O componente de sequência com caminho agora calcula uma mídia hero legível, distribui mídias de apoio e deriva a linha pelos centros observados. Textos externos de uma composição de evidência recebem uma faixa de leitura própria. A mudança aparece no vídeo: a cena de caminhos deixa de ser uma fileira de miniícones e o título da abertura deixa de ocupar a base da ilustração.

O resultado continua sendo um candidato técnico e **não uma aprovação estética**. A direção original ainda usa ícones procedurais e a última ressalva depende de texto; isso precisa ser resolvido por uma nova direção do sistema, não por outro replay.

O mesmo manifesto recompilado foi renderizado pelo runner Remotion em `distribution-remotion-recompiled-v6.mp4`. A imagem resultante é praticamente equivalente à do Motion Canvas porque ambos recebem a mesma composição corrigida. Isso confirma que a melhoria veio do componente de composição, e não de uma troca cosmética de motor.

O worker agora registra a geometria observada em 330 frames. A montagem contextual encaminha essas amostras à auditoria. O arquivo de auditoria do replay declara 18 frames solicitados e observados, mas `wholeVideoInspected: false`. Como o contrato histórico do plano não passa no verificador semântico atual, executamos somente uma avaliação técnica sob a política legada; ela **não certifica a ação semântica**. Ela também não detectou a interferência do ícone no texto. Esse caso permanece reprovado por inspeção visual e deve ser acrescentado aos casos negativos da avaliação, sem converter toda sobreposição intencional em erro.

## Remotion com o mesmo plano (comparação de 23/09/2026)

Após a preferência do usuário por experimentar os dois motores, o benchmark Remotion passou a aceitar a composição inteira do replay acima como **dados**: documento, grafo projetado, 32 camadas e oito materiais verificados por checksum. O novo runner `workers/remotion-benchmark/render-plan.mjs` recusa operações fora do subconjunto implementado e utiliza componentes React registrados em `src/plan.tsx`; não executa código recebido do planejador.

O arquivo `distribution-remotion-comparison.mp4` no diretório do piloto tem 11 s, 720×1280, 30 fps e não contém áudio. O recibo `distribution-remotion-comparison.receipt.json` vincula seu checksum ao plano e ao manifesto usados pelo Motion Canvas. O render levou aproximadamente 51,8 s **incluindo bundle**; isto não estabelece vantagem ou desvantagem de desempenho em produção. O TypeScript passou na verificação estática.

A inspeção do vídeo Remotion encontrou a mesma interferência entre headline e ilustração e as mesmas cenas posteriores pouco expressivas. O motor não recebeu direção ou materiais novos. Essa comparação demonstra que Remotion consegue executar o caso, mas não que ele melhore a qualidade estética do plano. Os dois devem continuar disponíveis como caminhos de qualificação; nenhum será promovido automaticamente por preferência ou por um único replay.

Remotion ainda não está registrado como provedor de jobs comerciais do res. O runner permanece de **avaliação local**, inclusive porque sua licença distingue indivíduos/empresas pequenas de organizações que exigem licença empresarial. Confirmar a elegibilidade do produto antes de habilitar uso comercial. [Licença oficial](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md)
