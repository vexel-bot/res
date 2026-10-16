# Provedores e modelos para os Studios

O modelo planeja comandos para PhotoCraft, FilmCraft e EffectCraft. As mesmas
operações validadas executam a edição manual e a edição solicitada à IA. Este
cadastro não transforma automaticamente um modelo de texto em gerador de
imagem, voz ou vídeo; a geração de materiais mantém os seus contratos próprios.

O catálogo foi conferido na documentação oficial em 12/10/2026. São sugestões
de identificadores; permissões da conta, disponibilidade, custo e qualidade de
planejamento precisam ser conferidos no endpoint escolhido. O usuário adiou a
validação com um LLM real em 13/10/2026.

| Provedor | Sugestões registradas | Fonte oficial |
|---|---|---|
| OpenAI | GPT-6.1 Sol, GPT-6 Astra, GPT-6 Luna | [Modelos](https://developers.openai.com/api/docs/models) |
| Anthropic | Claude Sonnet 5.5, Opus 5.5, Haiku 5.5, Fable 5.1 | [Modelos](https://platform.claude.com/docs/en/models/overview) |
| Google | Gemini 3.8 Flash, Gemini 3.5 Flash-Lite | [Modelos](https://ai.google.dev/gemini-api/docs/models) |
| Mistral | Mistral Large 4, Mistral Small 2603 | [Modelos](https://docs.mistral.ai/models) |
| DeepSeek | DeepSeek Flash, DeepSeek V4 Pro | [API](https://api-docs.deepseek.com/) |
| xAI | Grok 4.7 | [Modelos](https://docs.x.ai/developers/models) |
| Cohere | Command A Plus 05-2026, Command A Reasoning 08-2025 | [Modelos](https://docs.cohere.com/docs/models) |
| Groq | GPT-OSS 120B, GPT-OSS 20B, Qwen3.8 27B | [Modelos](https://console.groq.com/docs/models) |
| Together AI | Qwen3.8, Kimi K3 | [Modelos serverless](https://docs.together.ai/docs/serverless/models) |
| Fireworks AI | Kimi K3, GLM 5.3 Flash | [API compatível](https://docs.fireworks.ai/getting-started/quickstart) |
| OpenRouter | Identificadores configurados pelo administrador | [Catálogo](https://openrouter.ai/docs/guides/overview/models) |
| Ollama | Qwen3 8B, GPT-OSS 20B | [API](https://docs.ollama.com/api/openai-compatibility) |
| Personalizado | Modelos do endpoint informado | Contrato JSON configurável |

São 13 presets e 25 sugestões de modelos, com alguns modelos disponíveis em
mais de um provedor. Avaliar modelos maiores para planejamento composto e
modelos menores para ajustes simples é uma hipótese de uso; não houve benchmark
de inferência nesta entrega.

## Configuração

1. Configure `STUDIO_LLM_CREDENTIAL_KEY` no ambiente privado do servidor, com
   pelo menos 32 caracteres aleatórios. Preserve essa chave em backup privado:
   trocar o valor sem migrar as credenciais impede a decifragem das conexões.
2. No Studio, abra **Direção com IA → Conexões de IA**. Um owner ou administrador
   pode registrar, atualizar ou desativar conexões do seu workspace.
3. Escolha o preset ou cadastre endpoint, protocolo e identificadores de modelo.
   A chave é enviada somente ao backend autenticado; o campo fica vazio quando
   a conexão é reaberta. O navegador guarda apenas a seleção do modelo.
4. Para APIs cobradas, informe teto de reserva e os maiores preços de entrada
   e saída entre os modelos cadastrados. Esses preços são informados pelo
   administrador, não consultados automaticamente. O ledger conserva reservas
   de pedidos com resultado desconhecido; confira também a cobrança no provedor.
5. Ative a conexão e selecione seu modelo. Servidores locais em loopback podem
   usar `local_free`. Nenhum download de pesos ou instalação de Ollama ocorre
   automaticamente.

## Protocolos e extensibilidade

Suportados diretamente: Chat Completions, Responses, Claude Messages, Gemini
generateContent, Cohere Chat v2, Ollama Chat e JSON HTTP personalizado. Os
presets registram URL base e autenticação adequada. A API aceita cabeçalhos
extras sem credenciais e caminho de requisição alternativo.

No protocolo personalizado, configure `requestPath`, `requestTemplate` e
`responseTextPath`, um JSON Pointer para o texto/objeto da resposta. Valores
inteiros `${model}`, `${prompt}`, `${system}`, `${max_tokens}`, `${context}` e
`${credential}` são substituídos antes do envio. Use `${credential}` para
segredos exigidos no corpo, sem gravar uma chave literal no template.

Exemplo de template sem segredo:

```json
{
  "model": "${model}",
  "prompt": "${prompt}",
  "max_tokens": "${max_tokens}",
  "api_key": "${credential}"
}
```

O protocolo genérico cobre APIs HTTP que possam ser descritas por esse contrato.
Serviços que exijam assinatura IAM/SigV4, OAuth com renovação, gRPC ou formatos
binários precisam de um gateway ou adaptador específico; não se declara suporte
nativo a todos os protocolos de transporte/auth existentes.

Não há streaming de tokens nem retries automáticos. Cada pedido tem uma
submissão auditada, saída limitada, erro sanitizado e revisão esperada do
documento. A interface reconcilia recibos após interrupções, bloqueando uma
nova edição enquanto o resultado anterior permanece desconhecido. Comandos
de shell, scripts, plugins, expressões e histórico não são entregues à IA.

## Evidência

Os sete formatos passaram por testes HTTP de serialização e normalização com
transporte simulado. Um endpoint HTTP local determinístico passou pelo backend
real, PhotoCraft real, persistência, pixel esperado, replay, reconciliação e
undo. A interface real passou pelo cadastro e remoção de credenciais cifradas.
Não houve chamada paga nem avaliação de modelo real. A validação de inferência
foi adiada pelo usuário; nenhum modelo do catálogo deve ser apresentado como
qualificado apenas por existir um preset.
