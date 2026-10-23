# Origem da Face KLIC

- Repositório solicitado: https://github.com/vexel-bot/res
- Branch: `ai-studios-novo`
- Commit consultado: `68abe189c3cbd360b82044667d1f9dc95d99c006` — Add files via upload.
- Diretório: `ai-studios-novo/`.
- Cópia local auditada em 20/10/2026: `círculo-pontilhado-interativo/`. Os 17 arquivos da branch são idênticos byte a byte; a cópia local também preserva a imagem temporária de exportação em `.aistudio/`.

Auditoria reproduzível, sem modificar a referência: `node scripts/klic/audit-face-reference.mjs`. O comando compara os arquivos com o ref Git já obtido e executa os geradores local/integrado em contextos isolados com a mesma semente, cobrindo todos os atributos de 6.760 partículas, as 72 fitas e três raios. Consulte `docs/klic/LOCAL_REFERENCE_AUDIT_2026-10-20.md` para os resultados e limitações da integração.

`types.ts` e `sphereGenerator.ts` adaptam diretamente os tipos e a geometria originais. `faceSimulation.ts` adapta as equações de `src/components/ParticleSphereCanvas.tsx`: fitas harmônicas, rotação/inclinação, perspectiva, molas, repulsão vetorial e onda de interação. `voiceModulation.ts` preserva os parâmetros visuais de `src/utils/voiceAnalyzer.ts`, substituindo o proprietário de áudio e as cadências simuladas pelos sinais reais já publicados pela Clicko.

Adaptações de integração: coordenadas normalizadas para o espaço existente; delta de tempo e subpassos; transição suave de estados sem reiniciar fase; orçamento compacto; prefixos intercalados cobrindo as 72 fitas; composição transparente; tema existente; preferência por movimento reduzido; pausa fora da tela; limites de estabilidade e descarte. A física não usa aleatoriedade por quadro. O estado inicial usa uma semente estável para evitar mudanças de identidade entre pontos de montagem.

Não foram importados o aplicativo demonstrativo, seu CSS global, fonte externa, canvas fullscreen, bloqueio de rolagem, atalhos 1/2/3/Espaço/M, microfone singleton, cadência fictícia, bundler ou dependências. `motion` não é necessário. Não houve merge da branch de origem.
