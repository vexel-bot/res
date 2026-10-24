# Procedência e arquitetura do Studio de Vídeo

Revisão: 17/10/2026. Checkout inspecionado: `5cab414dd942c721f8e6fdf65dcd82b4ade28722` mais as alterações locais de Vídeo e Imagem existentes antes desta etapa. Não houve reset, cherry-pick ou substituição de arquivos pelo conteúdo de outro projeto.

## Linhagem interna consultada

Foram inspecionados `status`, branches, log de todas as referências (60 commits), histórico de `server/studios`, histórico com `--follow` da interface e reflog. `src/studios/video/VideoStudio.tsx` ainda era um arquivo local não rastreado: não há um commit anterior desse caminho que se possa atribuir à implementação.

| Commit real | Inspeção e decisão |
| --- | --- |
| `5cab414dd942c721f8e6fdf65dcd82b4ade28722` | Integração de DuduSilvaai à sessão Clicko. Reutilizados o proxy autenticado, isolamento de clientes e `ProductDataProvider`. |
| `cfa5f2b5cb4eda1dbd6edfed91221eb12cdddaa9` | Departamento Criativo e preservação do corpus. Mantidos seus documentos e rotas; não reconstruído. |
| `a5735d9e15988f966fd9488539b66275538faa5e` | Diff dos registries e de `jobs.py`: desativou renderizadores antigos a favor de Craft. Não reativamos o registry legado nem copiamos seu renderer de 1.303 linhas. O novo provedor `ffmpeg.timeline-v1` tem contrato explícito para a timeline canônica e rejeita documentos nativos. |
| `b91f7172feaef6b007736d44869ecb423f7d2ef1` | Inventário da árvore anterior (`video_render`, `contextual_render`, Remotion/Motion Canvas) comparado à arquitetura atual. Depende de contratos/pipelines antigos; rejeitado como restauração automática. |
| `4af887309bbb1f28e34fd77e4f5165df91a03d81` | Diff da CI: instalava FFmpeg/ffprobe no runner, não nesta máquina. Não comprovava instalação local. |

As versões locais anteriores de `VideoStudio`, `VideoEditor`, `videoModel`, Imagem e cota de imagem foram preservadas. Projetos com `nativeEditorState` continuam no editor Craft original; o novo caminho não converte nem remove esse estado.

## Referências externas verificadas

SHAs obtidos por `git ls-remote URL HEAD`; arquivos lidos via URLs raw fixadas no SHA e inventários da GitHub API. Nenhum checkout externo foi aplicado ao repositório Clicko. Conteúdo de README descreve intenção do autor, não comprovação de capacidade em produção.

| Referência | SHA exato consultado | Arquivos/diretórios inspecionados | Licença e utilização |
| --- | --- | --- | --- |
| [OpenCut Classic](https://github.com/OpenCut-app/opencut-classic) | `cf5e79e919144200294fb9fed22a222592a0aeea` | `LICENSE`; `apps/web/src/core/managers/{timeline,project,playback}-manager.ts`; `commands/timeline/element/insert-element.ts`; inventário de `docs/`; `rust/crates/compositor/src/compositor.rs` | MIT, copyright OpenCut 2025–2026. **Referência arquitetural, zero código incorporado.** Separação de mídia, comandos, estado, monitor e compositor é compatível. Não trouxemos Next.js, Bun, GPUI, wgpu nem armazenamento próprio. Projeto arquivado. |
| [OpenCut atual](https://github.com/OpenCut-app/opencut) | `e668010778568641babef2cc40be4703ae6916d6` | `LICENSE`, `README.md`, `apps/desktop/src/panels/timeline.rs`, inventário da árvore | MIT, copyright OpenCut 2026. **Referência arquitetural, zero código incorporado.** A reescrita anuncia APIs/plugins/headless; o painel desktop consultado é um placeholder de timeline. Não foi usado como dependência pronta. |
| [FFmpeg](https://github.com/FFmpeg/FFmpeg) / [upstream oficial](https://git.ffmpeg.org/ffmpeg.git) | `94cba3150c6b83057ed48b833689adc806715cc0` | `LICENSE.md`, `libavfilter/vf_overlay.c`, documentação oficial de filtros e CLI | LGPL predominante, condições variáveis conforme build. **Executável externo**, chamado por subprocess com argv, sem shell. Não copiamos fonte. Abaixo consta a distribuição efetivamente utilizada, que tem outro commit. |
| [OpenTimelineIO](https://github.com/AcademySoftwareFoundation/OpenTimelineIO) | `f8a2f36df61ce88eb6b73a57df393a87d3e3e42e` | `LICENSE.txt`, `src/opentime/rationalTime.h`, `src/opentimelineio/clip.h` | Apache-2.0. **Referência de modelo temporal, zero código ou dependência incorporados.** A timeline Clicko já armazena fps racional, frames, faixas e intervalos de origem em microssegundos; adicionar outro modelo duplicaria a autoridade. Intercâmbio OTIO fica para etapa posterior. |
| [Remotion](https://github.com/remotion-dev/remotion) | `02109419d34bea9ddfb45883b6dbf1ec477379e6` | `packages/core/LICENSE.md` | Licença própria com critérios de elegibilidade, licença empresarial e restrições de redistribuição. **Avaliado e não adotado.** Sem pressupor elegibilidade da Clicko; nenhuma dependência/código novo. Motion desta etapa é próprio, persistido e compilado por FFmpeg. |
| [Shotcut](https://github.com/mltframework/shotcut) | `ff417ebfedd9f6d701fd6af439affeafcb6e8a0f` | `COPYING`, `src/commands/timelinecommands.h` | GPL-3.0-or-later no arquivo de comandos. **Referência funcional somente**, sem código incorporado. Estudados comandos de corte, ganho, fade e undo. Qt/MLT não foram adicionados. |
| [Kdenlive](https://github.com/KDE/kdenlive) | `364e2d5078b1b4cf2c44839bf250780c6a14f98d` | `COPYING`, `src/timeline2/model/timelinemodel.hpp` | GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL no arquivo analisado. **Referência funcional somente**, sem código incorporado. Reforçou a autoridade do modelo sobre alterações da interface. Qt/KDE/MLT não foram adicionados. |

Histórico externo adicional efetivamente consultado: os commits Classic `79dcec8a2ec2f5cad9be95e5b52fbfa752fb6ac4` (split builtin/freeform masks) e `401cc35743aafc4c8bdfb8055501650390bde88b` (animate params over time) foram identificados na API de histórico de `timeline-manager.ts`; seus patches não foram incorporados.

## Distribuição executável e ferramentas

- Distribuidor: [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds), listado na [página oficial de downloads](https://ffmpeg.org/download.html).
- Arquivo verificado: `ffmpeg-n9.0-latest-win64-lgpl-shared-9.0.zip`, 77.224.121 bytes.
- SHA-256 do ZIP: `320f698345a15625bd5571fd1aa2f49a041d2e6c4c4088bbce04f8c33993e979`, comparado ao digest da API de release antes de extrair.
- Reinstalação fixada em `scripts/video/install-ffmpeg.ps1`: release `autobuild-2026-10-17-20-51`, arquivo versionado `ffmpeg-n9.0.2-28-g669f5ab083-win64-lgpl-shared-9.0.zip`, SHA-256 `00ab3bc8fe02554bd0fffac9968bba498d1ab7e899a4871b85fbba828a50bfcc`. O ZIP versionado e o alias `latest` inicial são arquivos distintos; os digests não são intercambiáveis.
- Versão medida: FFmpeg e ffprobe `n9.0.2-28-g669f5ab083-20261017`.
- Commit do FFmpeg **do binário**, resolvido na API: `669f5ab083c7732c10f1ce9e4f1915960dd88457`.
- Configuração medida: `--enable-shared --disable-static --enable-version3 --enable-libopenh264 --disable-libx264 --disable-libx265`; `--enable-gpl` e `--enable-nonfree` ausentes. Licença identificada: LGPL-3.0-or-later.
- Codificação exercitada: `libopenh264` (H.264) + AAC nativo, MP4/YUV420p/faststart. OpenH264 tem termos próprios; o inventário completo de bibliotecas do build permanece no pacote e em `ffmpeg -buildconf`. Não se afirma que todas as distribuições FFmpeg tenham a mesma licença.
- O diretório local ignorado `.codex-runtime/ffmpeg/` conserva o ZIP, `LICENSE.txt`, documentação, DLLs e cabeçalhos originais. Não foi adicionado ao bundle do navegador nem ao Git. Se uma distribuição for entregue a terceiros, seus avisos, fontes correspondentes e obrigações precisam acompanhá-la; esta etapa instala uma ferramenta local e não publica um pacote de terceiros.
- `Node v24.15.0`, `Python 3.12.14`; React/TypeScript, FastAPI, SQLAlchemy, Celery e Pillow são dependências já existentes. Nenhuma dependência npm/Python foi adicionada.

## Implementação Clicko

1. Interface React mantém painel de materiais, propriedades, timeline e monitor, usando componentes e tokens Clicko. Arquivos e navegação Craft existentes continuam disponíveis.
2. Modelo único: `CreativeDocumentV1.composition.mediaTimeline` (`studio.media-timeline.v1`). Clipes mantêm os tempos de timeline em frames e origem em microssegundos; fps racional evita assumir 30fps. Títulos são `CaptionCueV1` com campos aditivos de motion/keyframes.
3. Gravação dedicada exige revisão e identidade de pedido. Compare-and-swap impede escritores obsoletos; recibos duráveis no barramento existente permitem conciliar resposta perdida. Não é permitida reescrita de composições nativas por esse endpoint.
4. Render é um novo tipo de job da fila existente (`timeline_render`, perfil `media_cpu`). O pedido guarda snapshot imutável; materiais são autorizados por workspace e checksum. Em desenvolvimento, despacho em executor limitado evita bloquear a requisição pela configuração eager. Produção continua em Celery/Redis.
5. O compilador próprio gera apenas filtros reconhecidos e valores numéricos validados. Texto é rasterizado por Pillow em PNG transparente com fonte local, sem interpolar texto em shell/drawtext. Fade, deslocamento, escala, opacidade, rotação, velocidade, mixagem e fades de áudio são operações reais. Parâmetros desconhecidos são rejeitados.
6. Prévia e exportação utilizam o **mesmo MP4**; não há um compositor de preview divergente. Exige ação para renderizar a revisão editada; o monitor identifica revisões antigas.
7. ffprobe valida streams H.264/AAC, duração e dimensões antes de armazenar o MP4. Apenas depois da gravação e checksum o job pode concluir.
8. Entrega usa os assets existentes e um catálogo de leitura na Biblioteca global. Não cria cópia em localStorage. Conteúdo é transmitido com sessão, escopo de cliente/workspace e suporte a Range; o navegador não recebe tokens de backend.

## Limites explícitos

MVP limitado a 10 minutos, 16 faixas, 32 itens, 1920px por dimensão e 60fps; keyframes lineares de X/Y/escala/opacidade, rotação estática e transições por sobreposição/fade. Rejeita máscaras, filtros arbitrários, composição nativa ou recursos não representados pelo compilador. Não implementa preview de efeitos em tempo real, curva Bézier, GPU, remoção de fundo, geração integral por IA, avatar, nova síntese de voz ou intercâmbio OTIO.

Provedores de IA e runtimes Craft continuam dependendo de configuração própria. A regra comercial de minutos de vídeo não foi reinventada nesta etapa; sua conciliação com jobs renderizados, assim como armazenamento global, precisa de uma política explícita. Produção distribuída exige workers e armazenamento provisionados.

Os testes com mídia real e os testes de contrato são registrados em `VIDEO_STUDIO_DELIVERY.md`. Disponibilidade de navegador/QA visual é relatada separadamente; não equivale à validação dos arquivos de mídia.
