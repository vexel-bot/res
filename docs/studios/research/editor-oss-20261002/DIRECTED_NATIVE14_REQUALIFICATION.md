# Requalificação técnica dos três estudos dirigidos — native.14

04/10/2026. Original em `C:/Users/edugu/Downloads/res`. Nove novos MP4s foram produzidos pelos documentos, planos, jobs e assets reais do Studio: organização, comparação e captura de interface, cada um com A/B/controle. Todos têm 1080×1920, 30 fps, 450 frames, 15 s, H.264/AAC, qualidade high e renderer `4.0.527-native.14`. O QC técnico passou nos nove; todos conservam o aviso de silêncio. **Revisão humana e autonomia continuam não avaliadas.**

Os documentos e MP4s históricos native.5 permanecem intactos. A direção de cada novo plano é idêntica à direção canônica anterior, exceto pela revisão esperada da nova cópia. Os mesmos materiais autorizados mantêm seus checksums. Não há geração paga, novo motor, outro modelo de projeto ou novo clone de repositório nesta rodada.

## Evidências e alcance

O [recibo selado](directed-native14/verification.json) verifica 66 fontes: as 62 previamente qualificadas, sem alteração, mais quatro fontes do fluxo de estudo. Os três novos helpers foram arquivados em bytes junto ao recibo. Foram conferidos nove jobs atuais pela API e pelo banco, seus snapshots, revisão/versão, plano, resultado, checksum do arquivo e preservação das nove revisões e MP4s anteriores.

Cada MP4 foi completamente decodificado a 270×480. Foram retidos 4.050 hashes de frames, seus timestamps CFR, diferenças de canais e nove folhas de contato. A dimensão 1080×1920 pertence aos streams originais conferidos por ffprobe; a análise dos pixels desta rodada usa 270×480. Os recibos do renderer também conservam geometria DOM de todos os 4.050 frames. Bounds não provam cobertura de máscara ou bounds de glifos. Nas duas comparações dirigidas, os únicos bounds fora do canvas são do `occluder`, cujo percurso authored entra e sai do quadro; isso não foi classificado como corte de texto.

O áudio foi decodificado a mono/48 kHz para análise, com 720.896 amostras por arquivo. As primeiras 720.000 correspondem aos 15 s; as 896 finais são padding da decodificação AAC. A energia foi registrada em janelas de 20 ms, mantendo o aviso de silêncio do QC. Presença, energia e duração não aprovam sincronização causal ou escuta.

As três novas sessões cegas foram criadas pela API após conferir as três variantes de cada estudo, igualdade de briefing/materiais, decisões distintas e simplicidade do controle. As sessões históricas não foram alteradas. As atuais estão `not_assessed`, sem blockers e sem review:

| Estudo | Sessão nova |
|---|---|
| Organização | `d2412e84-c643-4c3d-b697-583c31562a47` |
| Comparação | `c7d85c2d-2dad-4e7f-8fca-b45736544732` |
| Interface | `e2182ac8-2824-4888-b385-a14ffb81c8ef` |

A [galeria cega](../../../../output/visual-directed-native14-20261004/blind-review/REVIEW.html) mostra as letras sorteadas pela API e os próprios bytes dos assets canônicos. Seus nove aliases são hard links NTFS, conferidos por identidade de arquivo e SHA, sem cópia adicional de dados de mídia. Os nove MP4s coletados somam 10.182.593 bytes; esse valor não é uma auditoria de todo o espaço do projeto, storage, temporários ou caches.

No navegador, as nove opções carregaram sem erro, com duração de 15 s, dimensão de vídeo 1080×1920 e largura exibida de 280 px. Cada uma chegou a `ended`/15 s em velocidade 1×, sem outro player em reprodução. A automação estava sem som; não é avaliação humana nem prova de escuta. A galeria foi devolvida a 0 s, pausada e com som habilitado. Observações DOM, eventos de reprodução e screenshots estão fixados no recibo.

## Interrupção e recuperação documentadas

A primeira solicitação HTTP expirou aos 120 s, mas seu job terminou normalmente; o identificador foi recuperado sem reenviar o render. O tempo retornado pelo renderer foi 172.406 ms.

Durante a variante B de organização, os processos locais da aplicação pararam. A lease estava vinculada ao próprio job e sua identidade de processo Windows já não existia. O pedido de cancelamento veio da API; o serviço existente foi chamado somente no ramo `cancel_requested → cancelled`, que retorna antes de executar um provider. Nenhum output foi publicado nessa reconciliação. A API de retry reutilizou o mesmo job e snapshot.

A primeira tentativa de restaurar a API foi iniciada sem `REMOTION_NATIVE_ENABLED=true` e falhou com `video_render_provider_unavailable`. O diagnóstico foi preservado. Corrigimos a flag no processo da API e repetimos pelo endpoint de retry do mesmo job; o resultado final native.14 foi conferido. A rodada não omite essas intervenções nem se apresenta como execução sem assistência.

Os tempos individuais retornados pelo renderer variam de 65.188 a 172.406 ms. Não há estimativa de p95, comparação causal de desempenho com native.5 ou promessa de realtime. A restauração mudou os processos concorrentes do ambiente e não constitui um benchmark controlado.

## Checks e trabalho restante

Ruff passou nos três novos scripts. O diff check restrito aos componentes/CSS previamente alterados passou; o check global apontou whitespace preexistente em duas licenças de fontes, que foi preservado. Nenhum código de produção mudou nesta rodada; a integridade das 62 fontes anteriores foi conferida antes, durante e após os decodes.

A [revisão criativa e protocolo](DIRECTED_NATIVE14_CREATIVE_REVIEW.md) separa observação, diagnósticos das duas lentes, inferência, assertions e contraprovas. Permanecem abertas a distinção entre os dois estudos gráficos, leitura móvel do disclosure, utilidade dos holds e escuta dos acentos. O QC e a reprodução completa não resolvem essas questões.

O usuário recebeu o pedido de preferência cega e notas humanas; nenhum score foi preenchido pela automação. O critério dirigido exige aprovação dos quatro eixos do handoff e preferência frente ao controle nos três estudos. Depois vêm três briefs novos com intervenções explícitas. As direções históricas reutilizadas aqui não contam como esses briefs e não demonstram generalização autônoma.

Precisão do contrato atual: a revisão individual registra clareza, ritmo, continuidade e adequação; a comparação exige adicionalmente acabamento. `_visual_approved` verifica clareza/ritmo/continuidade/acabamento ≥4 e a aprovação individual vinculada ao checksum/revisão. Portanto, coletar as cinco notas apresentadas na galeria; acabamento ausente continua pendente, sem valor inferido.

A ligação destes projetos verticais de 15 s à prévia central de `VideoStudio` ainda precisa de observação real. A galeria é um artefato de revisão dos MP4s, não essa qualificação de interface. O lançamento recusado de um novo frontend em 3319 não foi repetido nem contornado.

A limpeza dos clones/bundles continua pendente: a revisão automática havia recusado a remoção por `blocked by policy`. A ação não foi repetida nem contornada.
