# Café Aurora — piloto híbrido no res

As opções atuais são `animatic-g.mp4` (ritmo mais pausado) e `animatic-h.mp4` (ritmo mais rápido). Cada uma tem 15 s, 720×1280, 30 fps, H.264/AAC. Foram criadas por plano contextual v2, aplicadas a um `CreativeDocument` e renderizadas pelo provedor experimental `remotion.contextual-v2`, com finalização de áudio pelo FFmpeg. A seleção humana e a exportação final seguem pendentes.

O roteiro efetivamente executado mantém filmagem em movimento nos primeiros oito segundos: grãos e xícara, preparo no filtro e café servido. A partir de 8 s, o mesmo take de servir continua atrás da composição da embalagem; entre a revelação e a chamada final, a posição do produto é preservada. O som usa música CC0 e dois efeitos CC0 vinculados às cenas. Não há locução nem áudio original duplicado.

Arquivos para revisão:

- `animatic-g.mp4`, `animatic-h.mp4`: as duas opções com som.
- `contact-g.jpg`, `contact-h.jpg`: quadros de 0,5 s a 14,5 s.
- `reference-g-authored.json`, `reference-h-authored.json`: direção executável e intervenções manuais declaradas.
- `reference-g-plan.json`, `reference-h-plan.json`: planos aceitos pela API.
- `reference-g-document.json`, `reference-h-document.json`: composições persistidas antes do render.
- `reference-g-render.json`, `reference-h-render.json`: recibos do render e checksums.
- `cost-receipts.json`, `audio-provenance.json`, `beans-discovery.json`, `brew-discovery.json`, `pour-discovery.json`: custo e origem dos materiais.
- `pilot-evaluation.json`: avaliação técnica, limites e estado da revisão humana.
- `component-reuse-three-briefs.json`: três briefs com textos e materiais diferentes, todos com plano nativo pronto sem alteração dos componentes.

O fluxo do planejador também foi exercitado com briefing e acervo real (`planner-brief.json`, `planner-result.json`). A resposta do modelo falhou na validação do contrato: vinculou IDs de assets a necessidades de material inexistentes e, numa verificação local posterior, apresentou conflitos de composição e múltiplos elementos hero. Por isso, os animatics foram dirigidos pelo agente e **não demonstram planejamento totalmente autônomo**. A tentativa de gerar filmagem pelo Gemini Veo e a de gerar música pelo Lyria receberam HTTP 429; nenhuma gerou arquivo utilizável e não houve repetição paga automática. O custo medido do planejador foi US$ 0,092602. Contando conservadoramente as reservas de operações sem custo medido, o total é US$ 0,532602, abaixo do teto de US$ 10.

A imagem de produto é um asset real do acervo local, mas tem baixa resolução e sua licença comercial ainda precisa de qualificação. A avaliação humana mínima de 4/5 em ritmo, continuidade, clareza e acabamento ainda não foi registrada. O funcionamento técnico passou; a qualidade visual e a elegibilidade comercial permanecem pendentes.

Para reproduzir no ambiente local isolado, com `PYTHONPATH=backend` a partir da raiz do repositório: `python backend/scripts/run_native_hybrid_pilot.py render g`, `python backend/scripts/run_native_hybrid_pilot.py render h`, `python backend/scripts/run_native_hybrid_pilot.py receipts` e `python backend/scripts/evaluate_native_hybrid_pilot.py`. As chamadas pagas não são repetidas por esses comandos. O banco e storage do piloto ficam apenas nesta pasta; `.local-session.json` é credencial local e não deve ser compartilhado.

Licenças consultadas: [Pexels](https://www.pexels.com/license/), [FreePD CC0](https://github.com/0lhi/FreePD) e [SFXMint CC0](https://sfxmint.com/api/docs).
