# Motion contextual e aquisição autônoma de materiais

Implementação de setembro de 2026, restrita ao fluxo de edição de vídeo do res.

## Contrato editorial executável

O plano contextual V2 preserva os planos anteriores e acrescenta `visualRole`,
`depthTreatment`, `motionCues`, `cameraCues`, `keywordCues` e requisitos detalhados
de material. A LLM escolhe relações semânticas. O compilador registrado resolve
grupos, posições e keyframes, sem executar código retornado pelo modelo.

`res.editorial-components.v2` contém os perfis `gentle`, `standard`, `emphasis`,
`camera_push`, `stagger`, `path_flow` e `deliberate_hold`. As cenas são compiladas
em três grupos: fundo, conteúdo e tipografia. Câmera e parallax transformam os
grupos; a tipografia permanece independente. `emphasis` produz antecipação,
overshoot e estabilização em `0,92 → 1,04 → 1,00`.

A auditoria usa o grafo e frames decodificados do MP4. Ela registra trilhas de
câmera, easing, overshoot, palavras-chave, saliência simultânea, diferença de
pixels dentro da região dos elementos e evidência dos estados inicial/final de
cada cue. Isso não concede aprovação humana.

## Registro de materiais

Todos os provedores usam o mesmo manifesto de capacidade, configuração,
aquisição e custo. A ordem efetiva é projeto, catálogo, stock licenciado,
componente procedural, geração original e impedimento.

- Pexels descobre fotos e vídeos com orientação e duração. O arquivo é baixado
  para quarentena, validado e inspecionado antes de entrar no plano. A origem,
  autor e licença permanecem no recibo. A API exige credencial.
- Brandfetch oferece uma prévia por domínio. A Logo API é tratada como hotlink
  de descoberta; ela não entra na exportação. O render requer arquivo autorizado
  do cliente, kit oficial ou acesso compatível à Brand API.
- Componentes Lucide continuam locais e determinísticos. Eles só atendem a uma
  necessidade genérica de ícone. Filmagem, logo, objeto isolado ou requisito de
  alfa nunca recebem esse fallback.
- Gemini Image cria candidatos originais. O job fica ligado à revisão e ao run,
  reserva orçamento antes da submissão e passa pela mesma inspeção visual. O
  arquivo é classificado como `generated_original`, nunca como material oficial.
- O recorte local roda em processo separado com `rembg` e U²-Net pequeno. O
  sistema não baixa pesos: exige `u2netp.onnx`, versão operacional fixada e
  checksum SHA-256. O código e a licença do modelo ficam no recibo.

Sem credencial ou sem direitos suficientes, o requisito permanece bloqueado.
Uma falha de provedor não autoriza uma substituição semanticamente inferior.

## Orçamento do piloto

`STUDIO_PRODUCTION_TEST_BUDGET_USD` limita cada correlação de produção em
development/test. A política `res.motion-pilot.v5` mantém a distribuição antiga
para execuções de até US$1. A política atual é `res.motion-pilot.v6`. Em uma execução autorizada de US$2, os limites são
valores absolutos: US$0,40 para direção e composição, US$0,50 para imagem,
US$0,80 para inspeção e crítica e US$0,30 de reserva para uma correção limitada,
inclusive de direção ou composição. Inspeção de materiais e
crítica final possuem subtetos separados de US$0,40; somente a crítica final
pode utilizar a reserva. Vídeo generativo continua com alocação zero nesta
política. Cada job persiste categoria, subcategoria, valor e limites antes da
chamada externa.

Os tetos do provedor continuam valendo. Quando os dois existem, aplica-se o
menor. Produção registra consumo sem herdar esse teto de teste.

## Qualificação

O teste real do HyperFrames 0.8.31 exporta uma composição do compilador com
câmera Bézier, blur, grupos semânticos, overshoot e tipografia cinética. O MP4 é
decodificado pela auditoria e precisa apresentar as trilhas e evidências de
ação esperadas. Testes adicionais cobrem compatibilidade V1/V2, conflito entre
cue e track explícita, Pexels sem credencial, Brandfetch apenas para prévia,
recorte sem modelo fixado, idempotência e envelope de US$1.

O piloto autônomo de montagem mista só deve renderizar depois que um provedor
de filmagem ou de geração original estiver configurado. Enquanto ambos estiverem
indisponíveis, o resultado correto é um impedimento, preservando o vídeo anterior.

## Continuidade e legibilidade qualificadas

Uma transformação entre formatos reutiliza o mesmo arquivo adquirido ou uma
`contentIdentity` explícita em todos os estados procedurais. O compilador
preserva as razões 0,64, 1,00 e 1,68 para vertical, quadrado e horizontal e
interpola a geometria do viewport anterior até a seguinte. Um fade, um rótulo
igual ou duas formas parecidas não comprovam continuidade.

Anotações e o material anotado compartilham um grupo de transformação. Assim,
um push-in não separa o marcador do alvo. A auditoria registra proporções,
arquivo e identidade do conteúdo de cada estado e bloqueia perda de identidade.

O runtime desativa quebra arbitrária no interior de palavras. O compilador e a
recuperação de overflow tentam alargar ou elevar a caixa antes de reduzir o
tipo; a informação essencial não desce do equivalente a 16 px numa apresentação
de 300 px. O checksum de um material comprova somente identidade do arquivo:
uma nova ação, critério, intervalo ou recorte requer evidência compatível.

As regras selecionadas de `higgsfield-ai/skills` entram como conhecimento com
origem e limites: função explícita de cada referência e correção visual
localizada por causa. Elas não são anunciadas como capacidade executável nem
importam motores ou modelos externos para o res.

## Referências operacionais

- [Pexels API](https://www.pexels.com/api/documentation/)
- [Brandfetch Logo API](https://docs.brandfetch.com/logo-api/overview)
- [Brandfetch Brand API](https://docs.brandfetch.com/brand-api/overview)
- [rembg](https://github.com/danielgatis/rembg)
- [U²-Net](https://github.com/xuebinqin/U-2-Net)
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [YouTube API developer policies](https://developers.google.com/youtube/terms/developer-policies)
