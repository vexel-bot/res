# Três estudos dirigidos no renderer atual — revisão e protocolo

04/10/2026. Projeto original: `C:/Users/edugu/Downloads/res`. Esta rodada conserva a direção authored dos estudos históricos; não demonstra direção autônoma nem melhora estética causada pelo renderer. As novas cópias passam pelos documentos, planos, jobs e assets reais do Studio. A rodada operacional está em `output/visual-directed-native14-20261004/execution.json`; somente entradas com `artifact` têm MP4 coletado e checksum conferido.

## Evidência observada e limites

O primeiro MP4 de organização tem 450 frames, 1080×1920, 30 fps, 15 s e AAC. O job `de7cd5f3-7e82-41ca-a79f-d2599c06c623` executou native.14 em 172.406 ms. O SHA-256 do arquivo é `f2eae2907b62bebd648a5142e851de6253f367594b7f68e5a06a224be8687d63`. A direção é idêntica à direção canônica anterior, exceto pela revisão esperada do novo documento. Os materiais mantêm seus checksums.

Nos 15 frames amostrados 0/59/79/109/139/179/219/244/279/309/329/359/389/419/449, as peças Ideia/Plano/Resultado começam dispersas, aproximam-se e terminam alinhadas com um conector. A frase final está visível nos frames 359–449 amostrados. A folha de contato observa estados; não certifica continuidade entre amostras, compreensão ou qualidade do movimento.

O QC técnico passou, conservando o aviso de silêncio: razão 0,8237556. A observação audiovisual do serviço é `partial`, com 30 amostras a 2 fps, leitura humana pendente e precisão de eventos sonoros desconhecida. Não substituímos essas incertezas por notas. A decodificação adicional do script `editor-directed-native14-audit.py` registra todos os 450 frames a 270×480 e energia de áudio em janelas de 20 ms; continua sendo evidência técnica, sem certificar sentido narrativo.

## Mecanismos de falha que precisam de revisão

Organização e comparação conservam as mesmas três palavras e a mesma assertion canônica ampla: conjunto disperso → reorganização → estrutura ordenada e conectada. Isso limita o quanto podemos afirmar sobre diferenciação de mensagem entre estudos. A comparação também usa revelação/oclusão, mas esses operadores só ajudam se o público identificar a relação que mudou.

O rodapé de disclosure usa texto pequeno em um canvas vertical. A amostra em 270 px não basta para aprovar sua leitura. Os longos holds podem sustentar entendimento ou parecer inertes. Os quatro acentos sonoros originais pontuam a peça, mas sua presença não prova sincronização causal com cada ação. A captura de interface precisa mostrar a edição, a aplicação e o resultado real na ordem correta; um corte convincente pode esconder a ação essencial.

## Diagnósticos independentes das duas lentes

**Lente Spielberg — acesso visual.** Observação: a organização já permite localizar as três peças nos estados amostrados; comparação usa o mesmo vocabulário visual. Princípio documentado: a entrevista pública trata cinema como linguagem visual e discute encenação e experiência do público. A tradução para estes gráficos é uma inferência operacional. Decisão: conservar geografia e identidade, concentrar atenção em uma mudança por etapa e usar o hold final para conferir o resultado. Efeito esperado, ainda hipotético: o espectador descreve a transformação sem depender do título. Risco: repetir a promessa por texto e movimento sem demonstrar uma consequência específica. [Entrevista da DGA](https://www.dga.org/craft/dgaq/issues/0604-winter-2006/dga-interview-steven-spielberg).

**Lente Gilligan — causa e consequência.** Observação: a captura de interface tem uma ação real que pode explicar seu resultado; nos gráficos, movimento e conector precisam sustentar a relação anunciada. Princípio documentado: a história oral descreve construção de cenas, transformação e resolução de setups; adaptar isso a uma peça de 15 s é inferência. Decisão: exigir antes/ação/depois identificáveis e perguntar qual informação se perde quando retiramos o movimento ou o trecho de aplicação. Efeito esperado, ainda hipotético: o público liga o resultado à ação que viu. Risco: confundir proximidade espacial com causalidade ou confiar numa frase final para resolver o que os estados não mostram. [História oral da Television Academy](https://interviews.televisionacademy.com/interviews/vince-gilligan).

As lentes concordam em preservar conteúdo, fazer o evento observável e verificar seu resultado. A síntese usa a clareza espacial como gramática dominante e a consequência como critério de diagnóstico. Nenhum nome de cineasta especifica timing, fonte, keyframe ou efeito; as decisões executáveis estão nos planos canônicos existentes. Não há clonagem de voz, estilo pessoal ou atribuição de autoria dos estudos a essas pessoas.

## Manter, mudar e reconstruir

Manter nesta comparação: materiais autorizados, textos, canvas, áudio, duração, contratos, controles simples e direções A/B previamente authored. Alterar esses fatores no meio da requalificação destruiria a comparação entre versões do renderer.

Mudanças candidatas para uma revisão posterior, ainda não aplicadas: tornar a relação específica da comparação distinguível da organização; aumentar o disclosure se a leitura móvel falhar; alinhar um acento ao evento que de fato precisa de pontuação; reduzir um hold somente se a observação completa mostrar perda de progressão. Cada alteração exige novo comando/plano, revisão, digest, job e checksum; uma observação não produz um novo vídeo.

Reconstruir a cena se o conteúdo for trocado sob o mesmo ID, a aplicação real for omitida, a ordem causal estiver invertida ou o título continuar sendo a única evidência da promessa. Trocar cor ou acrescentar blur não corrige esses casos.

## Assertions falsificáveis para a observação

Os intervalos abaixo orientam a revisão; não substituem as assertions persistidas nem criam outro modelo de projeto. Os tempos devem ser conferidos na direção canônica de cada variante.

| Estudo / objeto | Inicial → evento → final | Intervalo a inspecionar | Evidência necessária | Contraprova |
|---|---|---|---|---|
| Organização / Ideia, Plano, Resultado | Dispersos → deslocamento com identidade preservada → alinhados e conectados | Introdução 0–79; percurso a partir de 80 até o último keyframe de cada peça; conector 190–245; hold até 449 | Sequência completa e rastreio dos textos, posições locais/parents e estado final | Texto trocado, peça que desaparece sem volta, inversão da ordem anunciada ou hold que não contém o resultado |
| Comparação / as mesmas três peças | Relação inicial → alteração de disposição e revelação → relação final que o público consegue nomear | Percurso e revelação; oclusão 245–310 nas variantes dirigidas; final 330–449 | Sequência e descrição humana livre antes de revelar a intenção | Público descreve apenas organização, ou identifica outra peça como substituta da original |
| Interface / tarefa e resultado | Estado antes de aplicar → editar/aplicar/conferir → resultado real | Toda a captura; vizinhança dos cortes authored (276 ou 285 conforme variante), seguida do resultado até 449 | Fonte original, crops com checksum, source ranges, ordem dos eventos e reprodução completa | Resultado de outra tarefa, ação ausente no corte, texto que surge sem edição visível ou resultado antecedendo aplicação |
| Todos / título e som | Mensagem apresentada → leitura e pontuação → conclusão sustentada | Entrada, ação essencial, frase final e término do áudio | Fonte final, palavras inteiras, hold, reprodução móvel e escuta | Título oculto/cortado, pontuação deslocada, áudio duplicado ou disclosure ilegível |

O controle simples faz a mudança de estado sem as receitas dirigidas. O seu propósito é permitir descobrir se o percurso animado ajuda; ele pode vencer. Não há aprovação presumida de A ou B.

## Repertório pesquisado e tradução operacional

Heer e Robertson estudaram transições entre gráficos estatísticos e encontraram benefícios em condições específicas, junto a limites de tempo, complexidade e semântica. Para o res, conservar objetos e dividir mudanças em etapas é uma hipótese de composição a verificar; o artigo não prova eficácia publicitária destes vídeos. [Pesquisa primária, 2007](https://idl.cs.washington.edu/files/2007-AnimatedTransitions-InfoVis.pdf).

A orientação de coreografia do Material organiza foco e relações entre elementos em transição. Aqui ela informa etapas e hierarquia; a aplicação a motion graphics promocionais continua sendo inferência, com teste frente ao controle. [Material Design: Choreography](https://m1.material.io/motion/choreography.html).

Não foi preciso baixar novos repositórios nesta rodada. O repertório já incorporado é exercitado no renderer existente. A limpeza de clones e bundles anteriormente recusada permanece pendente; não foi repetida nem contornada.

## Critérios de aceite e revisão humana

Primeiro, conferir job, snapshot/revisão/versionamento, fontes/assets autorizados, checksums, decode, duração, dimensões, áudio e avisos. Depois, criar novas sessões cegas A/B/C pelo endpoint existente somente quando as três variantes do estudo estiverem coletadas. As sessões históricas permanecem intactas.

O revisor assiste aos três vídeos completos, em tamanho de celular e com som; descreve o que mudou, identifica possíveis falhas e escolhe A/B/C antes de revelar a condição. O critério dirigido do handoff exige quatro eixos humanos ≥4/5 e preferência frente ao controle nos três estudos. Campos não respondidos continuam `not_assessed`; QC, hashes, lentes conceituais e folhas de contato não preenchem esses campos.

O contrato em execução também exige a nota de acabamento na comparação, além de clareza, ritmo, continuidade e adequação da revisão individual. A galeria pede as cinco notas; nenhuma é derivada das outras.

Se os estudos dirigidos forem aceitos, avaliar a generalização com três novos briefs e todas as intervenções explicitadas. Esta rodada não conta como esses três novos briefs e não demonstra autonomia. Outras proporções e a ligação desta rodada à prévia central da UI ainda precisam de observação real.
