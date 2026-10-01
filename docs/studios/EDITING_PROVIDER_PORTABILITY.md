# Independência de provedores na edição de vídeo

Gemini continua como principal. A API do estúdio agora usa `EditingAIRequestV1` e `/editing-ai-jobs`, sem exigir uma marca no contrato do cliente. Os endpoints anteriores continuam compatíveis com projetos e jobs existentes.

## Separação por responsabilidade

| Responsabilidade | Execução atual | Como trocar |
| --- | --- | --- |
| Planejamento contextual | Gemini ou adaptador multimodal Chat Completions | Configuração do papel, endpoint e modelo fixado |
| Criação/alteração de imagem | Adaptador Gemini implementado | Um novo adaptador precisa implementar e validar essa operação |
| Criação/alteração de vídeo | Adaptador Gemini implementado | Um novo adaptador precisa implementar e validar submissão, consulta, mídia e revisão |
| Montagem e exportação | FFmpeg contextual; HyperFrames no caminho já existente | Não dependem da LLM de planejamento |
| Acervo, fontes e documentos | Armazenamento e banco do res | Permanecem disponíveis independentemente do provedor |

O painel consulta `GET /api/v1/studios/v1/editing/ai`, que distingue a configuração e as operações de cada papel. Um endpoint de texto não aparece como gerador de vídeo. A operação indisponível é bloqueada antes da criação do job, com alternativas de acervo/configuração.

Exemplo de configuração: manter `STUDIO_EDITING_AI_PROVIDER=gemini` e substituir somente `STUDIO_EDITING_AI_PLANNING_PROVIDER=compatible`. Imagem e vídeo continuam usando Gemini. `none` desliga uma responsabilidade na nova interface; as montagens com materiais existentes continuam disponíveis. As chaves Gemini e os endpoints legados seguem suas configurações anteriores.

O adaptador `compatible.editing-planner` usa `STUDIO_EDITING_AI_BASE_URL` com prefixo de API, `STUDIO_EDITING_AI_MODEL`, chaves separadas por ambiente e orçamento exclusivo de testes. Exige Chat Completions com entrada de imagem, JSON e o ID de modelo informado na resposta. Não há garantia de compatibilidade apenas porque um provedor aceita chat: detalhes de transporte, recursos e qualidade precisam ser qualificados. Modelos que retornam IDs de versão diferentes exigem configuração explícita desse ID. As tarifas do adaptador permanecem `unpriced` até configuração de uma referência datada; consumo retornado é registrado sem estimativa financeira inventada.

As respostas passam pelo mesmo compilador contextual, verificações de materiais, revisão de documento, operações executáveis e render. O teste de integração desliga o Gemini, fornece uma resposta simulada do outro adaptador, aplica o plano e exporta MP4 pelo FFmpeg. Isso comprova o caminho independente; não qualifica a qualidade de uma API externa real.

## Retentativas e portabilidade

Cada job fixa provedor, modelo, ambiente, tarifa, documento, checksums e, no adaptador compatível, uma impressão digital do endpoint. Mudar a configuração não redireciona jobs em andamento para outra empresa. O mesmo job é consultado/retomado no provedor original. Se o endpoint ou modelo mudar, a retomada exige restaurar a configuração correspondente; não ocorre reenvio ao destino novo.

Não existe fallback automático que envie conteúdo privado a outro provedor ou gere cobranças novas após um timeout incerto. Quando um novo adaptador for qualificado, uma nova tentativa com outro provedor deve constituir um novo job rastreável, com destino e custo explícitos. A API não apaga o histórico do pedido anterior.

O res guarda planos, assets e timeline em seus próprios contratos e armazenamento. Trocar a LLM não exige regenerar fontes, logos, cortes, legendas ou arquivos já incorporados. GPT continua limitado a testes locais conforme a decisão anterior; a autorização para múltiplos provedores não altera implicitamente essa política.

## Limite atual

Há duas implementações de planejamento e uma implementação de geração/transformação de mídia. Portanto, a dependência da LLM de planejamento foi reduzida com um caminho alternativo executável, mas ainda é necessário qualificar outro gerador de mídia para redundância real de vídeo generativo. Não basta cadastrar uma URL para transformar uma API de texto em editor de vídeo.

Tracking, rotoscopia, estabilização e as demais técnicas não implementadas continuam indisponíveis. Independência de provedor e cobertura de técnicas são avanços distintos: adicionar uma LLM não implementa essas técnicas no renderizador. A matriz de capacidades e as pendências de qualificação em `EDITING_RESOURCES_GEMINI.md` continuam válidas.

## Validação local

A rodada com adaptadores, acervo e worker aprovou 33 testes. Foram acrescentadas regressões para repetição após troca de provedor e serialização dos pedidos legados; a rodada focada verifica esses casos junto do fluxo completo do planejador alternativo. Dois testes de interface passaram. TypeScript, Ruff e build de produção passaram, mantendo o aviso existente de tamanho do bundle.

O teste alternativo exporta MP4 com mídia local e resposta de IA simulada, sem chamadas pagas ou dependência de chave Gemini. O teste de transporte verifica o formato HTTP, modelo e resposta com `MockTransport`. Endpoints de terceiros e qualidade editorial de seus modelos precisam de validação real antes da ativação. O manifesto do worker de mídia está na versão 0.3.0, com os dois tipos de job registrados.
