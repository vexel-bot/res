# Mattes por imagem — implementação e evidência técnica

O res agora executa a receita tipada `asset_matte` v1 sobre o documento/grafo existentes: PNG arbitrário, alpha ou luminância sRGB, inversão, intervalo semiaberto e transformação entre grupos distintos. A fonte é consumida sem aparecer como imagem colorida. Remotion continua renderizando os gráficos e FFmpeg finaliza a saída. A implementação é original, orientada pelos estudos de dependências do Natron e coordenadas do Motion Canvas; nenhum código ou motor desses editores foi incorporado.

[Compatibilidade e limites](ASSET_MATTE_COMPATIBILITY.md): `studio.asset-matte.v1`, compiler `res.native-recipes.v4`, component library 6, provider `4.0.527-native.8`. Snapshots v1/v2/v3 continuam legíveis; recompilação é explícita. A política tipográfica v3 é conservada. O parâmetro opcional vazio não é serializado nas receitas antigas. Binding de fonte/target/asset/intervalo, parâmetros e versão entram na composição canônica e seus digests.

## Prova real

[asset-matte-receipt.json](asset-matte-receipt.json) verifica hashes das fontes de implementação, XMLs, PNGs, evidências e MP4s. Consolida **129 casos pytest únicos aprovados e um ignorado**, preservando a sobreposição entre rodadas e o histórico de falhas corrigidas. A regressão cobre contratos de receitas/grafo/editor, Unicode/fontes/hold, compilação editorial e a fixture existente de parenting/máscara/stroke/blur. O teste de render legado HyperFrames foi ignorado porque seu runtime explicitamente fixado está indisponível; isso não é um passe do HyperFrames.

As seis fixtures passam por upload do PNG original → plano pela API → apply → inspeção da revisão → job real → MP4 → checksum/QC → FFmpeg decodificando todos os frames. Somente o despacho assíncrono do job é substituído para permitir sua execução síncrona no teste; render, armazenamento e QC são reais.

| Fixture | Comportamento observado | Evidência |
|---|---|---|
| Alpha | Branco e preto opacos têm a mesma cobertura; furo/transparência ficam vazios; semi-alpha é parcial | [vídeo](asset-matte-render/alpha-normal/matte.mp4), [recibo](asset-matte-render/alpha-normal/evidence.json) |
| Alpha invertido | Cobertura complementar também fora do footprint da imagem | [vídeo](asset-matte-render/alpha-inverted/matte.mp4), [recibo](asset-matte-render/alpha-inverted/evidence.json) |
| Luminância | Preto opaco não cobre; cinza × alpha produz cobertura menor que alpha isolado | [vídeo](asset-matte-render/luminance-normal/matte.mp4), [recibo](asset-matte-render/luminance-normal/evidence.json) |
| Luminância invertida | Complemento da luminância × alpha, sem contar opacidade do pai duas vezes | [vídeo](asset-matte-render/luminance-inverted/matte.mp4), [recibo](asset-matte-render/luminance-inverted/evidence.json) |
| PNG 256 × 128 com contain | Fonte cabe em 128 × 128 conservando proporção; letterbox transparente | [vídeo](asset-matte-render/alpha-wide-contain/matte.mp4), [recibo](asset-matte-render/alpha-wide-contain/evidence.json) |
| Mesmo PNG com cover | Recorte central na caixa da fonte, antes da transformação entre grupos | [vídeo](asset-matte-render/alpha-wide-cover/matte.mp4), [recibo](asset-matte-render/alpha-wide-cover/evidence.json) |

Cada vídeo tem 320 × 320, 30 fps, 15 frames/0,5 segundo, QC técnico passed. O matte atua somente nos frames 2–12; 0, 13 e 14 comprovam o target sem matte. Há 35 amostras de cobertura por vídeo em sete frames, mais amostra fora do footprint e a contraprova contain/cover. Os valores esperados vêm dos bytes do PNG e das transformações authored, não do bbox ou da matriz retornada pelo worker. A tolerância por canal é menor que 12/255 para o MP4 H.264; erros efetivamente observados estão no JSON consolidado.

Os seis renders repetidos depois do gate de PNG estático passaram. Erro máximo observado: 5/255 entre as 210 amostras. No ponto que distingue proporção/recorte, contain retornou RGB (0,0,0) e cover (100,102,100), com expectativa 102 por canal. Tempos locais observados de render: 17.859–21.969 ms; vídeos entre 6.172 e 9.460 bytes. Não são medidas de projetos comerciais longos.

Fonte e target têm pais com movimentos/rotações distintos; o pai da fonte também escala. As matrizes em quatro frames ativos são comparadas com uma fórmula independente, tolerância 0,002. O target usa borda de 4 px no pai: seu deslocamento de padding entra na transformação uma vez. Opacidade local da fonte 0,5 é entrada do matte; opacidade 0,2 do pai da fonte não é entrada, conforme `source_layer_only`; opacidade 0,8 do pai do target é aplicada uma vez. Observações DOM explicitamente dizem `pixelCoverageObserved: false`; cobertura é verificada no vídeo decodificado.

## Diagnóstico, custo e regressões

Negativos rejeitam fonte/asset/identidade/intervalo inválidos, checksum ou MIME divergentes, binding adulterado, ciclo/parent ausente, duas máscaras no mesmo target, paint stack/transição não suportados na fonte e role de fonte inconsistente. O runner verifica assinatura/IHDR PNG, limites de pixels e ausência de acTL antes de bundle/decode; [asset-matte-png-study.json](asset-matte-png-study.json) registra 17 verificações, inclusive APNG original com dois frames rejeitado. O nome acTL dentro de texto ancillary não causa falso positivo. Isso não equivale a validar CRC/todo o arquivo PNG: a decodificação real continua obrigatória antes da captura.

[Contraprova APNG por API/job](asset-matte-render/animated-negative/evidence.json): plano/apply aceitam o asset de MIME PNG, mas o runner interrompe antes do browser com `hybrid_asset_matte_animated_png_pending`; nenhum vídeo é publicado e o resultado permanece vazio. Após essa primeira tentativa, o job fica `retrying` pela política genérica existente de erros de render. Classificação terminal específica não foi implementada nesta rodada; a correção indicada é fornecer PNG estático, sem prometer sucesso de retry do mesmo APNG.

As execuções locais e seus tempos/tamanhos estão registrados individualmente no JSON; fixtures de meio segundo não estabelecem p95, realtime 1080p ou custo em projetos longos. Ruff dos arquivos desta capacidade, TypeScript do worker e sintaxe dos runners passaram. Não foi declarada aprovação de lint de todo o checkout compartilhado.

Histórico preservado: upload inicial com kind incorreto; primeira amostra situada na borda do target; amostra do PNG reduzido muito próxima do furo; amostra do cover fora do target. Os testes foram corrigidos com pontos interiores/consequência observável, mantendo a tolerância original. [Diagnóstico da amostra reduzida](asset-matte-wide-diagnostic.json) e [frame](asset-matte-wide-diagnostic-frame-4.png) conservam a observação anterior; não são recibos de qualificação.

A regressão editorial também encontrou três licenças com CRLF em vez dos bytes LF exigidos pelo manifesto. Foram restaurados os bytes que correspondem aos hashes originais e adicionada regra `.gitattributes` restrita às licenças desse pacote para conservar seus finais de linha. Fontes, manifesto e validação estrita não foram alterados. [Compatibilidade](FONT_LICENSE_BYTE_COMPATIBILITY.md) e [integridade](font-license-integrity.json) documentam a correção; importação real/deduplicação passou depois.

## Estado e trabalho restante

Estado: implementado com evidência técnica dessas fixtures. Revisão humana, legibilidade no celular, qualificação comercial/A-B dos três estudos e autonomia em briefs novos permanecem pendentes. Não há notas humanas preenchidas. PNG estático não oferece tracking/roto, vídeo de máscara, morph de caminhos ou combinação de paint stacks sobre a fonte. Limites e diagnósticos estão no contrato de compatibilidade.

A revisão automática de aprovação rejeitou a remoção dos clones/bundles anteriores com `blocked by policy`, sem outra razão fornecida. A limpeza continua pendente e nenhum espaço recuperado foi confirmado. Não houve nova tentativa nem uso de outro mecanismo para contornar a rejeição. Esta capacidade acrescenta fixtures originais pequenas e recibos; não baixa outro editor.
