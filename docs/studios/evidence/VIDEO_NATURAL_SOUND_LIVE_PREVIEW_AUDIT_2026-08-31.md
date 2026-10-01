# Video Studio — escuta sincronizada da montagem

Data: 31/08/2026. Repositório: `C:\Users\edugu\Downloads\res`.
Continua o checkpoint 31 e a vertical de vídeo assistido do plano mestre.

## Resultado e fronteira

O Preview do Video Studio passa a reproduzir os sons externos da edição salva
junto com o take e as legendas. O botão existente reproduz, pausa e cancela o
carregamento, sem criar render job ou outra versão do documento. Somente arquivos
privados já referenciados na timeline participam; nenhuma voz, música, clonagem,
gravação, nova dependência ou modelo de IA foi ativado.

| Antes | Agora | Fronteira preservada | Evidência |
| --- | --- | --- | --- |
| Preview sem sons externos; export necessário para ouvi-los | Web Audio local projeta os trechos ativos da timeline salva | CreativeDocument continua canônico; grafo de áudio é efêmero | Amostras de áudio no browser e revisão do documento inalterada |
| `timeupdate` conduz a montagem | Atualização por frame acompanha o relógio do vídeo e reinicia o som no tempo de saída | Proxy/original usam o time-map existente | Seek e reprodução contínua atravessando corte |
| Assets protegidos sem cancelamento no helper de blob | Mesmo helper aceita AbortSignal opcional | Mesmos endpoints, token e autorização; consumidores anteriores compatíveis | Falha HTTP e cancelamento durante download |
| Painel lateral com cinco labels apertadas | Abas em duas linhas, texto de 12 px, alvos de 44 px | CSS restrito ao Video Studio, sem redesign global | Screenshot e verificação de largura dos controles |

Arquivos principais: `naturalSoundPreview.ts`, `useNaturalSoundPreview.ts`,
`VideoStudio.tsx`, `NaturalSoundPanel.tsx`, CSS local e Action Contract de playback.
`src/api.ts`/`src/api/productApi.ts` recebem somente o argumento opcional de sinal
para o download de blob existente. Não há alterações de backend, schema ou banco.

## Regras de escuta e recuperação

- Início, duração, offset de origem, ganho linear a partir de dB e fades vêm dos
  clips salvos. Mudar de som no inspector não muda o mix. Campos ainda não aplicados
  não entram na escuta.
- O mesmo arquivo é decodificado uma vez por sessão da peça; buffers são privados
  à instância e descartados ao sair/trocar contexto. Não há cache persistente novo.
- Download usa autenticação existente. SHA-256 precisa corresponder à referência
  antes da decodificação; tamanho, duração e memória também são verificados.
- Todos os sons precisam carregar antes de iniciar o vídeo. Erros de rede,
  checksum, codec ou intervalo não viram sucesso parcial ou vídeo sem o som pedido.
- Pausa, seek, buffering e fim interrompem os nós de áudio. A timeline é
  reinterpretada em segundos de saída, mesmo quando os cortes reordenam a fonte.
- Edição da timeline/assets cancela a escuta e downloads pendentes. Mudança de peça
  fecha o AudioContext. Ocultar a aba pausa o preview, sem retomada automática.
- O MP4 de Saída e o preview não devem tocar simultaneamente: iniciar um pausa o
  outro. A proteção foi implementada; a jornada completa de alternância de players
  e o comportamento em dispositivos físicos ainda precisam de validação adicional.
- Navegador sem Web Audio e contexto interrompido têm erro explícito. O MP4 em
  Saída permanece alternativa para formatos/limites incompatíveis com o browser.

O adapter limita o preview a oito fontes, 32 trechos, arquivos de até 20 MB,
fontes de até dez minutos, mono/estéreo e 128 MiB de PCM retido. O limite de PCM é
avaliado após decode: não é uma garantia de pico de memória do decoder. Pan,
efeitos e keyframes não suportados são recusados, não silenciosamente ignorados.

## Precisão e o que não significa aprovação

O agendamento usa o relógio do AudioContext, offsets e envelopes de ganho. Seek no
meio de um fade retoma o ganho intermediário em vez de reiniciar o fade. O player
observa a diferença entre o relógio do vídeo e do áudio; diferença de 60 ms provoca
ressincronização. Esse limiar é uma estratégia de correção, **não medição nem
garantia de latência audiovisual máxima** em qualquer navegador/dispositivo.

Nos cortes há interrupção/reagendamento após seek do vídeo. Não é ainda um motor
de decodificação de vídeo frame-exact, gapless ou WebCodecs. Original do take
continua no elemento de vídeo com seu mute existente; o caminho assistido aceita
som original sem efeitos. Não existe limiter/normalização automática adicional.

O preview ajuda a editar; não aprova licença, ausência de fala/música, realismo,
sincronismo de foley com ação física ou qualidade final. O MP4 renderizado continua
necessário para QC/revisão. `rightsStatus=unknown`, escuta `pending` e gate de
publicação do perfil natural/sem voz permanecem inalterados.

## Verificação

- TypeScript aprovado.
- Build final e `git diff --check` dos arquivos rastreados alterados aprovados;
  permanece o aviso conhecido de chunk JavaScript acima de 500 kB.
- **24/24** testes de timeline, placement e preview; **6/6** Action/Screen Contracts.
- Audit estrito: **430 controles canônicos executáveis**, zero sem action ID,
  zero URLs conhecidas órfãs/conflitantes; nenhum controle decorativo novo.
- OfflineAudioContext real: PCM confirma offset, ganho, fades, silêncio,
  sobreposição de dois trechos e seek no meio do envelope.
- Teste nativo do adapter: checksum divergente recusado, download cancelado e
  resposta tardia incapaz de ativar o mix.
- Jornada autenticada: falha HTTP 503 visível e vídeo pausado, cancelamento de
  download pela UI, recuperação, som após seek em ambos os trechos, silêncio após
  pause/fim e áudio após atravessar o limite entre takes reordenados.
- Reproduzir/pausar não muda a revisão. Edições, undo, conflito, reload, isolamento,
  render/review e PCM do MP4 continuam cobertos pelo mesmo E2E.
- Axe A/AA sem violações detectadas em Sons/Saída; 390 × 844 sem overflow horizontal,
  cabeçalho sem sobreposição e controles do inspector sem texto extravasado.

Uma execução usava polling externo do RMS instantâneo em um trecho de 0,3 s e
falhou de forma intermitente. A instrumentação passou a guardar amostras no próprio
browser durante a reprodução, com tempo de timeline e pico. Os limiares de áudio
não foram reduzidos; a janela temporal esperada também é verificada. A jornada
passou após essa mudança (59,3 s). O resultado sustenta presença temporal do som,
não uma prova exaustiva de sincronismo perceptual em hardware real.

Validação final conjunta: **4/4 E2E passaram em 56,3 s**, incluindo o teste nativo
de cache/decoder e contexto de áudio suspenso. Repetir a preparação na mesma
instância não baixou novamente; uma nova instância baixou a fonte e a suspensão
real do AudioContext foi recusada. A jornada principal passou novamente em 40,8 s.

Screenshots inspecionados:

- `artifacts/validation/video-studio-header-mobile.png`
- `artifacts/validation/video-studio-natural-sound-mobile.png`
- `artifacts/validation/video-studio-ugc.png`

Os sons e vídeos usados aqui são fixtures técnicas, não os anúncios finais.

## Pendências, retorno e meta

Sem commit/push, deploy, mudanças na VPS, Figma, novos serviços ou modelos. O
rollback retira o adapter/hook e a conexão no player, restaura o aviso de preview
sem mix e mantém o renderer multicue. Não exige migração nem exclusão de assets.
Preservar todas as alterações anteriores no worktree.

Ainda são necessários take autorizado para o caso café, escuta humana das fontes,
mix sincronizado ao take, qualificação acústica e admissão controlada pelo servidor.
Também seguem abertos fidelidade de envelopes após split, recuperação de uploads,
qualificação em outros browsers/dispositivos, CX com pessoas e demais verticais
da meta. O lote permanece **0/10 UGC aprovados para produção**. Voicebox segue
adiado. Este é progresso de implementação e evidência, não conclusão da meta ampla.
