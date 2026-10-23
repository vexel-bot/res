# Clicko — Auditoria funcional e audiovisual

Data: 23/10/2026. Ambiente: Windows, checkout `res`, perfil local DEV isolado.
Branch auditada: `codex/klic-atualizacao-20260823`.
Base Git: `5cab414dd942c721f8e6fdf65dcd82b4ade28722`, mais alterações locais autorizadas das etapas anteriores.

## 1. Resumo executivo

A Clicko tem uma base **realmente operacional de composição e edição audiovisual 2D**: cria documentos editáveis, mantém camadas e versões, recebe planos determinísticos pela conversa KLIC, importa mídia e exporta PNG/MP4 com Pillow/FFmpeg. Foram produzidos novos arquivos no serviço em execução, com sessão DEV emitida pelo servidor, sem fixture de autenticação, sem provedor simulado e sem inferência paga.

Isso **não equivale a geração cinematográfica por IA, motion avançado ou homologação de produção**. O resultado automático atual é um template de três cartões, com texto genérico, deslocamentos, fades e pouco desenvolvimento temporal. O principal limitador artístico é o planejamento determinístico e o vocabulário reduzido de composição/animação; não é a capacidade de escrever um MP4. Instalar um LLM, isoladamente, não acrescentará ferramentas inexistentes ao renderizador.

Os três motores Craft têm fontes verificadas, mas não têm binários nativos nem módulos WASM utilizáveis neste ambiente. Os agentes especialistas estão em `local_tools`, sem inferência. A KLIC mantém sua configuração Gemini existente; configuração não comprova chamada bem-sucedida, acesso ao modelo ou gratuidade.

Resultado técnico: TypeScript/build aprovados; 245 testes do comando npm e 11 testes Node complementares aprovados. A suíte Python dos testes do backend **não passou: 888 aprovados, 277 falhas, 112 pulados**, sem erros de coleta reportados no XML. Ruff global tem 323 ocorrências. `npm audit` reporta uma vulnerabilidade alta. Não houve deploy, instalação de modelo, migração destrutiva, chamada paga ou alteração de chave/modelo KLIC.

**Limite de homologação:** o controle do navegador está desabilitado nas configurações do Work. Não foi possível validar agora botões, seletores, responsividade e playback nas telas reais, nem produzir capturas atuais da UI. Testes HTTP e imagens extraídas dos exports não substituem essa etapa. A auditoria técnica e audiovisual disponível foi realizada; a homologação visual integral permanece bloqueada.

Legenda de evidência usada no relatório:

- **R** — execução real no serviço DEV ou leitura/decodificação de arquivo real.
- **T** — teste automatizado; pode usar mocks, fixtures ou processos substitutos. Não prova acesso a provedor externo.
- **C** — inspeção do código/contrato; não implica execução do recurso.
- **H** — hipótese que precisa de medição ou conferência adicional.
- **B** — bloqueado ou indisponível neste ambiente.
- **NT** — não testado nesta rodada; não significa aprovado.

## 2. Estado atual da Clicko

Express atua como BFF, React/TypeScript/Vite como frontend e FastAPI como serviço de projetos, mídia, agentes e jobs. O procedimento existente `npm run dev:local` mantém a aplicação em `127.0.0.1:3018` e o backend em `127.0.0.1:8018`, sem expor o perfil à rede pública. O comando de status confirmou `ready=true` e ponte de identidade válida. **R**

O perfil `.codex-runtime/clicko-dev` contém governança, conversas, banco SQLite, uploads e exports privados. Provisiona identidade, workspace e cliente DEV reservados, sem login comercial. A sessão opaca tem cookie HttpOnly/SameSite Strict e expiração de oito horas; não foi usado cookie inventado, bypass por cabeçalho ou conta comercial. Controles de autorização e escopo continuam na ponte Express/FastAPI. **R/T/C**

O supervisor foi parado e reiniciado pelo controle configurado, sem reset de dados. O script de persistência exigiu mudança de PID e reencontrou os documentos, o histórico KLIC, as mídias originais e os exports com os mesmos hashes. **R**

As alterações anteriores de 20–23/10 foram preservadas. Os relatórios históricos são referências de evolução, não provas substitutas da rodada atual:

- `docs/audits/IMAGE_VIDEO_TECHNICAL_AUDIT_2026-10-20.md`;
- `CLICKO_RELATORIO_TECNICO_ATUALIZADO_2026-10-21.md`;
- `docs/audits/STAGE2_COMPLETION_REVIEW_2026-10-22.md`;
- `CLICKO_ETAPA3_HOMOLOGACAO_STUDIOS_2026-10-22.md`;
- `CLICKO_MODO_DESENVOLVEDOR_2026-10-23.md`.

## 3. Estado dos Studios

| Tela/fluxo | Estado de execução atual | O que falta homologar |
|---|---|---|
| Imagem — Gerar Imagem | UI e contratos existem; runtime informa geração IA não configurada. **C/R/B** | Inferência, qualidade, fidelidade e UX real |
| Imagem — Editar Imagem | Composição local por camadas e PNG aprovados por API. Editor avançado depende de PhotoCraft. **R/C/B** | Controles, seleção, alinhamento e responsividade no navegador |
| Vídeo — Criar Vídeo | Motion 2D local e montagem de mídia própria funcionam; cenas IA indisponíveis. **R/B** | Qualidade criativa e percurso visual completo |
| Vídeo — Editar Vídeo | Timeline, cortes, ordem, título, overlay, ganho e fades exportados de fato. **R** | Manipulação visual da timeline/inspetor e paridade do monitor |
| Motion Design | Documento, camadas, planos KLIC, revisão e MP4 locais funcionam. **R** | Motion avançado; editor EffectCraft indisponível |
| Publicidade — Criar Anúncio | Código reutiliza montagem de materiais próprios; geração completa/avatar bloqueados. **C** | Fluxo próprio de anúncio não foi executado de ponta a ponta |
| Publicidade — Criativos | Reutiliza Image Studio; geração depende de provedor. **C/B** | Inferência e resultado publicitário real |
| Biblioteca | Upload, consulta e download autenticados dos assets foram exercitados. **R** | Organização, filtros e cards atuais na UI |
| KLIC | Encaminhamento local, contexto, tarefas e conversa persistente aprovados. **R** | Conversação Gemini real, microfone, TTS e interação visual atual |
| Composição/editorial avançado | Há contratos, componentes e rotas; não é uma segunda prova de motor disponível. **C/B** | Runtimes, contratos pendentes e qualificação própria |

As rotas estão organizadas em `/studios/image/*`, `/studios/video/*`, `/studios/advertising/*` e `/studios/tools/*`. Opções futuras são explicitamente desabilitadas; não foram convertidas em botões que fingem processamento. Criar um criativo não publica campanha de anúncios. O código não permite concluir que existe um gerenciador de campanhas homologado só porque há uma aba Publicidade. **C**

Carregamento de página HTML, build ou resposta 200 não foram contabilizados como teste de formulário, seletor, navegação ou salvamento via navegador. Estados vazios, mensagens de erro e breakpoints têm implementação inspecionada, mas a posição real dos painéis, sobreposições, rolagem e toque continuam **NT/B**. Capturas Motion/Imagem do relatório DEV anterior são históricas, não capturas desta auditoria.

## 4. Funcionalidades operacionais

Comprovação **R** nesta rodada:

- Sessão DEV legítima, escopo de workspace/cliente e ponte de serviços prontos.
- Pedido de motion de 15 s pela conversa KLIC, criação de três cenas e nove camadas editáveis e aplicação explícita do plano revisável.
- Edição contextual com esclarecimentos quando faltam alvo ou valor, sem alteração do documento durante o planejamento.
- Persistência de revisões, sete versões no teste C inicial e preservação binária do export anterior.
- Importação de MP4, WAV e PNG próprios; cortes e reorganização no conteúdo exportado, não apenas no JSON.
- Título, imagem sobreposta, ganho de áudio e fades de entrada/saída em MP4 real.
- Composição PNG com forma, gradiente, sombra, texto e imagem importada com crop/ajustes.
- Idempotência da solicitação de render, download privado e preservação de checksums dos originais.
- Recuperação depois de reinício do servidor sem apagar projetos.

Os testes de autorização, isolamento, quotas, regressões de agentes e rotas têm cobertura **T** na suíte. São evidências complementares: doubles de rede e fixtures nesses testes não foram chamados de render ou inferência reais.

## 5. Funcionalidades parcialmente implementadas

O monitor local Canvas apresenta camadas de composição. A mídia temporal importada e sua mixagem dependem da prévia/exportação canônica FFmpeg; o próprio código informa essa diferença. Portanto não é um monitor audiovisual completo em tempo real. **C**

O comando de texto tem regras para cor, fonte, alvo/cena, duração, fade, deslocamento e dinamismo 2D. Não interpreta qualquer solicitação criativa livre. Pedidos vagos pedem esclarecimento, em vez de inventar alterações. **R/C**

Revelação por palavras existe; animação tipográfica por letras, curvas de velocidade desenhadas, transições compostas e direção de câmera não estão qualificadas no caminho local. Gradiente, sombra e transformações não fornecem perspectiva 3D. **R/C**

Há contratos e adaptadores para provedores de IA, histórico e referências. Existência de contrato, material de referência ou opção “preservar produto/logo” não comprova fidelidade de geração nem disponibilidade de pesos. **C/B**

## 6. Funcionalidades indisponíveis

- PhotoCraft, FilmCraft e EffectCraft em execução nativa e no navegador: faltam builds. **R/B**
- Geração/edição generativa de imagem e vídeo no perfil atual: endpoints de capacidade informam não configurado/indisponível. **R/B**
- Perfis experimentais de text-to-video: preflight retornou `TimeoutExpired`, `usableNow=false`, readiness desconhecida. Timeout não foi interpretado como prova de pesos presentes ou ausentes. **R/B**
- Inferência local dos especialistas: Ollama/llama-server não estavam disponíveis no PATH e nenhum modelo foi carregado ou instalado. **R/B**
- Inferência Gemini KLIC e voz remota: chamadas externas do perfil bloqueadas; credenciais existentes não foram testadas contra o provedor. **B/NT**
- Máscaras arbitrárias, 3D real, câmeras, gráficos de dados animados e sincronização criativa automática com áudio no compilador local: não implementados como recursos gerais. Entradas não suportadas não devem ser anunciadas como prontas. **C**
- Homologação atual pelo navegador: indisponível por configuração da ferramenta. **B**

## 7. Arquitetura multiagente

Fluxo efetivamente exercitado: conversa KLIC → ação `mode.local-production` → contexto do documento/seleção → tarefa do orquestrador → plano de comandos validado → aplicação explícita com revisão esperada → nova versão → job local → asset/export.

| Papel | Responsabilidade atual | Execução comprovada |
|---|---|---|
| KLIC | Entrada conversacional principal, histórico, encaminhamento e contexto | Canal de produção local real; conversa Gemini não exercitada |
| Audiovisual | Planejar cenas e comandos, alterar composição e controlar render | Regras determinísticas locais, sem inferência |
| Visual | Preparar planos de elementos, composição/edição e materiais compartilháveis | Responsabilidade em classe própria; delegação de planos no código/testes; composição PNG real |

Os especialistas são independentes por responsabilidade e configuração de papel, **não três modelos de linguagem em execução**. O agente audiovisual pode delegar a preparação de elementos ao visual; este devolve comandos/planos de formas, não necessariamente uma imagem gerada por IA. Assets reais têm ID, origem e checksum e podem ser reutilizados sem duplicar serviços. **C/T/R**

Validação inclui schema, limites de comandos/propriedades, autorização, workspace/cliente, revisão, locks, seleção e referências de mídia. Tarefas/eventos e recibos são persistidos; replay de aplicação já comprometida é idempotente. Planejamento não altera o documento. Conteúdo vindo de modelo não recebe autoridade para executar código arbitrário. **C/T/R**

O envelope financeiro, políticas externas e quotas permanecem ativos. No DEV, orçamento externo é zero e outbound Node/TTS/Python está bloqueado. A regra comercial existente de imagens conta toda solicitação aceita, inclusive falha/cancelamento; vídeo contabiliza apenas cenas geradas por IA, não exportações/prévias do editor. Testes de contrato cobrem essas regras; esta rodada não gastou quota comercial real. **C/T/R**

## 8. Modelos e integrações de IA

| Integração | Configuração observada | O que foi realmente executado |
|---|---|---|
| KLIC principal | `developer-api`, modelo configurado `gemini-3.8-flash`, `configured=true` | Leitura sanitizada da configuração; sem inferência externa |
| Especialista audiovisual | `local_tools`, revisão de configuração 0 | Regras locais |
| Especialista visual | `local_tools`, revisão de configuração 0 | Composição local e regras/contratos |
| Ollama opcional | Transporte com JSON schema e verificação de pesos locais já instalados | Nenhuma inferência; runtime/modelo não instalado |
| IA Image/Video | Stages `configured=false`, operações vazias, sem fallback automático | Consulta de capacidade, não geração |

O identificador Gemini acima é **o valor lido da aplicação**, não afirmação de disponibilidade comercial ou validação do catálogo do fornecedor. Modelo e chaves não foram trocados. `freeTierVerified=false`: ter chave e configuração não permite assumir custo zero.

O caminho Ollama existente exige metadados locais, schema de saída e limites de contexto/tokens. Não baixa pesos automaticamente nem transforma uma resposta JSON em qualidade artística garantida. A [documentação oficial de structured outputs](https://docs.ollama.com/capabilities/structured-outputs) descreve controle do formato; a qualidade do planejamento ainda precisaria de benchmark local e validação dos comandos.

Hardware inspecionado: aproximadamente 7,71 GiB de RAM e Intel UHD Graphics; o valor de 1 GiB informado pelo Windows não comprova VRAM dedicada. Durante a auditoria houve pouca RAM livre. É inadequado prometer geração pesada de imagem/vídeo ou um LLM grande com fluidez nesse equipamento sem medição. Alternativas gratuitas exigem verificação de licença, pesos, quantização, consumo, latência e qualidade; nenhuma foi instalada aqui.

## 9. Resultados dos testes de vídeo

Os testes usaram HTTP real no perfil DEV e FFmpeg real, não automação do navegador. Entradas B são fixtures audiovisuais **autorais e declaradamente sintéticas**: vídeo vermelho/azul, tom 440 Hz e cartão PNG. São provas de edição, não filmagem comercial nem saída de IA.

### A — Criação do zero

Pedido: vídeo motion de 15 s sobre inovação e inteligência artificial, com três cenas, tipografia, elementos gráficos e transições. O canal KLIC retornou um plano local; aplicá-lo criou nove camadas, três cenas de 5 s e composição 1280×720/24 fps. Export real `motion-a.mp4`, revisão 2, 845.829 bytes. **R**

Automático: estrutura das cenas, posições, títulos, fade/deslocamento e render. Regras fixas: geometria proporcional, cartão escuro, barra coral, fonte system e títulos “Da ideia à ação”/“Crie o próximo passo”. Não houve pesquisa de conteúdo, storyboard semântico, geração de imagens, música ou narração. A aplicação do plano foi uma etapa explícita; não um pipeline autônomo de direção criativa.

### B — Edição de material existente

Documento inicialmente de 6 s, retimado para 4 s; dois cortes de 2 s do arquivo próprio, com trecho azul antes do vermelho, invertendo a ordem original. Título editável, PNG sobreposto, áudio a −6 dB e fades de 0,5 s. Export real `video-b.mp4`, 304.284 bytes. **R**

A conferência de pixels fora do título/overlay mostrou azul em 0,8 s e vermelho em 2,8 s. O áudio decodificado apresentou RMS de 0,04653 no corpo, 0,00177 no início e 0,00257 no final, coerente com os fades. São fades por clip, não transições avançadas entre cenas. Não foi avaliado sincronismo labial ou ritmo musical com esse tom sintético.

### C — Edição posterior por comando

| Pedido | Resultado observado |
|---|---|
| Alterar título da segunda cena sem novo texto | Esclarecimento, zero comandos e nenhuma mutação |
| Novo título explícito “Inteligência em movimento” | Apenas o título da cena 2 alterado |
| Transição mais suave | Fades de opacidade; não um novo motor de transições |
| Aumentar duração sem quantidade, com seleção | Esclarecimento, sem adivinhar duração |
| Duração explícita de 4 s | Retiming apenas do título selecionado, de 5 para 4 s; isto **não é um aumento** |
| Cor dos cartões sem valor | Esclarecimento |
| Cartões tangerina | Somente os três cartões, preservando títulos e barras |
| Composição mais dinâmica sem alvo claro | Esclarecimento |
| Primeira cena mais dinâmica | Scale/rotação 2D nas três camadas dessa cena |
| Texto palavra por palavra | Revelação no título selecionado da cena 2 |

Após esses dez pedidos, revisão 8 e sete versões, export `motion-c.mp4` de 2.423.115 bytes. As camadas fora do escopo comparadas pelo teste permaneceram iguais. O export A permaneceu com o mesmo hash. **R**

O caso complementar C2 **passou**: “Aumente a duração da primeira animação para 5 segundos”, com o primeiro título selecionado, passou de 96 para 120 frames (4→5 s). As outras camadas permaneceram iguais; documento na revisão 9, oito versões e novo export `motion-c2.mp4` de 2.561.771 bytes. Os dois exports anteriores A/C continuaram com seus hashes originais. Não se considera o pedido anterior de 4 s como comprovação de aumento. **R**

### D — Conformidade técnica

| Arquivo | Duração | Vídeo/áudio | Quadro | Integridade |
|---|---|---|---|---|
| `motion-a.mp4` | 15 s | H.264/AAC | 1280×720, 24 fps | Decodificação integral aprovada |
| `motion-c.mp4` | 15 s | H.264/AAC | 1280×720, 24 fps | Decodificação integral aprovada |
| `motion-c2.mp4` | 15 s | H.264/AAC | 1280×720, 24 fps | Decodificação integral aprovada |
| `video-b.mp4` | 4 s | H.264/AAC | 1280×720, 24 fps | Decodificação integral aprovada |

Duração dos streams de áudio/vídeo coincide nos quatro arquivos medidos. A/C/C2 incluem trilha silenciosa, não áudio criado criativamente. A presença de AAC não é evidência de narração ou trilha sonora. **R**

Tempos observados de job+download: A 174,896 s; C 212,447 s; C2 169,049 s; B 2,443 s. A/C ocorreram com a suíte Python concorrendo por recursos. C2 ocorreu depois, mas não integra uma série repetida/controlada. Não são benchmark isolado nem SLA de produção. O custo de motion depende das camadas e filtros, não apenas da duração. **R/H**

Hashes SHA-256 para rastreio, sem publicar mídia de QA no Git:

```text
motion-a.mp4  74175ebb4871c824f29be67681ebd46eb821c8604ae31283e337fdcd06caee8c
motion-c.mp4  593c6c42317dbcc67535d0995b27277a8ed96ab50606eb7a38db34db1f96eb31
motion-c2.mp4 cfff519ed09015694a91aa7ce310809f69402c7648461ddc018aa7a692e07149
video-b.mp4   3f4fa55492cf829ffce626086b0d0806286e7b7f3aafbf5152fd49ac45739c1f
image-i.png   f36613cdb2d47118a107c0c494a095ed3786ca9cc813834f000f296d25491b03
```

## 10. Resultados dos testes de Motion Design

| Recurso | Situação precisa no caminho local | Evidência |
|---|---|---|
| Tipografia cinética | Fade/movimento do bloco e revelação de palavras; não sistema tipográfico avançado | R/C |
| Letras/palavras | Palavras implementadas; letras independentes não implementadas como recurso geral | R/C |
| Cartões/formas | Retângulo/ellipse e cartões editáveis, com propriedades limitadas | R/C |
| Gradientes/sombras | Gradiente simples e sombra rasterizada; sem iluminação 3D | R/C |
| Easing | Linear, ease-out e ease-in-out definidos em código; sem editor geral de Bézier | C/T |
| Keyframes | x/y, escala, rotação e opacidade; limites de quantidade | R/C/T |
| Animações simultâneas | Múltiplas camadas e propriedades compostas | R |
| Câmera/perspectiva | Não há câmera 3D no compilador 2D | C |
| Profundidade | Ordem de camadas, sombra e escala; não profundidade espacial real | R/C |
| Transições complexas | Fades locais funcionam; wipe/morph/transições compostas não qualificadas | R/C/B |
| Gráficos animados | Formas podem ser animadas, mas não há gerador geral de gráficos de dados comprovado | C/NT |
| Máscaras | Não há máscara arbitrária suportada na timeline canônica | C |
| Elementos 3D | Não implementados no caminho local, nem provados por EffectCraft | C/B |
| Multicamadas | Nove camadas no motion testado; limites não equivalem a capacidade sustentada | R |
| Sincronização criativa com áudio | Mix/fades funcionam; beat/sílabas/animação automática não comprovados | R/C/NT |

O contrato local limita uma página, 24 camadas e dimensão até 1920; o contrato da timeline admite até 32 itens/camadas, 16 tracks, 600 s e 60 fps. São **limites de admissão de caminhos diferentes**, não promessa de desempenho nessas configurações. O teste atual foi 720p/24 fps, não uma homologação de 1080p/60 fps/32 camadas.

Há uma infraestrutura de renderização reaproveitável, mas falta um vocabulário de motion com semântica temporal: unidades por palavra/letra, stagger com intenção, curvas autorais, composição de transições, pacing e templates realmente distintos. EffectCraft é candidato de integração, não prova de que esses recursos já estejam acessíveis hoje.

## 11. Resultados dos testes de imagem

O teste I criou um documento visual local 1280×720 e compôs gradiente/sombra, texto editável e PNG importado com crop, brilho, contraste e saturação. O export `image-i.png` foi aberto/verificado por Pillow e inspecionado visualmente. O texto ficou legível e as camadas visíveis; isso não constitui criação generativa. O checksum da fonte foi preservado. **R**

Composição e edição destrutiva do bitmap são operações distintas: os ajustes do documento não substituem o arquivo original. Não houve teste real de segmentação, inpainting, remoção de fundo, reconstrução de produto ou preservação semântica de logo. Essas funções exigiriam ferramentas/modelos qualificados além do compositor atual. **C/B/NT**

Referências, proporções e pedidos de resolução existem nos fluxos IA, mas não foram convertidos em resultado fictício. A capacidade do backend retornou `configured=false` e `operations=[]`. A chave da KLIC não foi reutilizada como autorização implícita para geração de imagens. **R**

Para o agente visual auxiliar a produção: reutilizar biblioteca, asset IDs, checksums, composição e PNG atuais; acrescentar contrato de briefing/entrega por cena, dimensões/área segura, transparência e direitos; só integrar um gerador após licença, admissão de custo/hardware e teste real de fidelidade. Não duplicar armazenamento ou criar outro serviço de imagens sem necessidade.

## 12. Análise da qualidade audiovisual

Inspeção **visual de quadros reais extraídos** dos MP4s, mais JSON/código e medições. Não houve reprodução audiovisual humana contínua dentro do navegador, nem avaliação de um diretor de arte independente. Não se atribuem notas artísticas definitivas com base em automação.

### Matriz objetiva e subjetiva

| Critério | Natureza | Achado nos arquivos reais | Conclusão permitida |
|---|---|---|---|
| Container/codec/duração/decodificação | Objetiva | H.264/AAC e durações corretas | Export tecnicamente válido |
| Cortes, ordem e fades de áudio | Objetiva | Pixels azul→vermelho e RMS verificados | A edição entrou no arquivo |
| Mudanças de texto/cor/versão | Objetiva | Dados, hashes e quadros diferentes | Edição não ficou só no plano |
| Movimento no meio da primeira cena A | Objetiva, amostrada | Diferença média absoluta entre 1,5 s e 2,5 s = 0 | Há ao menos esse intervalo visualmente estático |
| Legibilidade/hierarquia | Julgamento visual amostrado | Títulos contrastantes, poucas informações, cartão legível | Base clara, mas pouca riqueza de hierarquia |
| Direção criativa/originalidade | Subjetiva + causa em código | Mesma geometria em três cenas; frases genéricas | Template demonstrativo, não produção autoral profissional |
| Ritmo/continuidade | Julgamento temporal limitado + estrutura | Três blocos iguais de 5 s; fades; sem música/locução | Pacing pouco desenvolvido; falta conferência contínua humana |
| Profundidade/acabamento | Visual + código | Sombra/gradiente e rotação plana | 2D simples, não câmera ou cena 3D |
| Fluidez/percepção de artefatos | Necessita playback e revisão | Arquivos decodificam e quadros têm texto íntegro | Não comprova ausência de judder/artefato em todos os frames |

### Deficiências e responsabilidade técnica

| Problema observado ou limite | Responsável/causa | Solução recomendada | Dependência/complexidade/prioridade |
|---|---|---|---|
| Três cartões quase iguais | `local_agents.py`: layout e frases fixos | Templates distintos e briefing de direção por cena, com validação humana | Compositor existente; média; P1 |
| Longos trechos sem transformação | Keyframes concentram entrada/saída | Motion contínuo intencional, pacing e antecipação/overshoot controlados | Curvas e presets; média; P1 |
| Texto apenas surge em bloco/palavra | Revelação por máscara temporal de palavras | Layout tipográfico e animação por glifo, sem perder edição | Medição de fontes e paridade Canvas/Pillow; alta; P1 |
| Fades escurecem antes da próxima cena | Sem composição de transições entre clips | Transições limitadas e testadas, com handles e continuidade | Timeline/compiler/preview; alta; P1 |
| Sem trilha, locução ou direção sonora no A | Planejador não cria/seleciona áudio | Briefing sonoro e assets autorizados; depois alinhamento temporal | Áudio real/licenças; média/alta; P1 |
| Dinamismo significa scale/rotação 2D | Vocabulário atual do agente | Comandos expressivos e planos temporais, sem renomear 2D como 3D | Ferramentas/benchmark; alta; P1 |
| Prévia não engloba toda mídia temporal | Monitor de camadas separado do compilador | Paridade verificável de montagem, áudio e export | Monitor+FFmpeg/Craft; alta; P1 |
| Render motion caro nos ensaios | Rasterização e filtros por camada; CPU concorrente | Benchmark isolado, instrumentação e cache de material imutável | Medição antes de otimizar; média; P1 |

Potenciais diferenças de tipografia por fonte instalada e de sombra próxima à borda entre Canvas/Pillow/FFmpeg são **H**, não defeitos visuais definitivamente comprovados nesta rodada. Precisam de golden frames e conferência cruzada. Sem vídeo de referência autorizado validado para esta rodada, não se inventou comparação com uma produção externa.

## 13. Estado dos motores Craft

| Motor | Fonte pinada | Binário nativo | JS/WASM navegador | Papel previsto |
|---|---|---|---|---|
| PhotoCraft 0.7.0 | 1.569 arquivos íntegros | Ausente | Ausente | Edição/composição de imagem nativa |
| FilmCraft 0.6.0 | 1.236 arquivos íntegros | Ausente | Ausente | Edição temporal e mídia no modelo nativo |
| EffectCraft 0.8.0 | 1.016 arquivos íntegros | Ausente | Ausente | Composições/efeitos e motion nativos |

`scripts/craft/provenance.py` passou, incluindo craft-libs, fontes e FilmCraft compatível com EffectCraft. O preflight retornou ausência de Docker e daemon Linux, Rust requerido 1.95.0 e wasm-bindgen 0.2.129. Código-fonte íntegro não é motor executável nem qualificação artística. **R**

Ativação concreta: disponibilizar builder Linux/WSL2/Docker com recursos adequados; compilar adapters independentes e WASM pelos scripts existentes; validar hashes, proveniência, licenças e formatos nativos; configurar executáveis ou imagem local; executar comandos, importação, preview, round-trip, export e paridade navegador/nativo com mídias reais. Só depois declarar cada comando suportado. Não substituir silenciosamente por FFmpeg quando o pedido é de Craft.

EffectCraft mantém uma revisão upstream própria de FilmCraft. Unificar dependências sem verificar essa compatibilidade pode quebrar o motor. A disponibilidade futura de EffectCraft também não prova suporte geral a máscaras, câmera ou 3D em todos os comandos da Clicko: requer auditoria específica do adapter e da UI.

## 14. Infraestrutura e backend

| Área | Diagnóstico |
|---|---|
| Express/FastAPI | Bridge autenticada e escopo funcionando no DEV. Servidor de projeto/mídia preserva autorização. **R/T** |
| SQLite/arquivos | Documentos, revisões, tarefas e assets duráveis; recuperação pós-reinício aprovada. Não é teste de recuperação de desastre. **R** |
| FFmpeg/FFprobe | Runtime privado n9.0.2, encoder libopenh264, filtros necessários disponíveis, export/decode reais. **R** |
| Pillow/NumPy | PNG, texto/formas e conferência de pixels/áudio locais. **R** |
| Canvas | Monitor local 2D no frontend; paridade de tela não conferida nesta rodada. **C/NT** |
| Fila local | Executor de duas threads, oito slots e registro durável de jobs. Não é broker distribuído nem prova de retomada automática de job interrompido. **C** |
| Workers avançados | Diversos manifests/checkpoints/fontes/artefatos de qualificação ausentes, refletidos na suíte vermelha. **R/T/B** |
| Erros | Schema, revisão e escopo são checados. Um enum inválido enviado pelo harness recebeu 422 corretamente. **R** |
| Logs | Evidências privadas e erros preservados; nenhum banco/log/token incluído no conjunto de publicação. |

O compilador local usa FFmpeg para cortes, velocidade, overlays, títulos rasterizados, fades, mix e keyframes. Filtros por pixel e PNGs de camadas podem custar CPU/memória; os ensaios não isolam qual parcela explica os tempos elevados. O caminho existente deve ser instrumentado antes de reconstruir a arquitetura. **C/H**

O FFmpeg possui filtros como xfade/acrossfade, mas [existirem na ferramenta](https://ffmpeg.org/ffmpeg-filters.html) não significa que estejam integrados ao contrato e à UI atuais. Da mesma forma, uma futura fila distribuída exige ambiente apropriado; a [documentação Celery](https://docs.celeryq.dev/en/stable/faq.html#windows) não oferece suporte oficial ao Windows. Não foi instalado broker ou Celery nesta etapa.

## 15. Problemas identificados

| ID | Problema | Prioridade/impacto | Causa/evidência |
|---|---|---|---|
| P-01 | Vulnerabilidade alta transitiva em body-parser | P0 antes de expor produção; disponibilidade | `npm audit`: GHSA-27r3-jxmh-p828, versão afetada <1.20.9 |
| P-02 | 277 falhas e 112 pulados Python | P0 para homologação completa | Artefatos, contratos, runtimes e qualificação incompletos; não só um problema |
| P-03 | Motores Craft indisponíveis | P1; bloqueia editores nativos | Binários/WASM/builder ausentes |
| P-04 | Motion automático visualmente básico | P1; bloqueia padrão artístico desejado | Template e ferramentas limitados |
| P-05 | Monitor parcial de mídia temporal | P1; dificulta edição confiável | Canvas de camadas não é playback integral da montagem |
| P-06 | Especialistas sem inferência; geração IA bloqueada | P1 para planejamento; P2 para geração pesada | Runtimes/configuração/hardware/qualificação |
| P-07 | QA visual atual bloqueado | P1; impede concluir homologação de tela | Navegador desabilitado no Work |
| P-08 | Ruff global vermelho e árvore npm não limpa | P2; manutenção/reprodutibilidade | 323 achados e três pacotes extraneous |
| P-09 | Custo de render sem benchmark isolado | P1; experiência e capacidade | Tempos altos sob concorrência; causa relativa ainda não medida |

O [advisory body-parser](https://github.com/advisories/GHSA-27r3-jxmh-p828) descreve negação de serviço por bytes adicionais após corpo comprimido. Não foi explorado contra o servidor. A correção pontual de dependência é recomendada com regressões antes de exposição; não foi executado `npm audit fix --force`, nem uma atualização ampla fora das correções que impedem os testes autorizados.

As quatro falhas Python que exigem diagnóstico individual não foram escondidas sob “falta modelo”:

1. `test_raw_contract_repair_resolves_duplicate_blur_and_camera_identifies_primary_hero`: papel visual `support` versus `accent` esperado.
2. `test_sequence_with_path_preserves_authored_spatial_network`: `editing_component_sequence_path_requires_media`.
3. `test_worker_rejects_old_or_unbound_plan_even_if_new_plan_approved`: export/review retorna 422 em vez de 202 esperado.
4. `test_export_bookkeeping_does_not_invalidate_same_creative_review`: export PNG retorna 422 em vez de 201 esperado.

Todas já aparecem na baseline comparável. Isso não as torna aceitáveis nem permite atualizar expectativas para “ficar verde”: revisar contrato, fixture e implementação sem remover as proteções de revisão/media.

## 16. Correções realizadas

Nesta auditoria não foi necessário alterar comportamento do produto para concluir as provas locais. Não houve redesign, novo modelo, novo motor ou simulação de recurso. Correções históricas de contexto HMR, tarefas antigas e cliente DEV pertencem às etapas anteriores preservadas no Git, não são entregas novas desta rodada.

Foram adicionados três instrumentos reprodutíveis:

- `scripts/audits/studios-functional.ts`: sessão real, contexto KLIC, edição, render, hashes e verificação pós-reinício.
- `scripts/audits/audiovisual-evidence.py`: entradas próprias, decode, metadata, frames, PNG e medidas objetivas de áudio/cortes.
- `scripts/audits/review-git.mjs`: revisão de escopo, manifest de arquivos e busca de padrões/valores de credenciais sem imprimi-los; não faz stage/push automaticamente.

Corrigido também o comparador existente `scripts/video/triage_stage1.py`: normaliza o prefixo conhecido `backend.tests` entre rootdirs e **não chama teste ausente de resolvido**. Três checks de regressão conferem equivalência de IDs, preservação de namespace de terceiros e resultado da comparação atual. O JUnit original não foi modificado.

A primeira execução do harness B usou enum de direitos inválido e foi corrigida para o contrato existente. Um timeout de transporte em outra tentativa foi preservado; o harness recebeu rota no diagnóstico, prazo maior e checkpoints. Não se atribuiu a causa do timeout ao backend sem evidência. Esses ajustes são do teste, não correções de uma API que deveria aceitar dados inválidos. Os retries não apagaram projetos ou evidências anteriores.

A revisão de publicação inclui também arquivos já staged e exige correspondência entre seu conteúdo e o arquivo examinado. Ajustados apenas espaços finais/linhas vazias em dois relatórios históricos para passar `git diff --check`, sem mudar seus resultados.

## 17. Resultados dos testes automatizados

| Verificação executada | Resultado | Classe/limite |
|---|---|---|
| `npm test` | 243 Node + 2 isolamento de arquivos Vite = **245 aprovados**, zero falhas/skips | T; inclui mocks e fixtures |
| Craft state complementar | **7 aprovados** | T; não render Craft real |
| Controle/reset local complementar | **4 aprovados** | T; segurança e ciclo de vida |
| TypeScript `npm run lint` | Aprovado | Tipagem; não lint visual |
| `npm run build` | Aprovado, frontend e bundles Node | Não comprova provedores/runtimes |
| Python `pytest backend/tests` | **888 aprovados, 277 falhas, 112 pulados**, 1.277 resultados JUnit, 22 warnings | T/R mistos; não suíte completa verde |
| Ruff `backend/app backend/tests scripts` | **323 ocorrências**: 319 testes, 4 scripts, zero em backend/app | Reprovado globalmente |
| Ruff backend/app + scripts novos de mídia + triagem | Aprovado | Escopo restrito explícito |
| `python -m pip check` | Aprovado | Compatibilidade de dependências; não auditoria CVE Python |
| `npm audit --json` | **1 alta**, zero críticas | Reprovado em segurança de dependências |
| `npm ls --all` | Árvore informa 3 extraneous | Não equivale a instalação limpa reproduzível |
| Proveniência Craft | Aprovada | Fontes, não runtime |
| Preflight Craft | Bloqueado, exit 2 | Sem Docker Linux/builds |
| Harness audiovisual DEV | A/B/C/C2/I aprovados com backend/render reais | R; não UI automatizada |
| Persistência após reinício | Aprovada, mudança de PID e hashes preservados | R; não teste de crash no meio de render |
| Auditoria de mídia | Quatro MP4 decodificados e PNG verificado | R; frames dos quatro inspecionados |
| QA atual do navegador | Bloqueado | B; não substituído por HTTP |
| Inferência externa/local e voz real | Não executadas | B/NT; custo externo zero |

Os testes Node de auth/DEV/finanças/quotas e os testes Python de agentes, isolamento, render e persistência foram incluídos conforme sua coleta. Nem todo teste que passa exercita infraestrutura real. Os scripts live e os arquivos gerados fornecem a evidência real separada.

Triagem das 277 falhas (classificação diagnóstica, não dispensa): 244 por arquivo/manifest/runtime ausente; 2 por helper/provider antigo; 8 por contrato/endpoint/motor retirado; 3 Craft; 7 por fonte/wheels de worker; 1 divergência de lock de integridade; 8 por evidência de qualificação/read model; 4 de diagnóstico individual acima. Não foram contornadas verificações de integridade para obter aprovação.

Comparação com baseline anterior: 860 aprovados/292 falhas/113 pulados em 1.265 resultados. A normalização dos IDs não encontrou novas falhas entre os casos comparáveis. **Não se afirma que 15 falhas foram corrigidas**: a baseline coletava cinco métodos de empacotamento Linux upstream, somando 15 falhas/subcasos, ausentes da coleta atual restrita ao backend. Não foram excluídos seletivamente testes do backend para reduzir números.

Ruff: E402=2, E501=74, E702=2, E731=5, F401=225, F841=1, I001=14. Os quatro achados de scripts preexistentes estão em `scripts/agents/acceptance.py` e `scripts/video/acceptance.py`. Não se realizou limpeza massiva fora do escopo. Pacotes extraneous: `@emnapi/runtime`, `@img/sharp-wasm32`, `tslib`; não foram apagados por conveniência. Auditoria CVE Python completa não foi executada.

Evidências privadas preservadas em `.codex-runtime/audit-2026-10-23*`: JUnit/log Python, resultados Node, Ruff, audit/árvore npm, build/tipos, preflight/proveniência, `live.json`, `media-analysis.json`, MP4/PNG e contact sheets. Logs brutos podem conter dados de fixtures e não são material de publicação. As imagens dos exports são provas de conteúdo; **não são capturas das telas**.

Reprodução, mantendo o ambiente DEV e as entradas do ensaio:

```powershell
npm run dev:local
.venv\Scripts\python.exe scripts/audits/audiovisual-evidence.py fixtures
node --import tsx scripts/audits/studios-functional.ts
.venv\Scripts\python.exe scripts/audits/audiovisual-evidence.py analyse
# Parar/iniciar o mesmo perfil sem reset; depois:
node --import tsx scripts/audits/studios-functional.ts --verify
npm test
node --import tsx --test tests/unit/craftState.test.ts
node --test scripts/dev-local-control.test.mjs scripts/dev-reset.test.mjs
npm run lint
npm run build
.venv\Scripts\python.exe -m pytest backend/tests -q
.venv\Scripts\python.exe -m ruff check backend/app backend/tests scripts
.venv\Scripts\python.exe -m pip check
npm audit
```

O harness tem checkpoint de IDs em pasta privada fixa para retomar este ensaio; não é um teste que recria a prova do zero ao executar novamente. Para um novo ensaio, arquivar **somente a pasta de evidências validada e explicitamente escolhida**, preservando os documentos e dados DEV. Não usar reset de banco ou pasta ampla como etapa implícita.

## 18. Pendências consolidadas

| ID/prioridade | Impacto e causa | Solução/dependências | Complexidade | Critério de conclusão |
|---|---|---|---|---|
| P-01 / P0 | DoS de dependência antes de produção | Patch direcionado do body-parser/lock; testes de corpos comprimidos e limites | Baixa/média | Advisory eliminado no lock, regressões e build aprovados |
| P-02 / P0 | Homologação completa impossível com 277 falhas | Restaurar artefatos verificáveis; reconciliar contratos; diagnosticar quatro casos, sem afrouxar gates | Alta | Suíte completa reproduzível, falhas resolvidas e skips justificados por perfil |
| P-03 / P1 | Edição nativa não utilizável | Builder Linux, native/WASM e testes reais de cada adapter | Alta | Comandos+round-trip+preview/export+paridade e licenças aprovados |
| P-04 / P1 | Qualidade profissional não alcançada | Motion presets/curvas/tipografia/transições e direção por cena | Alta | Biblioteca de exemplos reais revisada por humanos, editável e sem regressão |
| P-05 / P1 | Decisões de edição sem monitor integral | Paridade monitor/timeline/export e áudio | Alta | Mesmo quadro/tempo/áudio em preview/export, conferência de UI |
| P-06 / P1–P2 | Planejamento rígido e geração bloqueada | Benchmark de pequeno modelo local, depois geradores licenciados qualificados; manter KLIC | Alta | Inferência real, planos válidos, latência/custo/hardware medidos |
| P-07 / P1 | Botões/fluxos atuais não homologados | Habilitar controle do navegador e executar checklist por tela e viewport | Média | Capturas, criação/edição/export real, estados vazios/erro e toque verificados |
| P-08 / P2 | Manutenção/instalação pouco limpa | Correções de lint em lote separado e validação de instalação pelo lock | Média | Ruff no escopo acordado verde, instalação limpa reproduzível |
| P-09 / P1 | Render longo sem capacidade conhecida | Medições isoladas por preset/resolução/camada, telemetria e limites | Média/alta | Tempos p50/p95 e memória medidos; fila e cancelamento exercitados |
| P-10 / P1 | Ritmo sonoro e sincronização só parciais | Assets autorizados, envelopes/markers e alinhamento temporal com edição preservada | Alta | Áudio real e transições avaliados em playback humano e métricas |

Para publicidade, além dessas dependências: teste próprio de criativo/anúncio com identidade e materiais autorizados, histórico/organização e distinção explícita entre exportar criativo e publicar campanha. Não anunciar um gerenciador de campanhas sem implementar e homologar esse fluxo.

## 19. Recomendações de melhoria

Reaproveitar a base canônica de documentos, assets, contexto KLIC, agentes, revisões, recibos, camada local, compiler FFmpeg, infraestrutura de custos e componentes dos Studios. Não criar outro banco, compositor ou fila de IA em paralelo apenas para melhorar uma demonstração.

**Viável sem gasto externo de API (R$ 0):** direção de arte humana, novos presets 2D controlados, easing e pacing, biblioteca de assets próprios, validação de texto/área segura, melhores testes de quadros e áudio, paridade de preview, benchmark de render, correção de contratos/dependências e estudo de modelos locais pequenos. Isso consome trabalho, energia e hardware; R$ 0 de serviço não significa custo total nulo.

**Depende de recursos disponíveis/investimento:** máquina Linux/WSL adequada para builds e qualificação, RAM/GPU para geração local pesada, armazenamento/backup e fila de produção, mídia licenciada, revisão criativa especializada e eventual acesso pago a geração/voz com teto financeiro autorizado. Camada gratuita de provedor é uma possibilidade a verificar, nunca uma promessa de uso ilimitado ou gratuito da chave existente.

Antes de comparar modelos, definir corpus de briefs autorizados, exemplos desejados, critérios de erro/escopo, fidelidade, latência e custo. O agente deve planejar com o catálogo de ferramentas realmente disponível. Não instalar automaticamente um modelo maior nem substituir a KLIC.

## 20. Roadmap das próximas implementações

| Fase | Entrega futura proposta | Reutilização/dependências | Gate de conclusão |
|---|---|---|---|
| A — Qualidade de Motion | Presets expressivos, tipografia cinética, curvas, transições e composição por cena | Camadas/keyframes/renderer atuais; paridade tipográfica | Vídeos reais com variação, edição preservada e revisão artística humana |
| B — Inteligência audiovisual | Brief/storyboard, seleção de templates e comandos mais ricos; benchmark local de planejamento | Papéis e orquestrador existentes, schema/escopo/custos | Inferência real mensurada, sem operações inventadas ou alterações fora do alvo |
| C — Geração de materiais | Entregas visual→audiovisual por cena, referências/direitos e geradores qualificados | Biblioteca e checksums atuais; modelo/hardware quando disponível | Materiais reais, fidelidade e custo aprovados; original preservado |
| D — Produção automatizada | Roteiro→assets→edição→áudio→validação→export com checkpoints e revisão | Jobs/versões/recibos, monitor integral e instrumentos de QA | Reexecução idempotente, cancelamento/retomada e revisão humana da peça |
| E — Produção | Segurança, runtime Craft, dependências, suíte completa, capacidade, backup e observabilidade | Linux/workers/recursos dimensionados | Gates de segurança/qualificação e carga aprovados, antes de deploy |

Segurança e triagem P0 de E são **pré-requisitos transversais**, não tarefas a adiar até terminar A–D. A ordem artística pode começar com A usando só ferramentas locais, sem esperar um gerador pago. Não foi iniciada automaticamente nenhuma dessas grandes evoluções nesta auditoria.

### Próximas cinco implementações recomendadas

1. **Baseline reproduzível e segura:** patch da dependência, triagem contratual/artefatos e separação clara de gates local/nativo/modelo, sem esconder falhas da suíte completa.
2. **Pacote Motion 2D expressivo:** presets de cenas e tipografia, easing/ritmo/transições com critérios visuais humanos e golden frames. Ataca diretamente a qualidade atual.
3. **Monitor audiovisual e QA unificados:** cuts, overlays, texto e áudio com paridade export/preview; benchmarks isolados e revisão de playback.
4. **Planejador audiovisual local qualificado:** modelo pequeno compatível com o hardware, corpus de briefs e ferramentas reais; manter KLIC e agente visual independentes.
5. **Materiais compartilhados e qualificação nativa:** briefing visual por cena, PNGs/assets editáveis e build/validação Craft; geração pesada somente quando hardware/licença/custo estiverem aprovados.

### Fechamento e publicação

O relatório descreve o checkout auditado antes de sua consolidação em commits, incluindo as limitações e falhas acima. A publicação deve incluir código/documentação autorizados das etapas anteriores e os instrumentos desta auditoria, **não** `.env`, bancos, logs, exports, capturas privadas ou o pacote de referência `círculo-pontilhado-interativo`.

Remoto configurado e preservado: `https://github.com/vexel-bot/res.git`. Branch de trabalho preservada: `codex/klic-atualizacao-20260823`. O resultado efetivo do push e os hashes local/remoto são informados na entrega da conversa e ficam verificáveis no histórico da branch; este arquivo não tenta conter o hash do próprio commit. Nenhuma conclusão deste relatório depende de merge na principal ou deploy.
