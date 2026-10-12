# Worker gráfico experimental do res

Este worker recebe somente `res.motion-canvas-composition.v1`. Ele carrega componentes TypeScript registrados; prompts e planos não podem fornecer código executável. Arquivos são vinculados por ID e checksum no manifesto. FFmpeg codifica o vídeo visual, enquanto a mixagem e a avaliação final continuam no backend do res.

Preparação local:

```powershell
npm ci
npx playwright install chromium
npm run check
```

Render de diagnóstico:

```powershell
node render.mjs C:\caminho\manifest.json C:\caminho\saida
```

O diretório de saída contém frames PNG, `visual.mp4` e `receipt.json`. O provedor contextual é opt-in (`motion_canvas_enabled` e `studio_editorial_motion_provider=motion-canvas.contextual-v1`) e permanece experimental. Uma operação sem implementação causa impedimento; ela não é convertida silenciosamente em fade ou cartão.

Os testes relevantes são `backend/tests/test_motion_canvas_render.py`, `backend/tests/test_motion_canvas_cases.py` e `backend/tests/test_motion_canvas_projection.py`. A qualificação visual está documentada em `docs/studios/MOTION_ENGINE_QUALIFICATION_2026-09-23.md`.
