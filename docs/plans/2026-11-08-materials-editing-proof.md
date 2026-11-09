# Materiais do anúncio e comprovação de composição — 08/11/2026

Continuação implementada: ver [segmentação temporal e geração local automática](2026-11-08-automatic-material-effects.md). Este documento registra a etapa anterior de composição com materiais preparados.

## Entrega executada

A Clicko passou a preparar recortes por contorno, compor máscaras estáticas e em vídeo, animar uma janela da fonte e revelar camadas progressivamente no renderizador canônico de CPU. Há uma área de materiais por produto/serviço e um seletor explicável de receitas. Nenhuma credencial Anthropic foi cadastrada e nenhuma geração/modelo pago foi chamado nesta execução.

O teste de aplicação executou upload → conjunto de materiais → vínculo de versão → prévia da receita → inserção em timeline vazia → job local → MP4 persistido → download. Foram exportados 12 estudos de 6 segundos e uma galeria de 72 segundos, 640 × 640, 24 fps, H.264/AAC. São estudos técnicos, com áudio silencioso; não são um anúncio aprovado.

Artefatos locais:

- `C:/Users/edugu/OneDrive/Documentos/res/output/prova-edicao-2026-11-08/galeria-12-tecnicas.mp4`
- `C:/Users/edugu/OneDrive/Documentos/res/output/prova-edicao-2026-11-08/evidencias.json`: IDs de documentos, revisões, jobs, assets e durações.
- `C:/Users/edugu/OneDrive/Documentos/res/output/prova-edicao-2026-11-08/contato-12-tecnicas.jpg`: três amostras temporais por estudo.
- `.codex-runtime/editing-proof-20261108/state.json`: estado recuperável da aceitação pela aplicação.
- `.codex-runtime/editing-proof-20261108/ui-report.json`: aceitação em navegador real.

## Fluxo do cliente

1. Abrir um projeto em Vídeo ou Publicidade e expandir **Produto, estratégia e copy do anúncio → Materiais do produto ou serviço e direção de edição**.
2. Criar um conjunto para cada produto/serviço. Informar tipo, finalidade da edição, descrição, cores, fontes e restrições visuais.
3. Enviar logo, manual de identidade, fotos de produtos, demonstrações, provas, apresentador, narração ou elementos preparados. Cada arquivo tem um papel. Um cliente pode reutilizar o conjunto em vários anúncios.
4. Quando necessário, abrir **Preparar recorte de imagem**, marcar o contorno e criar um PNG. A preparação é local, manual e preserva posição e dimensões da fonte; não é segmentação semântica por IA.
5. Para fontes que devem coincidir, informar o mesmo grupo de alinhamento. É uma declaração do usuário, não uma medição automática de registro ou identidade.
6. Salvar e vincular a versão ao anúncio. Uma mudança no conjunto exige novo vínculo; o planejador não mistura silenciosamente versões.
7. Em projeto canônico, **Disponibilizar materiais para edição** registra referências verificadas por escopo/checksum no documento. As LLMs recebem o conjunto e a relação de arquivos ainda não importados. Nenhuma chamada de modelo ocorre nesse botão.
8. Conferir a recomendação e suas exigências. Preparar um estudo de 6 segundos mostra a timeline antes da aplicação. A inserção direta exige timeline canônica vazia, revisão atual e prévia atual; preserva montagens existentes.
9. Exportar pela Clicko e revisar os critérios abaixo no vídeo. A execução de uma receita não concede aprovação editorial.

Os fatos da oferta e a copy continuam registrados no dossiê versionado existente. O manual de marca em PDF pode ser armazenado como referência; esta entrega não executa extração/OCR nem transforma o upload em prova independente de uma promessa.

## Como a escolha funciona

A seleção local considera finalidade, tipo de produto, presença de materiais, contagem de elementos distintos e grupos de alinhamento. Primeiro bloqueia receitas incompletas; depois ordena as utilizáveis pela adequação. É uma regra explícita de direção inicial, sem nota de qualidade ou promessa de conversão.

- Produto físico para apresentação: priorizar montagem dos recortes disponíveis, preservando forma e rótulos.
- Software/serviço com interface pertinente: favorecer a interface como demonstração/evidência, preservando o contexto do apresentador.
- Comparação de variantes: priorizar revelação por máscara quando estados e máscara estão alinhados.
- Explicação: considerar texto em profundidade, interface ou percurso gráfico conforme os materiais.
- Transformação: exigir estados preparados e coerentes; não gerar automaticamente personagens/mundos/eventos nem presumir sua consistência.

Sem uma técnica adequada e viável, a recomendação pode ficar vazia. Uma técnica conhecida não passa a ser executável por estar no nome de uma referência.

## Critérios anotados por técnica

| Técnica | Materiais exigidos para o estudo | Critérios de análise do vídeo |
| --- | --- | --- |
| Progressão de ação | Dois vídeos distintos de demonstração | Cada corte avança a ação; antes/depois compreensíveis; sentido da demonstração preservado. |
| Continuidade de motivo | Estados inicial e final com grupo comum | Mesmo objeto/assunto reconhecível; escala e posição coerentes; informação nova no segundo estado. |
| Revelação com oclusor | Dois estados alinhados e oclusor PNG | Oclusor acompanha a frente da revelação; sem vazamentos; estado final visível. |
| Variante por máscara | Dois estados alinhados e máscara em cinza | Registro temporal/espacial; rótulo e forma preservados; variante legível ao final. |
| Texto atrás do assunto | Base, recorte PNG alinhado e gancho salvo | Texto atrás do assunto; bordas sem halos/tremor; mensagem compreensível; rosto e mãos preservados. |
| Rolagem em janela | Conteúdo alto e moldura PNG com janela transparente | Moldura imóvel; sem vazamentos; texto relevante dentro da janela; chegada em informação útil. |
| Interface como evidência | Apresentador e captura real pertinente | Captura sustenta a afirmação; leitura no celular; nenhuma funcionalidade inventada. |
| Passagem entre mundos | Dois estados preparados com identidade comum | Identidade, figurino, escala e movimento coerentes; mudança serve ao conceito. |
| Evento localizado | Cenário limpo e evento recortado | Cenário/câmera coerentes; entrada e consequência; escala, contato e sombras plausíveis. |
| Inventário animado | Cenário e dois recortes de objetos | Persistência de forma/rótulo; trajetórias e profundidade coerentes; produto não esconde mensagem. |
| Painel contínuo | Panorama preparado | Motivo contínuo; textos/rostos seguros; percurso compreensível. O estudo percorre o panorama em vídeo. |
| Pilha de recortes | Cenário e dois recortes de objetos | Bordas limpas; profundidade coerente; identidade e leitura dos produtos. |

O registro executável está em `backend/app/services/studios/ad_editing_recipes.py`; preserva links dos Reels e os critérios originais da pesquisa. As 12 categorias são as catalogadas na pesquisa anterior de @creators, @paulo.ia e @moonsol.design. Esta execução não assistiu novamente aos 45 Reels nem afirma ter enumerado todo efeito contido em cada vídeo.

## O que foi comprovado e seus limites

**Comprovado em execução local:** preparação de PNG por polígono; multiplicação entre alpha original e máscara; inversão; máscara em vídeo com variação temporal; revelação animada; rolagem por recorte; composição em camadas; render dos 12 estudos; persistência e entrega pela aplicação; isolamento por cliente; bloqueio de kit/prévia desatualizados; importação de materiais no manifesto canônico.

**Não qualificado por esses estudos:** segmentação automática de cabelo/mãos/pessoas em movimento, tracking, geração de novos mundos/personagens mantendo identidade, geração de eventos com contato/sombras corretos, morph semântico ou equivalência estética integral às referências. As receitas dessas categorias compõem materiais já preparados. O recorte humano do estudo foi manual e grosseiro; demonstra oclusão, sem homologar bordas naturais para anúncio final. Um corte entre duas imagens não comprova uma transformação generativa.

O renderer aceita máscaras de imagem/vídeo para trilhas de vídeo/overlay, com canal de cinza ou alpha e inversão. A máscara é aplicada em coordenadas da fonte, antes de crop/escala/rotação. Vídeo-máscara usa o mesmo tempo de origem e velocidade dos clipes alvo; imagem-máscara permanece estática. A máscara multiplica a transparência existente, sem tornar novamente opacas regiões já transparentes.

O recorte animado usa largura/altura normalizadas e `cropX`/`cropY` como percurso 0–1 dentro do espaço restante da fonte. `revealProgress` também varia de 0 a 1. A linguagem de comando das LLMs expõe esses contratos e continua rejeitando expressões, filtros arbitrários e assets inventados.

Os estudos locais usam o editor canônico. Projetos nativos recebem contexto e lacunas no manifesto, mas continuam sujeitos aos próprios comandos de importação/render; vincular um conjunto não altera um arquivo nativo por fora do motor.

## Validação e correções encontradas

- Suíte de 31 casos passou: materiais/máscaras/fonte, copy, contrato de motion, patches editoriais e timeline real. Inclui FFmpeg/ffprobe reais e assertivas sobre pixels decodificados.
- `npm run lint` passou.
- Os 12 estudos e a galeria final completaram jobs reais da aplicação. O título encontrou `timeline_title_font_unavailable` no Windows. Foi adicionado fallback Arial Bold para a família padrão Liberation Sans, e as receitas novas usam a família `system`. O job falho foi repetido com sucesso.
- A revisão de amostras levou ao ajuste da posição do texto em profundidade, à sincronização do oclusor e à margem horizontal dos textos da janela.
- Revisão visual: 0,2 s, 3 s e 5,7 s por estudo, mais testes de pixels. Não equivale a avaliação humana integral de playback/áudio ou a aprovação de anúncio.
- Navegador real: upload, quatro pontos no contorno, criação de PNG, salvar, vincular, bloqueio das 12 receitas com materiais insuficientes e importação canônica passaram. A CLI agent-browser travou; a aceitação final usou Playwright. Apenas descoberta opcional de provedores/modelos foi isolada; uploads, processamento e persistência de materiais usaram endpoints reais.
- O consumo adicional de API desta execução foi **US$ 0**. Não houve ativação da API Anthropic.

## Pontos de implementação

- `backend/app/routers/studio_ad_materials.py`: rotas autenticadas de conjuntos, vínculos, recorte, prévia, aplicação e importação.
- `backend/app/services/studios/ad_materials.py`: armazenamento por workspace, versões, escopo, preparação e contexto para planejamento.
- `backend/app/services/studios/ad_editing_recipes.py`: pré-requisitos, recomendação, critérios e timelines executáveis.
- `backend/app/providers/studios/timeline_ffmpeg.py`: primitivas seguras de máscara, crop e revelação.
- `src/studios/shared/ProductMaterialsPanel.tsx`: fluxo de materiais e preparo local.
- `src/studios/video/CanonicalVideoEditor.tsx`: controles de máscara, recorte, revelação e keyframes.
- `backend/tests/test_ad_materials_and_masks.py`: regressões e aceitação por pixels.
