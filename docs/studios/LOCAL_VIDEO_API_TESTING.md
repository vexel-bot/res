# Testes locais da API de vídeo

**Estado em 28/08/2026:** credenciais locais emitidas, API autenticada e smoke de ingestão aprovado. Este procedimento não usa nem altera a VPS.

## Credenciais e funções

Os segredos ficam somente nos arquivos locais ignorados pelo Git:

- `.env`: `SECRET_KEY` para assinar JWTs da Clicko e `AI_API_KEY` para autenticar um futuro sidecar OpenAI-compatible;
- `.env.video-test`: usuário de laboratório, senha e token de acesso Clicko com um único workspace.

Essas credenciais não são intercambiáveis:

- o cliente da Clicko usa o JWT obtido por `/api/v1/auth/login`;
- o backend usa `AI_API_KEY` ao chamar `AI_BASE_URL`;
- FFmpeg/FFprobe e HyperFrames local não usam chave de modelo;
- uma API externa — Gemini, Runway ou outra — exige uma chave emitida pelo próprio fornecedor. Uma chave local não concede acesso externo.

`AI_BASE_URL` e `AI_MODEL` permanecem vazios. Assim, planejamento por IA falha fechado até existir sidecar revisado; os testes de mídia continuam funcionando de forma independente.

## Inicialização

No diretório `backend`:

```powershell
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Liveness e readiness:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health/live
Invoke-WebRequest http://127.0.0.1:8000/health/ready
```

## Smoke autenticado

Em outro terminal, ainda em `backend`:

```powershell
python -m scripts.smoke_video_api_eager `
  --credentials ..\.env.video-test `
  --output ..\benchmarks\studios\video\video-api-eager-smoke-2026-08-28.v1.json
```

O script:

1. valida ou renova o JWT pelo login oficial;
2. confirma que o usuário possui exatamente o workspace de laboratório esperado;
3. gera MP4 vertical sintético de dois segundos com áudio;
4. envia multipart `video/mp4` autenticado;
5. cria media ingest com idempotency key ligada ao asset;
6. executa FFprobe em modo embedded local;
7. exige job `succeeded`, ingest `ready`, um stream de vídeo e um de áudio;
8. grava somente evidência não secreta.

## Render e QC

O conjunto local reproduzível é:

```powershell
python -m pytest `
  tests/test_ffmpeg_ugc_video_render_provider.py `
  tests/test_video_render_job.py `
  tests/test_video_technical_quality.py `
  tests/test_media_ingest.py `
  tests/test_media_proxy.py `
  tests/test_media_waveform.py -q
```

Essa bateria executa FFmpeg/FFprobe reais e cobre ingestão, proxy, waveform, render, lineage, isolamento de workspace e QC. Ela não prova avatar, clone de rosto/voz nem geração por modelo externo.

## Segurança e rotação

- Nunca copiar `.env` ou `.env.video-test` para documentação, issue, commit ou log.
- O token de laboratório expira; o smoke o renova por login quando necessário.
- Para rotacionar `SECRET_KEY`, todos os JWTs atuais serão invalidados.
- Para rotacionar `AI_API_KEY`, atualizar o sidecar e o backend conjuntamente.
- Produção deve usar secret manager e PostgreSQL; estes arquivos são exclusivamente locais.

