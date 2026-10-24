# Auditoria da fonte local e integração da Face KLIC — 20/10/2026

## Resultado

A pasta `círculo-pontilhado-interativo/` está completa como demonstração visual e corresponde byte a byte aos **17 arquivos** de `ai-studios-novo/` na branch remota `ai-studios-novo`, commit `68abe189c3cbd360b82044667d1f9dc95d99c006`. A imagem temporária de exportação em `.aistudio/` é o único arquivo local adicional. As **18 entradas de arquivo do ZIP** também coincidem por SHA-256 com a pasta extraída.

A Clicko já continha uma integração funcional dessa mesma geometria antes desta tarefa. Ela foi auditada, preservada e validada; não foi substituída por uma segunda implementação equivalente. A mudança técnica necessária foi isolar o projeto demonstrativo da checagem TypeScript da plataforma, mantendo as duas verificações separadas. Também foi criada uma auditoria reproduzível da origem e da equivalência matemática.

Não houve commit, merge, push, instalação, troca do gerenciador de pacotes ou exclusão da referência e de seu ZIP.

## Estrutura encontrada

| Área | Projeto de referência | Clicko principal |
| --- | --- | --- |
| Entrada | `index.html`, `src/main.tsx`, `src/App.tsx` com canvas fullscreen | `src/main.tsx` → `src/App.tsx`, rotas e providers existentes |
| Componente visual | `src/components/ParticleSphereCanvas.tsx` | `KlicPlasma` → `KlicHologram` → `mountKlicHologram` |
| Geometria | `src/utils/sphereGenerator.ts`, `src/types.ts` | `src/klic/face/sphereGenerator.ts`, `types.ts`, `faceSimulation.ts` |
| Animação e física | Loop dentro do componente; ondas, mola, repulsão e choque por clique | Modelo separado, relógio contínuo, subpassos temporais e interação local |
| Áudio | `src/utils/voiceAnalyzer.ts`: microfone próprio e cadências demonstrativas | `useKlicVoice.ts`, `audioAnalysis.ts`, `HologramCommunication`: eventos e amostras do áudio existente |
| Tema e estilos | CSS global preto, fonte externa, bloqueio global de toque/rolagem | `ThemeContext`, CSS localizado, canvas transparente, fonte nativa e layout preservados |
| Configuração | `package.json`, `tsconfig.json`, `vite.config.ts`, `bun.lock` vazio | Manifesto, lockfile npm, Vite e TypeScript próprios da plataforma |
| Imagens | PNG de referência em `public/assets/aistudio/` e cópia temporária | A face é procedural; a imagem não substitui a animação |

Foram examinados integralmente o componente, gerador, analisador de áudio, tipos, entradas, CSS e configurações relevantes da referência. Na plataforma, foram conferidos os componentes principal/flutuante, adaptadores visuais, simulação, testes e as ligações com os serviços reais de áudio.

## Comparação e integridade

O acesso remoto funcionou. Foi executado `git fetch origin ai-studios-novo`, sem mesclar branches. A comparação utilizou o conteúdo real de cada blob Git, incluindo configurações, estilos e imagem, e não apenas os nomes dos arquivos.

Hashes de arquivos centrais, iguais no local e no GitHub:

- `src/components/ParticleSphereCanvas.tsx`: `f0bb6d98bb798c51d5cd75debf5567ac2d5e8ff78eeb4956643593a218131cfa`.
- `src/utils/sphereGenerator.ts`: `5e2b955a121e25d9a6031bf7c4c67bcd620a4c35562e00a3d424bdc74ea1ef92`.
- `src/utils/voiceAnalyzer.ts`: `b19d7d8067db2afb99f81f81bd7b0b701a178198c8814a09dc678e471a2c0864`.

Auditoria reproduzível:

```powershell
git fetch origin ai-studios-novo
node scripts/klic/audit-face-reference.mjs
```

O script é somente leitura e usa o ref Git já obtido. Compara todos os arquivos, lista extras, verifica hashes e executa somente os geradores puros em contextos separados, com a mesma sequência aleatória. Confere todos os atributos das partículas para raios 1, 110 e 252. Resultado: **6.760 partículas, 72 fitas e equivalência numérica dentro de 1e-10 relativo**. Os comentários do demonstrativo estimam cerca de 5.200 pontos, mas o algoritmo efetivamente produz 6.760. `baseRadius` varia de 0,75 até menos de 1,20, apesar de outro comentário mencionar 1,35.

O script retorna erro se os arquivos diferirem, a referência estiver ausente ou a geometria deixar de corresponder. Nenhum conteúdo de arquivo de ambiente é impresso. A evidência detalhada da execução permanece em `.codex-runtime/klic-local-reference-comparison.json`.

## Integração preservada e diferenças necessárias

A versão integrada reaproveita as fórmulas e atributos do gerador local, incluindo as 72 fitas, harmônicos, massa, tamanho e posições. O modelo de animação adapta as equações do componente local para o espaço já existente do chat. A equivalência da geometria de origem foi comprovada pela execução dos dois geradores; a implementação de produção permanece independente da presença da pasta demonstrativa.

As diferenças entre demonstrativo e produto são intencionais:

- O demonstrativo ocupa a tela inteira e pinta preto; a Clicko mantém o centro do chat e compõe com transparência em ambos os temas.
- O demonstrativo controla estados com 1/2/3, Espaço e M. A plataforma usa as fases reais da KLIC e não incorpora esses atalhos globais.
- A referência usa cadências artificiais quando não há microfone e para representar fala. A Clicko usa RMS e bandas espectrais reais do microfone e do áudio TTS reproduzido, com dados antigos/silêncio decaindo a zero.
- A referência reinicia o efeito ao mudar estado e recria partículas no resize. A plataforma conserva o modelo, a fase e o canvas durante transições de tema/estado e redimensionamento.
- A referência aplica mola e amortecimento por quadro e contém ruído aleatório no impulso. A adaptação utiliza delta de tempo, subpassos estáveis, semente inicial reproduzível e recomposição para a posição de equilíbrio dinâmica.
- O produto adiciona orçamento adaptativo, DPR limitado, composição raster reutilizável, pausa fora de tela, descarte de listeners/recursos e respeito a movimento reduzido.
- A interação completa com o ponteiro permanece somente na esfera central da aba KLIC. Miniaturas preservam movimento autônomo e cliques, conforme o pedido anterior. Clicar na esfera central continua sem iniciar gravação; os controles explícitos de voz permanecem responsáveis por isso.

Os estados `Idle`, `Listening` e `Speaking` permanecem ligados a `plasmaState` e `audioSignal` publicados por `useKlicVoice`, tanto na aba principal quanto no mini chat e no painel de voz. Não foram modificados serviços, endpoints, autenticação, conversas, anexos, persistência, permissões ou outros módulos da plataforma.

## Dependências e lacunas do demonstrativo

Nenhuma dependência foi adicionada. React, TypeScript, Canvas 2D, `requestAnimationFrame`, `ResizeObserver` e Web Audio já existem no projeto. A perspectiva e os pontos são calculados em 3D e projetados em Canvas 2D; não se trata de imagem estática, WebGL ou uso de Three.js.

O manifesto da referência menciona Vite 8, TypeScript 7, `motion`, Express e Gemini, mas a esfera não precisa desses upgrades nem de `motion` ou de chamadas Gemini para desenhar. Nenhum manifesto, CSS global, fonte externa, segredo, cache ou `node_modules` da referência foi copiado para a aplicação.

O pacote local é uma demonstração visual, não um sistema completo de conversa: não implementa backend de chat/TTS, usa fala simulada, só contém tema preto e não gerencia adequadamente movimento reduzido ou descarte do microfone em todos os caminhos. Essas partes não foram importadas. O lockfile demonstrativo está vazio; a instalação independente com todas as versões declaradas não foi realizada. Sua tipagem foi validada separadamente com o compilador já instalado na Clicko.

## Arquivos desta tarefa

- **Criado:** `scripts/klic/audit-face-reference.mjs` — comparação local/Git e equivalência dos geradores.
- **Criado:** este relatório.
- **Modificado:** `tsconfig.json` — exclui somente `círculo-pontilhado-interativo/`, que possui configuração própria. `noUnusedLocals` e `noUnusedParameters` da plataforma continuam ativos.
- **Modificado:** `src/klic/face/SOURCE.md` — acrescenta a origem local comprovada e o comando de auditoria.

Antes da alteração, `npm run lint` falhava em `círculo-pontilhado-interativo/src/App.tsx` por import React sem uso. A correção separa os projetos sem editar ou afrouxar a checagem da Clicko e sem alterar os arquivos de referência.

O estado Git inicial tinha 131 arquivos modificados/não rastreados, incluindo trabalhos anteriores. Foi registrado um snapshot de hashes em `.codex-runtime/klic-local-reference-baseline-2026-10-20.json`. Fora da documentação de origem complementada nesta tarefa, os arquivos existentes são preservados. A branch continua `codex/klic-atualizacao-20260823`, HEAD `5cab414`.

## Verificações executadas

| Verificação | Resultado |
| --- | --- |
| Comparação local/GitHub | 17/17 arquivos idênticos em bytes |
| Comparação ZIP/pasta | 18/18 arquivos idênticos por SHA-256 |
| Geradores local/integrado | 6.760 partículas × 3 raios; 72 fitas; todos os atributos equivalentes |
| Tipagem da referência, em separado | Aprovada com `tsc -p círculo-pontilhado-interativo/tsconfig.json --noEmit` |
| Tipagem/lint principal | Aprovada com `npm run lint` (`tsc --noEmit`) |
| Testes existentes | 223 testes Node e 2 testes Vite aprovados |
| Build da plataforma | Vite, servidor e worker de anexos aprovados |
| UI principal | Canvas 2D ativo, 6.760 pontos, nenhuma camada de plasma sólido antiga, posição central preservada |
| Mouse | Dispersão observada após arrastar, abertura na região afetada e recomposição após afastar o ponteiro; não iniciou voz |
| Mini chat | Abriu e fechou; header, estado vazio e launcher usam a mesma face em modo `click`, sem campo de hover |
| Chat | Digitação de `Teste 1 2 3 M` preservada; texto apagado ao concluir, sem envio de mensagem nem execução dos atalhos da referência |
| Temas | Claro e escuro conferidos pelos controles reais de Configurações; preferência original escura restaurada |
| Responsividade | 390×844: canvas 220 px; 320×568: canvas ~170,4 px; sem transbordamento horizontal da página ou corte da esfera; viewport temporário restaurado |
| Escuta/fala | Página local de testes com Web Audio/AnalyserNode e HTMLAudioElement reais, alimentados por áudio sintético identificado como teste; respondeu à energia e retornou a amplitude zero no silêncio |
| Desempenho amostrado | Cerca de 57–58 FPS em amostras de 120 frames com 6.760 pontos no fixture; não é garantia universal de 60 FPS |
| Console da aba KLIC | Nenhum warning/erro retornado na conferência final |
| Limpeza | Fixture de áudio encerrado, contextos liberados pelo fluxo existente, abas auxiliares fechadas; aba KLIC mantida aberta |

As imagens de evidência estão em `.codex-runtime/klic-local-reference-qa/`: temas claro/escuro, larguras 390/320, dispersão e estados de áudio no fixture. A cena do fixture é somente de desenvolvimento, explicitamente identificada; não substitui eventos reais no produto. Testes automatizados existentes também cobrem transição de tema sem novo contexto, pausa/restauração, descarte, movimentos reduzidos, sinais de áudio e recomposição completa.

## Validação manual ainda necessária

Não foram gravados dados do microfone pessoal nem chamadas APIs pagas para testar uma conversa. O teste de áudio usa amostras sintéticas reais no analisador, não uma conversa de produção. Para validar ponta a ponta: iniciar conversa pelo botão de voz, autorizar o próprio microfone, falar, observar `Listening`, aguardar a resposta TTS e verificar `Speaking`, pausas e encerramento. Repetir com o provedor de voz configurado no ambiente real.

O fallback nativo `speechSynthesis` não expõe amostras PCM neste fluxo; mantém o estado de fala, mas não oferece sincronização espectral da animação. Não foi inventada uma cadência para preencher essa ausência.

O tratamento de ponteiros de toque, cancelamento e preservação de rolagem é coberto pelos testes automatizados. Gesto em tela sensível ao toque física e uma inspeção longa de memória/desempenho em aparelhos variados continuam sendo verificações manuais; não foram simulados como realizados. A integração existente foi mantida e validada dentro desses limites, sem reconstruir a KLIC.
