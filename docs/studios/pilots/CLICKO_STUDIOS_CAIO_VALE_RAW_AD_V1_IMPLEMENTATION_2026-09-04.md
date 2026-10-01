# Implementação — anúncio bruto Clicko Studios com Caio Vale

Data: 2026-09-04  
Estado: `blocked_source_video_authentication`  
Publicação: `private_review`

## Resultado objetivo

A infraestrutura, a copy e a nova voz local PT-BR do piloto estão prontas. A voz Kokoro `pm_alex` foi rejeitada pelo usuário por soar como IA genérica e substituída pelo checkpoint regional `Chatterbox-Multilingual-pt-br`, usando sua voz stock sem áudio de referência ou clonagem. O vídeo-base e o anúncio com lip-sync não foram produzidos porque `OPENAI_API_KEY` voltou a retornar `HTTP 401 / provider_authentication_failed` no preflight de leitura do modelo. Nenhum `POST /videos` foi enviado, nenhuma operação Sora foi criada e o custo externo foi US$ 0.

## Entregue

- configuração OpenAI com segredo protegido, flags desligadas por padrão e teto de gasto explícito;
- contratos tipados de request, operação, download, resultado e duração `content_fit`;
- porta `GenerativeVideoProvider` separada de avatar e renderização;
- adapter temporário `openai.sora-2` com preflight, idempotência, polling, timeout, download e desligamento definitivo em 24/09/2026;
- cancelamento local honesto: a API não oferece cancelamento do job em andamento, portanto nenhum `DELETE` inválido é enviado;
- runner resumível que nunca repete o POST quando já existe uma operação registrada;
- remoção obrigatória de todo áudio do MP4 canônico e validação `ffprobe` de um vídeo/zero áudios;
- copy de cinco beats auditada pelas lentes Carlton, Hopkins, Bencivenga e Kennedy;
- voz PT-BR local Chatterbox regional, 27,12 s, com voz stock, sem referência e sem clonagem;
- checkpoint PT-BR, modelo-base, código, vocabulário e condicionamento stock fixados por revisão e checksum;
- áudio normalizado para −16,1 LUFS e −1,4 dBTP, sem clipping ou silêncio contínuo inesperado;
- tentativa Kokoro preservada no ledger com estado `rejected_human_naturality`;
- runner MuseTalk 1.5 FP16/25 FPS/batch 1, fail-closed por commit, pesos, licenças, checksums e inputs;
- HeyGem mantido apenas como referência arquitetural; `heygemModelCreated=false`;
- histórico Gemini/LTX preservado e nova tentativa OpenAI anexada aos ledgers.

## Copy falada

> Se sua agência começa um vídeo escolhendo cenas, ela já começou pela etapa errada. Gerar clipes é só o começo. Sem uma lógica comum, oferta, audiência e referências viram decisões soltas na produção. O Clicko Studios organiza estratégia, copy, roteiro, personagem e produção em um fluxo revisável. Cada decisão fica ligada ao objetivo da campanha. Assim, sua equipe pode avaliar o que funciona, corrigir a etapa certa e preservar a identidade de cada projeto. Quer testar esse processo na sua agência? Solicite acesso ao piloto do Clicko Studios.

## Gates

| Gate | Estado | Evidência |
|---|---|---|
| Copy e cinco beats | aprovado | quatro lentes 9/10; CUB risco 2/2/3 |
| Duração natural | aprovado | 27,12 s, sem corte e velocidade 1.0 |
| Voz técnica | aprovado | PCM 16-bit, 24 kHz, mono, −16,1 LUFS, true peak −1,4 dBFS |
| Voz humana | pendente | audição de naturalidade e pronúncia pelo usuário |
| OpenAI modelo/chave | bloqueado | nova tentativa retornou `401 provider_authentication_failed` antes do POST |
| Vídeo-base Caio Vale | não criado | depende do preflight válido |
| Admissão visual | não executada | depende do MP4 base |
| Pesos MuseTalk | não baixados | política evita custo/armazenamento antes da admissão visual |
| Anúncio bruto | não criado | depende do vídeo-base e do benchmark MuseTalk |

## Custo

- Custo externo realizado: US$ 0.
- Custo de um job aprovado: US$ 1,20 para 12 s em 720×1280.
- Teto rígido do runner: US$ 1,50.
- Tentativas automáticas: zero.

## Geração local da voz selecionada

O gerador exige modo offline, verifica os checksums e não carrega o voice encoder:

```powershell
$env:HF_HUB_OFFLINE='1'
$env:CLICKO_CHATTERBOX_SOURCE_REVISION='5de7a54aa4e5e2baadb0182dde554908b48b85c2'
& 'C:\Users\edugu\Downloads\clicko-oss-evaluation\venvs\chatterbox-ptbr-cu124\Scripts\python.exe' -m scripts.generate_chatterbox_ptbr_pilot_voice --asset-root 'C:\Users\edugu\Downloads\clicko-oss-evaluation\artifacts\chatterbox-ptbr-b3952f18'
```

O comando deve ser executado a partir de `C:\Users\edugu\Downloads\res\backend`.

## Próxima execução após corrigir a chave OpenAI

1. Substituir somente `OPENAI_API_KEY` no `.env` por uma chave de projeto válida.
2. Executar o preflight sem `--execute`; ele não cria vídeo.
3. Somente após `preflight=passed`, executar uma vez com `--execute`.
4. Inspecionar frames e admitir ou rejeitar o rosto. Uma rejeição não gera uma segunda variante automaticamente.
5. Apenas se aprovado, resolver individualmente os pesos/licenças do MuseTalk e executar o anúncio privado.

O runner é:

```powershell
$env:OPENAI_OUTBOUND_ENABLED='true'
$env:OPENAI_VIDEO_GENERATION_ENABLED='true'
$env:OPENAI_MAX_EXTERNAL_SPEND_USD='1.5'
python -m scripts.generate_openai_avatar_source
python -m scripts.generate_openai_avatar_source --execute
```

Os comandos devem ser executados a partir de `C:\Users\edugu\Downloads\res\backend`.

## Referências oficiais OpenAI

- https://developers.openai.com/api/docs/guides/video-generation
- https://developers.openai.com/api/docs/models/sora-2
- https://developers.openai.com/api/reference/cli/resources/videos
