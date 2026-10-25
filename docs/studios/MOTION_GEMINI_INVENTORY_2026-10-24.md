# Motion Gemini experimental — inventário anterior à implementação

Pedido `09a1c7fc-7c26-4965-82e7-95e5847410e6`, 24/10/2026.

| Área existente | Reutilização / limite |
|---|---|
| `LocalProductionStudio` | Mesmo briefing, projetos, duração/formato, revisão, camadas, histórico e export |
| `agent_orchestrator` / `AudiovisualAgent` | Mesmo job `agent_plan`, idempotência, revisão humana, validação e aplicação |
| `AgentOutput`, `LocalLayerStyle`, `proposed_document` | JSON de operações fechado; locks, seleção, assets e renderer reais |
| `UniversalLLMPlanner` | Transporte nativo Gemini e normalização de tokens já disponíveis |
| `StudioLLMConnection` / `llm_connections` | Criptografia Fernet existente; credencial experimental privada por criador/workspace |
| Ponte Express/FastAPI e Modo DEV | Sessão autorizada, loopback, claim assinado e feature flag desligada por padrão |
| FFmpeg/Pillow, documentos/versões | Execução local e projeto editável, não geração de vídeo pelo Gemini textual |
| Política financeira | Orçamento zero; nenhuma liberação global de outbound, retry ou fallback pago |

A conexão universal atual permite remoto metered ou Ollama local. Não se deve
marcar Gemini remoto como `local_free` nem alterar a configuração conversacional
da KLIC. O experimento terá credencial própria, invisível às conexões genéricas,
e só ingressará no mesmo orquestrador mediante admissão DEV explícita.

`models.list` informa modelos/métodos/limites de contexto, não o faturamento da
conta ou a quota restante. A inferência ficará fail-closed sem comprovação
operacional do Free Tier, quota e autorização vinculadas à chave/modelo/usuário.
Nenhuma chave real foi fornecida nesta tarefa; comparação real depende disso.
