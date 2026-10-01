# Video Studio — vários sons independentes, sem voz

Data: 31/08/2026. Código: `C:\Users\edugu\Downloads\res`.
Continuação do checkpoint 30, sem ativar voz, música, clonagem ou lip-sync.

## Resultado do corte

A aba Sons permite adicionar outro trecho sem substituir o anterior. Cada trecho
tem ID estável, posição, intervalo de origem, volume e fades próprios. É possível
reutilizar o mesmo arquivo importado, selecionar pelo painel ou pela timeline,
desativar/reativar o trecho e desfazer o último ajuste de som. A composição e os
assets continuam no CreativeDocument existente, gravados por revisão otimista.

Rascunhos locais não são descartados ao selecionar outro som: o painel exige aplicar
ou usar a ação explícita de descartar. Uma edição de volume não reativa um trecho
desativado. Locks do trecho escolhido e da track são respeitados; um lock de outro
trecho não impede uma edição independente.

O limite da UI é 32 trechos e até oito arquivos de som além do take. Reutilizar uma
fonte não duplica upload nem referência. Origem/licença continuam sendo declarações
do asset, compartilhadas pelos trechos que o usam, não prova de direitos verificados.

## Desfazer e concorrência

Desfazer é de **um nível, na sessão atual**, para adicionar/ajustar/desativar/reativar
som. Requer o mesmo documento, versão e revisão do último ajuste. Restaura somente
assets e timeline daquele snapshot; não relaxa a política sem voz/sem música.
Outras edições ou reload desabilitam a ação. Em conflito 409, recarrega a revisão
do servidor e não sobrescreve o trabalho de outra sessão. Não é histórico geral,
redo ou colaboração transacional em tempo real.

## Evidências executadas neste corte

- `npm run lint`: aprovado (TypeScript).
- Timeline e placement: **20/20** testes, incluindo imutabilidade, seleção exata,
  reutilização, limites, locks, toggle reversível e preservação de outros trechos.
- Action/Screen Contracts: **6/6**. Execução combinada: **26/26**.
- `npm run audit:cx-strict`: **430 controles executáveis canônicos**, nenhum sem
  action ID; 45 entradas/59 URLs conhecidas, zero órfãs ou conflitantes.
- E2E autenticado de Video Studio: **1/1**, repetido com sucesso após correção
  visual; última execução total **52,2 s**. API, ingest e render FFmpeg reais.
- Reutilização da mesma fonte em dois trechos; assets sem duplicação; primeiro
  trecho intacto ao adicionar o segundo; reload preserva ambos.
- Proteção de rascunho ao trocar, descarte explícito e seleção pela timeline.
- Desativação, desfazer consumido e conflito real com um PUT concorrente: ganho
  atualizado por outra sessão preservado, sem desfazer indevido.
- MP4 decodificado para PCM: silêncio antes da primeira entrada, áudio nas duas
  janelas esperadas e, após desativar só o segundo trecho e renderizar novamente,
  primeira janela audível e segunda silenciosa.
- Axe A/AA em Sons e Saída sem violações detectadas; fluxo móvel 390 × 844 sem
  overflow horizontal; screenshots móvel e desktop.
- Build aprovado, com aviso preexistente de bundle JavaScript acima de 500 kB.

A primeira execução falhou porque `getByLabel(..., exact: true)` não localizou o
select cujo label contém opções. O snapshot mostrou o controle existente; o teste
foi corrigido para o papel acessível `combobox`. Não foi uma ausência funcional.

A inspeção visual encontrou sobreposição real do título com o botão de revisão
no celular, embora Axe/overflow passassem. O cabeçalho local ganhou duas linhas
até 600 px, preservando título/voltar e colocando revisão em linha própria. O E2E
agora verifica as posições geométricas, além de capturar o cabeçalho e a lista de
sons. Não houve redesenho do shell global.

Screenshots:

- `artifacts/validation/video-studio-header-mobile.png`
- `artifacts/validation/video-studio-natural-sound-mobile.png`
- `artifacts/validation/video-studio-ugc.png`

## Limites e próximo corte

O vídeo e o WAV do teste são fixtures técnicas; **não são anúncio UGC final nem
som natural aprovado**. A escuta de produção e os direitos seguem pendentes.
Nenhum classificador foi promovido ou interpretado como garantia de ausência de fala.

O preview da montagem continua sem mix externo ao vivo; o resultado é conferido
no MP4 renderizado em Saída. Sobreposições de som podem exigir ajuste de ganho e QC:
este corte não implementa limiter, normalização automática ou envelope fiel após
split. Também não implementa remoção definitiva, redo, recuperação de uploads não
associados após reload ou validação humana de CX.

Próximo avanço de conteúdo: take próprio/licenciado, sem fala ou música, para o
caso café; confirmar autorização, escutar as fontes candidatas e validar o mix
sincronizado ao take. Foi solicitado ao usuário esse material. Em paralelo ainda
cabem avanços locais no editor; a ausência do take não foi marcada como bloqueio
da meta inteira. A admissão acústica controlada pelo servidor permanece pendente,
e o gate de publicação do perfil natural/sem voz continua fechado.

Os dez anúncios continuam **0/10 aprovados para produção**. Voicebox fica adiado.
A meta ampla de CX, Presenter e Motion permanece ativa, não entregue como concluída.

## Escopo técnico e rollback

Mudanças em `NaturalSoundPanel.tsx`, `naturalSoundTimeline.ts`, `useVideoStudio.ts`,
`VideoStudio.tsx`, CSS local, registry de ações e testes. Sem mudança de backend
neste corte: ele usa a capacidade multicue validada no checkpoint 30. Sem schema,
nova dependência, deploy, commit/push, Figma ou alteração de configurações/serviços
da VPS. Originais preservados; nenhuma exclusão de mídia.

Rollback deve remover somente as alterações deste corte e manter os documentos
multicue protegidos contra um editor antigo que substitua toda a track. Não usar
reset amplo no worktree, que contém trabalho anterior do usuário e dos checkpoints.
