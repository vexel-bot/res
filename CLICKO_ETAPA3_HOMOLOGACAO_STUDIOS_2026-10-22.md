# Clicko — Etapa 3: homologação dos Studios e integração com a KLIC

Data de referência: **22/10/2026**, America/Sao_Paulo.
Checkout: `C:\Users\pedro\Downloads\res`.

## Parecer executivo

**Correções e validação técnica disponíveis concluídas. Homologação autenticada
da interface ainda pendente, por escolha explícita do usuário nesta etapa.**

O usuário escolheu “Concluir os testes técnicos e deixar a homologação autenticada
pendente”. Não foi criada conta, sessão, licença ou registro de cliente para
substituir essa sessão. A prévia sem login, autorizada em um pedido anterior,
permanece separada desta qualificação: ela não prova autenticação comercial.

Há produção e edição locais reais, por regras determinísticas, com projetos
canônicos editáveis e exportação Pillow/FFmpeg. A nova rodada passou nos testes
direcionados e no build. Um motion de 15 segundos foi criado pela rota KLIC,
editado, exportado em duas versões, recuperado após reinício e reproduzido até
o fim no navegador. Isso **não** comprova o fluxo de edição completo na UI.

Referência principal: [revisão de conclusão da Etapa 2](docs/audits/STAGE2_COMPLETION_REVIEW_2026-10-22.md).
Os relatórios anteriores e suas evidências foram preservados.

## 1. Ambiente e acesso

- `npm run dev:status` confirmou Express em 3018, FastAPI Studios em 8018 e
  prontidão do perfil isolado `.codex-runtime/stage1-local`.
- Banco, armazenamento e FFmpeg foram comprovados também por criação, render,
  download e recuperação após encerramento/reinício dos serviços.
- O perfil de prévia já usava o contexto de desenvolvimento autorizado no pedido
  anterior. **Não foi ativado um novo bypass para esta homologação.**
- O armazenamento local de governança não tinha credenciais cadastradas nem
  sessões de navegador no levantamento inicial. Não copiamos dados de produção.
- Na inspeção somente leitura, o Motion recusou o cliente selecionado com
  “Cliente não encontrado neste ambiente”. A governança não tem esse cadastro;
  o estado local da interface não substitui um vínculo autorizado no servidor.
- Não removemos o cabeçalho de cliente, não trocamos silenciosamente o escopo e
  não alteramos permissões para contornar essa recusa.

A confirmação de UI restringiu-se à navegação e ao estado de erro, em viewport
desktop disponível. Não houve edição de projeto por esse acesso de prévia.

![Estado de acesso preservado, com orientação e ações de recuperação](.codex-runtime/stage3-preview-scope-error.png)

## 2. Estado dos três Studios

| Área | Comprovado tecnicamente nesta rodada | Ainda não qualificado |
| --- | --- | --- |
| Motion Design | Projeto de 15 s, três cenas, nove camadas, títulos por palavras, formas/cartões, keyframes, easing, transformações 2D, fades, edição contextual, versões e dois MP4s reais | Fluxo completo autenticado no editor, seleção/toque e responsividade visual de todos os painéis |
| Vídeo | Importação de vídeo/imagem/áudio, cortes reais, duração, títulos, overlay, escala/rotação/opacidade, fades de vídeo/áudio, render, Range/download, biblioteca e recuperação | Montagem livre por modelo, geração cinematográfica e homologação visual autenticada |
| Imagem | Upload, tamanho/posição, crop, ajustes, texto/formas/camadas, cor, PNG, versões/restauração e preservação do original | Geração inédita por modelo, remoção automática de fundo e editor PhotoCraft compilado |

Gradiente, sombra e propriedades avançadas existentes permanecem no painel local.
A prévia Canvas não foi declarada como reprodução completa de vídeo/áudio:
os materiais temporais são reunidos pela prévia/exportação canônica FFmpeg.
Não há câmera/perspectiva 3D homologada.

## 3. Correções implementadas

### Comando de desfazer integrado à KLIC

“Desfaça a última alteração” não entrava no roteamento local. Agora, com projeto
em contexto, é encaminhado ao fluxo de produção sem chamar o provedor conversacional.
O backend prepara a composição da versão salva imediatamente anterior como
**plano revisável**, usando o catálogo existente de operações.

A aplicação cria uma nova revisão e mantém snapshots e exportações anteriores.
Não executa restauração invisível na conversa. Sem histórico, retorna uma
explicação; com seleção, pede desmarcar antes de uma restauração global. Locks,
escopo, assets, revisão esperada e idempotência continuam sendo impostos.
O snapshot deve pertencer ao mesmo documento, workspace e tipo de conteúdo.
O comando não depende de um modelo local disponível.

Essa operação significa restaurar a versão salva anterior. Não é uma pilha
multinível de undo/redo conversacional: desfazer novamente pode restaurar o estado
anterior à própria restauração. Undo/redo de alterações ainda locais continua
nos controles já existentes; não foi substituído por simulação.

### Pedidos incompletos passam a pedir o dado necessário

- “Troque a cor do cartão selecionado”: solicita #RRGGBB ou uma cor da marca.
- “Altere somente o título da terceira cena”: solicita o novo texto entre aspas.
- Duração sem valor/alvo inequívoco não altera o projeto por adivinhação.

Há regressões demonstrando ausência de alteração durante planejamento e pedidos
de esclarecimento. Quatro casos Python e o roteamento Node falharam antes das
correções: `stage3-before.*` e `stage3-routing-before.log`.

### Recuperação do projeto solicitado pela KLIC

Um rascunho de outro projeto podia prevalecer sobre `?document=...`.
O editor agora prioriza o projeto explicitamente solicitado e não recupera a
operação pendente de outro documento. O rascunho anterior é preservado no backup
local `:previous`. Abrir o mesmo projeto ou reabrir sem um link explícito mantém
a recuperação normal. O servidor continua sendo responsável por autorização.

### Usabilidade sem reconstrução do frontend

- Erro de abertura deixou de ser uma frase solta: há título, orientação,
  “Tentar novamente” e “Ver clientes e ambiente”, sem liberação indevida.
- Tipografia, acabamento e editor completo de keyframes foram agrupados sob
  demanda depois da área principal, evitando empurrar prévia/propriedades para baixo.
- Seletor de projeto, controles de reprodução e mensagens longas receberam
  ajustes de quebra e largura em telas pequenas.
- Mantidos tokens de tema, fonte do sistema, coral, componentes e navegação.

Tipagem/build aprovam essas alterações. Não declaramos que os painéis completos
foram aprovados visualmente em desktop/tablet/celular ou temas: a sessão real e
o cliente autorizado não estavam disponíveis. Os breakpoints existentes de
1200/640 px foram preservados e refinados, não substituídos.

## 4. KLIC, especialistas e orquestrador

A KLIC continua sendo a única conversa. Gemini, voz, histórico e configuração
de chaves não foram removidos ou substituídos. Nenhuma chamada paga foi executada.
AudiovisualAgent e ImageAgent continuam usando **regras determinísticas**.

O ensaio integrado percorreu o roteador real da KLIC, a ponte assinada e o
backend/banco/armazenamento reais, com governança isolada de teste. O fixture de
serviço não entrou no navegador nem foi apresentado como sessão legítima.
O fallback de modelo do ensaio é uma sentinela que falha fechado e conta chamadas;
não é uma resposta de IA usada para produzir o material.

| Pedido | Resultado técnico observado |
| --- | --- |
| Criar motion de 15 segundos sobre tecnologia e inovação | Plano audiovisual; seis elementos gráficos delegados ao agente visual; três cenas e nove camadas após revisão/aplicação |
| Trocar cor do cartão sem informar a cor | Esclarecimento, zero operações |
| Aumentar a duração da segunda animação sem valor | Esclarecimento, zero operações; sem retiming global |
| Mudar a animação selecionada para 3 s | Só o título selecionado retimado |
| Texto palavra por palavra | Revelação local no título selecionado |
| Alterar título da terceira cena | Solicita texto se ausente; aplica o texto explícito somente ao alvo correto |
| Deixar transições mais suaves | Keyframes de opacidade com easing; não é um motor avançado de transições |
| Desfazer última alteração | Plano de restauração revisável; composição anterior recuperada sem perda de histórico |

Testes adicionais cobrem seleção, plano corrompido, revalidação na aplicação,
revisão obsoleta, cancelamento/recuperação, recibos idempotentes, permissões,
custos e isolamento. Isso não comprova cancelamento de um modelo real em execução.

## 5. Prova principal de criação e exportação

Comandos reproduzíveis, no perfil isolado pronto:

```powershell
node --import tsx scripts/agents/stage2-live.ts --stage3
npm run dev:stop
# Reiniciar npm run dev:local e confirmar npm run dev:status antes de verificar:
.venv\Scripts\python.exe scripts/agents/stage2-verify.py --stage3
```

Os serviços foram efetivamente reiniciados entre produção e verificação.
Pasta nova: `.codex-runtime/stage3-validation`; evidências da Etapa 2 não foram
sobrescritas. Documento `da79ebea-c16e-412c-9393-173f3fb6b552`, revisão **11**,
dez snapshots, três cenas, nove camadas independentes.

O ensaio reduz explicitamente o projeto editável de 1280×720 para 640×360 para
renderização de QA nesta máquina; não apresenta essa saída como Full HD.

| Arquivo | Resultado | SHA-256 |
| --- | --- | --- |
| `motion-v1.mp4` | 15 s, 640×360, H.264/AAC; 471.511 bytes | `510e06d5845b9692cce7d12683b09d13a468dcc3b53f8be4bd6e5c22d3f510b0` |
| `motion-v2.mp4` | 15 s, 640×360, H.264/AAC; 455.613 bytes | `c594fafa5f3da64ff1c6dfb897a7177ae993bacdb39cba4b89c1716456e5b880` |

Após a primeira exportação, mudou-se somente o título selecionado para coral;
os outros oito elementos foram comparados e preservados. A primeira entrega
continuou recuperável byte a byte. Após reinício, ambos os hashes coincidiram e
os dois MP4s passaram por decode integral com FFmpeg.

Os arquivos `document-v1.json` e `document-v2.json` mantêm o projeto editável.
`evidence.json`, `verification.json` e `klic-creation.json` registram a cadeia.

![Quadro extraído do MP4 final, não uma imagem usada para simular renderização](.codex-runtime/stage3-validation/rendered-frame.png)

### Reprodução real do arquivo no navegador

O MP4 final foi aberto em um reprodutor HTML5 local temporário e reproduzido
até `currentTime=15`, `duration=15`, `ended=true`, `error=null`, 640×360.
Prova: `browser-playback.json` e `browser-playback.png`, na pasta acima.
O servidor temporário em loopback foi encerrado depois da conferência.

![Arquivo exportado reproduzido até o fim](.codex-runtime/stage3-validation/browser-playback.png)

**Isso comprova playback do arquivo, não criação/edição/exportação pelo editor
autenticado.** O quadro intermediário confiável acima foi extraído por FFmpeg.

## 6. Vídeo real e compartilhamento entre Studios

O teste canônico executado nesta rodada gerou fonte própria vermelha/azul,
importou vídeo, PNG e WAV, fez dois cortes, título animado, overlay com rotação/
escala e faixa de áudio com ganho/fades. O MP4 de 2 s teve pixels, samples de áudio,
duração, conteúdo do título, fade, Range/download e recuperação verificados.
É montagem de materiais próprios, **não geração cinematográfica por IA**.

Cópia preservada: `.codex-runtime/stage3-shared-media/video-trim-title-audio.mp4`.
SHA-256: `d39c09e5e9c43e1b57f09f15b1ca7b6bc1701c9485ba445b2746c8455b31330b`.
Fonte preservada na mesma pasta como `video-source.mp4`.

O teste novo `test_stage3_shared_media.py` produziu um cartão PNG no Image Studio,
reutilizou o asset no Motion e na timeline canônica de Vídeo, renderizou ambos e
conferiu a cor tangerina nos pixels dos MP4s. O PNG e o documento de imagem
permaneceram inalterados. Acesso por outro cliente recebeu 404.

Pasta `.codex-runtime/stage3-shared-media`:

- `shared-image.png`: original preservado, SHA-256
  `6d1acb79dc64bf2cd2faf6cceece421faa34872ea3e15fdd0bbeb792b46d761c`.
- `shared-motion.mp4`: 3 s, SHA-256
  `39de7fc576ca62e3a7c025481a569fd3df729a81ef6b1ff5f3adc17e7fd2f13f`.
- `shared-video.mp4`: 2 s, SHA-256
  `ed69870dac4e0ddbc11a93a9a03779faf1cacc80dd5b4a22d41fa285a827407a`.
- `shared-evidence.json`: duração, hashes, origem por ferramentas locais e
  preservação do original. O teste executa FFmpeg real; não é mock de mídia.

Uma composição PNG reutilizada é uma referência de mídia; não substitui ou
achata destrutivamente o projeto de origem. Projetos Craft nativos não são
convertidos à força para o formato de camadas local.

## 7. Testes e limites da cobertura

| Validação desta rodada | Resultado |
| --- | --- |
| Python direcionado, 13 módulos — `stage3-python.xml` | **125 aprovados, 18 pulados**, zero falhas/erros — 143 casos |
| Compartilhamento novo com render real — `stage3-shared.xml` | **1 aprovado**, zero pulos/falhas |
| Ponte autenticada/isolamento — `stage3-bridge.xml` | **3 aprovados**, zero pulos/falhas |
| `npm test`, Node/TypeScript | **238 aprovados**, zero falhas |
| `npm test`, privacidade Vite | **2 aprovados**, zero falhas |
| Controle do supervisor local | **3 aprovados**, zero falhas |
| `npm run lint` | Aprovado |
| `npm run build` | Aprovado |
| Ruff dos arquivos Python alterados | Aprovado |
| `git diff --check` | Aprovado; avisos LF/CRLF não são falhas |
| Ensaio KLIC/BFF/backend e persistência após reinício | Aprovado, duas entregas e hashes iguais |
| Playback HTML5 do MP4 final | 15 s completos, sem erro |

São **129 testes Python aprovados e 18 pulados** nas três rodadas sem sobreposição
da tabela. A suíte da ponte autenticada foi executada separadamente; seu resultado
está em `.codex-runtime/stage3-bridge.xml/.log`, sem substituir o ensaio de sessão
real do navegador. Os testes de autenticação Node mantêm a recusa do contexto de
desenvolvimento em produção e a recusa de identidades forjadas por cabeçalho.

Os 18 pulos continuam ligados à fixture histórica que procura FFmpeg/libx264 no
PATH. Os testes reais executados usam o binário privado com libopenh264. Não se
alteraram essas condições para esconder pulos. Não foi rerodada a suíte Python
global da plataforma nem declaradas resolvidas suas falhas históricas fora do escopo.

Os fixtures de autoridade, provedores sentinela e contratos de modelo simulados
estão restritos aos testes. Não são prova de inferência real ou sessão comercial.
Na construção das novas provas, ajustaram-se dados do próprio ensaio ao contrato
existente (chave idempotente com pelo menos oito caracteres e comparação de
leituras GET antes/depois, evitando diferença de serialização UTC entre POST/GET).
Não se enfraqueceram validações da aplicação para aprovar testes.

Logs em `.codex-runtime/stage3-*.log/.xml`: before, routing-before, regression,
python, shared, node, control, types, build, live, persistence e diff-check.

## 8. Bloqueios e dependências remanescentes

1. **Homologação completa autenticada:** pendente por opção do usuário. É preciso
   conta/sessão legítima e cliente com vínculo autorizado para o ensaio de UI.
   Não foram criados cadastros nem retiradas proteções para fabricar esse resultado.
2. **Desktop/tablet/celular e temas do editor completo:** não qualificados
   visualmente; o estado de acesso foi inspecionado no desktop e as alterações
   responsivas compilaram. Isso não equivale a testar os painéis carregados.
3. **Craft:** novo preflight em `stage3-craft.json` confirmou PhotoCraft,
   FilmCraft e EffectCraft como `blocked-missing-build`, sem artefatos nativos/
   browser e sem Docker Linux disponível. Não foi instalado nem compilado um motor.
4. **Modelos gratuitos:** nenhum modelo foi instalado ou inferido. Runtime,
   pesos, licença, memória, qualidade e desempenho ainda precisam de comprovação.
   A configuração existente de Gemini não prova disponibilidade de cota gratuita.
5. **Voz e Gemini:** código e configurações preservados; microfone, síntese e
   conversa real com modelo não foram acionados nesta etapa de orçamento zero.

## 9. Arquivos e arquitetura preservada

Arquivos de implementação alterados nesta etapa:

- `backend/app/services/studios/local_editing.py`: esclarecimentos de cor/texto.
- `backend/app/services/studios/local_agents.py`: proposta determinística de restauração.
- `backend/app/services/studios/agent_orchestrator.py`: restauração com o pipeline validado existente.
- `server/klic/localProduction.ts` e teste: roteamento do comando de desfazer.
- `src/studios/local/LocalProductionStudio.tsx`: recuperação de link, erro acionável e controles sob demanda.
- `src/studios/local/localModel.ts` e teste: regra de prioridade de recuperação.
- `src/studios/local/local-production.css`: quebra, largura e controles pequenos.
- `src/studios/ClickoStudioView.tsx`: navegação de recuperação no editor local.
- `backend/tests/test_stage3_homologation.py` e `test_stage3_shared_media.py`: regressões e mídia real.
- `scripts/agents/stage2-live.ts` e `stage2-verify.py`: modo `--stage3`, pasta independente e cenário ampliado.
- README, CHANGELOG, operação dos agentes e este relatório.

Reutilizados: React/TypeScript, componentes/tokens Clicko, KLIC/BFF Express,
ponte assinada, FastAPI, contratos canônicos, banco/eventos/recibos existentes,
Pillow, Canvas e compilador FFmpeg. Nenhuma dependência nova, migração, frontend
reconstruído, API paga, chave alterada, deploy ou push.

## 10. Próxima etapa

Executar o checklist autenticado das fases 2/3/5/6/8 com uma conta e cliente
autorizados: criar/editar pelo navegador, controles manuais/undo/redo, temas,
desktop/tablet/celular, download e reabertura. Depois, qualificar um runtime/modelo
gratuito e os motores Craft em uma infraestrutura compatível, sem presumir
qualidade ou disponibilidade por simples presença de arquivos.

**Custo externo desta etapa: R$ 0.** O escopo técnico disponível foi concluído;
a homologação completa da experiência de usuário não recebeu um rótulo indevido
de “100% finalizada”. A Clicko local permaneceu saudável em 3018/8018 após as provas.
