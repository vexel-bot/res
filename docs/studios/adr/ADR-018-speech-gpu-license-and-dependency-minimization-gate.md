# ADR-018 — Gate de licença e redução de dependências dos candidatos speech GPU

**Data:** 2026-08-27  
**Status:** accepted — revisão técnica concluída, revisão jurídica e rebuild pendentes  
**Escopo:** Chatterbox PT-BR e Kokoro + OpenVoice V2

## Decisão

As duas imagens locais continuam sendo evidência de build e isolamento, não artefatos
distribuíveis nem providers do produto. O inventário package-focused SPDX confirmou
que os locks atuais carregam dependências maiores que os caminhos de inferência PT-BR
selecionados. Nenhuma promoção é permitida enquanto não existir uma revisão `v2`
reduzida, um SBOM completo por arquivo/camada e aprovação explícita de código, pesos,
runtime CUDA e obrigações de distribuição.

O inventário técnico versionado está em
`workers/speech-gpu/candidate/license-review.v1.json`. Os dois SPDX locais permanecem
fora do Git, sob `.candidate-build/sbom`, ligados ao digest OCI e a SHA-256. Eles
inventariam 125/130 distribuições Python e 95 pacotes Debian por imagem. O escopo é
deliberadamente parcial: não varre cada arquivo, layer, peso ou texto de licença.

Docker Scout 1.18.3 não chegou a um estado terminal depois de armazenar a primeira
imagem para indexação. Syft 1.51.0 foi baixado da release oficial e teve o arquivo
Windows AMD64 conferido contra o checksum publicado, mas a varredura integral foi
interrompida quando a expansão temporária ameaçou consumir a reserva do host. Todo o
temporário desses scanners foi removido. Isso é uma limitação registrada, não um gate
considerado aprovado.

## Chatterbox

`pykakasi` é GPL-3.0-or-later e só é importado pelo ramo japonês do tokenizer; sairá
do candidato PT-BR. `praat-parselmouth` também é GPL-3.0-or-later, mas entrou pela
lista ampla de dependências do Perth. O caminho realmente usado pelo watermarker
implícito importa NumPy, Librosa e Torch, não Parselmouth. A revisão `v2` deverá gerar
wheel do commit Perth auditado, instalá-lo com `--no-deps` e declarar somente o grafo
de imports testado.

`soxr` permanece sujeito a revisão LGPL, e as 13 distribuições CUDA publicadas como
NVIDIA Proprietary Software exigem termos e notices próprios. A licença MIT do código
Chatterbox e Perth não resolve automaticamente os termos dos checkpoints.

## Kokoro + OpenVoice

O sidecar usa apenas Kokoro PT-BR, extração direta de embedding, `ToneColorConverter`
e WavMark. Mesmo assim, `openvoice.api` importa os cleaners de inglês e mandarim ao
carregar o módulo. Isso introduz `Unidecode` GPL-2.0-or-later, `eng_to_ipa` sem licença
declarada, além de `cn2an`, `jieba`, `pypinyin` e `inflect`. A revisão `v2` terá um
patch pequeno, reproduzível e com digest para separar o converter do frontend TTS.

Kokoro também importa `misaki.en` antes de saber que o locale é `p`; o patch `v2`
deverá carregar G2P por idioma e remover o extra inglês/`num2words`. Já
`phonemizer-fork` GPL-3.0-or-later é usado pelo `EspeakG2P` PT-BR atual e não pode ser
simplesmente removido. Ou aceitamos e materializamos suas obrigações, ou substituímos
a fronteira G2P por uma alternativa compatível antes da promoção.

O pacote `espeakng-loader` continua necessário como API Python, mas os bytes de runtime
do wheel são substituídos pelo build eSpeak manifestado. Sua ausência de licença no
METADATA e as obrigações GPL do runtime continuam abertas. O mesmo vale para WavMark,
seu checkpoint, `soxr` e as distribuições CUDA.

## Sequência da revisão v2

1. preservar locks, imagens e evidência `v1` sem reescrita;
2. criar patches auditáveis ligados aos commits upstream de Chatterbox/Perth,
   OpenVoice e Kokoro;
3. gerar novos locks Linux AMD64/CUDA e provar que os pacotes removidos não reaparecem;
4. repetir source audit, instalação, imports offline, smoke isolado e SPDX focado;
5. executar SBOM completo em runner com storage efêmero suficiente;
6. produzir notices/corresponding source e obter aprovação comercial explícita;
7. somente depois executar benchmark privado consentido — a promoção do provider ainda
   será uma mudança separada.

## Consequência

`workers/speech-gpu/worker.manifest.json` continua com `providers: []`. Nenhum peso
externo foi baixado, nenhum dado biométrico foi usado, nenhuma inferência foi executada
e a VPS permaneceu fora desta etapa.
