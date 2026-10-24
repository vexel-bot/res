# Studios — arquitetura visual e complexidade progressiva

Estado local de 24/10/2026. Não modifica backend, autorização, cotas, Gemini ou
voz. Os inventários prévios são `UX_INVENTORY_2026-10-23.md` e
`UX_REVISION_INVENTORY_2026-10-24.md`.

## Navegação e componentes

`StudiosWorkspace` mantém o catálogo de `studioNavigation.ts`, as nove rotas e
as identidades `create-image`/`create-video`. Imagem, Vídeo, Publicidade e
Ferramentas adicionais são categorias horizontais permanentes, seguidas das
ferramentas da categoria atual. Setas/Home/End movem o foco; Enter/Espaço ativam.
`categoryStudioTool` recupera a última ferramenta permitida de cada categoria.
O guard é consultado antes de mudar a categoria ou ferramenta.

Até 1000 px, dois `ClickoSelectMenu` com nomes acessíveis substituem as linhas:
Área dos Studios e Ferramenta. Escape/clique externo fecham o seletor existente;
recursos futuros aparecem desabilitados no desktop e como nota Em breve no móvel,
sem rotas fictícias. O catálogo é centralizado em `studioNavigation.ts`.

| Componente compartilhado | Consumidores | Responsabilidade |
|---|---|---|
| `StudioEditorFrame` | `LocalProductionStudio`, `CanonicalVideoEditor` | Barra, materiais, prévia, inspector opcional, timeline redimensionável |
| `StudioUtilityPanel` | Imagem, Vídeo, produção local | Projetos, histórico, produção, configurações e saídas sob demanda |
| `StudioKlicButton` | Todos os Studios criativos | Abrir a conversa global existente, não criar outro cliente de chat |
| `useStudioShortcuts` | Edição local e canônica | Acionar os mesmos botões de salvar/desfazer/refazer, sem interceptar undo em texto |
| `LocalInspector` | Motion e composição de imagem | Controles por tipo; acabamento, transformação e keyframes progressivos |

Os painéis utilitários são não modais, recebem foco no botão Fechar e devolvem
o foco ao disparador. Escape de um seletor aberto fecha primeiro o seletor.
Abrir a KLIC recolhe o painel de ferramentas concorrente.

O cabeçalho oferece um único `StudioKlicButton`, ligado ao mesmo evento e ao
`FloatingAIAssistant` global. O estado acessível acompanha a visibilidade real,
e o foco retorna ao disparador visível ao fechar. Entradas duplicadas e o balão
são ocultados apenas nos Studios. A partir de 1440 px, a conversa tem 360 px e o
workspace reserva 380 px à direita; abaixo disso, alterna-se temporariamente para
a vista de conversa. O editor fica invisível, mas montado e preservado, voltando
ao fechar. Não há controles ativos por baixo do painel. O CSS limita ambos os
lados no celular, sem herdar a largura global que cortava o botão Fechar.

## Um projeto, diferentes densidades de controles

Na edição local, adicionar texto/forma/material e editar o inspector altera a
mesma composição. Transformações, tipografia, sombras, gradientes e keyframes
continuam nos controles existentes. Não existe uma cópia “simples” do documento.

Na montagem canônica, o mesmo `mediaTimeline` mantém clipes, áudio, títulos,
faixas, cortes, velocidade, keyframes e renderização. A prévia renderizada é
identificada pela revisão; uma prévia DOM não é anunciada como render final.
A troca de documento não descarta uma montagem suja ou operação incerta.
A lista de projetos e a capacidade do renderer local são carregadas sem aguardar
o preflight opcional de geração IA. Verificações pendentes não concedem capacidade.

Os editores nativos preexistentes permanecem em **Ferramentas do Studio**.
São formatos/motores próprios, dependentes de runtime, não uma conversão
automática do projeto local. Nenhum runtime foi inventado ou substituído.

## Criação e publicidade

- Imagem: descrição, formato, estilo e Gerar; depois vêm finalidade, referências
  e configurações avançadas/preservação/marca recolhidas. Serviço e utilização
  continua separado. Consentimento junto à geração, cota e revisão humana
  continuam no fluxo real.
- Vídeo: ideia principal, formato, duração e materiais; nome/público/roteiro em
  opções. Defaults são determinísticos e revisáveis, sem chamada de IA.
- Publicidade: produto/oferta, público e resultado. Benefício, CTA e direção são
  opcionais. Usa Image/Video Studio e Biblioteca, sem gerenciador de campanhas.
- Imagem sem provedor: mensagem curta e geração desabilitada; nenhum resultado
  fictício. A edição manual continua disponível.

## Responsividade e temas

O frame calcula a altura restante da janela, reage a `visualViewport`, resize,
mudanças do layout e desmonta seus listeners/observadores. As regiões possuem
scroll próprio. A timeline usa pointer capture ou teclado; altura entre 100 e
360 px, limitada proporcionalmente ao workspace. O default é 110 px se o frame
tem menos de 520 px de altura, 170 px nos demais; o ajuste explícito é preservado.
Motion mantém a reprodução na toolbar e o cursor na prévia.

Até 900 px, Prévia/Materiais/Propriedades/Timeline alternam a região visível do
mesmo editor; não são quatro documentos nem cópias do canvas. Sem seleção,
Propriedades não aparece. Controles numéricos e **Faixa do elemento** permitem
editar sem depender de arrastar. Abaixo de 640 px os controles têm dimensões e
fontes adequadas à entrada móvel. Não se declara teste em hardware móvel real.

São usados os tokens de tema existentes e a fonte de sistema
`-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`. Coral/tangerina
continuam ações da Clicko; azul `#6EB8F5` identifica a KLIC.

## Validação e reprodução

`npm test` inclui `.test.tsx` e SSR do workspace; `npm run lint` é a checagem
TypeScript configurada no projeto, não um novo ESLint. `npm run build` valida os
bundles. O smoke `scripts/audits/studios-ux-live.ts` usa os contratos e a sessão
DEV reais; não substitui QA do navegador. Requer o fixture privado criado por
`scripts/audits/audiovisual-evidence.py fixtures` na auditoria anterior.

Resultados, comandos, arquivos e limitações:
[relatório da revisão atual](../../CLICKO_REVISAO_EXPERIENCIA_STUDIOS_2026-10-24.md).
