# Limpeza de código — 6 de setembro de 2026

## Escopo e critério

O inventário percorreu os módulos TypeScript/JavaScript do frontend, backend, configurações e testes. O grafo de imports foi rastreado a partir de `src/main.tsx`, `server.ts`, `vite.config.ts` e dos nove arquivos de teste. As referências textuais, scripts npm e imports dinâmicos foram conferidos antes das exclusões. O executor de testes foi preservado: sua entrada é o script npm, não um import da aplicação.

As alterações locais anteriores foram preservadas. Uma cópia do estado anterior à limpeza, incluindo arquivos ainda não versionados, foi guardada em:

`C:\Users\pedro\AppData\Local\Temp\clicko-cleanup-65d13e0bb2eb41dca3fff493c85e293a\before-cleanup.zip`

## Remoções confirmadas

- Sete componentes sem caminho de execução a partir das entradas atuais: `AnalyticsVisualizations`, `CollaborationView`, `CreativeMatrixView`, `DashboardView`, `SmartBriefingView`, `StudioView` e `StudioImmersiveView`. O Dashboard ativo continua sendo `DashboardEditorialView`; o Analytics ativo continua sendo `AnalyticsIntelligenceView`.
- Cálculos e tipos do Analytics antigo sem consumidores: scores, oportunidades, alertas, resumos e timeline. A detecção de anomalias efetivamente usada foi mantida.
- Cards e helpers antigos de Analytics sem consumidores, listas de automações e contas de exemplo não utilizadas, um inicializador de aprendizado nunca chamado, um tipo de template sem referências e exports sem utilização.
- Imports, variáveis, setters e estados sem leitura; a cópia de estado de perfil não consumida foi removida, mantendo o contexto derivado da conta autenticada e os eventos existentes.
- Estilos e keyframes do antigo fundo de autenticação, cujas classes já não aparecem na aplicação. Os estilos da galeria atual, formulários, logo e microimersões foram preservados.
- Dependências diretas sem uso `docx`, `motion` e `autoprefixer`, com atualização do lockfile npm e retirada de 27 pacotes. Nenhuma versão dos pacotes mantidos foi alterada.

As verificações idênticas de roles do backend passaram a reutilizar `security/accessControl.ts`. Nenhuma condição de autorização foi alterada.

Redução líquida aproximada: 2.200 linhas nos diretórios de código. O CSS de produção passou de 284,24 kB para 275,14 kB. Não se atribui ganho relevante de JavaScript à remoção dos componentes antigos: o bundler já não os incluía na entrada atual.

## Prevenção e validação

- `npm run lint`: aprovado; este comando executa o typecheck (`tsc --noEmit`). Foram habilitados `noUnusedLocals` e `noUnusedParameters`.
- `npm test`: 42 testes aprovados antes e após a limpeza. Cobrem autenticação, permissões, isolamento de workspaces, persistência, calendário, Analytics, automações, KLIC e CSV.
- `npm run build`: aprovado. Permanece o aviso preexistente do Vite sobre chunk JavaScript acima de 500 kB.
- `git diff --check`: aprovado.
- Navegador: renderização das 16 rotas em ambos os contextos Developer, Pessoal e Corporativo, sem exceções JavaScript ou respostas 5xx locais durante o teste. A sessão criada pelo teste foi encerrada.
- Autenticação: alternância, preservação de preenchimento, validação de e-mail, mesma instância do cenário, movimento reduzido e cinco resoluções de 390 a 2560 px verificados; sem overflow horizontal ou campos cortados.

## Limites preservados

A verificação de rotas é um teste de carregamento, não uma execução de todas as ações comerciais. Não foram realizadas publicações, cobranças, envios externos ou chamadas pagas de IA. Integrações reais dependem das credenciais e serviços configurados. Assets de marca, documentos, banco de dados, dados locais e contratos de API não foram eliminados por falta de imports. O lockfile alternativo do Bun foi preservado, sem declarar validação desse instalador; a instalação validada utiliza npm.
