# Redução da distância visual — execução de 02/10/2026

## Conclusão da rodada

A tradução das receitas deixou de ser apenas um contrato: coreografia, parenting local, tipografia por unidade inteira, matte retangular ligado a oclusor, desenho vetorial e exposição temporal de gráficos têm execução nativa. Os estudos usam o Studio real, com documento, plano aplicado, snapshot, render e recibos. A aprovação visual e a autonomia permanecem pendentes; testes e QC não fornecem notas humanas.

Repositório: `C:/Users/edugu/Downloads/res`. Workspace isolado: `4812f2c0-1a2a-4f6d-967d-17b370c8d849` (Laboratório Motion 01-10). Nenhum material de cliente, compra, instalação Adobe, chamada paga ou troca para Alight nesta rodada. APIs: **US$ 0**, dentro do teto compartilhado de US$ 10. Não há promoção a `render_verified`.

Resultado técnico: **9/9 variantes atuais** concluídas pela API, todas com QC `passed`, H.264/AAC, 15 s, 1080×1920 e 30 fps. São três briefs próprios com materiais prontos e render; o indicador retorna **0 aprovações visuais**, **0 comparações aprovadas** e fase `pending`. As três sessões congeladas existem em `not_assessed`. O índice vincula os nove checksums, IDs de jobs, revisões e planos aplicados.

Tempo registrado pelo provider nos nove renders atuais: aproximadamente **44–77 s** neste PC. São nove observações, sem medição de p95 ou promessa de desempenho geral. Todos têm um aviso de silêncio prolongado: o áudio contém acentos espaçados. Esse aviso não vira aprovação de som; exige escuta na revisão.

## Implementação

- `native_motion_recipes.py` traduz dados tipados para propriedades/tracks/nodes antes dos hashes; disputa de autoria, espaço de coordenadas ambíguo e recursos ausentes são rejeitados.
- `scene_compiler.py` v2.16 persiste receitas, parâmetros, versão, operações e direção de arte. A projeção Remotion independente inclui o digest da composição nativa. Parâmetros divergentes da operação baixada bloqueiam o render.
- O runtime mede a fonte final, revela palavras/caracteres, usa curvas e pivôs e desenha o traço. Motion blur integra amostras temporais de gráficos; não é blur estático. Parenting não duplica o deslocamento do pai.
- Oclusão inicial é restrita: irmãos, oclusor retangular, sem rotação/escala, translação crescente em um eixo. Mattes arbitrários, profundidade e refração continuam pendentes.
- Estudos gráficos e de interface têm critérios próprios de materiais. O gate comercial de produto/filmagem continua exigindo suas fontes e identidade autorizadas.
- Comparações entre documentos congelam três referências no mesmo briefing/acervo, com labels randomizados, revisão e checksum. Alterações tornam a sessão obsoleta. O Studio mantém cinco inputs de notas vazios (quatro eixos de aceite e adequação já exigida no recibo antigo), inspeções desmarcadas e achados estruturados por cena/intervalo/causa/correção.
- O indicador separa QC, qualidade visual e autonomia. A interface deixou de mostrar a imagem de exemplo da Aurora enquanto um material real está pendente.
- A comparação abre um diálogo maior com três previews de 280 px, em vez de depender da coluna lateral estreita. Campos de notas permanecem vazios; controles de vídeo e formulário pertencem à mesma sessão congelada.
- A biblioteca existente conserva a origem documental das técnicas. Cada operação baixada aponta a ficha `alight.<técnica>` como conhecimento de origem; execução nesta rodada é Remotion. Documentação não é tutorial assistido; referências anteriores sem áudio não viraram evidência acústica.

## Estudos e materiais

Cada estudo tem A, B e controle simples, 15 segundos, 1080 × 1920, 30 fps. Planos autorais dirigidos, com intervenções registradas; nenhum foi atribuído à direção autônoma do planejador.

| Estudo | Transformação e diferenças | Limite da inferência |
|---|---|---|
| Organização | Ideia/Plano/Resultado saem de posições dispersas para uma estrutura. A alinha verticalmente; B escalona ritmo e relação diagonal; controle salta entre estados. | É um estudo gráfico restrito, não anúncio comercial nem prova de linguagem cinematográfica. |
| Comparação | Mesmo conjunto mantém identidade enquanto a relação ganha um traço e uma consequência revelada por matte. O controle conserva o texto da consequência sem a revelação dirigida. | Ainda próximo visualmente do estudo de organização; a adequação e distinção conceitual precisam de avaliação humana. |
| Interface | Texto vazio → texto editado → aplicação persistida → legenda na prévia real. Recortes da edição e do resultado, com tempos de origem preservados. A/B diferem no ponto de corte e enquadramento; controle simples. | Captura de teste dirigida. Reprodução automática comprova funcionamento, não compreensão ou julgamento humano. |

Fonte: Manrope local, licença SIL OFL copiada para o pacote. Textos e vetores próprios. PCM original com pontuações discretas; sem voz. Áudio original dos vídeos é mudo e a finalização FFmpeg é única. Mix e sincronismo perceptivo continuam sujeitos à escuta humana.

Captura válida: `interface-capture-evidence.json` registra um texto inicial diferente do final e a revisão salva pelo PUT do documento real. A tentativa com texto inicial já final foi descartada como evidência de transformação. Crops são derivados explícitos da captura, com checksum do pai e geometria em pixels; não são uma interface inventada.

Na captura final (revisão 16 da tarefa), o clique começa em aproximadamente 7,1 s e a confirmação/inspeção termina em aproximadamente 10,8 s. Esses são tempos de parede da UI, não medição de frames codificados. A tarefa ficou em 15,004 s; foi removido somente o carregamento anterior, sem acelerar a ação ou cortar a espera desta gravação. A/B cortam entre os crops em 9,5/9,2 s. O script permite cortar uma espera longa explicitamente, mas esse mecanismo não foi necessário no material final. `interface-fast-input-cycle/` preserva as três primeiras exportações substituídas.

## Auditoria de falhas e correções executáveis

| Erro observado | Diagnóstico e ação |
|---|---|
| WOFF2 retornou 415 e depois faltou decoder | Upload não contemplava fonte WOFF2. Adicionado MIME, validação FontTools, limites de tamanho e Brotli fixado. Fonte falsa é rejeitada; a real é validada. |
| Plano sem foco principal | Preflight bloqueou aplicação. A direção passou a declarar papel principal correto. |
| Oclusor e texto em pais distintos | Receitas bloquearam máscara. Inserido grupo explícito comum, preservando coordenadas. |
| Traço alguns pixels abaixo do esperado | Teste real de pixels mostrou deslocamento de baseline do SVG inline. `display:block` corrige a posição. |
| Teste API recebeu `heavy_media_execution_in_progress` | Disputa com render real em andamento. Repetido com fila livre; bloqueio não foi removido. |
| `created_at` no armazenamento de eventos | Modelo usa `occurred_at`. Corrigida ordenação e adicionado teste com armazenamento SQL real; fixture antiga corrigida para espelhar o modelo. |
| Captura antes/depois igual | Tentativa anterior já havia salvo o texto. Reset restrito ao documento de teste e nova captura com estados distintos. |
| Probe da segunda captura retornou 409 | Chave idempotente reutilizada com outro asset. Chave passou a incluir checksum; recuperada a captura válida local. |
| Receita ultrapassava o primeiro trecho da interface | Limite ajustado ao frame de corte. Não foi afrouxada a validação temporal. |
| Dois principais em intervalos separados | Regra antiga contava elementos sem tempo. Agora aceita principais raiz explicitamente sequenciais, mantendo rejeição de sobreposição e relações ambíguas. |
| Fonte sem glifo da seta textual | Render bloqueou glifo ausente. O plano usa separador suportado, sem fallback silencioso de fonte. |
| Decodificação `No frame found at position` | Log resumido ocultava a causa. Logs completos agora são preservados, removendo telemetria geométrica do resumo. Fonte tinha 450 frames CFR/15 s e decodificava no FFmpeg. Limitar concorrência/cache não resolveu a reprodução isolada. Recodificar os dois crops para H.264 CFR30 all-intra sem B-frames permitiu concluir as três variantes pela API; a proveniência registra perfil, pai, checksum e tempo inalterado. Isso comprova compatibilidade deste material, sem provar uma causa geral de memória. |
| Captura preenchia texto rápido demais | Triagem dos quadros mostrou entrada instantânea; corrigida a gravação para entrada real de teclado progressiva e pausa inicial, conservando tentativa anterior. Não é aprovação de compreensão. |
| Recarregamentos e conexão resetada durante gravação | Logs da sessão mostraram navegação interrompida; ensaio isolado usa outra porta e HMR desligado, preservando a sessão aberta. Porta ocupada é registrada e não se encerra processo alheio. |

Diagnóstico do decoder usa a [documentação oficial do Remotion](https://www.remotion.dev/docs/troubleshooting/no-frame-found-at-position). Cache insuficiente e gaps são hipóteses documentadas. Não atribuir automaticamente todo problema a memória. A rodada registra o resultado do perfil explícito no recibo.

## Evidências, reprodução e avaliação

Pacote em `output/visual-distance-20261002/`:

- `execution.json`: assets/checksums, revisões, planos/jobs, artefatos, metadados, custos e intervenções;
- `*-plan.json`: planos realmente aplicados e manifestos;
- `*.mp4`: variantes e controles; `initial-cycle/` preserva o primeiro ciclo substituído por correções executáveis;
- `quality-program.json`: projeção do indicador e sessões congeladas;
- `render-index.json`, `cost-receipt.json` e `inspection-findings.json`: índice resumido, custo da rodada e triagem separada da avaliação humana;
- `human-review-template.json`: campos vazios para acompanhamento; não é recibo de aprovação;
- `studio-verification.json`: reprodução mecânica no Studio, dimensões/taxa/tempo e confirmação de formulário vazio, sem submissão de avaliação;
- `interface-before.png`, `interface-after.png` e `interface-capture-evidence.json`: evidência da tarefa real;
- logs API/worker e licença da fonte.

Executar `visual-distance-study.py prepare`, `capture`, `render`, `compare`. `materials` recupera uma captura local já verificada, sem repetir a ação. São ferramentas de validação dirigida, não caminho do planejador autônomo. Tokens são efêmeros em memória/stdin e não entram nos recibos.

Testes: **52 testes** na suíte focada de receitas, comparação, programa de qualidade, renderer e compatibilidade Alight; **9 testes** adicionais de observação semântica e reavaliação histórica. Curvas/pivô/hash/autoria, parâmetros obsoletos, ausência de capacidade, leitura/hold, compatibilidade antiga, foco temporal, fontes reais/falsas, permissões, armazenamento de sessões, comparação pendente/obsoleta/controle e separação QC/visual estão cobertos. Testes reais de pixels e API nativa também passaram, incluindo máscara/traço/parenting/motion blur e trim/velocidade em fps distintos. TypeScript do frontend e Ruff dos arquivos da rodada passaram. Isso não afirma que toda a suíte do repositório foi executada.

Reprodução pelo Studio: os **nove vídeos completos** terminaram em velocidade 1×, com duração de 15 s e dimensões 1080×1920, usando blobs da API autenticada. O primeiro ensaio registrou previews de aproximadamente 223 px; a melhoria de diálogo foi verificada no estudo de organização, com três previews de **280 px**, reprodução completa, cinco notas vazias e envio incompleto desabilitado. Essa repetição verifica o componente comum, não representa nove novos renders. Evidências em `studio-first-playback-verification.json`, `studio-verification.json` e screenshots. Reprodução foi **muda**; não equivale a ouvir ou aprovar esteticamente as peças.

A API compartilhada recarregou durante alterações paralelas. A tentativa de abrir novas instâncias isoladas de API/web foi bloqueada pela revisão automática (motivo informado: política). A validação terminou usando a instância existente e a porta de UI 3008, sem encerrar serviços alheios. Essa ocorrência é operacional e não muda os estados de aprovação.

Quadros amostrados são triagem, sem equivaler à compreensão do vídeo inteiro. Os gráficos continuam simples, com áreas estáveis de título/identidade e pouca variedade de linguagem; essa limitação está exposta para revisão, sem qualificá-los automaticamente como referência estética aprovada.

## O que falta para o aceite

Uma pessoa deve assistir às três opções de cada estudo inteiras e com som, conferir celular, registrar preferência cega, notas ≥4 nos quatro eixos e diferenças frente às referências. Reprovações precisam indicar intervalo, causa e correção executável. Reexportação exige revisão de plano/material/mix.

Depois de aprovação dirigida, executar três briefs novos com o planejador usando os mesmos operadores, sem alterar código ou esconder intervenções. A infraestrutura e os estudos desta rodada não demonstram essa autonomia. A fase segue aberta até essas evidências; nenhum resultado ausente vira sucesso.

O [brief do editor](../POWERFUL_VIDEO_EDITOR_BRIEF_2026-10-02.md) orienta o outro chat. Este relatório delimita as capacidades reais e seus limites para evitar implementações divergentes.
