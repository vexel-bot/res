# Auditoria — Google Generative Video APIs

Data da revisão: 2026-09-01

## Decisão

`adapt`, inicialmente desabilitado e limitado a benchmark não biométrico.

O candidato primário para o primeiro lote é o Veo 3.1 Lite no Vertex AI, somente se a conta for elegível ao crédito promocional e obtiver cota para o modelo. O Gemini Omni 1.1 Flash fica como candidato preferencial de longo prazo para geração e edição conversacional, mas não satisfaz sozinho o requisito de teste gratuito por API.

## Capacidades verificadas

### Gemini Omni 1.1 Flash

- modelo estável: `gemini-omni-1.1-flash`;
- texto e imagens para vídeo;
- edição conversacional por interação anterior;
- extensão de vídeo;
- interpolação entre primeiro e último frame;
- saída de 3 a 10 segundos, 24 FPS, de 360p a 4K;
- áudio nativo e SynthID;
- API disponível somente na camada paga;
- inglês é o idioma plenamente avaliado; PT-BR precisa de benchmark próprio.

### Veo 3.1 Lite

- modelo: `veo-3.1-lite-generate-001`;
- texto ou imagem para vídeo;
- primeiro e último frame, extensão e áudio nativo;
- 4, 6 ou 8 segundos;
- 9:16 e 16:9;
- 720p e 1080p, 24 FPS;
- região documentada: `us-central1`;
- oferta em preview e sujeita a cota fixa;
- prompts em inglês; o sistema traduzirá uma especificação PT-BR aprovada sem alterar sua intenção.

## Teste gratuito

O Gemini Developer API não oferece camada gratuita para geração de vídeo. Novos clientes do Google Cloud podem receber US$ 300 por 90 dias, sem cobrança automática durante o trial, mas o acesso a produtos pode ser limitado. Por isso o sistema nunca tratará o crédito como garantido: elegibilidade da conta, disponibilidade regional e cota do Veo precisam ser confirmadas antes de enviar qualquer job.

## Integração proposta

1. O conselho criativo produz `GenerativeShotSpecV1`.
2. Storyboard e animatic recebem aprovação humana.
3. O estimador calcula custo máximo por plano.
4. O adapter traduz a especificação para inglês e preserva o original em PT-BR.
5. O provider recebe somente os assets autorizados daquele plano.
6. O resultado é baixado para armazenamento controlado; URL temporária externa não vira a fonte canônica.
7. `ffprobe`, visão computacional e revisão humana comparam render, storyboard e intenção.
8. Uma reprovação retorna ao roteiro, direção, prompt ou provider responsável, sem apagar versões anteriores.

## Gatilhos de bloqueio

- gate R1 fechado;
- storyboard ou animatic sem aprovação;
- referência humana sem consentimento específico;
- asset sem direitos verificados;
- ausência de projeto, autenticação, cota ou crédito confirmado;
- custo estimado acima do teto do run;
- tentativa de fallback para provider pago sem autorização;
- modelo, região ou preço divergentes do registro auditado;
- ausência de disclosure e lineage do conteúdo sintético.

## Fontes primárias

- https://ai.google.dev/gemini-api/docs/video
- https://ai.google.dev/gemini-api/docs/omni
- https://ai.google.dev/gemini-api/docs/models/gemini-omni-flash
- https://ai.google.dev/gemini-api/docs/pricing
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/veo/3-1-generate
- https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing
- https://docs.cloud.google.com/free/docs/free-cloud-features

## Limitações e riscos

- crédito promocional não equivale a free tier permanente;
- cota fixa pode impedir o uso mesmo com crédito disponível;
- resultados precisam de validação de consistência entre planos;
- áudio gerado não substitui desenho de som, mixagem ou voz aprovada;
- filtros de segurança e restrições de pessoas reconhecíveis podem bloquear referências;
- endpoints e preços mudam; o preflight deve falhar fechado quando o registro estiver desatualizado.

