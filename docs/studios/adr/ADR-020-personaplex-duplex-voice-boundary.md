# ADR-020 — PersonaPlex é referência full-duplex, não voz de anúncio

**Status:** checkpoint rejeitado pela política atual; padrões arquiteturais referenciados  
**Data:** 27/08/2026

## Contexto

PersonaPlex combina fala bidirecional contínua, interrupções, prompt textual de papel e condicionamento de voz. O código do commit `3428dfd95309a7f3c84fd93259ded0f810d1ff91` é MIT, mas o modelo `fdaf4090a61cb315c138a1faee287ffd6c716309` usa a licença customizada NVIDIA Open Model, exige aceite no Hugging Face, é inglês-only e lista A100/H100.

O servidor upstream é apropriado para demo/pesquisa, não para a fronteira SaaS Clicko: compartilha estado e serializa sessões, recebe voice prompt por query/path, usa `torch.load` para `.pt`, baixa artefatos em runtime, registra prompts e roda como root no Dockerfile.

## Decisão

- Não baixar pesos, aceitar licença, construir imagem, registrar provider ou expor o servidor.
- Não encaixar PersonaPlex em `SpeechSynthesisProvider` ou `VoiceCloneProvider`; anúncios renderizados continuam na lane Chatterbox/Kokoro/OpenVoice.
- Preservar apenas os padrões de produto: protocolo full-duplex, eventos de interrupção/backchannel, prompts de voz e papel separados e replay offline determinístico.
- Se surgir um caso validado de conversa ao vivo, criar `DuplexConversationProvider` separado e pesquisar primeiro alternativa permissiva com PT-BR.
- Uma futura reconsideração do PersonaPlex exige mudança explícita da política open-source-only e parecer jurídico/segurança; nunca ocorre por upgrade automático.

## Alternativas consideradas

- **Usar PersonaPlex como TTS de copy:** rejeitada; modelo conversacional inglês e output condicionado à entrada contínua.
- **Expor o servidor upstream em GPU:** rejeitada; ausência de isolamento, supply-chain hermética, concorrência e governança biométrica.
- **Aceitar licença por ser comercial:** rejeitada; “uso comercial” não satisfaz a política mais restritiva de licença open-source.
- **Ignorar completamente:** rejeitada; taxonomia e métricas full-duplex agregam ao desenho futuro sem usar pesos/código no runtime.

## Consequências

- A roadmap de voz PT-BR não é desviada por um modelo inadequado.
- Nenhuma obrigação/licença condicionada é aceita em nome do usuário.
- A Clicko ganha uma fronteira conceitual limpa entre voz renderizada e conversa ao vivo.
- Caso o produto full-duplex seja priorizado, haverá trabalho novo de contrato, threat model, sidecar, benchmark, hardware e UX.

## Gate de reabertura

1. necessidade de produto e owner explícitos;
2. política/licença aprovadas pela entidade;
3. alternativa permissiva PT-BR comparada primeiro;
4. sidecar novo com IDs opacos, safetensors/formatos seguros, no runtime download, logs redigidos e isolamento por workspace;
5. corpus consentido, benchmark cego e deletion receipt;
6. GPU externa; VPS continua control plane.

## Rollback

Não há runtime para remover. O inventory permanece `rejected`; retirar a referência não afeta documentos, jobs ou providers existentes.
