# Self-hosted local evaluation

Esta pasta contém somente manifests e instruções auditáveis. Os pesos e binários ficam em
`.candidate-build/model-assets/`, ignorado pelo Git.

## Estado material

- `Qwen/Qwen3-4B-GGUF` Q4_K_M: 4.022.468.096 parâmetros; download e SHA-256 verificados.
- llama.cpp b10675/Vulkan: runtime verificado; API local OpenAI-compatible funcional.
- Chatterbox Multilingual pt-BR: quatro assets, 3.206.662.605 bytes; download e SHA-256 verificados.
- Qwen3-VL, Qwen3-Omni e modelos de avatar: não baixados neste host por hardware/licença.

Nenhum item nesta pasta é provider de produção. Os manifests `llm_gpu`, `speech_gpu` e
`vision_gpu` continuam com `providers: []`.

## Qwen local

Iniciar em background:

```powershell
backend\scripts\start_local_qwen_server.ps1 -Detach
```

Verificar autenticação, catálogo e completion:

```powershell
python backend\scripts\verify_local_qwen_api.py
```

Contrato local:

- base URL: `http://127.0.0.1:18080/v1`;
- model: `clicko-qwen3-4b-q4-k-m`;
- chave: valor `AI_API_KEY` do `.env` local;
- sem chave: `401`;
- concorrência: uma sessão;
- exposição: loopback apenas.

Não copie o `.env` inteiro, a chave SSH da VPS ou qualquer segredo para outro chat. Outro chat
Codex no mesmo computador pode ler `AI_API_KEY` do `.env` e usar o endpoint local sem que o valor
seja impresso. Pessoas externas ainda não possuem endpoint autorizado: isso exige HTTPS, rate
limit, rotação/revogação, tenancy e um worker em infraestrutura acessível.

O launcher recusa bind fora de loopback sem `-AllowNetworkExposure`. Esse switch é somente uma
trava explícita, não uma aprovação de segurança para exposição pública.

## Chatterbox pt-BR

Os assets estão prontos para serem montados read-only no sidecar. O preflight real encontrou CUDA
e o layout correto, mas a RTX 2050 oferece 4.095 MiB, abaixo dos 16.384 MiB exigidos pelo manifest
`speech_gpu`. Por isso nenhum modelo foi carregado, nenhuma voz foi clonada e nenhum dado
biométrico foi processado. O próximo teste precisa de GPU externa elegível e corpus privado com
consentimento ativo.

## VPS

A VPS Oracle permanece control plane. Ela não recebeu pesos, containers ou alterações nesta etapa.
Seu hardware documentado (2 vCPU, menos de 1 GiB de RAM, sem GPU) não é alvo de inferência.
