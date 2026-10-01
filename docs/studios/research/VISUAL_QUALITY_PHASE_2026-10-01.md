# Fase de qualidade visual verificável — 01/10/2026

## Estado e método

Esta fase separa três conclusões: funcionamento técnico do render, avaliação visual humana e autonomia demonstrada. Nenhum QC técnico aprova automaticamente a qualidade visual. O indicador interno usa os estados `not_assessed`, `correction_needed`, `rejected` e `approved`; uma aprovação exige inspeção do vídeo completo e em tamanho de celular, notas humanas de pelo menos 4/5 em clareza, ritmo, continuidade e acabamento, e vínculo ao ID, revisão do documento e SHA-256 do arquivo exportado. Um novo arquivo ou revisão invalida a avaliação anterior.

O indicador fica desligado por padrão (`STUDIO_VISUAL_QUALITY_INDICATOR_ENABLED=false`). No ambiente local foi ativado para a equipe. A API de leitura `/api/v1/studios/v1/workspaces/{workspace_id}/visual-quality` exige owner/admin. O Studio mostra os três eixos, pendências de material, os renders, achados com intervalo e ação corretiva, progresso dos três casos e reservas de API.

## Auditoria antes de decidir

Os logs locais de `tmp/localhost.stdout.log` e `tmp/localhost.stderr.log` terminam em 09/09/2026; não documentam uma falha atual do compositor. O banco local contém execuções de setembro bloqueadas por teto de orçamento e respostas que não cumpriram o schema. Essas evidências não sustentam uma troca de renderer nem a instalação imediata de um serviço externo. O ensaio de 30/09 tem seis animatics sintéticos, quadrados, silenciosos e de quatro segundos. Seus checksums estão em `benchmarks/studios/video/visual-quality-baseline-2026-09-30.v1.json`. Eles passaram no render técnico e foram classificados como **reprovados visualmente** à luz do feedback qualitativo do usuário; não há notas humanas numéricas para eles.

## Dados reais encontrados

O `nexus.db` local contém sete documentos do Studio em dois workspaces. Eles são variações de uma campanha Clicko sobre distribuição de conteúdo. Nenhum caso candidato reúne duas fontes de ação distintas verificadas e um asset de produto/marca identificado como tal na proveniência. O indicador aponta `two_distinct_action_sources_required` e `authorized_product_or_brand_asset_missing`. Não há três projetos de produto distintos e prontos. O orçamento reservado desta fase é **US$ 0 de US$ 10**; nenhuma API paga foi chamada. Por isso não foram produzidos vídeos de 15 segundos, comparações cegas ou aprovação visual.

A projeção observada foi salva em `output/visual-quality-phase-20261001/projection.json`, com progresso, bloqueios por workspace e orçamento. É um recibo de estado, não uma aprovação.

## Ajuste de escopo e ensaio seguro

O usuário dispensou a busca de projetos em outra pasta e autorizou continuar com outros materiais que não comprometam nada. A continuação usa o banco temporário dos testes e vídeos diagnósticos locais. Nenhum projeto de cliente foi importado ou alterado e nenhuma API paga foi chamada nesta continuação. Isso permite validar o comportamento do sistema enquanto a qualificação visual continua aberta.

O acervo anterior de `output/hybrid-aurora-pilot` foi auditado pelo README e recibos. Ele contém filmagem de banco e áudio com origem registrada, mas a embalagem real tem baixa resolução e licença comercial pendente. Ela não foi reutilizada nem tratada como marca autorizada nesta rodada. Os dois animatics Aurora tampouco foram promovidos a exemplos aprovados.

No teste de navegador, os três players usam um MP4 diagnóstico local de quatro segundos e respostas simuladas da API. As notas e estados da simulação pertencem ao teste de interface; não são avaliações humanas e não foram gravados no banco do Studio. O teste verifica reprodução privada, anonimização dos rótulos, escolha e conteúdo do recibo, não qualidade estética, duração final ou preferência humana real.

## Contratos para o próximo ciclo

Execuções marcadas com `qualityPhaseId=visual-quality-2026-10-01` exigem montagem mista de 15 segundos, escopo audiovisual, edição nativa e canvas 9:16. A criação para antes de qualquer provedor quando faltam briefing, identidade, duas fontes de vídeo distintas com direitos verificados ou asset real de produto/marca. O formulário de acervo agora permite informar papel visual e ação observável; esses dados seguem no `editingResource` da proveniência ao anexar o asset. A adequação da descrição ainda será conferida na revisão. A marca deve ser um asset real marcado como produto, embalagem, logo ou marca; não basta um ícone gerado. O Studio oferece um controle explícito para iniciar uma execução da fase.

Cada job pago mantém seu teto por execução e também é associado ao ledger compartilhado `budgetGroupId=visual-quality-2026-10-01`, com máximo de US$ 10 em todas as tentativas. O ledger conserva reservas de resultados incertos e usa custo medido quando disponível. Pré-voo rejeitado antes da submissão é liberado. O saldo e o número de tentativas aparecem no indicador. O limite local por provedor ainda pode ser mais baixo e continua valendo.

## Critérios ainda pendentes

Para cada um de três projetos elegíveis, registrar previamente mundo visual, ação observável, escalas, âncoras de continuidade, motivo dos cortes, papel do produto e eventos sonoros. Produzir duas versões dirigidas e uma concatenação de controle com os **mesmos arquivos de origem**, 15 segundos, 9:16 e áudio; revisar integralmente em velocidade normal e no celular. A revisão deve apontar cena, intervalo, causa e mudança executável. Comparação cega, preferência humana pela versão dirigida, notas 4/5 nos quatro eixos e trilha de intervenções manuais são obrigatórias antes de declarar avanço visual ou autonomia. Enquanto faltarem materiais e avaliações, o indicador permanece `pending`; nenhum componente ganha `render_verified` com base no ensaio sintético.

O recibo de comparação pode ser registrado em `POST /api/v1/studios/v1/documents/{document_id}/visual-quality-comparison`. Ele vincula duas execuções distintas da fase, checksums dos exports, fontes idênticas, EDL do controle totalizando 15 segundos, probe vertical com áudio e confirmação humana de comparação cega em velocidade normal e no celular. A declaração de correções manuais não registradas também é obrigatória e impede a aprovação quando verdadeira. O indicador revalida os vínculos; um render ou documento alterado volta a `pending`. A prova de que o arquivo de controle segue a EDL é uma atestação humana registrada, não uma verificação automática quadro a quadro. Hoje o contador é zero porque não existem três casos elegíveis nem os respectivos exports.

O Studio agora abre as duas montagens e o controle por acesso autenticado, embaralha a ordem e apresenta apenas “Opção 1”, “Opção 2” e “Opção 3” durante a reprodução. O recibo usa uma cópia imutável dos IDs, checksums de A/B e controle, revisão e EDL capturados antes de abrir os vídeos. A API exige `editAChecksum` e `editBChecksum` e recusa a preferência se outro cliente substituir um render durante a reprodução (`visual_comparison_viewed_render_changed`). Mudar a revisão, o projeto ou os renders descarta a sessão; carregamentos atrasados não recriam uma sessão antiga. A comparação usa confirmação humana de cegamento: quem preparou os arquivos pode reconhecê-los, portanto esconder os nomes sozinho não comprova um teste cego independente.

A API recusa controles com o mesmo checksum de A/B, fontes inativas ou com checksum diferente do documento, duração de origem não verificada e trechos fora da fonte. O indicador também invalida uma comparação se qualquer montagem perder o QC técnico ou uma fonte mudar. Os recibos antigos de revisão permanecem legíveis, mas sem os quatro eixos e confirmação de reprodução não aprovam a fase.

## Verificação desta continuação

Passaram 77 testes de backend nos arquivos `test_visual_quality_program.py`, `test_editorial_production.py`, `test_editing_resources.py` e `test_visual_direction_audit.py`, além de dois testes Playwright do indicador e da comparação. TypeScript e Ruff dos serviços novos passaram. Um dos nove testes específicos desta fase usa SQLite real e dois workspaces: uma reserva incerta de US$ 9,95 bloqueia outra de US$ 0,10; um custo medido de US$ 9,90 substitui a reserva e permite exatamente US$ 10. Nenhum provedor é chamado por esse teste.

Uma falha inicial do Playwright foi auditada no trace: o carregamento da página inicial consumiu cerca de 29 segundos do prazo de 30 segundos antes das ações do painel. Os testes passaram ao usar uma página mínima para o componente, com a mesma interface e sem carregar a home demonstrativa inteira. Outra falha transitória ocorreu quando o teste iniciou antes da mudança de critério de revisão obsoleta; a execução final usou os arquivos atualizados. Esses episódios não foram tratados como falhas do renderer.

Conclusão registrada: contratos, indicador, comparação e orçamento funcionam nos cenários testados. A nova rodada não produziu export comercial nem demonstrou avanço estético ou planejamento autônomo. Esses resultados continuam pendentes; não há promoção a `render_verified`.

Higgsfield e Veo permanecem candidatos para tomadas específicas não obtidas do acervo. Uma prova externa só deve começar com ação, enquadramento e continuidade definidos, reserva de custo prévia, licença/proveniência verificadas e comparação visual com o material disponível. A decisão sobre integração de produção depende desse resultado, não de uma falha inferida dos logs antigos.
