# Studios — inventário prévio da revisão de navegação

Pedido: `457f4b8c-1c73-4b9e-9ea9-b6f0e9ba6d2f`. Este mapeamento foi registrado
antes das alterações desta revisão. Complementa `UX_INVENTORY_2026-10-23.md`;
o checkout contém a implementação local anterior, que será preservada.

| Função | Componente atual | Nova localização / ajuste | Estado / dependência |
|---|---|---|---|
| Nove rotas e quatro categorias | `studioNavigation`, `StudiosWorkspace` | Categorias e ferramentas visíveis em duas linhas no desktop; dois seletores compactos no móvel | Rotas e permissões reais; sem novo entitlement |
| Recursos futuros | `futureTools` | Descoberta na categoria, desabilitados | Indisponíveis; nenhum botão fictício |
| Contexto e saída protegida | `App`, `studioNavigationAllowed`, guards dos editores | Mesmo fluxo; categoria só muda após seleção autorizada | Revisões, dirty/pending e escopo preservados |
| Ideia/formato/estilo | `ImageStudio` | Núcleo do formulário seguido da geração, antes dos detalhes | Formulário real; provedor indisponível no DEV |
| Referências, autorização, preservação, marca | `ImageStudio`, `imageModel` | Seções recolhidas, autorização junto da geração | Biblioteca real; envio depende de consentimento/provedor |
| Projetos/histórico/briefing | `StudioUtilityPanel`, `productApi` | Barra compacta; mesmas ações | Persistência e jobs existentes |
| Texto, forma, imagem, crop, ajustes e transformação | `LocalProductionStudio`, `LocalInspector`, `LocalLayerControls` | Canvas e inspector contextual existentes; padronização visual | Edição local real, locks/revisões mantidos |
| Motion/cenas/keyframes/easing | `LocalProductionStudio`, `LocalMonitor` | Frame integrado preservado; reprodução na barra | Motion 2D e export local reais, sem 3D novo |
| Materiais/cortes/títulos/áudio/efeitos/faixas | `CanonicalVideoEditor`, `canonicalTimeline` | Mesmo editor integrado; espaço recalculado após navegação | Render FFmpeg existente; sem reconstruir backend |
| Versões, undo/redo, salvar/exportar e recuperação | Editores locais/canônicos | Mesmos handlers/atalhos e painéis | Operações reais/idempotentes |
| Publicidade/briefings e Biblioteca | `VideoStudio`, `ImageStudio` | Produto, público, objetivo, formato; mesmos editores | Criação manual real; sem publicação automática |
| Ferramentas nativas/editoriais | `ClickoStudioView`, `CraftStudio`, `DepartmentStudio` | Acessos preservados na navegação e menu de ferramentas | Craft depende de binários/WASM; não operacional neste DEV |
| Conversa, voz, Gemini e histórico KLIC | `FloatingAIAssistant`, `StudioKlicButton` | Um acesso reservado no cabeçalho dos Studios; conversa existente sem balão sobre ações | Nenhuma mudança de modelo/chave/voz; chamadas externas não testadas |
| Desktop/notebook/tablet/celular | CSS dos Studios, `StudioEditorFrame` | Duas linhas compactas ou seletores, painéis por etapas | Verificação real no navegador; sem prometer hardware físico |

## Problemas concretos a corrigir

1. O catálogo inteiro depende de abrir “Alterar Studio”; ferramentas são difíceis
   de descobrir apesar de as rotas já existirem.
2. O balão global pode cruzar a área de Gerar/Timeline. Os Studios já possuem
   botões KLIC, portanto é possível consolidar o acesso sem remover a conversa.
3. A geração de imagem vem depois de detalhes opcionais; a navegação visível
   consumirá altura adicional e exige manter o núcleo do formulário prioritário.
4. Os editores integrados, contexto, versões e renderização já existem; devem
   ser aperfeiçoados e retestados, não substituídos por outra implementação.

## Limites desta revisão

Sem alterações de backend, contratos comerciais, credenciais, Gemini, voz,
cotas, dados comerciais ou migrações. Sem APIs pagas, push ou deploy. Somente
dados próprios de QA no Modo DEV. Dependências de geração IA e Craft permanecem
explícitas. A homologação final distinguirá navegador real, testes automatizados
e serviços não disponíveis.

## Fechamento de 24/10/2026

O mapeamento acima foi aplicado preservando as nove ferramentas. A navegação
desktop agora é permanente; tablet/celular usam dois seletores. Geração vem
antes dos detalhes, Motion tem playback na toolbar e timeline adaptativa.
KLIC usa acesso único, faixa lateral no desktop largo ou vista temporária nas
janelas menores, mantendo o editor montado. A homologação corrigiu largura do
chat móvel e carga do catálogo de vídeo indevidamente dependente do preflight IA.

Fluxos locais, resoluções, capturas, testes e limites estão discriminados no
[relatório desta revisão](../../CLICKO_REVISAO_EXPERIENCIA_STUDIOS_2026-10-24.md).
Não se promoveu a dependência IA/Craft a funcionalidade pronta, nem se removeu
recurso essencial para simplificar sua apresentação.
