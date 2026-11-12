# Higgins — fontes de criadores e workflows para ensinar edição

Coleta pública em 12/11/2026, encerrada aproximadamente às 11:54 BRT. Responsabilidade: fontes de criadores, procedência e cobertura; síntese final e QA pertencem ao coordenador. Lidas a definição original `agents/higgins.md` e a tarefa `tasks/investigate-osint.md` do squad. O diagnóstico Sackett → Booth → Creswell recebido definiu revisão de escopo documental, sem estimativa de eficácia no Clicko.

**Resultado:** seis fontes primárias úteis, incluindo três tutoriais em vídeo com descrição/capítulos do próprio publicador ou transcrição oficial. Nenhum vídeo foi assistido ou escutado nesta coleta. Dois vídeos adicionais ficam como candidatos porque só foi possível consultar mirrors. Nenhuma instalação, execução de workflow, geração, chamada paga ou troca de editor ocorreu.

## O que a evidência permite dizer

Os documentos públicos oferecem procedimentos concretos: decompor referências, registrar estilo em arquivo, planejar cenas antes de montar, comparar versões e guardar correções. Isso demonstra a existência de instruções, não que um agente as cumpre ou que produz qualidade equivalente às referências. Os repositórios e tutoriais não são independentes de seus autores; incentivos promocionais e seleção de resultados permanecem. Nenhuma alegação de eficácia recebe `Confirmed`. Neste relatório, conteúdo diretamente acessado é distinguido da confiança na eficácia: fonte primária pode ter conteúdo verificado e resultado não verificado.

## Matriz de fontes incluídas

### H1 — Matheus Gobbi: Editar vídeo com o Claude

- **Origem:** [página do próprio criador](https://matheusgobbi.com/edit), sem data editorial explícita; consultada em 12/11/2026. A autoria aparece na própria página. Não atribuí data a partir de repostagens.
- **Acesso real:** texto completo da página via HTTP público, status 200. `web.open` falhou; `Invoke-WebRequest` conseguiu. SHA-256 do HTML recebido às 11:53 BRT: `BA31D7DBF74ADCD643281C7B5513C625C94E541686D1BD1972A21C1B06D8BCEF`. O HTML integral não foi arquivado; o hash e a síntese abaixo preservam uma trilha limitada.
- **Método observado:** quatro prompts: organizar brutos/referências/exportações; preparar ferramentas; estudar 3–5 referências e criar `GUIA_DE_ESTILO.md`; apresentar storyboard com fala, imagem e duração antes da montagem. Correções devem atualizar o guia. A pilha citada é HyperFrames, FFmpeg, Whisper e yt-dlp.
- **Limite:** instruções públicas, sem logs de falhas, avaliações cegas ou prova de generalização. Arquivo de estilo é contexto persistido, não treino dos parâmetros.
- **Adaptação Craft — inferência:** manter os Crafts e traduzir o guia para as operações nativas; cada regra ganha intervalo-fonte, intenção, condição de uso, contraexemplo e teste. Guardar correções aprovadas como lições versionadas.
- **Teste refutável:** comparar guia genérico versus regras com demonstração/contraexemplo em briefs reservados; cegamento e mesmas mídias/modelo/orçamento. Se a rubrica não melhorar, o guia sozinho não sustentou a transferência. **Eficácia: Weak, fonte única.**

### H2 — edenfunf: ReelMimic / video-clone

- **Origem:** [repositório do autor](https://github.com/edenfunf/reelmimic), [SKILL completo](https://github.com/edenfunf/reelmimic/blob/main/.claude/skills/video-clone/SKILL.md), [entrada AGENTS](https://github.com/edenfunf/reelmimic/blob/main/AGENTS.md). `main`, consultado em 12/11/2026; commit não fixado nesta coleta.
- **Acesso real:** README, AGENTS e 127 linhas do SKILL textual inspecionadas; scripts citados não foram executados. O texto original é majoritariamente chinês tradicional.
- **Método observado:** análise de planos/ritmo/câmera/cor/texto; cada plano proposto relaciona referência, técnica e especificação de câmera. Pede style frames, comparação de sequências, revisão por contexto novo e evidência antes/depois dos reparos. O Motion Score declara converter medições da referência em dados usados pelo motor.
- **Limite:** contrato prescritivo e alegações do autor; não auditamos implementações nem resultados. Notas, limites percentuais e pontuações internas não são normas empiricamente validadas.
- **Adaptação Craft — inferência:** relacionar técnica → trajetória de comandos Craft → trecho renderizado; um revisor recebe referência, resultado e checklist ancorado, sem o argumento persuasivo do autor. Não copiar motor, limiares ou número de agentes.
- **Teste refutável:** omitir o mapeamento referência/operação em um braço; comparar fidelidade funcional em tarefas novas. Para o revisor, usar defeitos plantados e medir falsos positivos/negativos antes de confiar no parecer. **Eficácia: Weak.**

### H3 — TechNomadCode: remotion-video v1.2.0

- **Origem:** [release do autor, 05/10/2026](https://github.com/TechNomadCode/AI-Product-Development-Toolkit/releases/tag/v1.2.0), [SKILL versionado](https://github.com/TechNomadCode/AI-Product-Development-Toolkit/blob/v1.2.0/agent-skills/remotion-video/SKILL.md), [brief](https://github.com/TechNomadCode/AI-Product-Development-Toolkit/blob/v1.2.0/agent-skills/remotion-video/brief.md). Tag aponta para `1d3e2ca` na página de release.
- **Acesso real:** release, 54 linhas do SKILL e 57 do brief; vídeo da release não reproduzido.
- **Método observado:** ideia curta → storyboard → montagem; configuração comum para tempos de imagem/som; revisão de cada transição; leitura por alguém sem as notas; checagem técnica de frames/sync/áudio. Brief separa público, takeaway, materiais, textos, motion e entrega.
- **Limite:** receita de um autor, sem ablação. A alternativa de autoavaliação não equivale a avaliação independente; recomendações de loudness não comprovam escuta ou bom som.
- **Adaptação Craft — inferência:** aprovar poucos frames de direção de arte e uma transição crítica antes da montagem inteira; compartilhar tempos de eventos de imagem/som; revisar todas as emendas. Não instalar Remotion nem impor defaults desse brief a todos os anúncios.
- **Teste refutável:** comparar revisão por janelas livres versus cobertura integral e eventos críticos; medir detecção e reparo de defeitos conhecidos, separada da preferência estética. **Eficácia: Weak.**

### H4 — Joey Korenman / School of Motion: Intro to the Graph Editor

- **Origem:** [tutorial e transcrição oficiais](https://schoolofmotion.com/blog/intro-to-the-graph-editor-in-after-effects); [vídeo oficial ligado pela escola](https://www.youtube.com/watch?v=AG19fyRcOkA). Data não confirmada; fundamento anterior admitido como exceção ao recorte temporal.
- **Acesso real:** transcrição disponibilizada pela escola, com marcos de 00:19 a 36:52; sem reprodução do vídeo, sem áudio, sem baixar arquivos que pedem e-mail.
- **Método observado:** comparar movimento linear, ease e curvas modificadas; ligar inclinação da curva à velocidade; demonstrar desaceleração, bounce e coordenação de propriedades; criticar resultado e revisar offsets.
- **Limite:** ensino humano de craft, não experimento com agentes. A frase promocional de melhoria não é resultado medido. Presença de Bézier no projeto não indica boa escolha de curva, mas também impede diagnosticar movimento como inteiramente linear.
- **Adaptação Craft — inferência:** par positivo/negativo com os mesmos estados e durações, curvas distintas e justificativa perceptiva; salvar comandos nativos, amostras temporais e identificação da variante. O agente deve escolher pela intenção, não aplicar ease a tudo.
- **Teste refutável:** dar trajetórias novas e pedir seleção/execução coerente; comparar com preset único em avaliação cega e medir retenção dos estados legíveis. **Transferência: Weak.**

### H5 — Aidan Stanik: How I Edit Videos with Claude Code

- **Origem:** [vídeo no canal do autor](https://www.youtube.com/watch?v=BNPlUj-CxB0), publicado em 26/02/2026 segundo metadados indexados da página primária.
- **Acesso real:** descrição e capítulos da própria página retornados pela busca; abertura direta só expôs boilerplate. Não há transcrição inspecionada, playback ou escuta.
- **Conteúdo declarado pelo criador:** organização de assets em 7:39; prompting em 12:33; primeiro render/revisão em 15:55; correção de transições em 18:05; iteração motion em 19:02; salvar skills em 23:52. A descrição afirma que o vídeo foi editado com o workflow.
- **Limite:** capítulos e autodeclaração localizam material a estudar; não verificam a execução nem a qualidade. Economia de horas não foi medida aqui.
- **Adaptação Craft — hipótese:** capturar uma demonstração completa equivalente no editor nativo: materiais organizados → comandos → render → crítica localizada → reparo → regra reutilizável.
- **Teste refutável:** um agente sem a demonstração completa recebe apenas regra textual; outro recebe a trajetória com correção. Medir sucesso em um novo conjunto de assets, com mesmas condições. **Eficácia: Weak; cobertura baixa.**

### H6 — Мика Билялова: Claude Code Edits Videos for You in 10 Min

- **Origem:** [vídeo no canal da autora](https://www.youtube.com/watch?v=extVP9lokaI), 07/06/2026 segundo metadados indexados da página primária.
- **Acesso real:** descrição e capítulos retornados pela busca da própria página; abertura direta bloqueada por throttling. Sem transcrição, playback ou escuta. Idioma russo; descrição indexada em inglês.
- **Conteúdo declarado:** skills em 0:48; resultado em 4:25; MP4 em 4:53; alteração de logo/estilo em 6:05; edição de vídeo pronto em 11:12. Integrações de imagem/voz a partir de 7:27 são criação de mídia e não contam como evidência direta de capacidade editorial.
- **Limite:** marketing de facilidade e duração; não confirma tempo total, falhas ou generalização. Materiais e alterações não foram observados em reprodução.
- **Adaptação Craft — hipótese:** tarefa pequena de substituir logo/estilo preservando duração, copy e material; distinguir sucesso de editar propriedades de bom julgamento de linguagem.
- **Teste refutável:** após demonstrar uma substituição, medir transferência para novo asset com proporções/fontes diferentes, checando contrato e fidelidade visual separadamente. **Eficácia: Weak; cobertura baixa.**

## Vídeos candidatos, não incluídos como fontes verificadas

- [Mitrovic Alek — Full Beginner Mini Course](https://www.youtube.com/watch?v=rRTTeJqeWWY), data alegada 30/10/2026. Só descrição/capítulos em mirror Zolotube; origem direta sofreu throttling. Pistas: 9:31 arquivo de estilo; 11:29 gosto de marca; 14:23 análise de vídeos; 19:02 revisão. Verificar no original antes de promover alegações.
- [MoSidd — Full Remotion Tutorial](https://www.youtube.com/watch?v=f393grXJn9E), data alegada 11/09/2026. Só descrição em NatokHD e trecho de transcrição em SozAI; original sofreu throttling. Parece conter especificação por frames, mas não foi usada como evidência factual do processo.

## Procedimento proposto para ensinar no Craft — inferência de pesquisa

1. Selecionar uma habilidade pequena, por exemplo preservar identidade do objeto durante uma transformação ou manter texto legível no recuo de câmera. A referência precisa mostrar a habilidade; o contraexemplo precisa isolá-la.
2. Anotar estado inicial, evento, estado final, duração, objeto de atenção, limites de layout e som. Separar gosto de marca, regra técnica e hipótese de efeito sobre o espectador.
3. Gravar a execução nativa inteira: revisão do documento, materiais, consultas de repertório relevantes, argumentos de comandos aceitos/recusados, estados intermediários, prévia e correção. Não esconder erros: o exemplo deve ensinar diagnóstico e reparo.
4. Fazer o agente reproduzir em tarefa curta. Avaliar movimento em sequência, não apenas frames de repouso. Checar fonte realmente resolvida e recursos existentes antes de atribuir tudo a gosto.
5. Calibrar o avaliador com casos aprovados, rejeitados e defeitos anotados; medir se concorda com humanos e se reconhece incerteza. Um revisor em contexto novo continua sendo um modelo, sujeito a erro.
6. Registrar lição apenas após evidência do reparo, com antes/depois e limite de uso. Testar em novo briefing sem copiar o storyboard original. Contexto/recuperação continua distinto de treino de pesos.

Este procedimento é proposta testável, não pipeline implementado ou ganho demonstrado. Não decorre das fontes que exista um editor mágico, um número ideal de agentes ou que mais gasto produza melhor arte. O caso ÓRBITA tem ferramentas e keyframes Bézier existentes; ausência de aprendizagem não pode ser inferida da ausência de uma função específica, nem todo problema estético é defeito de ferramenta.

## Trilha de coleta e limites

Ferramentas: busca web/open público e leitura HTTP pública. Consultas principais: `site:matheusgobbi.com/edit`; `ReelMimic GitHub motion design agent`; `TechNomadCode AI Product Development Toolkit motion`; `Claude Code Remotion tutorial 0:00 skills video`; `site:schoolofmotion.com/blog Graph Editor tutorial`; buscas por títulos exatos. Foram abertos originais, raw GitHub e links de vídeos; mirrors serviram apenas a descoberta dos candidatos explicitados.

Preservação: URLs, versão/tag quando disponível, cobertura e digest do HTML de Matheus; nenhum arquivo externo completo ou vídeo foi arquivado, logo esta coleta não satisfaz preservação forense integral. Sem análise de geolocalização: irrelevante ao problema. Autores e projetos formam fontes separadas, mas alegações de resultados dentro de cada fonte permanecem de origem única. Não houve triangulação independente de eficácia, benchmark executado, teste com espectadores ou avaliação de áudio.

Handoff: enviar os seis registros e as hipóteses ao coordenador/Cochrane; Ioannidis deve auditar indireção e força das alegações; Kahneman deve revisar seleção de demos, viés de ferramenta e confusão entre preferência e capacidade.
