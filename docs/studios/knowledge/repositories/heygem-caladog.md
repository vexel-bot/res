# Auditoria — heygem-caladog

**Status:** `deep_static_review_complete_runtime_blocked`  
**Decisão provisória:** `reference-only` para código/containers; `adapt` somente para o contrato visual-only  
**Commit:** `a0053f7cd6440203d76737ac2920db8b293fb3f6`  
**Origem:** https://github.com/Caladog/HeyGem.git  
**Licença detectada:** `OTHER` em `LICENSE`

## Capacidade

authorized avatar benchmark candidate.

- Manifests: package.json
- Linguagens amostradas: JavaScript
- O cliente cria um registro de avatar a partir de um vídeo-base; ele não produz pesos faciais independentes.
- `addModel` copia o vídeo, extrai áudio e chama treinamento de voz. Esse caminho não será usado pela Clicko.
- A síntese visual chama `/easy/submit` com `video_url` e `audio_url` e consulta `/easy/query`.
- Requisitos da própria interface: vídeo com pelo menos 8 segundos, uma pessoa, rosto visível, 720p ou superior e MP4/MOV.
- Sinais estáticos: `{"gpu_signal": true, "container_recipe": true, "test_directory": false, "pt_br_signal": false}`
- Hardware observado: RTX 2050, 4 GB de VRAM. O README recomenda RTX 4070/32 GB RAM e a execução local depende de NVIDIA/Docker.
- PT-BR: o cliente não lista português entre os oito idiomas do script; o modo Clicko usará áudio PT-BR local pré-gerado.
- Determinismo: `unknown`
- Observabilidade: partial: git provenance and manifests inventoried

## Integração proposta

Manter aplicação e containers fora do domínio. Reimplementar somente um adapter visual que recebe vídeo-base e áudio local, sem executar extração ou treinamento de voz.

Tipos do repositório não podem atravessar worker/adapter para domínio, banco ou API. Somente contratos Clicko versionados são persistidos.

## Riscos

- o backend/modelo principal está na imagem externa `guiji2025/heygem.ai`, não neste repositório;
- a licença comunitária exige autorização adicional acima de 1.000 MAU e atribuição `Built with Silicon Intelligence`;
- pesos, datasets e cadeia do container não estão auditados;
- Fish Speech exige tratamento de licença separado e ficará fora do fluxo;
- identidade real requer consentimento, benchmark privado, revogação e exclusão;
- 4 GB de VRAM não satisfazem o envelope recomendado.

## Benchmark mínimo

license + dependency preflight, fixed fixture, resource envelope, output quality, repeatability, failure observability and PT-BR where relevant.

## Revisão necessária

- [x] confirmar a licença do código cliente e o limiar comercial de 1.000 MAU;
- [x] mapear o fluxo real de vídeo-base, áudio e polling;
- [ ] obter SBOM/licenças do container, pesos, datasets e exemplos;
- [ ] medir inputs, outputs, hardware, tempo e memória em GPU compatível;
- [ ] executar fixture reproduzível sem mídia pessoal;
- [ ] avaliar segurança e cadeia de suprimentos;
- [ ] revisar suporte PT-BR;
- [ ] aprovar ou substituir a decisão provisória.
