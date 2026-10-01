# Clicko — pesquisa e direção do estúdio de edição de vídeo

**Data da pesquisa:** 5 de setembro de 2026.  
**Produto:** Clicko. **Código examinado:** `C:\Users\edugu\Downloads\res`.  
**Decisão solicitada:** como transformar rosto, voz, objetivo e contexto do cliente em anúncio ou conteúdo final, com repertório atualizado e edição consistente.  
**Restrição confirmada:** até R$ 500/mês de APIs e infraestrutura no piloto, sem desenvolvimento.  
**API do GPT:** exclusivamente para testes locais; fora das dependências de produção.  
**Entrega desta rodada:** pesquisa, diagnóstico e plano. Não foram gerados vídeos, ativados fornecedores, contratadas assinaturas ou instalados monitores.

## 1. Recomendação executiva

**O melhor caminho para a realidade do Clicko é manter planejamento e montagem no próprio produto, aproveitar FFmpeg e HyperFrames já integrados e tratar voz e animação facial como componentes substituíveis.** O diferencial deve ser a escolha editorial: o que mostrar, em que ordem, com qual fala, ritmo, texto e som para aquele público.

O Clicko já tem React/Vite, FastAPI, filas, contratos audiovisuais, biblioteca de mídia, busca de conhecimento, timeline e revisão. Trocar essa base por uma plataforma de anúncios completa acrescentaria migração e custo antes de resolver os problemas observados. Há também um piloto local de avatar, mas ele ainda não demonstra geração satisfatória para qualquer foto e voz.

As três maneiras de avançar são:

| Etapa | Caminho | Resultado buscado | Decisão |
|---|---|---|---|
| Temporária | Produção assistida sobre o Clicko e ferramentas locais existentes | Uma peça completa que sirva de referência de qualidade: apresentador, demonstração, legendas, motion e mixagem | Começar aqui; distinguir operação assistida de automação pronta |
| Intermediária | Clicko controla a edição; voz/avatar usam adapters locais ou API por consumo | Foto e voz cadastradas uma vez; briefing curto; vídeo completo para revisão | Arquitetura recomendada para o piloto do produto |
| Avançada | Inferência própria qualificada, composição mais rica e aprendizado por experimentos | Menor custo por vídeo aprovado e personalização por nicho em escala | Expandir após evidência de qualidade, demanda e custo |

Não é necessário treinar um modelo fundacional para iniciar. É necessário conectar o conhecimento às decisões que chegam à timeline e aprender com revisões e resultados reais.

### Objetivo e critério de sucesso

> Após cadastrar seu rosto, sua voz e as informações da marca, a pessoa informa o objetivo e recebe um anúncio ou conteúdo vertical completo, revisável e coerente com seu nicho, sem precisar montar cenas manualmente.

O cadastro inicial pode exigir foto, amostra de voz e confirmação de uso da identidade. Nos próximos vídeos, esses materiais serão reutilizados. Uma foto sozinha não fornece a voz, a oferta, as provas do produto ou o conhecimento factual do cliente.

**Preferência confirmada:** gerar o vídeo direto e revisar depois. Roteiro e plano de edição continuam existindo internamente; não devem obrigar o cliente a aprovar sete etapas antes de ver um resultado.

Metas propostas para o piloto — metas de projeto, não resultados já obtidos:

- 12 briefings distintos, cada um com duas variantes de edição: 24 peças, cobrindo anúncios e conteúdo em três nichos de teste.
- Pelo menos 80% das peças aprovadas em até uma revisão editorial; medir separadamente defeitos de voz/rosto.
- Zero erro crítico de marca, nome, preço, oferta, fala omitida, licença ou identidade no arquivo aprovado.
- Custo de APIs e infraestrutura limitado a R$ 500/mês, incluindo tentativas; medir custo por vídeo aprovado.
- Medir tempo humano, tempo de fila e tempo de geração separadamente. Não anunciar geração instantânea antes do benchmark.

## 2. O que já existe no Clicko e o que falta

Esta análise usa código, manifests e documentos locais. Não executou novamente as suítes ou a geração audiovisual; testes e medições anteriores são identificados como registros históricos.

| Componente | Evidência encontrada | Implicação |
|---|---|---|
| Aplicação | React 19, TypeScript, Vite 6, Tailwind 4 e servidor Express em `package.json` | Preservar a aplicação atual; não propor Next.js ou outro frontend como requisito |
| Backend | FastAPI, SQLAlchemy, Alembic, Celery/Redis, suporte PostgreSQL, pgvector e boto3 | Usar filas e storage existentes; vídeo pesado não deve ocupar a requisição web |
| Edição | `FFmpegUgcVideoRenderProvider`, timeline, legendas, formas, texto e faixas de som | Base concreta para composição determinística |
| Motion | Adapter `HyperFramesCliVideoRenderProvider`; runtime fixa HyperFrames 0.8.12 e Node 22.15.0 | Evoluir a projeção do documento canônico, sem substituir o editor pelo clone |
| Conhecimento | `KnowledgeDocument`, `KnowledgeChunk`, busca híbrida e embeddings opcionais | Não criar outro banco vetorial ou outro sistema de RAG |
| Inteligência criativa | `KnowledgeClaimV1`, `CopyBriefV1`, `PerformancePlanV1`, `SceneBlueprintV1`, `AssetPlanV1` e outros contratos | Transformar referências em dados que alimentam esses contratos |
| Revisão | Plano e sete eixos de decisão; interface Video Studio → Revisão | Apoio à revisão já existe; o fluxo de vídeo direto precisa de política explícita nova |
| Voz e avatar | Scripts Chatterbox e MuseTalk; portas separadas para fala, avatar e vídeo genérico | Aproveitar isolamento existente, sem promover experimentos automaticamente |

### Lacunas que realmente impedem a promessa

1. **Admissão de mídia:** o renderer UGC exige proveniência `user-upload` para suas fontes visuais. Não basta importar o MP4 sintético e mudar seu rótulo. É preciso admitir avatar sintético com origem, identidade e direitos verdadeiros.
2. **Narração:** o código atual distingue `natural-sound-candidate` e `licensed-music-candidate`; narração local precisa de finalidade e tratamento próprios. Documentos antigos que descrevem ausência total de música já não representam integralmente o código lido.
3. **Composição:** o caminho FFmpeg examinado aceita uma faixa principal de vídeo e sobreposições específicas. Recorte de apresentador, picture-in-picture e overlays animados não podem ser prometidos só porque FFmpeg, como ferramenta geral, consegue realizá-los.
4. **Fluxo de aprovação:** documentos inscritos no controle editorial dependem de decisões humanas de prova, roteiro, storyboard, animatic, voz, rosto e cenário. Isso conflita com a preferência atual de vídeo direto para revisão.
5. **Revisão final:** o contrato editorial atual mantém `publicationAuthorized=false`; existe bloqueio de publicação específico para revisão final pendente. Aprovar pré-produção não resolve essa integração.
6. **Referências atualizadas:** não foi identificado um conector operacional que acompanhe especificamente `@creators` e `@moonsol.design`. A base pesquisável existe; a coleta, curadoria e promoção das novidades precisam ser conectadas a ela.

Fontes locais principais: [renderer](../../../../backend/app/providers/studios/video_render.py), [contratos editoriais](../../../../backend/app/domain/studios/editorial_review.py), [busca de conhecimento](../../../../backend/app/services/knowledge.py), [implementação editorial](../../pilots/CLICKO_EDITORIAL_IMPLEMENTATION_2026-09-05.md) e [interface de revisão](../../pilots/CLICKO_EDITORIAL_UI_IMPLEMENTATION_2026-09-05.md).

### O piloto Caio Vale: prova técnica e limites

O arquivo privado de anúncio bruto existe, com 11.215.416 bytes. O registro de execução informa 44,52 segundos, 720 × 1280, 25 FPS e 691,30 segundos de render local. A preparação usou câmera fixa e uma região facial associada a uma única fonte. Isso não constitui um detector geral capaz de trabalhar com qualquer usuário.

O mesmo registro descreve repetição bidirecional da base, suavização de boca/barba e revisão perceptiva pendente. As vozes stock anteriores foram rejeitadas. Não há fundamento para reaproveitar essas rejeições como aprovação de naturalidade ou para dizer que o produto já entrega o anúncio completo. O bruto foi produzido sem B-roll, motion, legendas e trilha.

O diagnóstico posterior também identifica falta de demonstração real do produto. A primeira melhoria editorial deve mostrar uma transformação verificável, em vez de sustentar toda a mensagem em uma cabeça falando. [Execução local](../../pilots/CLICKO_CAIO_LOCAL_CLONE_EXECUTION_2026-09-04.md), [diagnóstico criativo anterior](../ugc-motion-caio-2026-09-04/report-source.md).

### Inventário de clones: aproveitar com critério

Foi encontrado um registro de **42 repositórios**, ampliando o conjunto de 18 mencionado na conversa. Trata-se de inventário, não de 42 integrações prontas. Há inconsistências que precisam ser reconciliadas: o registro geral marca MuseTalk como Apache-2.0, enquanto o arquivo `LICENSE` do clone examinado declara MIT e a ficha posterior já corrige isso. Código, pesos e datasets exigem verificação separada.

| Grupo | Repositórios existentes a priorizar | Uso no Clicko |
|---|---|---|
| Composição e entrega | FFmpeg, HyperFrames | Motor principal e motion programático; aproveitar adapters já presentes |
| Intercâmbio e análise | OpenTimelineIO, PySceneDetect, OpenCV | Exportação de decisões e análise técnica quando resolverem um caso concreto |
| Interface de edição | react-timeline-editor, wavesurfer.js, Konva, Fabric.js | Referências/componentes selecionados, evitando duplicar a timeline atual |
| Voz | Chatterbox, OpenVoice, WhisperX | Comparação de fala autorizada, conversão de timbre e alinhamento; validar PT-BR e cada dependência |
| Avatar | MuseTalk, LivePortrait, LatentSync | Experimentos isolados; generalização e qualidade ainda precisam ser demonstradas |
| Arquitetura editorial | OpenMontage, OpenCut | Estudar processo e interação; não copiar indiscriminadamente implementação ou mídia |
| Efeitos mais complexos | SAM2, Depth Anything V2, RAFT, motion-canvas | Só incorporar quando uma técnica editorial justificar o custo e o hardware |

O [ADR-004](../../adr/ADR-004-open-source-video-rendering.md) já prioriza FFmpeg/HyperFrames e deixa Remotion fora da integração enquanto vigorar a preferência por ferramentas open source. A licença própria de Remotion permite uso gratuito em certas organizações, mas isso não o torna open source. A documentação atual informa gratuidade até três pessoas; empresas elegíveis ao plano de automação pago têm mínimo de US$ 100/mês. Não há motivo para reabrir essa migração no piloto. [Licenciamento oficial Remotion](https://www.remotion.pro/license).

## 3. Grupo de pesquisa 1 — produtos comparáveis e tecnologia

### O que os produtos semelhantes construíram

As páginas oficiais permitem comparar experiência, capacidades e preços públicos. Não revelam necessariamente a arquitetura interna, os custos reais de operação ou a rentabilidade de cada empresa. A stack proposta aqui é uma decisão de engenharia para o Clicko, não uma alegação sobre a implementação privada dos concorrentes.

| Referência | Capacidade pública pertinente | O que estudar para o Clicko |
|---|---|---|
| Creatify | Geração de anúncios a partir de produto/URL, roteiros, atores e edição | Briefing curto, demonstração do produto e variações de criativo. [Produto](https://creatify.ai/), [Product-to-video](https://docs.creatify.ai/api-documentation/product-to-video/product-to-video) |
| Arcads | Atores UGC, scripts e geração via API | Casting, direção da fala e comparação de variações. Foto de cliente não deve ser presumida equivalente a ator de catálogo. [API oficial](https://intercom.help/arcads/en/articles/10538922-arcads-ai-api-documentation) |
| HeyGen | Foto falante, avatar pessoal e Video Agent | Reutilização de identidade e geração guiada por briefing. [Photo Avatar](https://developers.heygen.com/photo-avatar), [guia de APIs](https://www.heygen.com/blog/heygen-api-guide) |
| D-ID | Foto falante e geração de apresentadores | Onboarding de identidade e integração de apresentação. [API e planos](https://www.d-id.com/pricing/api/) |
| Hedra / Kling Avatar | Geração de atuação guiada por imagem e áudio | Separar qualidade vocal da qualidade visual do apresentador. [Hedra](https://www.hedra.com/develop/models/video/hedra-character-3), [Kling](https://replicate.com/kwaivgi/kling-avatar-v2) |
| Shotstack / Creatomate | Composição por API, templates, preview e edição embutida | Contratos de timeline, reedição e geração em lote; são referências de montagem, não prova de avatar próprio. [Shotstack](https://shotstack.io/docs/api/), [Creatomate](https://creatomate.com/docs/) |

O padrão transferível é: entrada simples, produção em etapas internas, revisão de uma peça concreta e reaproveitamento de identidade/marca. O Clicko deve cobrar e controlar trabalho efetivo de geração; edição de texto ou trilha não precisa gerar outra vez o rosto inteiro.

### Comparação econômica dos fornecedores de rosto

Preços nominais em dólares, consultados nesta pesquisa. Não incluem câmbio, impostos, voz externa, montagem, armazenamento ou tentativas adicionais. O custo médio de um plano só vale quando os créditos são consumidos; não é o desembolso de um único vídeo.

| Opção | Preço público relevante | Aproximação para 30 s | Adequação ao piloto |
|---|---|---:|---|
| HeyGen Photo Avatar IV/V | US$ 0,05/s e US$ 1 por criação de Photo Avatar; API por consumo | US$ 1,50, mais criação quando necessária | Candidato econômico, sujeito ao enquadramento do Clicko nos termos de integração |
| Kling Avatar V2 Standard via Replicate | US$ 0,056/s; Pro US$ 0,11/s | US$ 1,68 Standard; US$ 3,30 Pro | Primeiro comparador técnico por consumo para imagem + áudio |
| Creatify API Starter | US$ 99/mês, 500 créditos; Aurora 20 créditos/15 s, Fast 10 | US$ 7,92 Aurora; US$ 3,96 Fast, com créditos totalmente usados | Custo fixo e foto própria tornam a opção pesada para R$ 500 |
| Hedra Character 3 | Varia com resolução | US$ 0,75 em 540p; US$ 1,50 em 720p; US$ 1,875 em 1080p | Tecnicamente pertinente; integração em produto exige atenção ao contrato API |
| D-ID Launch | US$ 35/mês equivalentes no anual de US$ 420; até 45 min | Cerca de US$ 0,389 se toda a franquia for usada | Desembolso anual e condições comerciais impedem tratá-lo como opção mensal barata comprovada |
| Arcads | Talking Actor: 800 créditos/minuto, arredondando para cima | 30 s consomem um bloco de 800; preço em dólares não confirmado | Referência, com cotação pendente |
| VEED Fabric 1.0 via fal | US$ 0,08/s em 480p; US$ 0,15/s em 720p na página do modelo | US$ 2,40 / US$ 4,50 | Alternativa com posicionamento explícito para apps, mas menor volume no orçamento |

Fontes: [HeyGen cobrança](https://developers.heygen.com/docs/pricing), [Kling preço](https://replicate.com/kwaivgi/kling-avatar-v2), [Creatify billing](https://creatify.mintlify.app/billing), [Aurora API](https://docs.creatify.ai/api-reference/aurora/post-aurora), [Hedra preço](https://www.hedra.com/develop/models/video/hedra-character-3), [D-ID](https://www.d-id.com/pricing/api/), [Arcads créditos](https://intercom.help/arcads/en/articles/13725589-how-are-credits-counted), [VEED/fal](https://fal.ai/veed-fabric-1.0).

**Cuidados que mudam a comparação:**

- Creatify anuncia custo menor para outros fluxos de avatar, mas o endpoint que recebe foto arbitrária é Aurora. Não usar preço de ator stock para estimar a identidade do cliente.
- Assinatura de aplicativo e acesso API têm tabelas distintas. Um plano web não deve ser usado como orçamento de integração.
- A documentação de suporte VEED apresenta preço diferente da página do modelo. Planejar pelo valor de US$ 0,15/s em 720p até confirmar a cobrança da conta/endpoint. [Suporte VEED](https://support.veed.io/en/articles/15230480-veed-fabric-1-0-api).
- O direito de publicar um MP4 comercial e o direito de incorporar um serviço em um SaaS são questões diferentes. Há restrições/ambiguidades nos termos de [HeyGen](https://www.heygen.com/terms), [Hedra](https://www.hedra.com/api-terms), [Replicate](https://replicate.com/terms) e no tratamento de serviços gerenciados da [D-ID](https://www.d-id.com/eula/). A seleção comercial precisa confirmar o caso Clicko; a existência de uma API não resolve sozinha essa condição.

### Stack recomendada por etapa

**Temporária — aproveitar a estação e o código atuais.** Manter React/Vite/FastAPI, documentos e filas existentes. Finalizar uma peça com FFmpeg; usar HyperFrames para motion coberto pelo adapter. Chatterbox/MuseTalk permanecem avaliação privada, com a identidade e os arquivos autorizados já disponíveis quando adequados. DaVinci Resolve pode servir de referência manual de montagem e som; seus materiais oficiais de treinamento são gratuitos. Não apresentar esse fluxo assistido como autosserviço concluído. [Treinamento Blackmagic](https://www.blackmagicdesign.com/products/davinciresolve/training).

**Intermediária — a arquitetura do piloto.** O Clicko mantém briefing, pesquisa, roteiro, sequência de cenas, seleção de assets, legendas, som, cache e revisão. O adapter de avatar pode chamar Kling Standard como primeiro candidato de imagem + áudio, após validação de acesso e uso; a rota local só atende clientes quando passar em qualidade e generalização. HeyGen é segundo candidato documental; VEED é alternativa com posicionamento de integração mais explícito e custo maior. O fornecedor não define os contratos do produto.

**Avançada — melhoria orientada por custo e qualidade.** Workers GPU dedicados, pipelines de voz/avatar qualificados, composição de múltiplas camadas, segmentação e tracking quando exigidos por templates, e seleção de receitas a partir de resultados. Continuar usando FFmpeg para entrega. Não começar por Kubernetes, treinamento fundacional, 3D generativo ou vários LLMs pesados na GPU de 4 GB.

**Planejamento sem GPT em produção:** iniciar com briefing estruturado, busca existente e receitas explícitas. Qualificar um modelo local ou fornecedor separado para planejamento opcional; nenhum foi validado nesta rodada como escolha definitiva. Protocolo compatível com OpenAI não significa uso da API do GPT. Separar credenciais e custos de testes locais, e definir comportamento de produção sem essa API, inclusive para embeddings. Não houve alteração de configuração ou chamada paga nesta pesquisa.

O [HyperFrames oficial](https://github.com/heygen-com/hyperframes) declara composição HTML/CSS e renderização de vídeo sob Apache-2.0. O benefício aqui é a continuidade com o adapter já criado. A licença efetiva do [FFmpeg](https://ffmpeg.org/legal.html) depende da build e das opções; a build de desenvolvimento não deve ser presumida aprovada para redistribuição.

Shotstack publica US$ 39/mês ou compra PAYG de US$ 75; 30 s custam 0,5 crédito de edição. É uma opção de terceirizar render, mas consumiria parte relevante do teto antes de voz/avatar. Creatomate calcula créditos por duração, resolução e FPS e recomenda copiar o render para storage próprio, pois os arquivos expiram após 30 dias. Nenhum dos dois justifica substituir o pipeline existente neste piloto. [Shotstack preços](https://shotstack.io/pricing/), [Creatomate preços e condições](https://creatomate.com/pricing).

**Dependência temporária a encerrar:** a OpenAI anuncia o desligamento da API Sora em **24/09/2026**. Preservar os assets e o histórico do piloto, mas não construir uma nova dependência permanente desse adapter. [Comunicado oficial](https://help.openai.com/en/articles/20001152-what-to-know-about-the-sora-discontinuation).

### Orçamento de piloto

Alocação proposta, sem contratação realizada:

| Centro de custo | Limite mensal |
|---|---:|
| Avatar/API ou computação de avaliação | R$ 300 |
| Voz, planejamento e embeddings opcionais | R$ 50 |
| Infraestrutura/storage incremental | R$ 50 |
| Reserva para câmbio, impostos e tentativas | R$ 100 |
| **Total máximo** | **R$ 500** |

Pressupõe uso da máquina e infraestrutura já disponíveis. Se hospedagem, energia ou manutenção ultrapassarem as reservas, reduzir o volume; não tratar trabalho local como custo econômico zero.

**Exemplo calculado, não cotação cambial:** usando R$ 6/US$ apenas para planejamento, Kling Standard custa R$ 10,08 por 30 s de geração facial. Com média hipotética de 1,5 tentativas, são R$ 15,12 por peça aprovada apenas nessa etapa. Dezoito peças de 30 s consumiriam R$ 272,16; vinte, R$ 302,40. O corpus de 24 edições pode reaproveitar a mesma fala/avatar em duas montagens, reduzindo novas gerações faciais.

O número final depende da duração, de rejeições e da voz. Registrar custo reservado, estimado, reconciliado e confirmado. Uma resposta incerta de API não autoriza reenviar a geração automaticamente. O teto é aplicado antes de enfileirar e novamente no worker.

## 4. Grupo de pesquisa 2 — roteiro, montagem e repertório

### Os dois perfis indicados foram identificados

Os perfis indicados são [Instagram @creators](https://www.instagram.com/creators/) e [@moonsol.design](https://www.instagram.com/moonsol.design/). A investigação foi ampliada para 24 posições de Reels de cada perfil: **48 registros e 47 publicações distintas**, com inspeção visual temporal de **12 vídeos selecionados**. A [análise editorial dos Instagrams](ANALISE-INSTAGRAM.md) contém os casos, tempos observados, técnicas, comparação e limitações; a [base de métricas](instagram-metricas.csv) preserva os valores públicos.

O maior total de visualizações observado em creators foi o tutorial de aniversário, com 62,3 milhões. O vídeo de humor sobre chamada recebeu mais repostagens: 12,1 mil contra 8 mil. Na Moonsol, os fixados de café e profundidade tiveram alta proporção de curtidas, mas são de 2025; a colaboração com creators é uma só publicação e não constitui benchmark independente das duas contas. Esses dados selecionam hipóteses editoriais, não provam retenção, conversão ou tendência atual.

As técnicas observadas incluem demonstração filmada, conversa intercalada com exemplos, narrativa com arquivo, recorte de produto, ordem de camadas, máscara de roupa, ajuste de perspectiva, keyframes, desenhos e diferentes estilos de legenda. A prioridade do Clicko é dominar as operações reutilizáveis e mudar as combinações estéticas conforme novas evidências. **Tendências não são estáticas:** uma receita guarda técnica e parâmetros; uma observação de tendência guarda data, contexto, atualização e limitações.

Os vídeos foram inspecionados por amostras de quadros durante a reprodução. Não houve audição técnica nem decupagem de todos os frames. Créditos de áudio foram lidos; BPM, efeitos sonoros, prosódia e mixagem permanecem não verificados. Contagens de salvamentos, retenção e conversão não foram inventadas.

`@creators` é uma fonte oficial de orientações do Instagram. `@moonsol.design` é fonte autoral de técnicas e estética. Popularidade de uma técnica não comprova conversão, e sua presença no perfil oficial não libera o áudio ou os assets para publicidade de terceiros.

### Fontes de plataforma que devem alimentar o estúdio

| Fonte primária | Aprendizado relevante | Uso no algoritmo editorial |
|---|---|---|
| [Instagram Best Practices](https://about.fb.com/news/2024/10/best-practices-education-hub-creators-instagram/amp/) | Centro de orientações gerais e personalizadas no dashboard profissional | Atualizar recomendações por plataforma; não apresentar dicas de uma conta como regra universal |
| [TikTok Creative Codes](https://ads.tiktok.com/business/en/creative-codes) | Hook, desenvolvimento e fechamento; texto, som e movimento com função | Checklist de estrutura e atenção; variar execução conforme o objetivo |
| [TikTok Creative Center](https://ads.tiktok.com/help/article/creative-center?lang=en) | Biblioteca pública de inspiração, anúncios e tendências | Descoberta de referências atuais |
| [TikTok Top Ads](https://ads.tiktok.com/resources/help/article/how-to-use-the-top-ads-dashboard?lang=en) | Filtros de indústria, região, objetivo e métricas relativas | Selecionar comparáveis; registrar filtros e disponibilidade dos dados |
| [Google Ads ABCDs](https://support.google.com/google-ads/answer/14783551?hl=en) | Atenção, marca, conexão e direção | Vincular benefício, presença de marca e CTA à finalidade da peça |
| [YouTube retenção](https://support.google.com/youtube/answer/9314415?hl=en) | Quedas e picos ajudam a investigar partes do vídeo | Vincular métricas aos timecodes; pico também pode sinalizar dificuldade de compreensão |

Não existe, nessas fontes, uma fórmula que garanta o “melhor vídeo” para todos os nichos. A seleção deve respeitar objetivo, público, oferta, canal e materiais disponíveis. Recursos analíticos específicos também podem ter duração e amostra mínimas; não prometer toda análise de retenção para qualquer Short de 15 segundos.

### Livros e ensino: transformar fundamentos em decisões

Foram verificadas páginas oficiais de editoras/autores e materiais educacionais. Não houve leitura integral dos livros nesta rodada; não será criada uma cópia integral deles na base.

| Referência | Por que estudar | Tradução prática |
|---|---|---|
| Walter Murch, [In the Blink of an Eye](https://www.silmanjamespress.com/shop/filmmaking-directing/in-the-blink-of-an-eye2nd-edition/) | Critérios de montagem e efeito do corte | Todo corte deve declarar sua função: informação, emoção, ação ou orientação |
| Karen Pearlman, [Cutting Rhythms](https://www.routledge.com/Cutting-Rhythms-Creative-Film-Editing/Pearlman/p/book/9781041024088) | Timing, ritmo e energia da montagem | Descrever aceleração, pausa e progressão; não medir ritmo só por cortes por segundo |
| Bruce Block, [The Visual Story](https://www.routledge.com/The-Visual-Story/Blockah2/p/book/9781315794839) | Organização visual de cor, forma, espaço e movimento | Definir hierarquia e progressão visual por família de template |
| [Blackmagic Training](https://www.blackmagicdesign.com/products/davinciresolve/training) | Montagem, cor, Fusion, Fairlight e entrega | Formação prática com exercícios e arquivos oficiais; registrar versão do material |
| [Adobe Learn Premiere](https://www.adobe.com/learn/premiere-pro) | Edição, títulos, áudio e animação | Aprender técnicas que possam ser implementadas no motor do Clicko |
| [Sven Pape / This Guy Edits](https://thisguyedits.com/about/) | Storytelling e raciocínio de montagem | Referência autoral de decisões editoriais; não prova de desempenho de anúncios |
| [Ben Marriott](https://www.benmarriott.com/about) | Processo de motion design | Transições e animação que orientem a leitura |

Os creators já catalogados no Clicko — como `@paulo.ia` e `@mep.io_` — continuam no acervo. O novo recorte deve adicionar os dois perfis indicados e priorizar edição de vídeo. As 900 unidades do manifesto anterior não serão tratadas como 900 análises concluídas, nem como pré-requisito automático para aprender com o primeiro piloto.

### Protocolo de pesquisa densa

Proposta inicial: três nichos de teste — educação/serviço profissional, produto físico e serviço local. São casos de avaliação; o produto continua multinincho. Para cada nicho, selecionar 12 referências: quatro anúncios comparáveis, quatro conteúdos orgânicos e quatro referências de execução visual/sonora. Deduplicar republicações e limitar concentração em um único autor.

Cada referência terá uma ficha com:

1. URL, autor, data de publicação quando visível, data de consulta, país/idioma, nicho e objetivo.
2. Primeiro quadro, primeira frase, promessa e momento em que o benefício se torna claro.
3. Transcrição autorizada ou notas próprias, beats e mapa de planos com timestamps efetivamente observados.
4. Função de cada corte e transição; relação entre fala, ação e imagem.
5. Tipografia, densidade textual, contraste, tempo de leitura e áreas ocupadas pela interface da plataforma.
6. B-roll: demonstração real, prova, contexto ou ilustração; evidência do que a fala afirma.
7. Voz, silêncio, trilha, ambientes e SFX; pontos de entrada/saída e função narrativa.
8. Limitações, contraindicações, versão simples/intermediária/avançada da técnica e teste proposto.
9. Métricas disponíveis com definição e janela; resultado desconhecido permanece desconhecido.

Views, seguidores e curtidas não são sinônimos de venda. CTR não mede sozinho rentabilidade. Resultados também dependem de oferta, distribuição e audiência. O relatório não cria um ranking de “top influenciadores” sem critério e dados comparáveis.

### Três famílias de edição para começar

**A. Anúncio com apresentador e benefício — 15 a 30 segundos.** Abrir com benefício ou problema específico; mostrar o produto ou evidência; explicar o mecanismo essencial; terminar com uma ação. Usar cortes em mudanças de ideia, legendas curtas e efeitos pontuais. Não fazer o avatar declarar uma experiência pessoal que não ocorreu.

**B. Demonstração de produto ou processo — aproximadamente 30 segundos.** Abrir com tarefa/resultado; contextualizar brevemente com o rosto; mostrar dois ou três passos; apresentar a consequência e CTA. A imagem deve demonstrar o argumento. Setas, recortes e zoom servem à compreensão. Se faltarem assets reais, pedir o material essencial ou reformular para conteúdo explicativo sem inventar demonstração.

**C. Conteúdo educativo ou de autoridade — 30 a 45 segundos.** Abrir com pergunta/erro concreto; apresentar dois ou três pontos; usar exemplos visuais; concluir com uma aplicação. Ritmo de compreensão, voz clara e marca discreta. A chamada final pode ser salvar, comentar ou conhecer um serviço, conforme o objetivo.

Essas durações são presets de experimento, não leis de algoritmo. A duração final deve respeitar a fala; reescrever excesso de texto antes de acelerar a voz ou cortar sílabas. Montagem visual de marca com motion intenso entra depois, pois exige mais materiais que uma foto de rosto.

### Foto, rosto e voz

O critério da foto é adequação técnica, não “formato de rosto melhor”. Usar uma pessoa, rosto nítido, iluminação uniforme, olhos e lábios visíveis, enquadramento sem cortar áreas importantes e postura natural. Retrato frontal e expressão neutra são recomendações da [documentação Photo Avatar](https://developers.heygen.com/photo-avatar). Movimento pessoal mais fiel pode exigir vídeo de referência, conforme a rota escolhida.

Para a voz própria, cadastrar amostra limpa de uma pessoa, com uso autorizado. O intervalo de 10–20 segundos é ponto de partida do piloto local, não requisito universal de todos os fornecedores. Preservar a referência original e ouvir o resultado: ASR pode conferir palavras, mas não valida naturalidade, timbre ou atuação.

Para demonstrações, usar identidade sintética original ou pessoa/locutor com autorização apropriada. Uma imagem ou voz encontrada publicamente na internet não deve entrar no cadastro como se fosse a identidade autorizada do cliente. Referências de personagem podem orientar características gerais de interpretação; o produto final continua centrado no rosto e na voz da própria pessoa.

## 5. Grupo de pesquisa 3 — áudio e conhecimento atualizado

### Onde obter efeitos e trilhas

| Fonte | Uso prático | Limite que o Clicko precisa registrar |
|---|---|---|
| [YouTube Audio Library](https://support.google.com/youtube/answer/3376882?hl=en-uk) | Música/SFX; filtros para faixas com ou sem atribuição | A garantia anunciada se refere ao YouTube; conferir a licença para outro destino e publicidade |
| [Meta Sound Collection](https://www.facebook.com/help/instagram/402084904469945) | Trilhas e efeitos para conteúdo comercial nas superfícies Meta | Não confundir com a biblioteca musical comum do Instagram nem presumir uso universal |
| [TikTok Commercial Music Library](https://ads.tiktok.com/resources/help/article/how-to-use-the-commercial-music-library?lang=en-GB) | Conteúdo orgânico e pago no TikTok, conforme região e placement | Produzir versão específica para TikTok quando a licença for limitada ao destino |
| [Pixabay](https://pixabay.com/service/license-summary/) | Curadoria manual de música e SFX incorporados a obra maior | Não redistribuir áudio isolado. A [API pública](https://pixabay.com/api/docs/) documentada cobre imagem/vídeo; não foi confirmado endpoint de áudio |
| [Freesound](https://freesound.org/help/faq/) | SFX CC0 como prioridade; CC BY com crédito | Excluir CC BY-NC de anúncios; uso comercial da [API](https://freesound.org/help/tos_api/) exige negociação separada |
| [ElevenLabs SFX](https://help.elevenlabs.io/hc/en-us/articles/13313564601361-Can-I-publish-the-content-I-generate-on-the-platform) | Geração de efeitos específicos ausentes do acervo | Conferir plano, direitos e unidade de cobrança; não extrapolar regras de SFX para Music |
| [Epidemic Sound Partner API](https://www.epidemicsound.com/business/developers/) | Catálogo integrado a aplicativos, com licenciamento aos usuários | Contrato comercial de parceria; preço não confirmado nesta pesquisa |
| [Artlist Music API](https://artlist.io/blog/your-fast-track-to-better-app-audio-with-the-artlist-music-api/) | Busca e uso de catálogo dentro de produto | Acesso comercial via parceria; assinatura comum não equivale a licença de redistribuição |

**Escolha para o piloto:** curar 12 trilhas instrumentais e 30 SFX com permissão compatível com cada projeto. Priorizar ativos próprios, CC0 ou licença comercial explícita. Não contratar de início vários catálogos. O cliente recebe o vídeo mixado; o áudio bruto não vira produto para download.

Antes de transformar essa curadoria em biblioteca compartilhada de autosserviço, confirmar que a licença cobre esse uso pelo Clicko e por seus clientes. Se uma faixa não estiver liberada para todos os destinos, manter versões diferentes do vídeo ou usar outra faixa compatível.

**Eleven Music merece tratamento separado:** os termos atuais restringem determinados planos a uso individual e proíbem bibliotecas/repositórios e revenda nos planos self-serve. Portanto, não criar um catálogo comercial compartilhado a partir de uma assinatura Starter. Há também restrições de setores e de prompts; não é fornecedor universal para todos os nichos. [Termos específicos](https://elevenlabs.io/eleven-music-model-specific-terms), [termos Music](https://elevenlabs.io/music-terms).

A página geral ElevenLabs consultada mostra Starter US$ 6/mês e Creator US$ 22/mês, com desconto inicial distinto do preço recorrente. A página API apresenta inconsistência entre unidade da tabela e descrição de cobrança de SFX/Music; não usar essa tarifa para fechar o orçamento sem conferir o painel. [Preços](https://elevenlabs.io/pricing), [API](https://elevenlabs.io/pricing/api).

### Como mixar

Manter faixas separadas de voz, música e efeitos. Voz é a referência de inteligibilidade; a música abaixa durante a fala, os efeitos sinalizam ações e o silêncio participa do ritmo. A técnica de ducking é documentada pela [Adobe](https://helpx.adobe.com/uk/premiere/desktop/add-audio-effects/adjust-volume-and-levels/automatically-duck-audio.html); FFmpeg oferece recursos como `sidechaincompress` e `loudnorm`. [Filtros oficiais](https://ffmpeg.org/ffmpeg-filters.html).

Preset inicial proposto: aproximadamente −16 LUFS integrados e pico verdadeiro abaixo de −1 dBTP, ajustado por audição. Isso é meta interna, não exigência universal do Instagram/TikTok. Conferir o arquivo final em celular: nenhuma sílaba cortada, clipping, música mascarando a fala ou efeito desproporcional. Manter velocidade vocal natural.

Cada asset precisa de autor, URL, licença, data de aquisição, hash, atribuição, destinos e usos permitidos. Manter esses dados na biblioteca já existente e vinculados ao render. Uma falha de licença deve impedir a seleção daquele asset, sem exigir recomeçar todo o projeto.

### Atualização dos dois perfis

O objetivo é acompanhamento recorrente com histórico e indicação de frescor. Não há evidência verificada nesta pesquisa de um webhook que entregue toda nova publicação de qualquer perfil de terceiro.

A coleção oficial da Meta no Postman informa capacidades de leitura de contas profissionais no fluxo Facebook Login; esse fluxo requer configuração própria e não acessa contas consumer. A elegibilidade exata dos dois perfis ainda precisa ser testada. As páginas diretas de Business Discovery e webhooks retornaram HTTP 429 durante a pesquisa. [Meta/Postman](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-ab559ffb-8e2c-4b0a-b43a-5737b6d2f672), [Business Discovery](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/business-discovery), [webhooks](https://developers.facebook.com/docs/instagram-platform/webhooks/).

**Operação proposta:**

1. Registrar `@creators` e `@moonsol.design` como fontes com função diferente: orientação de plataforma e técnica autoral.
2. Começar com registro manual de links e sínteses; revisão dos dois perfis duas vezes por semana enquanto a integração oficial não estiver comprovada.
3. Após teste de acesso, consultar a cada 12 horas dentro das permissões e limites reais. Deduplicar por identificador da publicação e detectar alteração de conteúdo.
4. Registrar última tentativa, último sucesso, erro e período efetivamente coberto. Ausência de resposta não significa ausência de novidades.
5. Colocar novidade em fila de curadoria. Uma atualização de plataforma pode receber prioridade; um efeito visual entra como hipótese para teste.
6. Mostrar internamente atraso superior a 24 horas como fonte desatualizada. Notificar apenas mudança relevante, falha persistente ou ação necessária; não enviar boletins vazios.

A sessão aberta no navegador foi usada para pesquisa pontual; não foi convertida em scraper ou serviço permanente. A posição oficial da [Meta sobre scraping](https://about.fb.com/news/2021/04/how-we-combat-scraping/) reforça a necessidade de acesso permitido. Monitoramento automático ainda não foi ativado nesta rodada.

### Como a base realmente melhora a produção

Reutilizar o conhecimento e a busca híbrida existentes. Armazenar três classes de conteúdo:

- **Fundamentos:** princípios duráveis de clareza, continuidade, ritmo e som.
- **Orientações/tendências datadas:** plataforma, técnica, público observado, período e revisão prevista.
- **Resultados próprios:** revisão humana e métricas vinculadas à versão de briefing, roteiro, voz, assets e edição.

O registro precisa de fonte, autoria, data, síntese própria, trecho/localizador, tipo de afirmação, limitações e status. O schema `KnowledgeClaimV1` já separa observação, afirmação documentada e inferência. Preservar essa distinção e acrescentar vigência e aplicabilidade sem fabricar certeza numérica.

Fluxo recomendado:

```text
Fonte observada → nota com evidência → curadoria → regra/receita versionada
                                                     ↓
Briefing + nicho + destino → busca de referências → plano de cenas
                                                     ↓
Voz/rosto + assets → edição → vídeo → revisão e métricas
                                     ↓
                         hipótese para próxima versão
```

A busca seleciona recomendações por nicho, objetivo, canal, direitos e materiais disponíveis. Uma regra de design não pode sobrescrever fatos do produto. Conteúdo externo é dado de referência, nunca instrução com autoridade para mudar o sistema.

No piloto, as novidades não alteram templates já usados sem versionamento. Revisões explícitas corrigem falhas concretas; experimentos comparam uma variável de edição por vez. Isso é recuperação de conhecimento e melhoria por evidência. Só haverá treinamento de machine learning quando existir um processo de treino efetivo com dados, avaliação e versões próprias.

## 6. Mapa de implementação e validação

O detalhamento operacional está no [plano de implementação](PLANO-DE-IMPLEMENTACAO.md). A sequência recomendada é:

| Ordem | Entrega | Critério para avançar |
|---|---|---|
| 1 | Reconciliar decisões antigas com voz/rosto e vídeo direto; consolidar baseline | Código, capacidade e estado de revisão sem contradições |
| 2 | Definir uma peça de referência completa e três receitas | Cada cena tem função, asset possível e som justificado |
| 3 | Admitir avatar, narração e música corretamente no pipeline | MP4 composto com origem verdadeira, sem reclassificar mídia para contornar contratos |
| 4 | Produção automática de rascunho e revisão final | Cliente chega ao vídeo completo; mudanças invalidam apenas resultados dependentes |
| 5 | Curadoria e atualização de fontes integradas à busca | Cada decisão recupera fonte/versão; falha de coleta aparece como falha |
| 6 | Rodar 12 briefings e 24 variantes | Qualidade, revisões, tempo e custo medidos; nenhuma aprovação inventada |
| 7 | Expandir provider/GPU/catálogos conforme resultados | Demanda e custo justificam o investimento |

A primeira fatia deve produzir uma peça inteira revisável. Acrescentar apenas telas de aprovação, scores de qualidade ou wrappers de geração não prova que o estúdio consegue editar bem.

### Avaliação audiovisual

Revisão integral com som e novamente sem som em tela de celular. Avaliar: clareza do hook, coerência do argumento, relação fala/imagem, fidelidade da identidade, naturalidade vocal, sincronização, leitura, ritmo, utilidade do motion, mixagem e CTA. Notas de 1–5 podem apoiar comparação; defeitos críticos impedem aprovação mesmo com média alta.

Preservar exemplos ruins e os motivos da rejeição. Um detector de silêncio, um ASR ou um checksum não substitui julgamento audiovisual. Da mesma forma, dados de retenção podem orientar edição, mas não isolam causalidade comercial sem desenho de experimento adequado.

### Validações de engenharia indispensáveis

- Rascunho automático sem aprovação humana fictícia; consentimento e permissões reais preservados.
- Alteração de voz/identidade invalida lip-sync; alteração de legenda não cobra outra geração facial.
- Fila repetida, callback duplicado e timeout não duplicam cobrança ou render admitido.
- Narração, música e SFX com tipos e origens corretos; licença por destino e checksums conferidos.
- Troca de usuário/workspace não expõe rosto, voz, mídia, revisão ou conhecimento privado.
- Revisão final ligada ao MP4/hash/revisão exatos; arquivo alterado perde a aprovação.
- Legendas PT-BR completas; marca, preço e CTA conferidos; saída decodifica e não contém quadros vazios inesperados.
- Atualização de fonte deduplicada, reversível e com registro de erro/atraso.
- Teto mensal considera jobs em andamento, tentativas e custo reservado.

## 7. Limitações e decisões pendentes de evidência

Esta é uma pesquisa dirigida às decisões do Clicko, com fontes oficiais e autorais selecionadas; não uma varredura de toda a internet. As fontes de fornecedores comprovam oferta pública, não superioridade visual ou resultados comerciais independentes.

Não foram medidos nesta rodada: qualidade comparativa de APIs, custos faturados da conta, tempo de render atual, elegibilidade Meta dos perfis e direitos de cada futuro asset. A análise dos Instagrams inclui amostragem visual temporal de 12 vídeos e métricas públicas, com limites detalhados no documento específico; não inclui audição técnica, retenção privada nem decupagem contínua de todos os cortes. As páginas de livros comprovam disponibilidade e tema, não leitura integral.

A inspeção local revelou documentação com estados históricos conflitantes. Usar código e registros específicos mais recentes para definir a execução; não interpretar inventários como promoção de providers. O worktree existente foi preservado.

**Decisão proposta:** investir primeiro em uma edição completa e convincente dentro do Clicko; depois automatizar esse padrão com identidade reutilizável, conhecimento versionado e revisão do vídeo final. A prioridade é reduzir o trabalho do cliente com qualidade verificável, mantendo a capacidade de corrigir a etapa que falhou.
