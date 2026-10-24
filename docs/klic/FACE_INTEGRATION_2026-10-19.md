# KLIC — integração da Face do AI Studio

## Resultado e origem

A representação visual da KLIC usa agora a geometria e as equações do projeto `ai-studios-novo/`, sem substituir o aplicativo Clicko pelo demonstrador.

- Origem: https://github.com/vexel-bot/res/tree/ai-studios-novo/ai-studios-novo
- Commit consultado: `68abe189c3cbd360b82044667d1f9dc95d99c006`.
- Branch de trabalho mantida: `codex/klic-atualizacao-20260823`.
- Integração por recuperação seletiva do código, sem merge, reset, force push ou alteração de contratos de API.
- As alterações locais preexistentes de Studios, backend e demais módulos foram preservadas. Não houve commit/push nesta entrega.

## Arquitetura e componentes reaproveitados

`AIChatView` e `FloatingAIAssistant` continuam responsáveis pelas conversas, histórico, compositor, anexos, modos, abertura/fechamento e callbacks. `useKlicVoice` mantém o microfone, MediaRecorder, limites de gravação, transcrição, síntese, reprodução, interrupções, erros e encerramento. A face não solicita permissão nem possui serviço de áudio próprio.

O contrato `KlicPlasma` foi mantido para preservar todos os pontos de montagem e alvos acessíveis. Seu conteúdo antigo foi substituído por `KlicHologram`, que é somente a camada React do canvas. O nome compatível não significa que o plasma antigo continue sendo renderizado.

Fluxo ativo:

```text
useKlicVoice → phase + audioSignal (amplitude, graves, agudos, origem e timestamp)
  → AIChatView / FloatingAIAssistant / KlicVoiceSession
  → KlicPlasma → KlicHologram
  → mountKlicHologram + HologramCommunication + ThemeProvider
  → KlicFaceSimulation → Canvas 2D
```

Foram reutilizados o ThemeProvider, a interpolação de tema de 400 ms, o ciclo rAF, o observador compartilhado de visibilidade, o tratamento local de pointer events e os analisadores de áudio já existentes. Não foi acrescentada dependência.

## Correspondência com o projeto de origem

| Arquivo da origem | Uso na Clicko |
| --- | --- |
| `src/types.ts` | Tipos preservados em `src/klic/face/types.ts`. |
| `src/utils/sphereGenerator.ts` | Geometria adaptada em `src/klic/face/sphereGenerator.ts`, com as mesmas 72 fitas, distribuição, ondas e atributos físicos. |
| `src/components/ParticleSphereCanvas.tsx` | Equações adaptadas em `faceSimulation.ts`; montagem React e desenho integrados aos componentes existentes. |
| `src/utils/voiceAnalyzer.ts` | Parâmetros visuais em `voiceModulation.ts`; microfone singleton e cadência simulada não foram importados. |
| `src/App.tsx` | Analisado, não importado; o roteamento e o aplicativo Clicko foram mantidos. |
| `src/index.css` | Analisado, não importado; sem fonte externa, fullscreen global ou bloqueio de rolagem. |
| `package.json` | Analisado, sem importar bundler/dependências do demo. React/TypeScript/Canvas nativos são suficientes. |

A linhagem detalhada está também em `src/klic/face/SOURCE.md`.

## Comportamento implementado

### Ajuste posterior de interação

O clique na esfera central da aba KLIC não inicia mais a conversa por voz; ela é um elemento visual, não um botão de voz. Os controles explícitos de voz do compositor permanecem operacionais. Apenas essa esfera central recebe `particleInteraction="full"`, conservando a dispersão ao passar o ponteiro.

Todas as miniaturas — launcher, cabeçalho, estado vazio, avatares e outros pontos — usam por padrão `click`: movimento orgânico contínuo e resposta breve ao clique, sem campo de repulsão por hover ou arraste. O clique continua propagando para o controle existente de abrir/fechar o balão, sem bloqueio de navegação. A mudança de modo limpa o campo de força sem recriar o canvas. A sessão de voz também usa esse modo sem hover.

Testes de interação cobrem miniaturas sem reação ao hover, ausência de bloqueio de clique/toque, ativação por teclado, limpeza dos listeners e troca de modo sem reconstrução. Rodada após este ajuste: tipagem e build aprovados; 218 testes aprovados. A validação visual desse ajuste não pôde ser executada porque o uso local do navegador permanece desabilitado nas configurações do Work.

- Face completa com 6.760 micropartículas da distribuição original, 72 fitas, perspectiva e ordenação exata por profundidade. Equipamentos mais limitados usam prefixos distribuídos por todas as fitas, até o mínimo de 5.040 pontos na versão completa.
- Movimento harmônico em repouso, respiração, rotação lenta, inclinação, deformação de fitas e profundidade. Sem superfícies sólidas, rosto humano, imagens sequenciais ou malhas.
- Repulsão localizada, transferência de movimento, onda de interação e molas com amortecimento. Integração temporal com subpassos e limites de estabilidade; a recomposição segue a forma em movimento, não uma fotografia inicial.
- Mouse e toque locais; sem `touch-action:none` global, captura do ponteiro ou bloqueio de rolagem. Arrastar partículas não dispara o callback de voz; toque/clique deliberado e ativação por teclado continuam disponíveis.
- Cor-base `#6EB8F5`, variações de profundidade da mesma família e brilho modulado por áudio. Tema claro aumenta contraste sem introduzir fundo preto/quadrado. Tema escuro mantém a composição transparente sobre o fundo nativo.
- Tema, estados e sinais de áudio atualizados sem remontar o canvas ou reiniciar a geometria.
- Respeito a `prefers-reduced-motion`, DPR limitado, redimensionamento proporcional, pausa fora de vista/em aba oculta e recuperação de perda de contexto 2D.
- Recursos e listeners liberados no unmount, sem atualizações React por partícula/quadro.

Todas as representações usam a mesma implementação: tela principal, sessão de voz, launcher flutuante, cabeçalho do mini chat, estado vazio e avatares de mensagens. Avatares de 20–34 px usam 288 pontos e launcher de 54–60 px usa 1.152; a redução é óptica e de custo, não outra identidade. Compactos desenham em aproximadamente 30 FPS, sem tratar essa cadência intencional como lentidão.

## Integração real de áudio

`HologramCommunication` aceita apenas amostras recentes (menos de 250 ms), da origem correspondente ao estado: `microphone` em Listening e `playback` em Speaking. Sinais ausentes, expirados ou incompatíveis decaem para silêncio.

As amostras de tempo fornecem RMS; os bins de frequência fornecem graves/agudos. Esses dados modulam raio, relevo, ondulações acústicas, microvibração, tamanho e brilho. A visualização mantém movimento orgânico quando não há voz, sem inventar volume ou cadência silábica.

O fluxo de microfone continua o mesmo: captura já existente → análise → transcrição. A reprodução continua usando o `HTMLAudioElement` existente e seu analisador. O balão flutuante agora propaga o mesmo `audioSignal` à sessão de voz e à identidade compacta; não abre uma segunda captura.

## Arquivos desta integração

- Novos: `src/klic/face/{types,sphereGenerator,voiceModulation,faceSimulation}.ts`, `faceSimulation.test.ts` e `SOURCE.md`.
- Adaptados: `src/klic/hologramRenderer.ts`, `hologramRenderer.test.ts`, `hologramInteraction.ts`; `src/components/KlicHologram.{tsx,css}`, `KlicPlasma.{tsx,css}`, `AIChatView.tsx`, `FloatingAIAssistant.tsx`.
- Limpeza visual: remoção de `KlicPlasmaSignature.css` e das regras exclusivas de camadas/keyframes do plasma em `src/index.css` e `CreativeWorkspace.css`. Dimensões, identidade textual, alvos interativos e estilos do restante da plataforma foram mantidos.
- Documentação: este relatório e apontamentos de versão nos relatórios históricos de holograma.

A captura/medição de áudio em `useKlicVoice.ts` e `audioAnalysis.ts`, assim como `KlicVoiceSession`, já estavam presentes no trabalho local anterior e foram reaproveitadas. Não foram trocados pelos serviços do demo. Modelos experimentais anteriores não importados pelo renderer ativo foram preservados para não descartar trabalho local da tarefa cancelada; não entram na execução da face.

## Validação executada

- `npm run lint`: aprovado (`tsc --noEmit`, verificação disponível no projeto).
- `CLICKO_TEST_CONCURRENCY=1 npm test`: 216 testes aprovados, zero falhas na rodada final.
- `npm run build`: aprovado, incluindo Vite e bundles do servidor/worker.
- `git diff --check`: aprovado.
- Testes da nova geometria: origem das equações, atributos físicos, todas as fitas nos prefixos, Z-sort, continuidade Idle, resposta a energia e espectro, onda de interação, recomposição, consistência em 30/60/120 FPS e movimento reduzido.
- Testes do renderer: contexto 2D único, superfície reutilizada, DPR, transparência, tema sem remontagem, pausa, recuperação de contexto, descarte e brilho por áudio.
- Testes reaproveitados: sinais frescos/expirados, análise de amostras, reprodução, mouse/toque, supressão de clique após drag, permissões de conversação, persistência, streaming, cancelamentos e isolamento de escopo.

### Conferência visual realizada antes da interrupção

- Tela principal em escuro e claro; mudança pelo seletor oficial mantendo a face montada; sem fundo quadrado nem camadas antigas no DOM.
- Desktop e viewports 390×844 e 320×568, sem overflow horizontal da página; componente com 252 px, 220 px e 170,4 px, respectivamente, conforme o layout existente.
- Dispersão pelo mouse e retorno ao sair da área; nenhum início de microfone após drag.
- Abertura/fechamento do mini chat, avatares/launcher, painel de conversas/histórico e entrada de texto, inclusive 1/2/3/M sem os atalhos globais do demo.
- Idle, Listening e Speaking na fixture local de desenvolvimento, com amostras reais de um sinal local e de um WAV efetivamente reproduzido; silêncio sem amplitude inventada. A fixture identifica explicitamente o áudio sintético de teste, não grava o usuário e não integra a interface de produção.
- Amostras locais de 120 frames próximas de 60 FPS, com 6.760 pontos e custo de desenho em torno de 8–9 ms nessa máquina. Não é garantia universal de desempenho.
- Sem erros/warnings de renderização registrados na rodada visual. Evidências locais em `.codex-runtime/klic-import-qa/`.

## Limitações e verificação manual restante

O navegador local foi desabilitado nas configurações do Work após a interrupção. Por isso, a inspeção visual não pôde ser repetida após o ajuste final de brilho/espectro e limiar de qualidade compacto; esses ajustes passaram pela rodada final de tipagem, testes e build. Não houve tentativa de contornar a configuração.

Não foram gravados áudio pessoal, aceitas permissões de microfone ou executadas chamadas pagas de TTS/IA. Uma conversa ponta a ponta com microfone físico/provedor real e toque em hardware móvel permanece como smoke test manual; as integrações foram verificadas por código, testes de contrato e fixture de áudio local.

O fallback nativo `speechSynthesis` não expõe PCM pelo fluxo atual: continua indicando Speaking, mas não inventa amplitude sincronizada. A modulação real está disponível quando há telemetria do microfone ou do áudio reproduzido por `HTMLAudioElement`.

Prévia local: http://127.0.0.1:3018/klic (depende do servidor local estar em execução).
