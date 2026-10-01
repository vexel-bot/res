# Brief de replanejamento — autonomia criativa para vídeo

**Estado:** iteração audiovisual rejeitada pelo usuário.  
**Escopo da rejeição:** 12 pilotos + 24 calibrações atuais.  
**Publicação externa:** zero.  
**Escala 64:** não despachada.  
**Próxima produção:** bloqueada até aprovação de um novo plano.

O estado executável deste gate está em `artifacts/validation/video-creative-pilot/factory-20260901-v1/creative-replan-state-20260901-v2.json`: 0/9 decisões aprovadas, limite de um golden e lote desautorizado.

## O que foi rejeitado

- os 36 MP4s atuais como resultado audiovisual;
- o uso de animatics placeholder transcodificados como se fossem vídeos editados;
- a progressão para calibração e escala sem um piloto final aprovado;
- qualquer alegação de qualidade de edição baseada apenas em codec, resolução, duração ou checksum.

Os arquivos permanecem somente como evidência de que a infraestrutura consegue executar jobs, aplicar QC técnico e preservar lineage. Eles não são referência estética nem ponto de partida criativo.

## O que permanece válido

- contratos de brief, mensagem, roteiro, recipe, direção visual, som, storyboard e learning;
- timeline multiasset, operações de edição, undo/redo e export FFmpeg;
- MotionGraph determinístico e goldens técnicos;
- inteligência assistida com decisões reversíveis;
- idempotência, retry, cancelamento, budget e gates de promoção;
- gates de direitos, consentimento, identidade, voz e publicação;
- bloqueio fail-closed da escala e dos providers avançados.

Esses itens são infraestrutura e governança. A aprovação deles não valida uma direção criativa.

## Diagnóstico para o novo plano

O erro central foi avançar a fábrica antes de existir um **golden video final**. No novo ciclo, qualidade audiovisual precisa ser demonstrada antes de multiplicação.

Nova ordem recomendada para discussão:

1. definir objetivo de negócio, audiência, nicho, oferta e canal do primeiro vídeo;
2. refazer a análise das referências em evidência observável: hook, montagem, composição, texto, motion, som, ritmo e CTA;
3. escolher uma única família e um único conceito para o golden;
4. aprovar roteiro/copy, mapa de assets e storyboard antes da edição;
5. produzir um teste de linguagem curto, com frames e áudio reais;
6. produzir um vídeo completo, assistir e revisar;
7. somente após aprovação, derivar três variações, depois 12, depois 24 e finalmente 64;
8. manter publicação, avatar, rosto e voz como autorizações separadas.

## Decisões que o novo planejamento precisa fechar

- qual é o primeiro tema/oferta e qual transformação deve comunicar;
- duração, plataforma e objetivo: orgânico, anúncio, educação ou prova;
- presença ou ausência de apresentador;
- origem das imagens: gravação própria, stock licenciado, geração ou combinação;
- voz: humana autorizada, locução licenciada ou vídeo sem voz;
- proporção ideal entre footage, presenter/split screen, motion e híbrido cinematográfico;
- referências obrigatórias e elementos que não devem ser copiados;
- critérios explícitos de aprovação para copy, imagem, ritmo, motion, som e CTA;
- teto de custo e tempo por golden e por variação.

## Gate de reinício

Nenhum job de nova produção deve começar até que o novo plano tenha:

- um brief aprovado;
- uma matriz de referência verificável;
- uma direção criativa escolhida;
- um mapa de assets com direitos;
- uma rubrica de qualidade audiovisual;
- um responsável humano pelo aceite do golden.

Depois desse gate, o sistema reinicia por um único golden. A fábrica 12+24+64 continua bloqueada até evidência audiovisual aprovada.
