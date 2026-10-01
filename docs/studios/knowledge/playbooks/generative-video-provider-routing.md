# Playbook — roteamento de geração de vídeo

## Objetivo

Usar APIs de vídeo como geradores de planos aprovados, e não como autores autônomos do vídeo inteiro. Roteiro, personagem, cenário, continuidade, edição e som continuam sob contratos próprios.

## Roteamento inicial

| Faixa | Provider | Uso | Regra financeira |
|---|---|---|---|
| `transport_smoke` | Hugging Face Inference Providers | provar autenticação, polling, download e QC com um plano descartável | somente crédito gratuito disponível; teto rígido de US$ 0,10 |
| `trial_draft` | Vertex AI / Veo 3.1 Lite | rascunhos dos goldens não biométricos | somente crédito promocional confirmado; sem fallback pago |
| `craft_revision` | Gemini Omni 1.1 Flash | editar iterativamente um plano selecionado | bloqueado até aprovação explícita de gasto |
| `final_candidate` | Veo 3.1 Fast ou Standard | plano final em que Lite não atinge o rubric | bloqueado até benchmark comparativo e aprovação de custo |

O Hugging Face oferece US$ 0,10 mensais a contas gratuitas para requisições roteadas e expõe text-to-video, incluindo modelos como Wan e HunyuanVideo. Esse valor serve para testar a fronteira técnica, não para avaliar uma fábrica audiovisual. Replicate pode permitir alguns usos gratuitos de modelos selecionados, mas exige billing depois de pouco uso. Créditos gratuitos do fal Sandbox não funcionam pela API; por isso nenhum deles é tratado como o trial principal.

## Preflight obrigatório

- `research_gate_open == true`;
- `storyboard_approval_id` presente;
- `animatic_approval_id` presente;
- `asset_rights_status == cleared` para todas as entradas;
- `provider_status == evaluation` ou `approved` e nunca `disabled`;
- autenticação presente sem registrar segredo;
- cota consultada;
- saldo promocional confirmado;
- custo estimado menor ou igual ao teto do run;
- localização e política de retenção registradas;
- referências biométricas ausentes no lote inicial.

## Estratégia de custo

1. Uma geração 720p, um resultado e a menor duração aceita.
2. Só repetir quando a crítica identificar uma variável modificável.
3. Promover no máximo um resultado por plano para resolução ou modelo superior.
4. Nunca gerar variações sem hipótese escrita.
5. Interromper o lote quando a taxa de aprovação ficar abaixo do limiar definido.

## Saída mínima por job

- provider, modelo, endpoint e versão;
- prompt original PT-BR e prompt efetivamente enviado;
- `GenerativeShotSpecV1` de origem;
- IDs das aprovações;
- parâmetros, seed quando disponível e negative constraints;
- custo estimado e observado;
- operação externa e timestamps;
- checksum, duração, resolução, FPS, codec e áudio;
- marcação de mídia sintética;
- avaliação objetiva, crítica criativa e decisão humana.

## Política de fallback

Falhas de autenticação, quota, crédito, licença, consentimento ou proveniência encerram o job. O sistema não troca silenciosamente de provider, não reduz salvaguardas e não inicia cobrança real.

