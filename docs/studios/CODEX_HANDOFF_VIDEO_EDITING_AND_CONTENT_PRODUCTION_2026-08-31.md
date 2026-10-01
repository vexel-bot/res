# Handoff Codex — edição de vídeo e produção de conteúdo

Use o repositório `C:\Users\edugu\Downloads\res` (não o diretório OneDrive). O
worktree está propositalmente sujo e contém a implementação incremental dos
Studios; preserve tudo, não faça reset, commit, push, deploy ou alteração na VPS.

## Direção atual

Focar exclusivamente em edição de vídeo e produção de conteúdo UGC. Por enquanto:

- sem voz, TTS, clonagem, Voicebox ou música;
- vídeos UGC usam sons naturais/foley com direitos e legenda editorial queimada;
- fluxo precisa ser mais ação que informação, mobile-first, sem emojis;
- testar criação de imagem, carrossel e vídeo, mas priorizar o vertical de vídeo;
- nenhum botão decorativo e nenhum estado que prometa capacidade inexistente.

## O que já funciona

- Studio canônico responsivo com route/action contracts e audit estrito;
- Video Studio com timeline, cortes, legendas editoriais e render FFmpeg;
- múltiplos sons naturais com offset, duração, ganho, fade, mute/restore e undo;
- preview Web Audio, render MP4 e inspeção de PCM;
- Review Room fixa MP4/hash e exige escuta humana integral;
- revisão server-owned de direitos por asset/hash;
- fronteira provider-neutral de análise fala/música e admissão de publicação;
- cadeia de qualificação assinada, mas sem detector real promovido.

Documentos principais:

- `docs/studios/STUDIOS_CX_SCREEN_FLOW_AND_INTERACTION_MASTER_PLAN_2026-08-28.md`
- `docs/studios/evidence/VIDEO_NATURAL_SOUND_VERTICAL_AUDIT_2026-08-31.md`
- `docs/studios/evidence/VIDEO_NATURAL_SOUND_LIVE_PREVIEW_AUDIT_2026-08-31.md`
- `docs/studios/evidence/VIDEO_NATURAL_SOUND_HUMAN_REVIEW_AUDIT_2026-08-31.md`
- `docs/studios/evidence/VIDEO_ACOUSTIC_DETECTOR_QUALIFICATION_CHAIN_AUDIT_2026-08-31.md`
- `benchmarks/studios/ugc/ugc-no-voice-natural-caption-casebook.v1.json`

## Estado dos testes

- backend focado mais recente: 28/28;
- TypeScript e build: passaram;
- audit CX: 443 controles executáveis, zero órfãos/conflitos;
- contratos: 6/6;
- último E2E completo do vídeo/review: passou com mídia real e mobile 390 × 844.

## Próxima ordem recomendada

1. fechar editor: seleção multicamadas, trim/split, ripple, reorder, snap, zoom e
   undo/redo persistente;
2. criar painel de propriedades claro para vídeo, texto, legenda e som;
3. implementar biblioteca de templates UGC e montagem por cenas;
4. executar os 10 casos do casebook com 6 avatares stock, fundos e copies, sem voz;
5. criar rubrica de avaliação: clareza do hook, coerência visual, ritmo, legenda,
   naturalidade do foley, legibilidade, CTA e integridade técnica;
6. corrigir o produto a partir dos resultados e só então considerar detector real.

Não declarar os 10 anúncios como produzidos até existirem arquivos finais,
evidência de direitos, revisão humana e resultados da rubrica. Estado atual: 0/10.

## Prompt copiável

> Continue a implementação no repositório `C:\Users\edugu\Downloads\res` usando
> `docs/studios/CODEX_HANDOFF_VIDEO_EDITING_AND_CONTENT_PRODUCTION_2026-08-31.md`
> como contexto. Preserve o worktree sujo. Foque em edição de vídeo e produção de
> conteúdo UGC com sons naturais e legendas editoriais, sem voz, TTS, clonagem ou
> música. Primeiro audite o editor atual e transforme a próxima lacuna de maior
> impacto em um corte vertical completo com persistência, responsividade,
> acessibilidade, telemetria, testes e rollback. Não altere VPS, Figma ou providers
> reais e não invente resultados dos 10 anúncios.
