# Geração de materiais para anúncios da Clicko

Pesquisa em 05/10/2026. Repositório original em Downloads. Feedback direto do usuário: “Nota 1 para os 3 vídeos”. Primeira entrega escolhida: **anúncio de produto/serviço com cenas e narração**. As notas são feedback geral de rejeição da qualidade atual; não atribuem quatro eixos, preferência, estudo, reprodução completa ou confirmação de avaliação no celular. Não registrar aprovação nem autonomia com esse feedback.

## Decisão

Priorizar **Higgsfield como candidato principal para clipes**, com **Gemini Image para imagens de referência** e **Omni como comparação**. Avaliar Ideogram para edições de imagem que precisam preservar produto/composição. HeyGen e Arcads ficam para peças em que um apresentador/ator tenha uma função comercial definida. É uma recomendação de piloto, não qualificação de qualidade dos fornecedores.

O percurso proposto é briefing → direção e storyboard → imagens de referência → clipes candidatos → seleção → narração → montagem no documento atual → revisão humana. Um gerador entrega mídia; seleção, continuidade, título, preço, CTA, som e montagem ainda precisam funcionar na Clicko. Preservar CreativeDocumentV1, operações tipadas, revisões, hashes e execução Remotion/FFmpeg.

## Comparação com fontes oficiais

| Opção | Função útil para o formato escolhido | Preço observado e limite da evidência | Prioridade |
|---|---|---|---|
| Higgsfield / Kling 3.0 Standard TTV | Clipes para mostrar produto, ambiente e ações | US$ 0,042/s promocional; US$ 0,084/s normal. Até 15 s por geração. Outros modelos/parâmetros têm preços próprios | Primeiro candidato de cenas |
| Gemini 3.1 Flash Lite Image | Criar/editar imagens de referência antes de animar | Saída 1K equivalente a US$ 0,0336 por imagem, Standard; somar entrada/texto | Primeiro candidato de imagem, aproveitando o caminho existente |
| Gemini Omni 1.1 Flash | Geração e edição de vídeo, inclusive com referência | Saída 720p: 5.792 tokens/s a US$ 17,50/milhão; US$ 0,10136/s. Entrada e texto/thinking adicionais | Comparação e alternativa |
| Ideogram | Composição e edição de imagem | Ideogram 4.0 no Higgsfield: US$ 0,03/imagem. Não atribuir esse preço ao 4.5 | Teste específico de imagem |
| HeyGen | Apresentador com fala e sincronização labial | Help Center: Avatar III US$ 1/min; Avatar IV photo US$ 3/min, studio/digital twin US$ 4/min em 720p/1080p. Valores por geração, separados do plano do site | Posterior, se o anúncio precisar de uma pessoa falando |
| Arcads | Atores virtuais, variações de anúncios e também geração de imagens/clipes | Talking actor: 800 créditos/min por ator, duração arredondada para cima. Não confirmei preço em USD nem direito de acesso à API por plano | Posterior, teste de UGC |

Fontes: [Kling Standard](https://open.higgsfield.ai/models/kling-video/v3.0/std/text-to-video/playground), [Google pricing](https://ai.google.dev/gemini-api/docs/pricing), [Omni](https://ai.google.dev/gemini-api/docs/omni), [Ideogram 4.0](https://open.higgsfield.ai/models/ideogram/v4.0/playground), [HeyGen API](https://help.heygen.com/en/articles/10060327-heygen-api-pricing-explained), [Arcads créditos](https://intercom.help/arcads/en/articles/13725589-how-are-credits-counted).

Higgsfield é uma plataforma com diversos modelos, não uma única qualidade ou tarifa. Omni é o modelo de vídeo dessa comparação; Gemini Image tem papel separado. HeyGen e Arcads não devem ser avaliados apenas como substitutos de geração de imagens. O Arcads também agrega modelos de cenas: seu encaixe adicional para nós seria o fluxo de atores/anúncios, que não é a primeira necessidade escolhida.

O repositório oficial arquivado [heygen-stack](https://github.com/heygen-com/heygen-stack/blob/main/references/api-reference.md) conserva outra tarifa de avatar, US$ 0,10/s. Os links de pricing dos developer docs retornaram erro nesta leitura. Usar a tabela do Help Center como referência pública de pesquisa e confirmar o endpoint/modelo e a tarifa efetiva da conta antes de reservar orçamento. Não substituir tarifa por créditos do plano web nem prometer os preços antigos do repositório arquivado.

A documentação pública [Arcads external API](https://external-api.arcads.ai/docs) contém OpenAPI com geração de imagem/vídeo, talking actors, estados e saldo de créditos. Li o HTML e extraí a especificação embutida sem executar seus scripts ou qualquer operação autenticada. O recibo `.arcads-api.json` registra URL/hash e as operações. API documentada não comprova acesso no plano, preço em dinheiro, cobertura idêntica do limite gratuito de imagens do site ou integração operacional na Clicko.

## O que o código já permite e o que falta

Leitura local, sem inspecionar valores de chaves:

- `backend/app/config.py` já diferencia modelos de planejamento, imagem e vídeo Gemini. Há configurações de orçamento; não alterei flags, saldos ou segredos.
- `backend/app/providers/studios/editing_ai.py` declara planejamento e geração/edição de imagem/vídeo pelo Gemini, com qualificação `pending_real_media_validation`. Isso é caminho existente, não prova de que a conta gera boas cenas.
- `backend/app/services/studios/production_materials.py` já resolve candidatos de material Gemini e separa aquisição/admissão. Reaproveitar esse percurso em vez de criar outro projeto ou fazer o frontend chamar provedores com chaves.
- `backend/app/services/studios/scene_generation.py` está ligado a difusão local; não usar seu nome/provider local para anunciar Higgsfield remoto.
- `backend/app/domain/studios/generative_video.py` V1 é específico de Sora. Higgsfield exige contrato versionado adequado; não preencher Higgsfield como Sora.
- `backend/app/domain/studios/providers.py` mantém os registros genéricos de geração paga e avatar vazios. Não habilitá-los por uma recomendação de pesquisa.

Para Higgsfield: adaptador backend de submit/status/estimate, intenção e request hash persistidos, idempotência do fornecedor, teto de tentativas e custo, reconciliação de resultado incerto, vínculo a workspace/documento/revisão, storage próprio e SHA-256, probe técnico e admissão editorial. O retorno `completed` entra como candidato. Reutilizar o consumo de assets já existente para montagem. O handoff anterior detalha esses pontos em `NULLMOTION_IDEOGRAM_HIGGSFIELD_20261005.md`; ainda não há adaptador Higgsfield operacional.

## Direção do piloto de 15 segundos

Objetivo: demonstrar um benefício observável de um produto/serviço real e levar a uma única ação. Público, produto, oferta, marca, plataforma final e CTA ainda não foram definidos nesta conversa. Hipótese de formato para o piloto: vertical, narração em português, 15 s. Antes da geração, preencher esses dados com materiais autorizados; não inventar características ou resultados de clientes.

| Intervalo | Função | Material e decisão de montagem | Critério verificável |
|---|---|---|---|
| 0–3 s | Gancho e identificação | Produto ou situação concreta em um plano reconhecível; uma frase de benefício | O espectador identifica o objeto/necessidade sem depender do título |
| 3–8 s | Demonstração | Uma ação contínua no mesmo produto/ambiente, a partir de referência aprovada | Estado inicial, ação e resultado são visíveis; identidade preservada |
| 8–12 s | Consequência e detalhe | Mostrar resultado ou detalhe relevante, motivando o corte pelo significado | Não há produto diferente, atributo inventado ou mudança de estilo sem motivo |
| 12–15 s | Oferta/CTA | Imagem autorizada, título e CTA editáveis no editor | Texto correto, leitura no celular e destino real do CTA |

Gerar somente os trechos que precisam de movimento. Gravação real é preferível quando a cena precisa comprovar uso, interface ou resultado factual. Uma imagem gerada é ilustração; não comprova desempenho do produto.

### Duas lentes de direção, sem impersonação

**Tradução visual, baseada no perfil Villeneuve:** construir uma imagem de referência por plano antes de gerar movimento; manter objeto, ambiente, luz e direção de tela entre tomadas. Efeito esperado: reduzir deriva e cortes sem relação. Inferência operacional, não promessa do modelo. Contraponto: imagens bonitas podem ficar lentas e esconder o benefício. Teste: sequência sem locução ainda identifica o objeto e a transformação.

**Legibilidade emocional, baseada no perfil Spielberg:** o gancho mostra uma necessidade concreta; o plano seguinte revela uma ação/resultado que resolve essa necessidade. Efeito esperado: compreensão comercial mais rápida. Inferência operacional. Contraponto: não inserir ator/reação apenas por hábito quando um detalhe do produto comunica melhor. Teste: após uma reprodução, o avaliador consegue explicar benefício e ação proposta.

Os perfis da skill remetem a [DGA/Villeneuve](https://www.dga.org/events/2024/may2024/duneparttwo_qna_0324) e [DGA/Spielberg](https://www.dga.org/craft/dgaq/issues/0604-winter-2006/dga-interview-steven-spielberg). Aqui apliquei os modelos documentados localmente; não fiz nova análise dessas entrevistas nem atribuí uma fala literal. Gramática dominante: demonstração clara; apoio: consistência visual. Evitar a colagem de cenas apenas associadas às palavras da narração.

Cada plano de demonstração terá uma asserção preenchida: `{object, initialState, event, finalState, interval, evidence, counterexample}`. Exemplo de reprovação: rótulo “mais fácil” sobre uma cena bonita, sem mostrar o que mudou. Objetivo, identidade visual, som e CTA devem estar definidos antes de submeter o piloto. O plano ainda não passa os gates de produção com os dados comerciais em aberto.

## Custo para decidir, não média prometida

60 s de saída Kling Standard TTV: US$ 2,52 promocional ou US$ 5,04 normal, em vários clipes. Duas/três tentativas equivalentes ao minuto: US$ 10,08/15,12 na taxa normal. Omni 720p: US$ 6,0816 de saída por 60 s; entradas/texto adicionais. Não são tarifas de um minuto final aceito, nem parâmetros equivalentes de qualidade/áudio/resolução.

Piloto econômico hipotético: dois clipes de 5 s e duas imagens Lite Image 1K. Saídas em uma tentativa: US$ 0,4872 promocional Kling ou US$ 0,9072 na taxa normal; duas tentativas de tudo: US$ 0,9744/1,8144, antes de entradas/texto, narração, música, montagem e infraestrutura. Isso usa a taxa **TTV**; se a requisição usar imagem→vídeo para preservar produto, cotar esse modelo separadamente antes da execução. O orçamento não implica qualidade nem autorização de gasto.

Medir gasto de todos os candidatos / entregas aceitas, tentativas, tempo humano e custo de som/render/storage. Com nenhuma entrega aceita, o custo por entrega aceita fica indefinido, não zero. Nenhum desses números é média medida da Clicko.

## Próximo resultado que vale validar

Um anúncio curto com materiais reais ou gerados, narração inteligível, CTA correto e continuidade, montado pelo documento atual. Comparar Higgsfield com o caminho Gemini quando houver acesso e execução autorizados. Mesma necessidade visual, referência, duração e condições de saída; registrar diferenças de parâmetros, custo e intervenções. Não escolher pela galeria do fornecedor.

Para qualificação, continuar os três estudos e a avaliação humana exigida pelo direcionamento: quatro eixos ≥4/5, preferência às cegas e depois três novos briefs autônomos. A nota 1 é evidência de que a qualidade atual precisa evoluir; não permite inferir qual falha dominou em cada frame. Registrar intervalos e critérios na revisão do próximo piloto.

Esta rodada executou pesquisa pública, leitura do código e preparação do piloto. Gasto externo: US$ 0. Nenhuma compra, chave criada, chamada de geração, modelo baixado ou promessa de integração concluída.
