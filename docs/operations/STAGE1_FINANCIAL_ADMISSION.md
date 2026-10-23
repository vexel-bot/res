# Admissão financeira · Etapa 1

## Uma autoridade, duas integrações de serviço

Node KLIC/Gemini e Google Cloud TTS agora pedem admissão a
`/internal/finance/reserve` e `/internal/finance/<recibo>/start` no FastAPI Studios.
O banco e o lock transacional são os mesmos usados pelas reservas Python Studios:
`studio_generation_jobs` e `external_policy.reserve_monthly`. Não há uma segunda
planilha/arquivo de saldo em Node. Os registros `external_call` não são executados
ou reenviados por workers e não possuem associação/membership de login.

A sessão e o RBAC continuam no BFF. AsyncLocalStorage leva a identidade autenticada
ao SDK, sem aceitar empresa/usuário/tarifa do corpo enviado pelo navegador. Um JWT
interno, com audiência `clicko-finance`, tipo e validade próprios, autentica a ponte.
JWTs comuns de Studios não servem para admitir despesas. O proxy público não monta
essa rota. Sem contexto autenticado, serviço, tarifa ou saldo, não há submissão.

## Habilitação futura — não executada nesta etapa

O perfil `npm run dev:local` força todas as flags pagas para `false`. Fora desse
perfil, uma chave de API sozinha não basta. É necessário provisionar no servidor:

```text
CLICKO_NODE_OUTBOUND_ENABLED=true
STUDIO_NODE_OUTBOUND_ENABLED=true
STUDIO_EXTERNAL_MONTHLY_BUDGET_USD=<teto global USD>
STUDIO_EXTERNAL_WORKSPACE_MONTHLY_BUDGET_USD=<teto por empresa USD>
STUDIO_EXTERNAL_USER_MONTHLY_BUDGET_USD=<teto por membro/empresa USD>
STUDIO_EXTERNAL_MODEL_MONTHLY_BUDGETS=<objeto JSON modelo: teto USD>
STUDIO_NODE_TARIFFS=<objeto JSON provider:model: configuração>
```

Cada entrada de tarifa exige `revision`, `validUntil` (data ISO), `unit`,
`inputUsdPerMillion`, `outputUsdPerMillion`, `maxInput` e `maxOutput`.
Os provedores aceitos são `google.klic` (unidade `tokens`) e `google.cloud-tts`
(unidade `characters`, modelo = ID exato da voz). Tarifas de teste nos testes
automatizados não são preços comerciais e não devem ser copiadas para produção.
O operador deve verificar tarifas atuais, dimensões de contexto, tokens de thinking,
classe da voz, limites do projeto e faturamento do provedor antes de habilitar.

Para Gemini Node, a reserva usa o teto **integral de entrada** do modelo configurado,
mais a saída limitada, não uma estimativa de tokens a partir do tamanho de imagens
ou áudios. `maxInput` deve ser o limite real do contexto aprovado para aquele modelo;
um valor artificialmente baixo não protege uma entrada multimodal maior. Para TTS,
bytes UTF-8 limitam conservadoramente caracteres. Zero não significa ilimitado.

Os três limites mensais e o limite por modelo também são obrigatórios nas reservas
pagas Python, inclusive desenvolvimento. Ferramentas locais gratuitas não passam por
reserva financeira externa. Conexões `local_free` continuam restritas a endpoints
loopback; não são uma forma de declarar um serviço remoto como gratuito.
O período financeiro deste ledger é o mês em UTC, não a preferência de fuso da interface.

## Idempotência, tentativas e resultado desconhecido

- O cliente deve reutilizar `Idempotency-Key` em reenvios da mesma operação. Sem
  essa chave, o identificador HTTP gerado pelo servidor não permite reconhecer
  uma nova requisição como repetição de outra anterior.
- A reserva vincula chave, identidade e fingerprint. Mesmo corpo/chave recupera
  o recibo; corpo diferente conflita. `start` adquire uma única submissão por UPDATE
  condicional. Concorrência e ACK perdido não autorizam outro POST ao provedor.
- Cada tentativa explicitamente admitida tem seu próprio recibo. SDK Gemini e TTS
  não multiplicam retries silenciosos. O retry da KLIC continua limitado a três
  tentativas transitórias, cada uma sujeita ao saldo, sem repetir stream publicado.
- Mudança de tarifa, mês ou reserva com mais de 60 segundos impede um novo start.
  Um recibo terminal não pode ser reiniciado como job. A animação/chat não simula
  uma resposta quando a despesa foi negada.
- Tokens de entrada, candidatos e thinking são registrados. O custo calculado é
  **estimativa de tarifa**, nunca fatura. TTS registra unidades e reserva, não tokens
  inventados. Nenhum prompt, áudio, resposta ou credencial é gravado no recibo.
- Desconexão, aborto, timeout e resultado desconhecido conservam a reserva. Passagem
  de mês não apaga uma submissão desconhecida. Um reinício não faz nova geração.

## Cotas comerciais e limites desta entrega

Imagens: uma unidade por solicitação aceita, inclusive falha/cancelamento; replay
ou retry do mesmo job não vira outra unidade. Vídeo: somente cenas geradas por IA
consomem minutos; edição, prévia e exportação locais não entram nessa cota.
Créditos KLIC e essas cotas comerciais não são USD nem comprovantes de faturamento.
Mensagem/anexo inválido no chat operacional é validado antes do consumo comercial.

A reconciliação automática desta etapa armazena uso/estimativa e conserva o maior
valor entre reserva e custos conhecidos. **Não há importação de faturas do Google,
OpenRouter ou Runway nem liberação automática da diferença de uma reserva por mera
estimativa.** Operações incertas e reservas expiradas não utilizadas podem exigir
inspeção administrativa. Uma tela de gestão de reconciliação permanece pendente.
Os recibos e tokens foram testados sem chamadas pagas; isso não homologa preços,
acesso real aos modelos nem o extrato comercial de uma conta externa.

O adaptador Python legado `services/ai.py`, sem workspace/reserva durável, passa a
falhar fechado com orientação para a conexão LLM canônica. Não reativá-lo somente
com `AI_API_KEY`. Higgsfield continua transporte experimental desativado e sem rota
de submissão na plataforma; precisa integrar a admissão central antes de exposição.
Modelos locais/GPU sem manifests continuam indisponíveis, não foram simulados.
