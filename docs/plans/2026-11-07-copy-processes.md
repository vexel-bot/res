# Clicko — processos de copy e qualidade do anúncio

Data: 2026-11-07. Estado: especificação operacional; implementação inicial separada. Responsável de coordenação: Copy Chief. Prioridade solicitada: qualidade do anúncio, sem análise de métricas de campanha neste trabalho.

Atualização do coordenador: a fundação manual de dossiê/copy por projeto e documento foi integrada e testada nesta sessão. O estado implementado, limites e referências de edição estão em [copy-implementation](2026-11-07-copy-implementation.md); os critérios observáveis estão em [ad-quality-criteria](2026-11-07-ad-quality-criteria.md). Os módulos automáticos descritos neste plano continuam propostas onde não há indicação explícita de implementação.

## 1. Decisão de produto e limites desta entrega

O sistema deve transformar conhecimento validado do produto em uma mensagem persuasiva, demonstrável e viável de produzir. A foto ou o rosto recebido identifica o apresentador; não substitui descoberta do negócio, pesquisa do público, oferta, provas nem autorização das falas atribuídas a essa pessoa.

O fluxo proposto é:

**Descoberta → pesquisa e classificação de fontes → público e sofisticação → oferta, mecanismo e provas → brief aprovado → ângulos → hooks → copy → roteiro audiovisual → revisão CUB e editorial → aprovação do cliente → narração, cenas e edição → revisão do vídeo → entrega e memória.**

Esta especificação organiza TODOS os processos de copy desse ciclo. Não é uma avaliação de uma campanha existente, não contém anúncios finais e não declara capacidade de conversão. A aprovação editorial indica conformidade com critérios documentados; eficácia comercial continua desconhecida sem observação real futura.

### Situação atual informada pela inspeção do coordenador

| Elemento | Constatação recebida | Implicação |
|---|---|---|
| Direções criativas | `backend/app/routers/studio_department.py`, trecho informado 112–225: outlines derivados de templates com `title`, `objective`, `audience`, `tone`, `evidence` | Uma direção preenchida não equivale a pesquisa, estratégia especializada ou texto gerado por LLM |
| Conhecimento do produto | Falta um dossiê forte e versionado de descoberta, produto e oferta | A primeira entrega deve instituir dossiê e artefatos manuais versionados |
| Edição canônica | Há comandos validados de patch/replace de timeline | O roteiro aprovado precisa virar contrato rastreável para o editor |
| Inspeção visual | Amostragem de seis frames de três fontes | Amostragem ajuda inspeção; não comprova revisão integral de fala, áudio, ritmo e continuidade |
| Voz e rosto | Binding de voz incompleto; runtimes de face/avatar em evolução | Aprovar texto e roteiro separadamente da prontidão dos recursos de produção |
| Novo provedor | API Anthropic mencionada ainda não cadastrada | Nenhuma etapa deste plano depende de ativá-la |

Essas constatações foram compartilhadas pelo coordenador; este documento não as apresenta como nova auditoria independente de código. Todos os estados, contratos e automações descritos a seguir são **proposta**, exceto quando explicitamente identificados acima. A implementação inicial não torna os módulos futuros automaticamente disponíveis.

Não executar chamadas pagas, cadastrar credenciais, produzir lote piloto, iniciar campanha ou comprar mídia como consequência deste plano. A implementação manual e o planejamento estão autorizados; consumo de novos provedores não faz parte desta entrega.

## 2. Hierarquia e despacho do Copy Squad

Preservar a hierarquia de `squads/copy/squad.yaml` e `.codex/team.json`, resolvidos contra `C:/Users/edugu/.codex/agents`. O Copy Chief coordena, define briefing e gates, sintetiza pareceres reais e aprova a progressão; não assume a redação de todos os especialistas.

| Camada original | Responsabilidade no sistema | Membros pertinentes e native_role |
|---|---|---|
| Orquestrador | Roteamento, contexto compartilhado, arbitragem de conflito, gates e histórico | Copy Chief: `copy-chief` |
| Tier 0 — foundation | Pesquisa de produto, clareza, distinção observável, afirmações defensáveis | Ogilvy: `copy--david-ogilvy`; Hopkins: `copy--claude-hopkins` |
| Tier 1 — psychology | Credibilidade, conversa do público, fluidez, sofisticação | Bencivenga: `copy--gary-bencivenga`; Collier: `copy--robert-collier`; Sugarman: `copy--joe-sugarman`; Deutsch: `copy--david-deutsch` |
| Tier 2 — impact | Redação específica, emoção, ponto central e CTA | Halbert: `copy--gary-halbert`; Carlton: `copy--john-carlton`; Makepeace: `copy--clayton-makepeace`; Kennedy: `copy--dan-kennedy` |
| Tier 3 — strategy | RMBC, mecanismo, oferta e extensões de relacionamento | Georgi: `copy--stefan-georgi`; Brunson: `russell-brunson`; Chaperon: `copy--andre-chaperon`; Settle: `ben-settle` |
| Tier 3 — VSL | Hook e narrativa de vídeo | Benson: `copy--jon-benson`; Kern: `frank-kern` |
| Tier 4 — active | Especializações complementares quando necessárias | Brown: `todd-brown`; Caples: `john-caples`; Schwartz: `eugene-schwartz`; Rutz: `jim-rutz` |

Os tiers são a organização original, não uma votação entre personas independentes. Não convocar todos em toda tarefa. Despachar cada especialista para um foco distinto e reunir o contexto de handoff antes da próxima fase. O mapa atual não declara membros sem arquivo; nomes só citados em textos históricos não ganham disponibilidade por essa citação.

Cada execução registra se houve agente real, revisão humana ou apenas checklist. Uma coluna com o nome de um especialista descreve responsabilidade planejada; só vira parecer realizado quando a execução correspondente existir. Não atribuir notas a agentes que não foram executados.

## 3. Unidade de trabalho e acervo de conhecimento

Separar produto, campanha e peça. Um produto possui várias ofertas e públicos; uma campanha escolhe versões; uma peça aplica um ângulo e uma duração. A duração não é o identificador da estratégia.

### 3.1 Dossiê de produto e pesquisa

O dossiê equivale ao conjunto de contexto do squad (`offerbook`, `avatar_research`, `unique_mechanism`, `swipe_vault`), armazenado no projeto do cliente. Não copiar dados de distribuição como se fossem dados do cliente.

| Bloco | Conteúdo mínimo | Quem confirma |
|---|---|---|
| Identidade | Produto/serviço, categoria, marca, responsável e descrição concreta | Cliente |
| Funcionamento | O que faz, passos observáveis, entradas necessárias, entregáveis, limitações e exclusões | Cliente + pesquisa Tier 0 |
| Público | Segmento prioritário, situação de uso, problema, desejo, linguagem, alternativas, objeções | Pesquisa + cliente; inferências rotuladas |
| Consciência e sofisticação | `awareness_level` e `sophistication_level`, justificativa, fontes e incerteza | Deutsch + Copy Chief; validação contextual do cliente |
| Oferta | Inclusões, preço/moeda/parcelamento quando aplicável, garantia real, condições, disponibilidade, destino do CTA | Cliente |
| Mecanismo | Como funciona, por que faria diferença, passos, limites, evidências; nome se existir | Georgi + cliente |
| Provas | Claims sustentados, origem, escopo, limitações, validade, permissão de uso | Bencivenga + titular da informação |
| Marca e apresentação | Tom, palavras preferidas/proibidas, pronúncia, papel do apresentador, exemplos autorizados | Cliente |
| Produção | Canal, duração, proporção, idioma, apresentador, voz, assets existentes, recursos disponíveis | Cliente + produção |
| Restrições | Promessas vedadas, sensibilidade de contexto, condições comerciais obrigatórias, restrições conhecidas de publicação | Cliente + revisão pertinente |

Não inferir profissão, experiência com o produto, resultados pessoais ou credenciais a partir do rosto. Apresentador, cliente real, ator e personagem são papéis diferentes. Depoimento em primeira pessoa exige material real e aprovação das falas; uma simulação não vira caso comprovado.

### 3.2 Fonte e classificação por informação

Cada entrada de pesquisa deve conter `id`, conteúdo, classificação, `source_id`, localização/trecho de apoio, data, autor da coleta, estado de validação e versão. A fonte guarda arquivo/URL/entrevista/demonstração, origem, data e status de consulta.

- `verified_fact`: material consultado sustenta a afirmação dentro de limites registrados.
- `client_statement`: declaração atribuída ao cliente; ainda não demonstrada independentemente.
- `hypothesis`: interpretação estratégica a testar ou validar; não pode entrar como fato no anúncio.
- `unknown`: falta informação. O sistema formula uma pergunta em vez de completar por imaginação.

URL recebida e não aberta permanece `not_consulted`. Referência não lida não pode ganhar resumo, citação nem selo de pesquisa. Fonte contraditória abre pendência. Uma correção preserva o registro anterior e identifica o que substituiu.

Pesquisar primeiro os documentos, URLs, gravações e anexos fornecidos. Pesquisa externa futura depende de escopo e fontes definidos; não existe autoexploração de mercado pronta por este documento. Quando executada, deve registrar consultas, páginas realmente acessadas, datas e limites de acesso. Conteúdo de concorrente informa o contexto; não fornece prova de que o produto do cliente entrega o mesmo resultado.

### 3.3 Mapa de claims e evidências

Cada claim guarda `claim_id`, redação permitida, tipo, `evidence_ids`, escopo, ressalvas, status e responsável. Status propostos: `draft`, `needs_evidence`, `supported`, `restricted`, `rejected`, `expired`. Cada vínculo claim→evidência registra uma decisão de suficiência: o que a fonte sustenta, o que não sustenta, por quê e quem avaliou. A existência de um `evidence_id` não aprova o claim automaticamente.

Um material de prova guarda `evidence_id`, tipo, origem, localização exata, resultado realmente demonstrado, contexto, período, limites, disponibilidade do asset e permissão de uso. Quantidade e especificidade numérica não substituem sustentação. Um vídeo efetivamente gerado pelo Clicko pode demonstrar sua capacidade de produzir aquele arquivo, com registro real de entrada, versão, execução e saída. Não demonstra o resultado comercial, médico, financeiro ou pessoal encenado no vídeo. A simulação de resultado é ilustração, não comprovação desse resultado.

Qualquer afirmação factual relevante, central ou secundária, em fala, legenda, gráfico, comparação ou imagem exige suporte proporcional. Sem suporte, deve ser removida, estreitada para capacidade demonstrável ou devolvida à coleta. Nunca resolver falta de prova inventando estudo, número, resultado, credencial, exclusividade ou depoimento. Ausência de urgência, bônus ou desconto é um dado válido; não é um campo a preencher artificialmente. O cliente confirma suas condições comerciais; seu aceite não converte uma alegação de eficácia em fato verificado. Declarações de resultado conservam `client_statement` até existir sustentação adequada.

## 4. Pipeline com entradas, saídas, responsáveis e gates

Legenda: **H** = cliente/editor/especialista humano; **M** = assistência de modelo futura ou agente executado explicitamente; **A** = validação determinística. Na fundação inicial, registros e decisões são manuais; as colunas M/A especificam evolução e não afirmam automação existente.

| Etapa | Entrada | Saída persistida | Responsável / execução | Gate e retorno |
|---|---|---|---|---|
| 0. Enquadramento | Solicitação e material disponível | Produto, objetivo, público inicial, formato, prazo, escopo de pesquisa e lacunas | Chief + cliente, H | Produto e objetivo identificáveis; caso contrário descoberta continua |
| 1. Discovery | Respostas e material do cliente | Dossiê inicial + lista priorizada de perguntas | Chief elicita; cliente responde, H | Produto/oferta/público confirmados no nível necessário; desconhecidos explícitos |
| 2. Pesquisa de produto | Dossiê, documentos e demonstrações | Ficha funcional, fontes e limites | Ogilvy/Hopkins; H/M, A para referências | Nenhuma capacidade presumida; lacunas críticas voltam ao cliente |
| 3. Público e mercado | Linguagem real, objeções, alternativas e contexto | Avatar, consciência, sofisticação e justificativa | Deutsch, suporte Collier/Ogilvy; H/M | Diagnóstico estratégico precede a redação; incerteza documentada |
| 4. Oferta | Condições reais e ação desejada | Oferta versionada + CTA/destino | Cliente, Chief; Brunson quando houver stack | Preço/garantia/inclusões usados no texto confirmados; urgência só se real |
| 5. Mecanismo | Funcionamento e diferenciação observável | Explicação causal e versão de mecanismo | Georgi; H/M | Obrigatório para VSL; em ad avulso, condição definida pelo claim e workflow específico |
| 6. Proof mining | Assets, casos, documentos e demonstrações | Mapa claim→prova + gaps + redações permitidas | Bencivenga; H/M, A para integridade | Nenhum claim central sem suporte adequado; coleta ou redução da promessa |
| 7. Brief estratégico | Versões aceitas do dossiê | Mini-RMBC ou RMBC completo aprovado | Georgi + Chief; H/M | Contexto pronto e approver identificado; sem aprovação não despachar redação |
| 8. Ângulos | Brief, público, provas, objeção central | Matriz de ângulos e escolha justificada | Chief coordena; especialistas por ângulo | Cada ângulo usa ponto central distinto, base comprovável e produção viável |
| 9. Hooks | Ângulo aprovado | Candidatos, avaliação editorial, escolha e reservas | Benson + Hopkins; H/M | Critérios de atenção/clareza/credibilidade documentados; hook não excede prova |
| 10. Body e CTA | Hook, provas e brief | Copy falada e escrita, variante identificada | Makepeace/Carlton + Kennedy | Um ponto e uma ação; promessa, corpo e destino coerentes |
| 11. Roteiro audiovisual | Copy, voz/apresentador e assets disponíveis | Cenas temporizadas + plano de som/texto/prova | Copy + produção; Benson/Kern quando pertinente | Tudo que a fala exige pode ser mostrado ou explicitamente solicitado |
| 12. Revisão | Texto e roteiro da mesma versão | Matriz CUB, notas, issues e veredicto | Chief + revisores reais, H/M; A auxilia | Reprovação retorna ao dono da causa; não seguir com pendência crítica |
| 13. Aprovação | Preview de texto/roteiro, claims e condições | Aprovação/rejeição humana do pacote exato | Cliente/editor autorizado, H | Aprovação aponta versão e escopo; edição semântica invalida aprovação |
| 14. Handoff de produção | Pacote aprovado | Manifesto para narração, cenas e edição | Chief → responsáveis de produção | Asset/binding indisponível gera bloqueio de produção, não falsa conclusão |
| 15. Verificação de execução | Voz, cenas, timeline e vídeo | Findings por timecode, comparação e revisão | Editor/cliente, H; A auxilia | Fala, legendas, CTA e prova consistentes; assistir integralmente antes de aceitar vídeo |
| 16. Entrega e memória | Pacote aceito e arquivos reais | Versão entregue, story, decisões e aprendizados | Chief + sistema | Artefatos e revisões rastreáveis; sem inventar resultados de campanha |

Descoberta usa as dez perguntas essenciais originais: produto, promessa, preço/garantia, bônus, mecanismo; dor, desejo, tentativas anteriores, sofisticação e linguagem real. O sistema deve aproveitar respostas já fornecidas e perguntar apenas o que falta. Dados opcionais sem aplicação recebem `not_applicable` com razão, nunca dados falsos.

No futuro, o modelo pode extrair informações, apontar conflitos, sugerir perguntas e rascunhos. A validação automática pode verificar schema, referências, versões, contagem de palavras, tempo estimado e campos. Nenhuma dessas operações prova verdade factual, qualidade estratégica ou aprovação do cliente por si só.

## 5. Prontidão e briefing antes de escrever

Adotar um `readiness_profile` por tipo de peça e `policy_version`. O score de completude ≥80% existente no squad é uma convenção operacional interna, não medida científica de conhecimento do produto. A completude não pode compensar ausência de um campo crítico.

Bloqueadores comuns: produto indefinido; público ou objetivo ausente; promessa contraditória com o produto; claim central sem sustentação; CTA sem ação/destino; condições comerciais mencionadas sem confirmação; texto atribuído ao apresentador sem definição do seu papel.

Em anúncio curto, usar o perfil específico do playbook: oferta/público suficientes, prova compatível e mini-brief; mecanismo profundo é recomendado, não obrigatório para todo anúncio. A indisponibilidade de duas modalidades de prova prevista no checklist original vira gap explícito; não fabricar um testemunho para completar o cadastro. O Chief pode propor peça demonstrativa com claims mais estreitos e perfil adaptado, documentando a diferença; não marcar que cumpriu o playbook integral quando não cumpriu.

Em VSL, exigir RMBC de 22 questões, consciência/sofisticação definidas, mecanismo explicado, proof stack disponível e condições reais do close. O limiar interno de mecanismo ≥70 é uma rubrica do squad, não comprovação de exclusividade ou eficácia.

O mini-brief contém: público e contexto; problema/desejo; promessa sustentada; ponto único; ângulo; consciência/sofisticação; canal; duração; destino/CTA; prova disponível; tom; restrições; apresentador/voz; recursos e limites. O RMBC longo amplia isso para as 22 questões da fase 0 de `playbook-vsl.md`.

Todo despacho recebe um snapshot: versões do dossiê, oferta, mecanismo/provas e brief; objetivo; escopo/foco do especialista; artefato a criar; restrições; gate; próximo destinatário. Não passar somente um título e um tom.

## 6. Anúncios de 15, 30 e 60 segundos

Preservar o playbook de ad copy: fase 0 mini-RMBC/Georgi → fase 1 hooks/Benson + defensabilidade/Hopkins → fase 2 body/Makepeace + ponto central/Carlton → fase 3 CTA/Kennedy → CUB/Halbert + Sugarman + Bencivenga. Análise de sofisticação antecede as decisões estratégicas.

O formato curto precisa ser planejado desde o brief. Não produzir VSL e cortar aleatoriamente até caber. Cada adaptação mantém intenção, prova mínima relevante e CTA legível; versões derivadas recebem revisão própria.

| Duração | Organização sugerida, ajustável | Critério de aceitação |
|---|---|---|
| 15 s | Hook/problema imediato → uma demonstração ou benefício sustentado → CTA | Mensagem única compreensível, sem acelerar fala para esconder excesso |
| 30 s | Hook → contexto/objeção → produto e prova → CTA | Espaço real para identificar o produto, sustentar a promessa e entender a ação |
| 60 s | Hook → situação/história breve → mecanismo ou demonstração → prova/objeção → oferta/CTA | Progressão clara; narrativa não consome toda a duração antes da proposta |

Essas distribuições são orientação de roteiro, não tempos universais. Duração final deve ser verificada com leitura e áudio reais, pausas, pronúncia de marca, demonstrações e tempo para ler condições. Estimativa por palavras é pré-checagem; não substitui medição do áudio.

O playbook original propõe dez hooks, cinco tipos com duas variações e três candidatos acima do limiar interno de 80/100. Persistir `rubric_id`, versão, dimensões, notas, avaliador e justificativa: ad-copy e definição Benson usam quatro dimensões de 25 pontos; a fase de hooks da VSL usa três dimensões de 0–100 e média. Resultados de rubricas diferentes não são diretamente comparáveis. Registrar `evaluated_start`, `evaluated_end` e `asset_version`; uma janela extensa da VSL não deve ser aplicada literalmente a anúncios curtos. Arousal Score é avaliação editorial, não probabilidade de parada de scroll ou previsão de retenção. O pack pode conter três versões revisadas para escolha; isso não inicia teste de mídia ou consumo de produção.

Na matriz de ângulos, guardar: `angle_id`, público, percepção atual, ponto central, promessa permitida, objeção, prova, tipo de hook, justificativa e exigências visuais. Um hook diferente com o mesmo argumento é variante do ângulo, não nova estratégia.

### Orgânico, paid e objetivo de awareness

Separar `distribution_mode=organic|paid` de `asset_type=short_ad|vsl|social_content`. Um anúncio orgânico com objetivo de resposta pode reutilizar mini-RMBC, ponto único, prova e CTA, adequando ação e linguagem ao canal. Conteúdo de consciência de marca/editorial não deve ser etiquetado como execução completa do playbook original de resposta direta, que explicitamente o exclui. Criar perfil editorial próprio e conservar a mesma obrigação de veracidade, clareza e revisão.

Não embutir regra de anúncio pago específica de plataforma sem verificar a fonte aplicável quando o canal for selecionado. Neste trabalho, apenas registrar restrições já fornecidas e pendências; não emitir parecer jurídico nem fingir atualização de políticas não consultadas.

## 7. VSL longa como workflow próprio

A VSL tem seções e contratos diferentes dos anúncios curtos. Preservar a ordem do workflow original:

1. **Fase 0 — Pesquisa e mecanismo:** Georgi responde às 22 questões RMBC; Deutsch calibra sofisticação. Gate de contexto e mecanismo antes dos hooks.
2. **Fase 1 — Hooks:** Benson apresenta candidatos e seleção com rubrica explícita. O score interno mínimo não representa evidência de desempenho.
3. **Fase 2 — Problema/agitação:** Carlton constrói sequência e linguagem do público; dores não podem ser inventadas nem atribuídas abusivamente ao espectador.
4. **Fase 3 — Solução e prova:** Georgi explica mecanismo; Bencivenga organiza demonstrações e evidências próximas às afirmações. O workflow pede ao menos três pontos de prova; a relevância e o alcance importam além da contagem.
5. **Fase 4 — Oferta e close:** Brunson estrutura inclusões/bônus reais; Kennedy redige ação, condições e urgência apenas se existir. Não fabricar valores de ancoragem ou inflar bônus para alcançar ratio do template.
6. **Auditoria final:** texto completo, promessa do hook versus entrega, prova, mecanismo, transições, legibilidade e CTA; registrar revisores, versões e decisões reais.

Guardar seção, `section_id`, posição, intenção, copy, claims, provas, cenas associadas, duração prevista/medida e status. Uma correção de mecanismo deve apontar quais seções e cenas afeta. Um resumo de 30 segundos da VSL é novo anúncio derivado, com mini-brief e aprovação próprios.

O roteiro cinematográfico pode enriquecer a narrativa quando o objetivo e os recursos justificarem. Não impor três atos complexos, transformação inventada, narrador com história fictícia tratada como real ou longa agitação a todo vídeo de quinze segundos.

## 8. Contrato de roteiro e handoff audiovisual

Copy falada, texto na tela e imagem têm funções distintas. O roteiro define o que cada uma comunica e não duplica tudo automaticamente. Preservar separação de texto de venda, direção visual e parâmetros técnicos do editor. Registrar `hook_promise`, `payoff_scene_ids` e `payoff_status`: a curiosidade precisa de resolução identificável na peça ou de uma expectativa explícita e verdadeira sobre o destino do CTA.

### 8.1 Campos por cena

| Campo | Função |
|---|---|
| `scene_id`, `section_id`, `copy_segment_ids` | Rastrear a origem da cena |
| `start`, `end`, `duration_estimated`, `duration_measured` | Planejamento e conferência de tempo |
| Intenção | O que o espectador deve compreender ou sentir |
| Copy falada | Texto exato aprovado, com pausas e pronúncia quando necessário |
| Apresentador/voz | Papel, idioma, versão de binding e estado de disponibilidade |
| Visual/ação | O que aparece e por que ajuda a mensagem |
| Prova exibida | `claim_ids`, `evidence_ids` e asset real que sustenta a fala |
| Texto na tela | Headline, legenda, condição/ressalva, CTA e período legível |
| Som | Trilha, ambiente, efeitos e relação com a inteligibilidade |
| Produção | Asset existente/solicitado, gerado/real, dependências, responsável |
| Edição | Corte/transição, enquadramento, continuidade, ênfase e restrições |
| Aceite | Como verificar que a cena cumpriu sua função |

Uma imagem bonita sem relação com a mensagem não satisfaz o gate visual. Uma sequência gerada ilustrativa não pode aparecer como registro real de resultado. Uma afirmação visual também é claim: gráficos, antes/depois e números na tela precisam da mesma sustentação da narração.

### 8.2 Manifesto para produção

O pacote aprovado inclui `dossier_version`, `offer_version`, `brief_version`, `copy_version`, `script_version`, `review_policy_version`, revisão/approval IDs, formato/duração, texto exato de narração, cenas, assets, provas, voz/apresentador, legendas, CTA e restrições. Produção deve usar esse snapshot, sem incorporar rascunhos mais recentes por acidente.

Antes de narrar: conferir texto final, papel do apresentador, idioma/pronúncia, voz selecionada e binding disponível. Antes de gerar cenas: conferir assets necessários, referências, claims visuais e recursos técnicos. Antes de editar: conferir durações reais, integridade dos arquivos, continuidade e correspondência com o roteiro.

Binding de voz incompleto gera `blocked_asset` na tarefa de produção. Rosto/voz substitutos não devem ser escolhidos silenciosamente. O texto aprovado continua válido se o problema for técnico e não houver alteração semântica; a tarefa técnica permanece pendente.

Comandos de timeline precisam apontar cena/segmento e versão de origem; aplicar patch/replace exige validação de intervalos e referências. Registrar três aceites distintos de duração: leitura editorial estimada, áudio final medido e montagem final medida. Fala que ultrapassa a janela retorna à adaptação textual; não acelerar silenciosamente nem sacrificar prova, condições ou legibilidade do CTA. Após a edição, comparar transcrição, textos de tela e CTA com o pacote aprovado; verificar sincronização, inteligibilidade, pronúncia, legendas, continuidade e prova visual. Assistir ao vídeo completo e ouvir o áudio completo. Seis frames são evidência de amostragem, não de aprovação integral.

## 9. CUB, revisão editorial e escalas sem ambiguidade

Os arquivos originais contêm inconsistências: algumas passagens chamam de score a gravidade C/U/B, em que menor é melhor; outras usam uma nota geral, em que maior é melhor. Há ainda uma linha `score <6 = REWRITE` incompatível com a própria escala de gravidade. Implementar literalmente essas linhas produziria decisões contraditórias.

Política proposta para o sistema: armazenar explicitamente `confusing`, `unbelievable`, `boring` como gravidade (menor é melhor) e `quality_score` como avaliação geral (maior é melhor), com `policy_version`. Nunca derivar automaticamente uma escala da outra nem converter nota por simples subtração.

Para execução fiel do CUB do squad, a proposta operacional combina os critérios documentados: cada revisor com C/U/B ≤5 e nota geral ≥8, sem pendência crítica. Nota geral 6–7 pede REVISE; abaixo de 6 pede REWRITE; dimensões acima do limite bloqueiam PASS. A revisão pode exigir REWRITE por problema estrutural de promessa/prova mesmo que uma média pareça aceitável. A VSL possui limites editoriais mais estritos em passagens específicas (≤3); registrá-los no perfil próprio.

Esses números são **rubricas internas propostas**, não verdades universais, certificação de anúncio ou validação do cliente. A qualidade precisa vir acompanhada de problema concreto, evidência e ação; a aprovação comercial humana permanece separada. Na fase manual, uma checklist preenchida não é auditoria multiagente. A definição de Bencivenga pode acionar proof audit já com U=5: esse valor deve abrir análise adicional quando aplicável, mesmo dentro do limite consolidado. Nenhum PASS numérico encerra uma pendência de prova ainda aberta.

### Revisores por workflow

- Ads: Halbert para hook, Sugarman para fluidez e persuasão, Bencivenga para prova; aplicar o painel final específico do playbook. Para cold ad, Carlton e Kennedy podem completar a análise dentro do limite de 3–5 revisores da task.
- VSL: Benson, Bencivenga e Carlton constam no playbook; a task também exige Georgi para mecanismo, além de Sugarman como regra geral. Planejar painel de cinco com esses focos, executado em lotes quando necessário.
- Roteiro narrativo: Kern/Benson podem revisar a progressão visual; isso complementa a revisão de prova e não fabrica um novo painel inexistente.

Revisores recebem o mesmo snapshot e focos distintos. Especialistas podem ter escrito uma seção no workflow original; registrar essa autoria e acrescentar leitura independente quando necessária. O Chief sintetiza divergências e exige justificativa específica, sem alegar consenso se não houve.

Cada finding deve ter `issue_id`, revisor, dimensão, gravidade, trecho/cena/timecode, problema observável, base de evidência/critério, ação, responsável, estado e versão. A justificativa pública resume a avaliação e a correção; não exige exposição de raciocínio privado interno do modelo.

### Outros controles editoriais

Clareza de primeira leitura, linguagem do público, ponto central, coerência hook→produto→prova→CTA, naturalidade oral, correspondência com o destino, duração e disponibilidade de assets são verificações obrigatórias. Arousal ≥80, cinco triggers e FK Grade 6–8,5 são convenções do squad; não devem incentivar exageros nem falas artificiais.

Registrar idioma e método de legibilidade. FK foi formulado para inglês; usar o valor em português apenas como sinal auxiliar identificado, com leitura oral e revisão linguística. Não declarar legibilidade validada em português apenas porque um script numérico retornou um intervalo. Em anúncios muito curtos, contagem de triggers não substitui compreensão e verdade. Se uma convenção não couber ao formato, documentar adaptação do perfil e revisão do Chief; não marcar falsamente o gate original como cumprido.

Nenhuma aprovação editorial depende de CTR, CPA ou faturamento nesta etapa. Não criar metas comerciais artificiais para preencher o template.

## 10. Estados, revisões e invalidação

Estado editorial da peça proposto:

`draft → discovery → research → brief_review → brief_approved → angles → drafting → script_review → copy_review → client_review → approved_for_production → production → final_review → delivered`.

Estados auxiliares: `blocked_input`, `blocked_evidence`, `blocked_asset`, `revise`, `rewrite`, `superseded`, `archived`. O bloqueio deve informar causa, etapa, dono da pendência e próximo passo. Não usar um único booleano `approved` para produto, texto e vídeo.

| Objeto | Estados próprios |
|---|---|
| Dossiê | `draft`, `needs_information`, `validated`, `superseded` |
| Brief | `draft`, `in_review`, `approved`, `stale` |
| Claim | `draft`, `needs_evidence`, `supported`, `restricted`, `rejected`, `expired` |
| Copy/roteiro | `draft`, `in_review`, `revise`, `rewrite`, `approved`, `stale` |
| Revisão | `pending`, `completed`, `superseded`; veredicto independente |
| Aprovação humana | `pending`, `approved`, `rejected`, `revoked`, `stale` |
| Produção | `not_ready`, `ready`, `running`, `blocked_asset`, `failed`, `completed`, `needs_revision` |

Salvar versão não significa aprovar. Aprovar copy não significa aprovar vídeo. Uma aprovação inclui identidade do responsável, data, versão/hash, escopo, comentário e dependências. Persistir snapshots imutáveis para consulta e versões filhas para revisões.

| Mudança | O que deve voltar à revisão |
|---|---|
| Preço/garantia/disponibilidade | Oferta, close, textos/CTA, cenas e áudio que citam condição; prova de produto intacta pode ser preservada |
| Promessa/mecanismo/novo resultado | Claims, provas, brief, ângulos, copy e roteiro dependentes; nova revisão CUB |
| Público/consciência/sofisticação | Estratégia, ângulo, hook, linguagem e objeções; materiais factuais continuam referenciáveis |
| Evidência retirada/expirada | Claims que a usam e todos os segmentos/cenas dependentes; bloquear entrega afetada |
| Ajuste de fala com mudança de sentido | Nova versão de copy, revisão correspondente, aprovação e narração afetada |
| Pontuação/pronúncia sem mudança de sentido | Registro editorial, conferência de áudio e tempo; escopo de reaprovação definido e registrado |
| Troca visual que altera implicação de prova | Revisão de claim visual e edição, mesmo sem mudar a fala |
| Correção técnica de volume/corte sem mudar sentido | Revisão de produção e vídeo; preservar aprovação de texto quando aplicável |
| Nova duração/canal | Nova peça derivada, adaptação, revisão de fit e aprovação própria |

Regenerar apenas o trecho afetado quando o contexto aprovado continua válido. Mais de três REWRITEs consecutivos exige interromper o loop automático, revisar dossiê/sofisticação com Deutsch e refazer brief com Georgi, conforme escalonamento original. Aumentar tentativas não substitui corrigir pesquisa insuficiente.

## 11. Aplicação no produto: telas e responsabilidades

A experiência deve apresentar trabalho concreto, não uma lista de nomes de agentes ou suposta reunião permanente.

1. **Conhecer o produto:** dossiê com material recebido, condições, prova, campos ausentes e fontes; salvar rascunho e validar informações são ações diferentes.
2. **Definir a mensagem:** brief, objetivo, público, formato, ângulos e justificativa; mostrar o que está sustentado e o que falta.
3. **Escrever e roteirizar:** versão do texto, copy falada, tela/legenda e cenas; comparar variantes e versões sem sobrescrever a aprovada.
4. **Revisar:** checklist manual inicial, findings por trecho/cena, decisões do editor; painel CUB apenas quando executado realmente.
5. **Aprovar e produzir:** preview exato do pacote, responsável por aprovação, dependências e disponibilidade de voz/cenas; encaminhar produção somente quando pronta.
6. **Conferir a entrega:** reprodução integral, correções por timecode, rastreio até o texto aprovado e entrega versionada.

O usuário deve entender por que um item está pendente e qual informação resolve a pendência. O sistema não deve exibir termos internos como CUB, RMBC ou native_role no fluxo básico quando isso não ajuda a decisão. Pode apresentar “clareza”, “credibilidade” e “interesse”, com detalhes de método na revisão avançada.

## 12. Implantação em etapas sem dependência de novas APIs

### Fundação agora — escopo de implementação do coordenador

Dossiê manual estruturado, versões de copy/roteiro, checklist de qualidade, decisões e histórico. Contexto persistido no projeto e distinguível dos campos antigos do brief. Uma revisão manual deve aparecer como manual. Direções por template devem continuar identificadas como sugestões derivadas do brief, sem promessa de pesquisa ou autoria especializada automática.

Critérios de aceite desta fundação: informações ausentes permanecem visíveis; versões anteriores são consultáveis; salvar não aprova; aprovação aponta versão; mudança relevante não herda silenciosamente aprovação; checklist usa pendente/aprovado/reprovado/não aplicável com justificativa; nenhum botão finge chamada de modelo que não existe; nenhuma nova chave ou consumo é exigido.

Este plano não declara que todos esses critérios já foram implementados. A entrega de código deve relacionar explicitamente quais foram realizados e quais continuam backlog.

### Próxima etapa — pesquisa assistida e contratos fortes

Modelo para extrair de material fornecido, classificar afirmações, detectar contradições e sugerir perguntas; biblioteca de fontes; mapa claim→evidência; perfis de prontidão e dependências. Verificações determinísticas de integridade. Antes de disponibilizar, definir provedor, orçamento, limites de chamada, registro real das execuções e fallback manual.

### Etapa seguinte — redação e revisão especializada

Orquestração por fases, artefatos estruturados e schema versionado; geração de candidatos limitada ao brief aprovado; peer review real com painel e focuses; correção com issue IDs; aprovação humana do pacote exato. Não liberar paralelismo irrestrito: respeitar dependências e slots, executando revisores em lotes.

### Integração audiovisual

Binding de voz confiável, recursos de face/avatar disponíveis, manifesto de cena/áudio, edição por comandos canônicos e revisão integral. Disponibilidade técnica não elimina os gates de copy; aprovação de copy não inventa disponibilidade técnica.

### Expansões de copy sobre a mesma base

Landing page e sales letter reutilizam dossiê/oferta/provas, com estrutura e revisão próprias. Email SOS preserva o workflow original: diagnóstico de estágio → Chaperon/email 1 → Settle/email 2 → Kern/email 3 → Sugarman/email 4 → Kennedy/email 5 → CUB, com arco, loops e oferta coerentes. Headlines avulsas usam o comando específico e especialistas da dispatch matrix. Adaptações não recebem aprovação em lote por herança automática.

Distribuição e análise de campanhas são handoffs posteriores e separados; não fazem parte da implementação nem da revisão de qualidade solicitada agora.

## 13. Verificação de implementação e memória operacional

Quando cada etapa for implementada, validar cenários que representem risco real: informação crítica vazia bloqueia despacho; hipótese não vira claim; preço antigo não persiste em cena derivada; aprovação de versão anterior não vale para texto alterado; revisão não realizada não aparece como PASS; falha de fonte não vira evidência consultada; rosto/voz indisponíveis bloqueiam produção; vídeo montado com texto divergente retorna para correção.

Checagens de qualidade editorial nesta fase: produto compreensível, um público prioritário, um ponto central, claims sustentados, CTA claro, fala natural, prova visível quando necessária, cenas úteis, condições legíveis, duração real e consistência com destino. Registrar resultado observável e pendências; não substituí-los por um número de qualidade isolado.

Toda fase concluída gera registro real no projeto: o que foi produzido, localização/versão, participantes efetivamente executados, gates realmente verificados, issues, decisão e próximo handoff. Preservar a função das stories e da memória original sem gravar dados de um cliente na distribuição do squad. Um planejamento pode ter uma story de planejamento; não deve gerar stories que aleguem pesquisa externa, auditoria de anúncio ou campanha inexistentes.

## 14. Base consultada e decisões de adaptação

Raiz técnica: `C:/Users/edugu/.codex/agents/squads/copy`. Foram consultados manifesto `squad.yaml`, `config.yaml`, `README.md`, `.codex/team.json`, definição completa `agents/copy-chief.md`, `kb/global/operational-rules.md`, `tasks/offer-discovery.md`, `workflows/playbook-ad-copy.md`, `workflows/playbook-vsl.md`, `tasks/cub-audit.md`, gates de data readiness/pré-dispatch/qualidade e templates de brief e cinema copy.

Adaptações explícitas: separar as duas escalas CUB; guardar policy_version; respeitar exceção de mecanismo para ad curto; preservar dados ausentes/sem aplicação; não inventar urgência, prova ou ancoragem para satisfazer template; reconhecer limites de FK em português; distinguir convenção editorial de evidência empírica; diferenciar planejamento, checklist manual, revisão especializada executada e aprovação humana.

### Registro real desta sessão de planejamento

Story de planejamento: `COPY-202611-PLAN-07`. Artefato: este documento. Não foi gerada copy de produto nem executada pesquisa externa ou chamada de provedor. Apenas este arquivo foi produzido pelo responsável deste subtrabalho; a implementação da fundação é responsabilidade do coordenador.

| Especialista realmente executado | Escopo | Resultado e síntese incorporada |
|---|---|---|
| `copy--david-ogilvy` | Processo de descoberta e pesquisa, Tier 0 | Protocolo fornecido: fatos/declarações/hipóteses/desconhecidos, fontes realmente consultadas, oferta confirmada e bloqueios específicos |
| `copy--stefan-georgi` | Mini-RMBC, VSL, estratégia e contratos | Protocolo fornecido: fase/artefato versionado, ads separados de VSL, mecanismo conforme formato e invalidação dirigida |
| `copy--gary-bencivenga` | Revisão do plano pela integridade da prova | APTO COM RESSALVAS; cinco correções incorporadas: capacidade real versus resultado simulado, claims secundários, aceite comercial versus comprovação, suficiência por vínculo e pendência de prova prevalecendo sobre nota |
| `copy--jon-benson` | Revisão do plano audiovisual | APTO COM RESSALVAS; cinco correções incorporadas: rubrica versionada por perfil, janela avaliada, resolução da promessa do hook, três aceites de duração e verificações audiovisuais observáveis |

Síntese do Copy Chief: as ressalvas concretas foram incorporadas ao desenho. Gate deste planejamento: cobertura dos processos, papéis, entradas/saídas, bloqueios, versões, aprovação e handoff especificados; implementação e validação no produto permanecem trabalho separado. Não houve CUB de anúncio, pontuação real de hooks, validação de desempenho ou consenso de especialistas não executados. As responsabilidades futuras das tabelas não são pareceres realizados.
