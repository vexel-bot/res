# Vídeo sem voz — remoção reversível de som original

Data: 31/08/2026. Repositório executado: `C:\Users\edugu\Downloads\res`.

## Resultado e fronteira

O Video Studio autenticado permite remover e restaurar o som original do take,
preservando o arquivo privado, os cortes e as legendas editoriais. A operação
persiste na track de áudio do CreativeDocument e também controla o preview nativo.
Esse corte não gera um anúncio com foley: silêncio é apenas uma prova privada de
edição. Os dez anúncios continuam em **0/10 aprovados para produção**.

O perfil atual mantém voz, narração, clonagem, lip-sync, conversa incidental e
música fora do lote. Voicebox continua adiado. Sons naturais exigem origem,
licença, sincronismo e escuta humana vinculados ao resultado.

## Implementação

- `VIDEO-MUTE-ORIGINAL` tem Action Contract, estado persistente, mensagem de
  resultado e controles utilizáveis no inspector Saída, inclusive no celular.
- A função pura `setOriginalAudioMuted` copia a timeline; exige um take e uma
  track de som original pareada; rejeita locks, áudio externo e track ausente.
- O PUT usa revisão otimista. Em conflito 409, recupera a revisão atual sem
  sobrescrever silenciosamente a edição de outra sessão.
- O renderer FFmpeg respeita `muted`. No caminho mudo, gera silêncio por trecho
  sem ler `[0:a]`; mantém AAC, frames e legendas no contrato de prova privada.
- Mudar o som invalida a elegibilidade da prova antiga para nova revisão. O
  snapshot de uma revisão já criada permanece inalterado.
- Forma de onda e QC técnico não são apresentados como detecção de fala/música.
  O painel separa encode concluído de escuta e validação acústica pendentes.

## Entrega impedida sem evidência

O backend recusa preflight, pacote e agendamento interno quando o snapshot de
vídeo/presenter declara `naturalSoundPolicy=required-before-approval`,
`voicePolicy=prohibited` ou `audioMode=natural-foley-only`.

O código retornado é `studio_publication_natural_sound_evidence_pending`, com
explicação legível na tela de publicação. Uma aprovação criativa genérica e flags
editáveis como `naturalSoundApproved` não substituem evidência acústica.

Este é um bloqueio provisório: **ainda não existe registro de admissão do mix
controlado pelo servidor nem fluxo para liberá-lo**. Downloads de provas privadas
e revisão criativa continuam disponíveis. Documentos legados sem esse perfil e
fluxos de imagem/carrossel não foram migrados; este corte não estabelece política
imutável para todos os documentos nem protege contra um editor retirar o perfil
por uma API autorizada. Essa governança exige implementação posterior.

## Verificação executada

| Verificação | Resultado |
| --- | --- |
| Timeline unitária, incluindo mute reversível/locks/áudio externo | 15/15 |
| Provider FFmpeg, video-render job e review binding | 18/18 |
| Publication preflight, incluindo gate de áudio | 7/7 |
| Jornada autenticada de Video Studio com MP4 real | 1/1; 44,4 s totais |
| Action Contracts | 6/6 |
| Audit CX estrito | 414 controles executáveis canônicos; zero sem contrato |
| TypeScript, Ruff dos arquivos alterados e build | Passaram; aviso conhecido de chunk >500 kB |
| `git diff --check` | Passou; avisos de conversão LF/CRLF |

A jornada E2E cobre upload, ingest, proxy, forma de onda, legenda editorial sem
transcrição, corte, reorder, trim, render, QC, reload e revisão. A extensão deste
corte prova:

1. Persistência de mute/restore e propriedade `muted` do preview após reload.
2. MP4 renderizado decodificado por FFmpeg: amostras s16le inteiramente zeradas.
3. Original intacto no teste de provider e snapshot anterior preservado no E2E.
4. 409 entre sessões sem perda de estado; 404 para documento/artefato estrangeiro.
5. Gate de entrega mesmo após aprovação criativa, nos três endpoints.
6. Botão acionável em 390 × 844, sem overflow horizontal; Axe A/AA sem violações
   detectadas na `.vs-shell` com mídia real. Isso não substitui teste humano.

O primeiro E2E ampliado revelou contraste insuficiente nos textos de 7 px do
artefato renderizado. A correção ficou restrita ao CSS do Video Studio: texto do
resultado, metadados e controles do painel de saída. A repetição passou. Não houve
redesenho do shell global nem alegação de auditoria visual completa do produto.

Screenshots locais: `artifacts/validation/video-studio-muted-mobile.png` e
`artifacts/validation/video-studio-ugc.png`. A mídia usada é fixture técnica, não
avatar/take aprovado ou anúncio pronto.

## Dependências e evidência anterior

As dependências de avaliação acústica foram isoladas em
`backend/requirements-audio-audit.txt`, incluído apenas pelo requirements de dev,
fora do requirements padrão da API e do worker de mídia. Nenhum modelo de voz foi
ativado. YAMNet ONNX continua challenger não qualificado, com escuta humana
pendente, não detector de produção.

O manifesto local do mix candidato do café agora separa corretamente o digest do
caso (`ec4e0b30af54b57c6abf8d4dcb03b5190c7e16517e02683b9aa50631e9ce6bf2`)
do digest do casebook (`624a1cffa264175170746a42defcad356fc601c36b9f25e3599d0ec10a908008`).
Nenhum dos três sons ou do mix candidato foi promovido a asset aprovado.

## Próximo corte e reversibilidade

Faltam take/avatar com direitos, entrada de foley com lineage, múltiplas fontes de
áudio no renderer, sincronismo visual, classificação calibrada, escuta humana e
admissão do mix vinculada ao checksum do vídeo final. CX-0 com pessoas permanece
pendente, assim como os outros cortes da meta.

Não houve migração de banco, mudança na VPS, Figma, deploy, commit ou push. O
usuário pode restaurar o som pela própria ação sem modificar o original. Rollback
de código deve retirar apenas este corte, preservando as demais alterações do
workspace; documentos com áudio mudo não devem ser enviados a um renderer antigo
que não suporte esse estado.
