# res — produção híbrida e qualificação por capacidade

Data: 14 de setembro de 2026. Estado: plano de implementação; não autoriza contratação de infraestrutura ou execução de benchmarks pagos.

## 1. Objetivo e decisões

O res recebe briefing, identidade e materiais disponíveis, decide como demonstrar a mensagem, resolve os materiais necessários e entrega uma composição editável. O sistema escolhe a tecnologia por necessidade da cena e por evidência de qualidade, custo e disponibilidade.

Preservar FastAPI, Celery/Redis, CreativeDocument, plano contextual, MotionGraph, catálogo, HyperFrames e FFmpeg. Gemini permanece diretor principal; adaptadores continuam substituíveis. GPT permanece restrito aos testes locais.

Motion Canvas será um candidato especializado de renderização, não uma migração antecipada. O difusor local continua requisito de pesquisa e qualificação, separado da aceitação do motor de motion. Um resultado gerado por API não concluirá a qualificação do difusor local.

A composição 60% motion, 30% avatar e 10% geração é uma hipótese de portfólio. Não criar quotas por vídeo. Gemini pode planejar todas as cenas; texto, logos exatos, legendas e gráficos serão renderizados deterministicamente. Correções nesses elementos não devem disparar nova inferência visual.

Limites mantidos: computador atual e Oracle apenas nas funções já permitidas; nenhuma inferência nova na Oracle, GPU contratada ou fallback pago automático. O saldo agregado de APIs do piloto permanece limitado a US$1, considerando o consumo já registrado. Saldo desconhecido não equivale a saldo disponível. Não prometer executar dez anúncios com esse orçamento.

## 2. Ponto de partida verificado

- Existem portas distintas para geração, avatar, síntese de voz, clonagem e renderização em `backend/app/domain/studios/providers.py`.
- O registro de materiais distingue descoberta, aquisição, inspeção e quarentena; a presença de credenciais ou de uma flag ainda não comprova qualificação.
- `GeneratedVideoPolicyV2` já seleciona perfis, mas limita duração gerada a quatro segundos; o pedido legado `single_short_clip` mapeia para Sora. Novos pedidos não devem herdar essa regra específica de fornecedor.
- Há caminhos HyperFrames, runtime gráfico, composição contextual, voz Kokoro, sidecar de clonagem e difusão local. Sua existência não comprova qualidade audiovisual ou prontidão comercial.
- A política de avatar existente exige no mínimo dez pessoas e trinta casos. MuseTalk e LatentSync estão rejeitados na política atual de seleção; não alterar esses estados apenas para viabilizar um teste.

Antes de implementar, fixar commit ou hash dos arquivos relevantes, versões dos componentes e localização do checkout. A inspeção desta rodada usou `C:/Users/edugu/Downloads/res`; a pasta homônima em OneDrive não contém o mesmo conjunto de documentos do estúdio.

## 3. Etapa A — seleção de tecnologia e contratos

Estender as APIs existentes de produção, capacidades, jobs e avaliação. Não criar outra timeline nem outra fila.

### Capacidade e elegibilidade

Cada perfil terá fornecedor, operação, versões, limites de entrada/saída, condições dos materiais, ambiente de execução, licença dos componentes, estimativa de custo/tempo e evidências de qualificação. Separar serviço configurado, acessível, modelo instalado, recursos disponíveis, inferência validada e usos visuais qualificados.

Antes de comparar qualidade e preço, eliminar perfis incompatíveis com a operação, direitos, recursos, política do ambiente ou orçamento. Selecionar entre os restantes pela adequação editorial e pelos resultados do benchmark. Desempate: maior taxa de aproveitamento observada, menor custo por resultado aceito e menor latência. Perfil sem medidas participa somente de experimento explicitamente habilitado.

### Pedidos e execução

Introduzir uma política versionada de produção por capacidade, preservando leitura dos pedidos antigos. Ela especificará perfis permitidos, operações, segundos de saída, máximo de candidatos, permissão experimental e referência ao orçamento da rodada. Durações serão validadas contra o perfil escolhido; custos considerarão unidades nativas cobradas e tentativas, não apenas os segundos aproveitados na montagem.

Cada cena registrará intenção, informações essenciais, estratégia de produção, materiais, alternativa editorial e critérios de aceitação. O diretor fornece decisões estruturadas; componentes registrados produzem código executável. Não executar código arbitrário retornado pelo modelo.

Registrar antes da submissão uma operação persistida, reserva de orçamento e identidade idempotente. Timeout com aceitação incerta mantém a reserva e consulta o identificador conhecido; não reenviar automaticamente. Revalidar cliente, revisão e hashes antes de incorporar qualquer resultado.

Resultado desta etapa: o mesmo pedido pode selecionar provedores distintos sem alterar a composição canônica; incompatibilidade retorna necessidade ou alternativa explícita.

## 4. Etapa B — motion confiável e comparação de motores

### Qualificar o caminho atual

Executar os mesmos componentes em seis casos controlados: tipografia com acentos e destaques integrados; câmera e grupos; recorte e oclusão; caminhos vinculados; produto com anotação; transição com continuidade de elemento. Usar o runtime e o compilador de produção.

Preflight e avaliação devem consumir a composição efetivamente exportada. Medir texto após carregamento da fonte, transformações ao longo do tempo, recortes, safe areas, hierarquia e presença das ações essenciais. Sobreposição intencional permanece permitida. Colisão textual, informação cortada ou ação essencial ausente bloqueiam a entrega.

### Motion Canvas como adaptador experimental

Projetar uma parte explícita do MotionGraph para componentes próprios do Motion Canvas, com lista de operações suportadas. Usar os mesmos assets, fonte, resolução, fps, duração e estados semânticos dos seis casos. Sem aproximar silenciosamente efeitos não suportados. SVG importado não implica geometria editável; Lottie dependerá de suporte testado às propriedades utilizadas.

Capturar prévia e exportação pelo mesmo caminho do adaptador. Promover somente uma capacidade em que ele passe todos os bloqueadores e demonstre: operação necessária ausente no caminho atual, qualidade humana superior sem perda essencial, ou custo/tempo menor com qualidade equivalente. Registrar comparação em três execuções por caso para tempo e estabilidade. Se não vencer em nenhum uso, manter experimental.

Não migrar documentos existentes. Identificar renderizador e versão em cada derivado e invalidar apenas os derivados afetados por mudança.

Resultado desta etapa: motion qualificado no caminho atual e decisão documentada sobre manter ou promover capacidades específicas do Motion Canvas.

## 5. Etapa C — avatar e voz com entrada bem definida

Primeiro produto de avatar: vídeo autorizado de apresentador existente + texto/áudio + sincronização labial. Foto para apresentador com atuação completa fica como capacidade distinta, pois requer pose, movimento e expressão além de lip-sync.

Reaproveitar Kokoro para voz stock e a porta existente de conversão de timbre. Qualificar OpenVoice com áudio-base em português, medindo pronúncia, prosódia e identidade. Preservar consentimento, isolamento por cliente e exclusão dos materiais de identidade.

MuseTalk será o primeiro candidato documental. Antes de qualquer ativação, mapear os componentes realmente usados na inferência, seus pesos e licenças. Não confundir licença MIT do código com licença dos pesos nem restrição de uso com proibição comercial universal. Manter a política atual; uma alteração para admitir modelos com condições próprias será uma decisão separada e versionada, não um ajuste automático do benchmark.

LatentSync será comparador somente após resolver licenças dos componentes e disponibilidade de hardware. A documentação informa 8 GB de VRAM para 1.5 e 18 GB para 1.6; não planejar sua execução na GPU local de 4 GB. Não ativar os pesos não comerciais do InsightFace na produção.

Medir o pipeline inteiro: preparação do rosto, TTS, conversão, lip-sync, composição e encode. FPS divulgado do modelo não representa velocidade do serviço completo. Falta de vídeo autorizado ou voz utilizável gera material pendente, sem criar aprovação de identidade.

Resultado: um caminho de dublagem qualificável, com escopo explícito. Avatar completo permanece pendente até seu próprio teste.

## 6. Etapa D — difusão local e geração externa

### Local

Manter o worker isolado e uma tarefa pesada por computador. Confirmar equivalência numérica do carregamento, buffers, scheduler, atenção e VAE antes de atribuir resultado ruim ao prompt ou trocar modelos. A comparação de um modelo pequeno não basta para atestar a execução real: registrar estatísticas e amostras intermediárias na configuração efetiva.

Executar a matriz existente de dois prompts concretos por três seeds, em rodadas de até duas amostras, somente após admissão de recursos. Cada candidato recebe avaliação de pertinência, identidade, continuidade e ação. Não reduzir limites de proteção para completar a rodada. Um modelo-base alternativo será comparado somente depois de execução numérica válida e com hipótese registrada. Candidatos reprovados permanecem disponíveis como evidência, fora do acervo utilizável.

### API

Comparar inicialmente um perfil Veo 3.1 Lite 720p, se disponível na conta, contra composição determinística da mesma necessidade editorial. Confirmar modelo, tarifa e duração mínima no momento da execução. Sem saldo suficiente, registrar o caso como não executado. O resultado por API produz material; o res conserva texto, marca, timing e montagem.

### GPU remota, condicionada

Preparar contrato do worker para execução remota autenticada, sem provisionar recursos. A execução exige autorização específica de infraestrutura e orçamento em dólares separado do piloto atual. Configuração proposta para eventual experimento: worker sob demanda, zero instâncias mínimas, concorrência inicial um, prazo de 30 minutos por candidato e no máximo duas amostras por rodada.

Primeiro candidato remoto: Wan2.2 TI2V-5B em perfil de 24 GB compatível com o caminho oficial, após conferir RAM de host e disco. LTX entra somente como próximo comparador se houver hipótese de melhoria e licença validada, não como download paralelo. Contabilizar inicialização, carga de pesos, execução, espera e armazenamento. Sem autorização ou capacidade disponível, essa frente permanece pendente sem impedir a qualificação de motion.

## 7. Etapa E — benchmark de produto e revisões

### Triagem em dez anúncios

Fixar um corpus versionado de dez briefings de 15–20 segundos: quatro de apresentador, três de produto/oferta em motion e três híbridos. A equipe registra entradas, identidade e critérios; o sistema decide cenas e obtém os materiais. O Codex não monta as cenas finais nem seleciona arquivos para simular autonomia.

Usar entradas idênticas nas comparações de provedores. Ter dois temas e duas identidades no conjunto; formatos adicionais não são uma frente dedicada nesta rodada. Materiais de pessoas permanecem privados e vinculados ao consentimento. Fixture controlada para testar renderizador é evidência técnica separada do piloto autônomo.

Realizar uma revisão por anúncio: menos texto, mais calma ou mudança de cor/destaque. Incluir um caso de alteração de voz que invalide lip-sync, e um de tipografia que preserve todos os materiais gerados. A invalidação seguirá dependências, não a remontagem indiscriminada do projeto.

Os dez anúncios selecionam candidatos. Para liberar avatar, executar posteriormente a política existente de dez pessoas/trinta casos; a triagem não substitui seus critérios.

### Critérios

- Técnica: arquivo integralmente decodificável, fonte correta, sincronismo temporal, ausência de colisões indevidas e rastreabilidade entre plano e resultado.
- Editorial: materiais pertinentes, informação preservada, foco, ações visíveis e continuidade; observações ligadas a cena, intervalo e checksum.
- Humana: notas de 1 a 5 em clareza, hierarquia, naturalidade e pertinência; mínimo 4 em cada dimensão essencial por candidato aceito. Dois avaliadores na comparação entre motores; divergência que atravesse o limiar mantém o caso em revisão.
- Avatar: acrescentar identidade, sincronização labial e inteligibilidade/prosódia em português, além das exigências da política específica.
- Auditoria automática tem cobertura declarada; frames amostrados não representam revisão integral. Aprovação humana permanece separada da crítica de LLM.

Permitir até duas correções automáticas por etapa, sujeitas ao saldo e aos limites de candidatos. Depois disso, preservar a reprovação. Qualificação fica vinculada a perfil, versão, cenário e evidências; não significa suporte universal.

### Regressões obrigatórias

Pedidos V1/V2; revisão antiga; cancelamento; submissão incerta; reserva concorrente; descarte de candidato; material obrigatório ausente; falta de credenciais; fonte com acentos; destaque sem duplicação; sobreposição intencional; incompatibilidade de renderer; revisão sem nova geração; nenhuma chamada GPT em produção; nenhuma GPU ou geração paga acionada como fallback.

## 8. Custos, interface e conclusão

Não adotar R$343–670 por cliente como custo validado. Registrar separadamente APIs, GPU, render, armazenamento, tentativas, espera e trabalho humano. Calcular custo por minuto aprovado como custo de todos os candidatos e etapas do caso dividido pelos minutos efetivamente aceitos. Caso sem saída aceita terá custo incorrido e taxa de aproveitamento zero, sem média artificialmente favorável.

Apresentar distribuição dos tempos, taxa de aproveitamento e falhas por etapa. Armazenamento compartilhado e capacidade ociosa terão premissa explícita de rateio. Projeção para dez clientes depende de teste de fila e capacidade; não inferir dez produções simultâneas de um único benchmark.

O painel de produção mostrará cenas, materiais pendentes, candidato, origem, custo e revisão. A inspeção técnica mostrará versões, provedores, reservas, evidências e causas de rejeição. Distinguir novo planejamento, recompilação e novo render.

Entregas em ordem:

1. Registro de capacidades e pedidos agnósticos com compatibilidade.
2. Motion qualificado e comparação controlada HyperFrames/Motion Canvas.
3. Cadeia de voz/avatar com decisão de elegibilidade, antes de execução.
4. Qualificação numérica/visual local e comparação externa limitada ao orçamento disponível.
5. Pilotos, revisão localizada e relatório de qualidade/custo; casos não executados explicitamente pendentes.

O marco inicial é um vídeo de Distribuição autônomo e revisável, aprovado nos bloqueadores de motion. A entrega completa exige evidências próprias para avatar e para difusão útil; não declarar essas frentes concluídas com contratos, mocks ou sucesso de outra tecnologia.

## Fontes técnicas verificadas

- [Motion Canvas: exportação FFmpeg](https://motion-canvas.io/docs/rendering/video/)
- [MuseTalk: entradas, limitações e execução](https://github.com/TMElyralab/MuseTalk)
- [MuseTalk: licença dos pesos](https://huggingface.co/TMElyralab/MuseTalk)
- [OpenVoice](https://github.com/myshell-ai/OpenVoice)
- [LatentSync: requisitos de inferência](https://github.com/bytedance/LatentSync)
- [InsightFace: licenças de código e pesos](https://github.com/deepinsight/insightface/tree/master/python-package)
- [Wan2.2: perfil TI2V-5B](https://github.com/Wan-Video/Wan2.2)
- [LTX-2: licença dos pesos](https://huggingface.co/Lightricks/LTX-2/blob/main/LICENSE)
- [Google: tarifas por modelo e resolução](https://ai.google.dev/gemini-api/docs/pricing)
- [Runpod: componentes cobrados em serverless](https://docs.runpod.io/serverless/pricing)

Fontes definem condições e hipóteses. Modelos, tarifas, disponibilidade e licenças serão conferidos novamente antes da execução correspondente.
