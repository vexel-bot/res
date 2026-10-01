# Demonstrações visuais verificáveis — implementação atualizada em 2026-09-22

## Estado da entrega

O caminho V2 separa execução, ação semântica e compreensão humana. A fixture
controlada mais recente passou pelos gates técnicos e semânticos fortalecidos,
mas permanece `awaiting_human_review` e `commerciallyQualified: false`. Ela não
é evidência de direção criativa autônoma.

O v31 continua preservado como baseline operacional reprovado. Seu recibo
histórico não foi reescrito.

## Correções implementadas

- A qualificação agrega avaliação técnica, execução, semântica, achados visuais,
  cobertura, gate observado e revisão humana. Um resultado semântico isolado
  não pode mais encerrar a qualificação.
- Adaptações canônicas deixam de escalar o cartaz inteiro de forma diferente em
  X e Y. Mídia, título e identidade recebem translação e escala uniforme próprias.
- Rótulos técnicos de formato não são inseridos nas adaptações canônicas. O
  conteúdo deve tornar a mudança reconhecível.
- Textos filhos de grupos são medidos e limitados no sistema de coordenadas do
  grupo, em vez de serem reposicionados como se ocupassem o canvas inteiro.
- Estados canônicos são reconhecidos pelo preflight visual como continuidade
  válida quando suas partes obrigatórias estão corretamente vinculadas.
- A verificação de formato exige ordem temporal, proporções observadas no DOM do
  render e pixels discriminativos para cada parte obrigatória. Um vídeo uniforme
  com geometria simulada é rejeitado.
- A similaridade visual da mídia principal é registrada entre estados. Ela é
  uma evidência limitada e não substitui compreensão humana.
- Eventos audíveis exigem um efeito materializado e vinculado ao intervalo,
  além de sinal efetivamente decodificado na mixagem.
- Inserção e passagem em feed exigem conteúdo canônico renderizado, componente
  de interface compatível e trajetória vertical observada. Fade isolado não
  comprova essas ações.

## Fixture controlada v2

O script `backend/scripts/qualify_semantic_demonstration.py` recompilou e
renderizou uma nova fixture por HyperFrames e FFmpeg.

- vídeo: `output/semantic-demonstration-2026-09-22-v2/canonical-format-engineering-fixture.mp4`
- componente: `res.editorial-components.v2.18`
- compilador: `res.scene-compiler.v2.12`
- runtime: `res.editorial-runtime.v2.5`
- auditoria: `studio.visual-audit-policy.v4`
- frames: 240 a 30 fps
- duração: 8 segundos
- checksum do MP4: `47b931042d6e57239882ee886395154315e28c289c35d1612f8642ef2cb508c2`
- checksum da direção: `c1f104fe42cd8779985e2a4aaa157fe36adac5b7886a9c7658a5cbc85905aabf`
- checksum da composição: `8ee6c3b9c79bf633efa8c58cf48426a3edb79b0b90f862a2ef454cf571cdd3f9`
- técnico: `passed`
- execução: `observed`
- semântica: `passed`
- resultado observado: `passed`
- visual/editorial automático: `unreviewed`
- revisão humana: `pending`
- estado agregado: `awaiting_human_review`

A auditoria observou a peça vertical no frame 58 e a peça quadrada no frame
200, com proporções renderizadas de aproximadamente 0,64 e 1,0. Imagem, título
e identidade apresentaram sinal de pixels nos dois estados. O efeito sonoro
vinculado também foi medido no intervalo declarado.

## Limites preservados

A fixture continua sendo um teste de engenharia manual, com ilustração simples,
uma única transformação e um efeito sonoro curto. Ela não comprova seleção
autônoma de conteúdo, aquisição de material, distribuição em feed, consequência
narrativa ou acabamento comercial. A inspeção por frames também não equivale a
uma revisão integral da experiência temporal.

O próximo piloto só poderá ser descrito como autônomo se partir de briefing,
identidade, duração e política de custo, sem cenas ou arquivos escolhidos pelo
Codex. A revisão humana continuará obrigatória para compreensão e qualidade.

Nenhuma API paga foi chamada nesta qualificação.
