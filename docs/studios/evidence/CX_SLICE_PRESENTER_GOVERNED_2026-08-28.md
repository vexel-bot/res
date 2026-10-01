# Evidência — slice CX Presenter governado — 2026-08-28

## Resultado

O fluxo `Editorial → Presenter → Identity Library → Presenter → Video Studio` deixou de depender de um payload genérico para produção autenticada. Identidade, voz, consentimento, versões e jobs são entidades reais; a demonstração guest continua explicitamente local e não publicável. Nenhum provider biométrico é promovido pelo frontend ou registrado por padrão.

## Identity Library e captura

- rota canônica `/library/identities`, Screen Contract e Action Contracts próprios;
- seis slots stock pré-selecionados, 3 mulheres e 3 homens, tratados como candidatos de catálogo, não pessoas ativadas;
- matrícula privada recebe vídeo de rosto/consentimento e áudio de voz em inputs separados;
- upload aceita MP4 e WAV/MP3/FLAC por allowlist e valida assinatura do conteúdo;
- grant registra `identity.enroll`, `avatar.generate`, `voice.enroll` e `voice.clone`, finalidade e expiração;
- perfis e versões de identidade e voz nascem `draft`; nenhuma aparência ou upload ativa uma cápsula;
- revogação real bloqueia usos futuros e é refletida na UI.

## Fronteira `avatar_video`

- contrato OpenAPI tipado para request, encode result, job e artefato;
- provider biométrico vive em `AVATAR_VIDEO_PROVIDERS`, separado do registry genérico;
- admissão exige documento, versões ativas e vinculadas, grant vivo, escopos, provider/modelo aprovados, licença comercial, benchmark aprovado e worker anunciado;
- execução repete os gates, protegendo chamadas diretas/CLI e revogações ocorridas depois da fila;
- samples são resolvidos no workspace, materializados por ObjectStorage e verificados por SHA-256;
- saída aceita somente MP4 ligado ao provider/versão/dimensões/FPS/checksum e disclosure sintético;
- artefato privado persiste `identityVersionId`, `voiceVersionId`, `consentGrantId`, digest do script, `reviewRequired=true` e evento de domínio;
- o Presenter recupera/polleia o job observável e só oferece handoff ao Video Studio após `succeeded`; o Video Studio adota o asset existente por ingest, sem duplicar upload nem alterar o original.

## Estados e controles honestos

- captura autenticada sempre abre o fluxo governado; readiness não grava uma captura fictícia;
- sem provider ou direitos o botão permanece explicado e desabilitado;
- job mostra fila, progresso, falha e sucesso em região viva;
- demonstração local não cria job nem artefato publicável;
- a produção continua indisponível enquanto o registry biométrico estiver vazio.

## Evidência executável

- `npm run lint` — aprovado após os contratos e handoff.
- `npm run test:cx-contracts` — 6/6, incluindo `SCREEN-PRESENTER`, `SCREEN-IDENTITY-LIBRARY` e ações governadas.
- `npm run audit:cx` — 44 registros, 59 URLs conhecidas, zero órfãs e zero conflitos.
- `python -m pytest tests/test_avatar_video_job_boundary.py -q` — 3/3: campos obrigatórios, admissão, isolamento tenant, revogação e adapter com artefato privado.
- `python -m pytest tests/test_api.py::test_private_upload_enforces_access_type_and_size -q` — upload de áudio válido e spoof rejeitado.
- Playwright Presenter/Identity — guest, gate autenticado, matrícula separada, perfis draft e revogação aprovados.

## Limites deliberados

- não existe provider biométrico real promovido no registry; Ditto/EchoMimic continuam candidatos condicionais;
- o teste do adapter usa provider fake e prova apenas a fronteira, persistência e gates;
- avaliação/ativação humana já existe no backend, mas uma superfície operacional de review da cápsula ainda deve ser aprimorada;
- qualquer saída real ainda precisa atravessar edição, render/QC e review no Video Studio antes de publicação.
