# Clicko — revisão da experiência dos Studios

Entrega local de **24/10/2026**. Pedido de referência:
`457f4b8c-1c73-4b9e-9ea9-b6f0e9ba6d2f`.

Esta é uma revisão incremental da entrega anterior, não uma reconstrução dos
Studios. Implementação e QA no checkout `C:\Users\pedro\Downloads\res`, Modo DEV
isolado em loopback. Sem APIs pagas, alteração de credenciais, migração,
publicação de campanhas, commit, push ou deploy.

## 1. Alterações realizadas

- Retirada a dependência do menu oculto “Alterar Studio” para descobrir ferramentas.
- Categorias e ferramentas visíveis no desktop; dois seletores no tablet/celular.
- Gerar Imagem apresenta ideia, enquadramento, estilo e ação principal antes
  das seções opcionais. Consentimento e indisponibilidade continuam explícitos.
- Mantidos os editores integrados existentes de imagem, vídeo e motion.
- Reprodução do Motion na toolbar. Timeline começa menor no notebook e continua
  redimensionável; não foram removidos keyframes ou propriedades avançadas.
- KLIC consolidada em um acesso no cabeçalho, usando a conversa global existente
  sem balão sobre inputs, geração, salvar, exportação ou timeline.
- Corrigidos dois problemas encontrados na homologação: largura herdada do chat
  que cortava o Fechar no celular e lista de projetos de vídeo que aguardava
  preflight de modelos de IA opcionais. A correção deste carregamento é apenas
  no frontend; capacidade não confirmada continua indisponível.
- Drag-and-drop local informa a limitação de um arquivo por vez, em vez de
  ignorar silenciosamente os arquivos excedentes.

## 2. Nova navegação

| Categoria permanente | Ferramentas reais preservadas |
|---|---|
| Imagem | Gerar Imagem; Editar Imagem |
| Vídeo | Criar Vídeo; Editar Vídeo; Motion Design |
| Publicidade | Criar Anúncio; Criativos para Anúncios |
| Ferramentas adicionais | Composição e formatos; Produção editorial e carrosséis |

As nove URLs, aliases `/image` e `/video`, identidades técnicas `create-image` /
`create-video`, escopo por usuário/workspace/cliente e permissões são os mesmos.
Categoria lembra sua última ferramenta permitida durante a sessão do workspace.
A seleção só muda depois do guard de saída. Recursos futuros permanecem como
Em breve, sem rotas ou ações que simulem disponibilidade.

No desktop, setas/Home/End movem o foco e Enter/Espaço ativam. Até 1000 px, os
seletores Área dos Studios e Ferramenta reutilizam o menu compartilhado da Clicko,
com nomes acessíveis, abertura para baixo, teclado e fechamento já existentes.

## 3. Organização dos Studios

**Imagem:** formulário inicial compacto; finalidade técnica, referências,
preservação/marca/configurações avançadas e serviço/utilização sob demanda.
Projetos, histórico e salvar briefing continuam na barra. A composição manual
mantém canvas, camadas e inspector por seleção, com exportação PNG real.

**Vídeo:** criação por ideia, duração, formato e materiais; edição pelo mesmo
`mediaTimeline`, com materiais à esquerda, monitor central, inspector contextual
à direita e timeline inferior. Não há outro documento “simplificado”.

**Motion:** nome, salvar, undo/redo, reproduzir e exportar na barra. Elementos,
camadas, preview, propriedades e timeline reutilizam o frame integrado. Tempo,
transformação, acabamento e keyframes continuam nos controles existentes.

**Publicidade:** produto/serviço, objetivo, público e formato; materiais da
Biblioteca e o mesmo documento seguem para o editor correspondente. Nenhum
gerenciador ou publicador automático de campanhas foi anunciado como pronto.

**Editorial e ferramentas:** sala editorial e composição continuam acessíveis.
Editores nativos continuam descobertos em Ferramentas do Studio, explicitando
dependências; o fato de o acesso existir não homologa seus binários/WASM.

## 4. Funcionalidades preservadas

- Criação/abertura de projetos, originais, materiais e Biblioteca compartilhada.
- Edição contextual de texto, formas e imagens, crop, contraste, posição e escala.
- Vídeo: cortes, faixas, áudio, textos, legendas, efeitos, sequências, keyframes,
  render, prévia, recuperação e exportação pelos contratos existentes.
- Motion: cenas, duração, curvas/animações, camadas e composição 2D existentes.
- Undo/redo, atalhos de salvar, revisão, versões, histórico, locks/idempotência
  e guard de alterações/ações pendentes. Nenhuma autorização foi relaxada.
- Conversa, voz, Gemini, anexos e histórico da KLIC mantidos nos componentes e
  serviços anteriores. A revisão não muda modelo, chave, cota ou implementação
  dos provedores. A abertura da conversa não implica chamada de inferência.

A preservação foi mapeada antes da revisão em
[UX_REVISION_INVENTORY_2026-10-24.md](docs/studios/UX_REVISION_INVENTORY_2026-10-24.md).
Nem todo efeito individual foi novamente exercitado manualmente; a cobertura
real desta etapa é discriminada abaixo, sem afirmar homologação total.

## 5. Componentes reutilizados e arquivos principais

React/TypeScript, CSS/tokens nativos, fonte de sistema e lucide-react já existentes.
Nenhuma biblioteca nova. Backend Express/FastAPI, persistência e FFmpeg reutilizados.

| Arquivo/componente | Papel nesta revisão |
|---|---|
| `src/studios/StudiosWorkspace.tsx` | Duas linhas desktop, seletores compactos, guard, foco e único acesso KLIC |
| `src/studios/studioNavigation.ts` | Mesmo catálogo; seleção segura por categoria e recursos futuros centralizados |
| `src/studios/studios-workspace.css` | Densidade, responsividade e espaço reservado da KLIC, só nos Studios |
| `src/components/ClickoSelectMenu.tsx` | Prop opcional de nome acessível; demais consumidores inalterados |
| `src/studios/image/ImageStudio.tsx` | Hierarquia da geração, sem trocar handlers, consentimento ou API |
| `src/studios/local/LocalProductionStudio.tsx` | Reprodução na barra e feedback de importação múltipla |
| `src/studios/shared/StudioWorkspace.tsx` | Frame existente, altura inicial adaptativa, estado/foco do acesso KLIC |
| `src/studios/shared/studioWorkspaceModel.ts` | Default de timeline testável, sem mudar limites de edição |
| `src/components/FloatingAIAssistant.tsx` | Evento de visibilidade para o disparador; mesma conversa e fluxo de fechar |
| `src/studios/video/VideoStudio.tsx` | Catálogo independente da IA e remoção de feedback duplicado na edição canônica |
| Testes de navegação, experiência e SSR compartilhados | Regressões de catálogo, geração, timeline, foco/ARIA e largura KLIC |

O checkout já continha mudanças da etapa anterior; foram preservadas, inclusive
`LocalInspector`, `LocalMonitor`, `CanonicalVideoEditor`, utilitários e CSS do
frame. Não foram alterados backend, pacotes, lockfile ou dados comerciais nesta revisão.

## 6. Melhorias de UX e comparação

- **Descoberta:** antes era necessário abrir “Alterar Studio” para conhecer as
  áreas; agora as quatro categorias são permanentes no desktop. Trocar categoria
  e ferramenta continua explícito, sem prometer redução artificial de cliques.
- **Criação:** antes o usuário passava pelas opções antes da ação de geração;
  agora o núcleo ideia/formato/estilo é seguido de Gerar, com defaults existentes.
- **Edição:** inspector só para a seleção, mesmo documento; ferramentas avançadas
  continuam recolhidas e acessíveis. Text undo nativo não é interceptado.
- **Prévia:** notebook 1190×668 mediu monitor com aproximadamente 289 px de
  altura e timeline inicial de 110 px, sem rolagem horizontal da página.
- **KLIC:** um acesso reservado. A partir de 1440 px, editor e conversa coexistem
  lado a lado. Em janelas menores, a conversa é uma vista temporária: o editor
  fica invisível mas montado, e retorna ao fechar com estado preservado. Portanto
  não se promete edição simultânea com chat em telas estreitas.
- **Disponibilidade:** projetos manuais não esperam a inspeção dos modelos de IA;
  a interface não habilita IA enquanto sua capacidade não estiver confirmada.

## 7. Responsividade e acessibilidade

Navegador real com viewport controlado, não testes em hardware físico:

| Tamanho | Conferência realizada |
|---|---|
| 1440×900 desktop | Navegação permanente, edição, inspector, temas e conversa lateral |
| 1190×668 notebook | Gerar visível antes das opções, vídeo/preview/timeline dentro da janela, KLIC temporária |
| 820×900 tablet | Dois seletores, menus e editorial; sem overflow horizontal involuntário |
| 390×844 celular | Menus, formulário, Motion por painéis, propriedades, timeline, KLIC e fechamento/foco |

No desktop, workspace terminou em x=1044,8 e chat começou em x=1060: sem
interseção. No celular, após corrigir `width:auto`, chat ficou x=74 a 380,4 em
viewport de 390; Fechar ficou inteiramente visível. `aria-expanded` acompanhou
abertura/fechamento e o foco retornou ao botão KLIC. O painel não bloqueou a
navegação lateral. No Motion móvel, Prévia/Materiais/Propriedades/Timeline
mostraram o mesmo projeto e texto de tamanho 76, sem criar cópias.

Temas claro/escuro exercitados pelo seletor oficial das Configurações, sem
injetar tema no DOM. Preferência escura restaurada. Fonte de sistema, coral e azul
da KLIC preservados. Touch físico, teclado virtual e leitores de tela completos
não foram homologados nesta etapa.

## 8. Resultados dos testes

### Automatizados

| Verificação | Resultado |
|---|---|
| `npm test` | **268 Node/SSR + 2 Vite = 270 aprovados**, sem falhas/pulados |
| `npm run lint` | **Aprovado** (`tsc --noEmit`; não há novo ESLint) |
| `npm run build` | **Aprovado**, frontend e bundles do servidor/worker |
| Python pertinente | **37 aprovados** na execução desta revisão; JUnit sem falhas/erros/pulados |
| `git diff --check` | Sem erros de whitespace; avisos de conversão LF/CRLF do checkout Windows |

Python: `test_image_frontend_contract`, `test_video_frontend_contract`,
`test_local_agent_stage2`, `test_stage2_completion`, `test_stage3_homologation`
e `test_stage3_shared_media`. Logs/JUnit privados em
`.codex-runtime/studios-navigation/{tests-final,types-final,build-final,python-final}.log`
e `python-final.xml`.

### Fluxos reais no DEV, não mocks de interface

- Todas as nove ferramentas acessadas pela navegação; categoria Vídeo recuperou
  Motion após visitar Imagem; teclado dos seletores e setas/Enter desktop conferidos.
- **QA · Navegação visível · 24-10:** projeto Motion de 12 s, texto adicionado/editado,
  tamanho 64→76, undo 64/redo 76, CtrlS, reprodução e MP4 real. Reaberto após reinício.
- **QA · Imagem navegação · 24-10:** importação de fixture próprio PNG pelo filechooser,
  crop 10%, contraste 1,05, salvamento v3, exportação PNG e histórico com versões.
  Composição reutilizou o mesmo documento e originais.
- **QA Navegação · anúncio manual:** produto, público, objetivo, 3 s, material da
  Biblioteca; abriu o editor canônico com o mesmo material. Escala1,1 criou edição
  pendente; mudar para Imagem foi bloqueado. Undo/salvar permitiram continuar.
  MP4 real exportado e reproduzido por HTML5 (3 s, readyState 4, término confirmado).
- Após reiniciar o servidor local nesta retomada, documentos, materiais e export
  continuaram disponíveis; nenhum reset dos dados foi executado.
- KLIC aberta/fechada em notebook, desktop e celular, sem enviar mensagens,
  ativar microfone, chamar Gemini, TTS ou geração. Projetos mantidos ao fechar.
- Console da aba de QA sem entradas de erro/warning na última conferência.

## 9. Capturas de tela e evidências

Capturas reais privadas, não mockups; não são enviadas ao GitHub:

- Antes da revisão: `.codex-runtime/image-spacing/after-1190.jpg` e
  `.codex-runtime/studios-ux/screenshots/motion-final-preview.jpg`.
- [Gerar Imagem, notebook](.codex-runtime/studios-navigation/image-notebook-final.jpg)
- [Prévia final, tamanho normal da janela](.codex-runtime/studios-navigation/studios-final-preview.jpg)
- [Vídeo integrado, notebook](.codex-runtime/studios-navigation/video-notebook-final.jpg)
- [Motion, exportação](.codex-runtime/studios-navigation/motion-export.jpg)
- [Editor de imagem, desktop](.codex-runtime/studios-navigation/image-editor-desktop.jpg)
- [Publicidade, desktop](.codex-runtime/studios-navigation/advertising-desktop.jpg)
- [Editorial, tablet](.codex-runtime/studios-navigation/editorial-tablet.jpg)
- [Motion, celular](.codex-runtime/studios-navigation/motion-phone-preview.jpg)
- [Propriedades no celular](.codex-runtime/studios-navigation/motion-phone-properties.jpg)
- [Timeline no celular](.codex-runtime/studios-navigation/motion-phone-timeline.jpg)
- [KLIC no celular, corrigida](.codex-runtime/studios-navigation/klic-phone.jpg)
- [KLIC lateral no tema claro](.codex-runtime/studios-navigation/klic-desktop-light.jpg)
- [KLIC lateral no tema escuro](.codex-runtime/studios-navigation/klic-desktop-docked.jpg)

## 10. Pendências e situação atual

**A revisão visual/funcional local está implementada e validada no escopo
descrito. Isso não equivale à homologação comercial de toda a plataforma.**

Continuam dependentes de infraestrutura ou homologação específica:

1. Geração por IA, Gemini/voz externos e qualidade audiovisual por modelo:
   não acionados; orçamento de testes externos permanece zero.
2. Motores Craft/binários/WASM e ferramentas 3D: indisponíveis neste DEV, não
   apresentados como edição operacional por esta revisão.
3. Variações de criativos, outras variações e adaptação social: Em breve.
4. Testes em aparelhos físicos/touch/teclado virtual, leitores de tela completos,
   grande volume de materiais e certificação de desempenho não realizados aqui.
5. Débito técnico global documentado em 23/10: Python 888 aprovados / 277 falhas /
   112 pulados, Ruff 323 achados e npm audit 1 alta. A suíte global e a auditoria
   de dependências não foram repetidas nesta revisão; os 270+37 aprovados acima
   não eliminam esse débito histórico nem justificam declarar produção pronta.

Prévia funcional: [Studios](http://127.0.0.1:3018/studios/image/generate).
Perfil DEV persistente, sem login comercial, nas portas 3018/8018. README, CHANGELOG,
inventário e arquitetura atualizados. Alterações permanecem locais; nenhum push
ou deploy nesta etapa.
