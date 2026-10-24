# Studios — unificação da navegação

> Atualização de 24/10/2026: as rotas e identidades técnicas abaixo permanecem,
> e a revisão mais recente mantém categorias/ferramentas visíveis no desktop,
> substituindo o seletor oculto **Alterar Studio**. Tablet/celular usam dois
> seletores compactos com os mesmos destinos e permissões.
> Motion, edição de imagem e montagem usam o workspace integrado descrito em
> [Arquitetura visual atual](UX_ARCHITECTURE_2026-10-24.md). O restante deste
> documento registra a entrega histórica de 19/10.

Entrega local: 19/10/2026. Escopo: navegação e adaptação dos componentes de Imagem/Vídeo existentes, sem reconstruir os editores ou alterar regras comerciais.

## Organização implementada

O menu lateral possui uma única entrada **Studios**, com o ícone Clapperboard e os mesmos estados, dimensões e classes das demais entradas. As entradas independentes Imagem/Vídeo foram removidas desse menu; as outras opções não foram reordenadas ou removidas.

A área Studios reutiliza as classes e os tokens da navegação superior de Configurações, com categorias e uma segunda linha de ferramentas. A navegação tem foco visível, nomes acessíveis, indicação `aria-current`, botões futuros desabilitados e rolagem horizontal restrita ao menu. Setas/Home/End movem o foco; Enter/Espaço ativam a opção.

| Categoria | Ferramenta / URL | Implementação reutilizada |
| --- | --- | --- |
| Imagem | Gerar Imagem — `/studios/image/generate` | `ImageStudio`, operação de criação existente. |
| Imagem | Editar Imagem — `/studios/image/edit` | O mesmo `ImageStudio`, operação de edição, originais e referências preservados. |
| Vídeo | Criar Vídeo — `/studios/video/create` | `VideoStudio`, área `ai`, briefing e materiais existentes. |
| Vídeo | Editar Vídeo — `/studios/video/edit` | Área `editor`, incluindo timeline canônica/FFmpeg ou editor nativo conforme o projeto. |
| Vídeo | Motion Design — `/studios/video/motion` | Área `motion`, sem substituir timeline, keyframes ou recursos do motor existente. |
| Publicidade | Criar Anúncio — `/studios/advertising/create` | Área `ad` do `VideoStudio`. |
| Publicidade | Criativos para Anúncios — `/studios/advertising/creatives` | Gerador de imagens existente, com objetivo Anúncio para um briefing vazio. Um briefing preenchido não é sobrescrito automaticamente. |
| Ferramentas adicionais | Composição e formatos — `/studios/tools/composition` | Acesso à área avançada PhotoCraft existente. Capacidade de composição/formatos depende do runtime; a navegação não cria um conversor fictício. |
| Ferramentas adicionais | Produção editorial e carrosséis — `/studios/tools/editorial` | `DepartmentStudio` já existente. |

**Variações de Criativos**, **Variações de imagem e vídeo** e **Adaptação para redes sociais** aparecem como **Em breve**, desabilitadas e sem rota funcional fictícia. A existência de enquadramento no prompt de imagem não foi apresentada como redimensionamento exato. Não foi criada integração de publicação ou gestão de campanhas publicitárias.

Os botões internos que mudam a área de Vídeo e os acessos à produção editorial também sincronizam a ferramenta selecionada. Os menus internos redundantes de escolha de operação são ocultados somente quando embutidos em Studios; ferramentas, campos, projetos, materiais e ações dos editores continuam presentes.

## Rotas, acesso e contexto

- `/studios` abre a criação de imagens quando permitida; para uma pessoa com acesso apenas a Vídeo, abre a ferramenta de criação de vídeo. Não concede acesso ao outro módulo.
- `/image` e `/video` continuam como aliases compatíveis. A navegação nova gera URLs sob `/studios/...`.
- A troca de ferramentas usa `pushState`, e o listener de `popstate` restaura a ferramenta e o módulo correspondentes. URLs diretas e recarregamento resolvem o mesmo catálogo.
- **Studios é um agrupador visual, não uma nova licença ou permissão.** Permanecem `create-image` e `create-video` como identidades técnicas de capacidade, API, quota e autorização. Categorias filtram opções pelas permissões/capacidades atuais, inclusive no contexto Pessoal/Workspace.
- Uma URL de uma ferramenta não autorizada exibe a proteção existente. A interface não monta o editor nem seu provider de dados antes de concluir a verificação do contexto.
- Somente um `ProductDataProvider` de mídia fica ativo. Isso preserva o escopo global de requisição já existente em `api.ts`, sem executar simultaneamente dois providers com módulos diferentes.
- As instâncias são separadas por usuário, conta, módulo e cliente. O contexto KLIC reconhece as novas URLs sem mudar sua identidade ou funcionamento.
- Operações sem confirmação e alterações nativas pendentes podem impedir a saída, mostrando um aviso. Durante essa proteção, a tentativa de Voltar é mantida na URL anterior; o fluxo normal usa o histórico do navegador. Essa situação excepcional não deve ser confundida com descartar ou cancelar o job no servidor.

## Preservação de estado

Trocar criação/edição ou áreas de vídeo dentro do mesmo módulo reutiliza sua instância. Ao alternar Imagem/Vídeo, não são mantidos dois contextos globais de API simultâneos: o módulo anterior é desmontado e seus dados de navegação são recuperados por escopo.

`studioSession.ts` mantém um cache de sessão por usuário/workspace/módulo. Briefings, materiais selecionados e referências a projetos podem ser retomados na troca de módulo e no reload. O formulário editorial usa também seu contexto de conteúdo/campanha. A persistência em sessionStorage é limitada a 1 MB por entrada, com fallback em memória se o armazenamento estiver bloqueado ou sem espaço; nessa situação, não se promete recuperação após fechar/recarregar a aba.

Autorizações de uso e confirmações sensíveis não são restauradas como consentimento. Não se armazenam credenciais nem URLs Blob de preview. Snapshots do cliente não substituem o servidor: autenticação, autorização dos ativos e verificação de revisão continuam obrigatórias; uma revisão alterada por outra sessão pode exigir atualização pelo fluxo existente de projetos. As recuperações de comandos nativos e de requests/jobs já implementadas foram preservadas.

## Arquivos desta etapa

- `src/App.tsx`: resolução das URLs, histórico e montagem da área unificada, mantendo os IDs técnicos anteriores.
- `src/components/Sidebar.tsx`: uma entrada Studios e estado ativo agrupado.
- `src/components/SpotlightModal.tsx`: acessos pesquisáveis dentro de Studios, respeitando as permissões existentes.
- `src/studios/StudiosWorkspace.tsx`, `studios-workspace.css`: shell e navegação superior; reaproveitamento de `SettingsView.css` sem modificar Configurações.
- `src/studios/studioNavigation.ts`: catálogo único e aliases; ferramentas futuras não recebem rotas ativas.
- `src/studios/studioSession.ts`: recuperação local de navegação, sem geração ou salvamento automático no backend.
- `src/studios/ClickoStudioView.tsx`: adaptação para ferramenta selecionada e isolamento da instância por conta/cliente.
- `src/studios/image/ImageStudio.tsx`, `src/studios/video/VideoStudio.tsx`: entradas controladas para as operações existentes, cache de sessão e sincronização de navegação. Sem alterar modelos, prompts enviados, endpoints ou persistência do servidor.
- `src/studios/video/CanonicalVideoEditor.tsx`, `src/studios/craft/useCraftStudio.ts`: proteção de saída durante requests/comandos pendentes; renderizador e comandos preservados.
- `src/studios/department/DepartmentStudio.tsx`: recuperação do formulário editorial e proteção de saída durante uma operação.
- `src/klic/pageContext.ts`: associação das novas URLs aos módulos anteriores.
- `studioNavigation.test.ts`, `studioSession.test.ts`: dez testes novos de catálogo, permissões, recuperação, corrupção e proteção de navegação.

Não houve alteração de código de backend, preços, créditos, limites, planos, modelos IA, uploads ou armazenamento de ativos **nesta etapa**. O checkout já continha mudanças de entregas anteriores nesses subsistemas, que foram preservadas e não devem ser atribuídas a esta unificação. Não houve push/publicação externa.

## Testes realizados e limites da validação

- `npm test`, concorrência 1: **188 testes aprovados**, sem falhas ou skips (178 anteriores + 10 novos).
- `npm run lint`: checagem TypeScript aprovada.
- `npm run build`: frontend, servidor e worker compilados com êxito.
- Python: **11 testes aprovados** em `test_image_frontend_contract.py`, `test_video_frontend_contract.py` e `test_clicko_studio_bridge.py`. Esses testes incluem fronteiras autenticadas, persistência privada e integração com providers controlados nos testes; não equivalem a uma nova geração paga por IA nesta entrega.
- HTTP na prévia isolada: as nove URLs de ferramenta, `/studios` e os dois aliases antigos responderam 200. Os bridges de Imagem e Vídeo responderam 200 nos respectivos escopos. Isso comprova entrega das rotas/serviços, não uma inspeção visual dos painéis.
- A saída real de vídeo já persistida continuou acessível com HTTP Range **206**, sem re-renderização ou nova cobrança. O motor CPU continuou disponível.
- `git diff --check`: sem erros de whitespace; podem aparecer avisos de conversão LF/CRLF do checkout Windows.
- **QA visual interativo pendente:** a ferramenta de navegador não conseguiu anexar a aba desta conversa. Após essa limitação ser informada, o usuário escolheu continuar com os testes disponíveis. Portanto não se declara uma conferência visual concluída de desktop/tablet/mobile nem de ambos os temas. O CSS utiliza os tokens claro/escuro existentes e limita o overflow dos menus; a verificação visual em navegador permanece um item de aceite separado.
- Não foi feita nova chamada paga de geração de imagem/cenas de vídeo, nem uma exportação nativa com runtime indisponível. A disponibilidade efetiva desses serviços continua indicada pelas interfaces existentes, sem resultados fictícios.

Prévia local: **http://127.0.0.1:3018/studios**. Os dados de teste e os serviços usados são os do ambiente isolado já existente em `.codex-runtime/video-qa/`; os demais módulos e dados principais não foram migrados para esse ambiente.
