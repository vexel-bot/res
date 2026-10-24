# Clicko — revisão de conclusão da Etapa 2

Data: **22/10/2026**, referência do cliente: America/Sao_Paulo.
Projeto verificado: `C:\Users\pedro\Downloads\res`.

## Parecer

**A entrega anterior não estava totalmente encerrada.** Havia um fluxo local
real funcionando, mas também falhas de edição contextual e lacunas de homologação.
Nesta revisão foram reproduzidos e corrigidos os casos de falha descritos abaixo,
reexecutados os testes e o ensaio integrado, e verificada novamente a persistência.

O resultado atual é um **MVP local determinístico validado tecnicamente**,
não uma plataforma generativa totalmente homologada. Não é correto afirmar que
três modelos de IA estão inferindo ou que toda a interface passou por validação
manual. Permanecem explicitamente pendentes a sessão legítima para o ensaio da
UI, os modelos/runtimes e os motores Craft compilados. Não houve contorno desses
requisitos para fabricar uma conclusão.

## 1. Estado por área

| Área | Situação comprovada |
| --- | --- |
| KLIC | Roteador real da conversa encaminha criação/edição ao backend; Gemini e voz preservados, sem chamada paga no ensaio |
| Especialistas | AudiovisualAgent e ImageAgent operacionais por regras; delegação real de formas registrada; **sem inferência de modelo** |
| Orquestrador | Tarefa, responsável, escopo, revisão, comandos tipados, histórico, tratamento de erros, recibo e limite de custo |
| Motion Design | Criação textual-modelo, três cenas, nove camadas, texto por palavras, keyframes/easing, formas, gradiente, transformações 2D e exportação real |
| Vídeo | Editor canônico FFmpeg, cortes/mídia/áudio/títulos/fades/exportação preservados; planejamento livre de montagem por IA não homologado |
| Imagem | Composição e ajustes locais, texto/formas/crop/camadas/PNG e compartilhamento de assets; sem geração/remoção automática de fundo por modelo |
| Projeto editável | Documento canônico, elementos independentes, versões, restauração e entregas separadas; não se confunde com MP4 ou projeto Craft homologado |
| Interface | Código integrado e aprovado em tipagem/build; navegação atual chega ao login, sem sessão para validar o editor completo |
| Operação | Prévia reiniciada e saudável em 3018/8018; provedores pagos desligados no perfil QA isolado |

O [relatório da implementação](STAGE2_AGENT_EXPERIENCE_2026-10-22.md) contém o
inventário detalhado. Esta revisão complementa e corrige o julgamento de conclusão;
não substitui resultados históricos por contagens de uma rodada diferente.

## 2. Problemas encontrados e corrigidos

Os quatro primeiros casos foram transformados em testes **antes** da correção:
os quatro falharam. Evidências em `.codex-runtime/step2-review-before.log/.xml`.

1. **Cor fora do alvo:** “Altere para #F28500”, com um cartão selecionado, podia
   cair na regra antiga e alterar os títulos. Agora a cor respeita a seleção.
2. **Duração com efeito global indevido:** mudar a duração da animação selecionada
   podia retimar o projeto inteiro. Agora retima somente os elementos-alvo,
   preservando a timeline e os demais elementos; operações globais pedem retirar
   a seleção. Intervalos e limites continuam validados.
3. **Texto literal interpretado como comando:** palavras como “coral” e “sombra”
   dentro do título entre aspas podiam acionar alterações de estilo. O conteúdo
   entre aspas é tratado como dado. Perguntas informativas não viram edições.
4. **Metadados inválidos de cena:** dados que não eram uma lista podiam ser salvos
   e quebrar a navegação. O backend valida os campos conhecidos, tempos e IDs;
   o frontend tolera rascunhos legados malformados sem lançar exceção.

Também foram fechados os seguintes casos de fronteira:

- Cena inexistente/zero/dez não pode virar uma edição global por erro de parsing.
- O backend impõe o escopo da seleção tanto ao validar o plano quanto antes de
  uma aplicação nova; não confia apenas na obediência do planejador/modelo.
- Recibos já comprometidos continuam replayáveis sem executar outra mutação,
  inclusive de uma regra antiga. Alteração do conteúdo da operação não ganha
  esse privilégio: o fingerprint deve continuar idêntico.
- Seleção tem limites de quantidade e tamanho de ID. Há um botão explícito de
  desmarcar a seleção para comandos globais.
- Um planejamento em `cancel_requested` bloqueia uma segunda computação até
  terminar. Isso **não** comprova interrupção imediata do compute de um Ollama real.
- O controle `dev:status` tinha timeout de 3 s, menor que a própria checagem de
  saúde de 4 s. Podia terminar com código zero e saída vazia. Agora espera até
  7 s e retorna falha explícita no timeout; o ensaio de aceitação também informa
  claramente quando o perfil ainda não está pronto.

Nenhum modelo foi autorizado a executar shell, código arbitrário, URLs ou
comandos fora do catálogo. Autenticação, revisão, direitos de mídia, validações
financeiras e preservação de originais continuam ativos.

## 3. Novas provas funcionais

Foram preservadas as evidências anteriores em `.codex-runtime/step2-validation`.
A revisão grava separadamente em `.codex-runtime/step2-review-validation`:

```powershell
node --import tsx scripts/agents/stage2-live.ts --review
```

O ensaio usa a conversa KLIC e a ponte assinada reais, com governança própria
de fixture e backend/banco/armazenamento/FFmpeg reais no perfil isolado. O fixture
não é uma sessão comercial do navegador. Seu fallback de modelo é uma sentinela
que falha fechado e conta chamadas; **nenhuma resposta simulada de LLM cria a mídia**.

Comprovado novamente:

1. Pedido textual de motion de 15 s sobre tecnologia/inovação.
2. Encaminhamento audiovisual e seis solicitações de formas ao agente visual.
3. Plano determinístico → aplicação → três cenas, nove camadas, 360 quadros/24 FPS.
4. Ajuste QA explícito de dimensão para 640×360 sem achatar o projeto.
5. Revelação do texto por palavras e dinamismo 2D da primeira cena.
6. Primeira renderização e exportação MP4.
7. Alteração posterior somente do título selecionado; os outros oito elementos
   comparados e preservados.
8. Segunda renderização; a entrega anterior continua disponível byte a byte.
9. Cinco versões anteriores e documento atual na revisão 6.
10. Após reiniciar os serviços, download com os mesmos hashes, documento
    reaberto e decode integral de ambos os MP4s sem erro.

Verificação após reinício:

```powershell
.venv\Scripts\python.exe scripts/agents/stage2-verify.py --review
```

Documento de QA: `02c39e6a-57ca-4707-9c92-4830ea7de9d6`.

| Entrega nova | Características | SHA-256 |
| --- | --- | --- |
| `motion-v1.mp4` | 15 s, 640×360, H.264/AAC | `d9bbb2ec45f37bc6f3b3e74c837b42e7f1fb0bb391b824c3e34e2e413ace92d7` |
| `motion-v2.mp4` | 15 s, 640×360, H.264/AAC | `e59049ff866e416ad3934bc2ffdee2f0fd962ffc09fdf63c9e6f9b51b1110cf6` |

Os arquivos `document-v1.json`/`document-v2.json` são os projetos editáveis.
`evidence.json`, `verification.json`, `klic-creation.json` e os logs registram a
cadeia. `rendered-frame.png` é extraído do MP4, não uma imagem usada para fingir
exportação. Os dois MP4s anteriores também foram recuperados com seus hashes
originais; a revisão não os substituiu no armazenamento.

## 4. Testes atuais e limites das provas

| Verificação | Resultado |
| --- | --- |
| Python direcionado, 12 módulos | **118 aprovados, 18 pulados, zero falhas/erros** — 136 casos |
| `npm test`: Node/TypeScript | **237 aprovados**, zero falhas |
| `npm test`: privacidade Vite | **2 aprovados**, zero falhas |
| Controle do supervisor local | **3 aprovados**, zero falhas |
| `npm run lint` | Aprovado |
| `npm run build` | Aprovado |
| Ruff do backend e testes acrescentados | Aprovado |
| `git diff --check` | Aprovado; avisos usuais LF/CRLF não são falhas de código |

Os três testes de controle usam servidor de controle sintético para comprovar
resposta após 3,5 s, timeout explícito e supervisor ausente. Não são provas de IA.
Os testes de plano corrompido/recibo legado usam fixtures isoladas, não dados de clientes.
Os 13 casos novos anteriores, mais dois de perguntas informativas, protegem os
limites de edição auditados. Reexecuções parciais não foram somadas à rodada final.

Os 18 pulados continuam ligados à fixture histórica que procura FFmpeg/libx264
pelo PATH. Os testes reais do compilador canônico usam o binário privado com
libopenh264. Não se alteraram fixtures para esconder esses pulos.

**Não foi executada uma homologação global da plataforma.** A suíte Python global
tinha falhas históricas fora do escopo; os resultados anteriores não foram
renomeados como aprovações atuais. A cobertura acima é dirigida à etapa entregue,
à integração e aos controles financeiros/acesso pertinentes.

Logs desta revisão em `.codex-runtime/`:

- `step2-review-before.log/.xml`: quatro falhas reproduzidas antes da correção.
- `step2-review-delivery-core.log/.xml`: rodada Python de entrega.
- `step2-review-node.log`, `step2-review-control.log`.
- `step2-review-types.log`, `step2-review-build.log`, `step2-review-diff-check.log`.
- `step2-review-live-final.log` e pasta `step2-review-validation`.

## 5. O que continua pendente

### Interface autenticada

A ferramenta de navegação recuperou a rota real de Motion Studio e constatou
“Acesse sua conta”. Sem uma sessão autorizada, não foram executados os fluxos
manuais completos de desktop/mobile e temas, importação, edição, recuperação,
exportação/download pela UI. Build e contratos HTTP não substituem essa prova.
Não foram criados cookie, conta, licença ou bypass para avançar.

**Para fechar esta pendência:** entrar normalmente na prévia com uma conta
autorizada e manter a aba aberta para a homologação do editor.

### Inferência e motores avançados

O novo levantamento encontrou aproximadamente 7,71 GiB de RAM total e 0,96 GiB
livre no instante medido, Intel UHD integrada, sem Ollama/Torch/Docker ou pesos
locais nos diretórios usuais. Não é uma medição de VRAM dedicada nem um benchmark
de inferência. Nada pesado foi instalado ou baixado sem autorização.

PhotoCraft, FilmCraft e EffectCraft continuam `blocked-missing-build`, sem
artefatos nativos/WASM homologados. A avaliação de comandos locais não libera
falsamente esses motores. Geração cinematográfica, imagem por modelo, remoção
automática de fundo, gráficos avançados, câmera/perspectiva 3D e interpretação
livre continuam fora da capacidade comprovada. As transformações entregues são 2D.

**Para fechar a parte de IA:** disponibilizar runtime/modelo gratuito compatível,
com origem/licença e memória verificadas, e executar benchmark real de JSON,
qualidade, tempo, cancelamento e consumo. Gemini gratuito da conta também não
foi presumido. A configuração conversacional atual da KLIC permanece preservada.

## 6. Arquivos alterados nesta revisão

- `backend/app/services/studios/local_editing.py`: alvo, literal, duração local e cenas inexistentes.
- `backend/app/services/studios/local_agents.py`: regras e perguntas sem edição.
- `backend/app/services/studios/agent_orchestrator.py`: escopo, replay e concorrência/cancelamento.
- `backend/app/domain/studios/agents.py`: limites de seleção.
- `backend/app/domain/studios/local_composition.py`: validação de cenas.
- `src/studios/local/LocalProductionStudio.tsx`, `localModel.ts` e teste: desmarcar/validar cenas legadas.
- `backend/tests/test_stage2_completion.py`: regressões e fronteiras.
- `scripts/dev-local.mjs`, `scripts/dev-local-control.test.mjs`: controle local robusto e testes.
- `scripts/agents/stage2-live.ts`/`stage2-verify.py`: pasta de revisão separada e aviso de prontidão.
- README, CHANGELOG, arquitetura e relatórios.

## 7. Custos, operação e conclusão

**R$ 0 em serviços externos e zero chamadas de modelo/TTS pago nos ensaios.**
Não houve instalação pesada, alteração de credenciais, dados reais de clientes,
migração destrutiva, deploy ou push. A árvore já estava modificada e foi preservada.

O perfil local está saudável em `http://127.0.0.1:3018`, com Studios em 8018,
dados QA persistentes e flags pagas desligadas. `npm run dev:status` confirma
prontidão; `npm run dev:local` inicia novamente se o processo for encerrado.
Isso não é instalação como serviço do Windows nem garantia de execução após reinício do computador.

**Conclusão:** as correções locais e a revalidação técnica foram concluídas.
A ordem completa não deve receber o rótulo “100% homologada” enquanto a UI
autenticada e as capacidades dependentes de modelo/motores não forem comprovadas.
O próximo passo imediato é a sessão legítima para o ensaio da interface, sem
necessidade de enviar senha a esta conversa.
