# Studios — inventário funcional e arquitetura de experiência

Pedido: reorganização UX/UI, sem alterações de backend, modelos, voz, permissões ou contratos. Sem push/deploy.
Baseline: commit `946397d04061952104f5e25319ea2c0bcf05958b`. Capturas anteriores: `dev-motion-ui.png` e `dev-image-ui.png`, privadas no perfil DEV; não são capturas novas.

## A. Levantamento antes das alterações

| Área / componente existente | Recursos e pontos de entrada que devem permanecer | Nova localização planejada |
|---|---|---|
| `StudiosWorkspace` | 9 rotas, Imagem/Vídeo/Publicidade/Ferramentas, acesso por módulo, navegação com proteção de trabalho em andamento, descoberta de opções futuras | Seletor único de Studio agrupado por área; mesma rota/entitlement |
| `ClickoStudioView` | Edição local, acesso a editores nativos/avançados existentes, recuperação de documento e passagem de contexto | Editor local padrão; recursos existentes sob menu de ferramentas, sem conversão implícita de projetos |
| `LocalProductionStudio`: projetos | Selecionar, criar, abrir por link, nome, recuperar rascunho, confirmar operação idempotente, recarregar revisão salva | Barra compacta + painel Projetos; alertas de recuperação continuam visíveis |
| Produção local: planejamento | Instrução, preparar/revisar/aplicar plano, seleção/cena, tarefas/eventos/recibos, conexões e papéis | Ferramentas de produção sob demanda; acesso à conversa KLIC existente; não criar chat novo |
| Produção local: camadas | Texto, forma, importar imagem/vídeo/áudio, biblioteca, seleção canvas/lista, ordem, duplicar/remover e locks | Painel esquerdo Camadas/Materiais, seleção direta e inspetor contextual |
| Texto local | Conteúdo, tamanho/cor, peso, alinhamento, revelação por palavra e intervalo | Inspetor Texto; acabamento/animação expansíveis |
| Formas locais | Preenchimento, retângulo/elipse, cantos, gradiente e sombra | Inspetor Forma; acabamento expansível |
| Imagem local | Asset original, crop/restauração, brilho/contraste/saturação, dimensões | Inspetor Imagem; ajustes contextuais |
| Transformações locais | Nome, x/y, largura/altura, rotação, opacidade, zIndex, fundo do projeto | Inspetor; transformação avançada expansível; fundo em Projeto |
| Motion local | Reprodução, cursor/tempo, cenas, início/duração, entrada, keyframes (propriedade/quadro/valor/easing), 32 chaves, duplicação | Canvas central + timeline inferior redimensionável; inspector da animação selecionada |
| Persistência local | Salvar, undo/redo, versões/restaurar, export PNG/MP4, cancelar render, erro, download e original preservado | Toolbar, Histórico e Saída; feedback visível, sem alterar handlers |
| Montagem canônica: materiais | Lista, importar, abrir biblioteca, adicionar clips/imagens/áudio e títulos | Painel Materiais do mesmo editor; nenhum serviço paralelo |
| Montagem canônica: seleção | Tempo inicial/duração, corte da fonte, velocidade, x/y/scale/opacidade/rotação, presets/fades | Inspetor apenas com seleção; controles específicos por tipo |
| Montagem canônica: áudio/texto | Ganho, fades áudio, áudio original, texto/cor/tamanho/fundo e remoção de fundo do título | Inspetor contextual; ferramentas específicas preservadas |
| Montagem canônica: timeline | Cursor, duração do projeto, faixas, títulos/CTA, muting, arrastar, reposicionar, dividir/remover, keyframes/limpar | Timeline inferior com rolagem própria; parâmetros numéricos continuam alternativa ao arrastar |
| Montagem canônica: operação | Undo/redo, salvar, gerar prévia/MP4, cancel/retry, recuperação, modelo/pedido IA, erro/reabrir revisão | Barra e painéis recolhíveis; não anunciar preview ao vivo como render final |
| `VideoStudio`: criação | Tipo, nome, objetivo, público, estilo, script, proporção, duração, idioma, materiais, salvar/continuar, projetos/legados, disponibilidade | Ideia principal + formato/duração e materiais; restante em opções; defaults locais revisáveis |
| Vídeo nativo | Editor FilmCraft/EffectCraft, formatos/export, modelo/conexão, comandos, revisão/aprovação, versões e recuperação | Entradas existentes preservadas, com disponibilidade explícita; sem fingir runtime instalado |
| Publicidade vídeo | Caminhos próprio/montagem, avatar/integral indisponíveis, oferta, benefício, público, objetivo, CTA, script e materiais | Três perguntas centrais; configurações e caminhos sob demanda; reaproveitar Video Studio |
| `ImageStudio`: criação/edição IA | Descrição, finalidade, formato, estilo, referências (até 3), fonte, preservar, instruções, marca, sugestão KLIC, autorização, cota/serviço | Ideia/formato/materiais em primeiro plano; detalhes técnicos e extras recolhidos, autorização e custo continuam junto da ação |
| Imagem: resultados | Preview/ampliar, variantes/derivações existentes, download, avaliação/notas/confirmação/revisão humana, job/cancel/retry, histórico | Prévia/resultados e painéis contextuais; nenhuma imagem fictícia quando serviço não disponível |
| Imagem avançada/editorial | PhotoCraft, documentos/carrosséis, vincular resultado e manter original, projetos/solicitações | Menu de ferramentas e histórico preservados; sem migrar documentos automaticamente |
| Publicidade imagem | Finalidade Anúncio, briefing e contexto de marca/referências, revisão e export | Campos de produto/público/resultado salvos no mesmo briefing; não inventar gestão/publicação de campanhas |
| Biblioteca global | Arquivos, modelos, marca, campanhas e linhagem existentes; assets compartilhados por ID/checksum | Reutilizada via callbacks; sem alterar módulo externo |
| KLIC global | Conversa persistente única, contexto documento/camada, comandos reais e voz existentes | Botão discreto no editor abre painel global existente; controles manuais independentes |

## B. Redundâncias e decisões

- Cabeçalho, categorias, ferramentas, escolha de editor e cabeçalho interno competem pela altura: usar navegação compacta única.
- Biblioteca, comando e histórico antes do canvas: transferir para laterais/painéis sob demanda.
- Propriedades vazias ocupam coluna e propriedades avançadas ficam longe da seleção: renderização contextual, com transformação/acabamento recolhidos.
- Timeline e output abaixo da dobra: workspace em grid limitado à janela, regiões internas com scroll; saída em painel próprio.
- Não remover confirmações, quotas, revisão, erros e recuperação para simplificar: manter informação necessária no momento da ação.
- Formulários e edição têm momentos distintos; o mesmo documento e os mesmos handlers permanecem responsáveis por salvar e exportar.
- Recursos nativos são outro formato existente, não um modo “avançado” que converte silenciosamente o projeto local. A descoberta deve esclarecer essa fronteira.

## C. Contrato de preservação e validação

Alterar organização/estado de UI; não mudar IDs, endpoints, versões, campos comerciais, modelo Gemini, voz ou cota. Novos defaults são locais, explícitos/revisáveis, sem inferência automática. Nenhuma funcionalidade indisponível será apresentada como operacional.

Verificar Node/tipagem/build e testes Python pertinentes; adicionar regressões para defaults, layout/controles e navegação. No navegador DEV: abrir/criar/importar/selecionar/editar, keyframes, timeline, salvar/recuperar/histórico, KLIC, export; desktop/notebook/tablet/celular e temas. Capturas de antes/depois somente se forem reais. Browser inicialmente bloqueado por configuração do Work; usuário confirmou intenção de habilitar, a disponibilidade ainda será conferida.

## D. Fechamento de 24/10/2026

O acesso ao navegador tornou-se disponível. Foram exercitados os fluxos reais
de criação manual, importação, seleção, edição, atalhos, versões, exportação
PNG/MP4, reprodução HTML5, KLIC global e painéis responsivos no DEV. Os recursos
deste inventário foram redistribuídos, não substituídos por novos serviços.
O [relatório final](../../CLICKO_REDESIGN_STUDIOS_2026-10-24.md) registra a matriz
de evidências, limitações e capturas privadas. A
[arquitetura visual](UX_ARCHITECTURE_2026-10-24.md) descreve a localização atual.
