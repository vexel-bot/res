# Auditoria Clicko — 05/09/2026

## Estado

**Em andamento. Não certificada como 100% funcional ou pronta para produção.**
Esta etapa contém correções de código e testes de regressão. Inspeção estática não equivale a validação visual, execução em dispositivos ou integração externa ponta a ponta.

Imagem e Vídeo foram excluídos das mudanças: componentes, rotas, geração, edição e fluxos permanecem preservados. Nenhuma alteração em CSS, cores, tipografia ou dimensões nesta etapa. As alterações preexistentes no repositório foram preservadas.

## Correções desta etapa

- Governança: requisições antigas não substituem a sessão de uma conta selecionada depois; dados são publicados após a carga completa e filtrados pelo workspace. Respostas de mutações de uma conta anterior não atualizam a conta atual.
- Navegação dos módulos auditados: não abre módulos protegidos enquanto a sessão está carregando ou indisponível. O comportamento das rotas de Imagem/Vídeo foi mantido fora dessa alteração.
- Contas: contas removidas do seletor não são recriadas automaticamente a partir dos exemplos na próxima abertura.
- API de governança: ausência de identidade não assume mais o administrador padrão; registro público não adiciona outro administrador a um workspace existente. A identificação ainda é baseada em headers, não em uma sessão criptograficamente autenticada.
- Equipe: validação de e-mail, bloqueio de ativação antes de aceitar convite e verificação de assentos na reativação. Feedback de convite não afirma entrega de e-mail inexistente.
- Aprovações: comentários obrigatórios nas ações correspondentes, datas futuras válidas para agendamento, bloqueio de alteração de estado de conteúdo publicado, prevenção de envios simultâneos no painel, seleção consistente com o filtro.
- Calendário: navegação de meses sem saltar fevereiro em datas como 31/01; validação de data e horário antes de serializar; espera por aprovação sem anunciar sucesso quando a API falha; prevenção de duplo salvamento; respostas de planejamento de outro workspace são ignoradas.
- Biblioteca: detalhe acompanha os resultados filtrados; upload iniciado em outro workspace não grava arquivos no ambiente atual; seleção e confirmação de exclusão são limpas na troca de contexto.
- KLIC: cancelamento/invalidação de resposta ao trocar workspace ou limpar histórico; bloqueio de envios simultâneos; memória de aprovação filtrada por workspace; falha de armazenamento não derruba o chat.
- Radar: a resposta mais recente prevalece, com proteção de contexto/região e descarte após desmontagem.
- Analytics: proteção contra sincronização atrasada de outro workspace; análises antigas não alteram o estado da nova consulta; resposta sem métricas não apaga o último snapshot; demonstração reinicia desligada após troca de workspace.
- Conexões: endpoints exigem associação ao workspace; autorização/desconexão exigem administrador; sincronização aceita administrador ou acesso a Analytics; tokens expirados são recusados; falha de desconexão preserva o estado e apresenta erro; métricas indisponíveis não são anunciadas como métricas obtidas.
- Configurações: preferências principais e de notificações são gravadas em um único registro, evitando salvamento parcial entre duas chaves. Leitura das chaves antigas mantida.
- Busca global: índices a partir de conteúdos, campanhas, clientes, arquivos, aprovações e automações do ambiente atual, com filtro de permissões e retirada dos resultados fixos fictícios.
- Histórico: tratamento de datas inválidas, limpeza de seleção na mudança de contexto e neutralização de fórmulas em CSV exportado.

## Continuação — persistência e calendário

- Governança agora salva usuários, workspaces, assinaturas, aprovações, convites e auditoria em arquivo privado no servidor. As APIs existentes foram preservadas. Não é um banco multi-instância nem uma solução de autenticação.
- Escrita atômica antes da resposta HTTP, inclusive exclusões 204; falha de armazenamento retorna 503 e restaura o estado em memória. Arquivos inválidos são recusados sem sobrescrita; conflitos de escrita são recusados. Há cópia da revisão anterior.
- Diretório padrão excluído do Git e bloqueado no Vite, incluindo backups, locks e temporários. Armazenamento em public/dist é recusado. Testes HTTP verificam o bloqueio sem ler dados reais.
- Calendário em lista filtra o mês selecionado, preservando o acesso aos rascunhos sem data. O indicador de distribuição por canal considera o período em análise, não todo o histórico.
- Arrastar conteúdo com aprovação atualiza a data na API antes de anunciar sucesso. Mantém a etapa de revisão; não aprova nem publica implicitamente. Colaboradores não podem alterar localmente a data de um fluxo controlado pelo administrador. Datas inválidas/passadas em reagendamento são recusadas e requisições antigas não atualizam outro contexto.
- Documentação operacional em `GOVERNANCE-PERSISTENCE.md`. O servidor de prévia iniciado nesta auditoria foi reiniciado com o backend atualizado. O snapshot versão 1 permanece compatível e é convertido para a versão 2 na primeira mutação autenticada.

## Continuação — autenticação

- O redirecionamento simulado do login foi removido. A nova entrada inclui login, cadastro essencial, aceite obrigatório, validação de senha, visualização da senha, “Lembrar de mim”, recuperação, redefinição, verificação opcional e logout.
- Senhas usam `scrypt` com salt; sessões e tokens são aleatórios e persistidos somente como hash. A sessão fica em cookie HTTP-only, SameSite Strict e Secure em produção, sem token acessível ao frontend.
- Rotas privadas recusam acesso sem sessão. Identificadores em headers permanecem habilitados apenas quando `NODE_ENV=test`, nos processos isolados do runner.
- Troca e remoção de perfis validam as associações da identidade autenticada. Cadastro de novo ambiente exige sessão. Perfis legados só podem ser reivindicados pelo fluxo de recuperação associado ao e-mail existente.
- Redefinir a senha revoga sessões anteriores; tokens são de uso único e expiram. Login, cadastro e recuperação possuem limitação local de tentativas.
- O provedor transacional de e-mail ainda não foi definido. A aplicação não afirma que enviou uma mensagem. Verificação obrigatória permanece desligada até essa integração existir; tokens podem ser expostos à UI apenas no desenvolvimento com uma opção explicitamente insegura e bloqueada em produção.
- A interface foi revisada no navegador em 1280×720, sem overflow horizontal, erros ou warnings de console. Os breakpoints de coluna foram inspecionados; QA em dispositivos físicos ainda permanece pendente. Termos e Política aguardam os textos jurídicos oficiais; nenhuma cláusula foi inventada.

## Cobertura e limitações por módulo

| Módulo | Validação realizada | Pendente |
| --- | --- | --- |
| Perfis / Workspace / permissões | Autenticação, sessão, guardas, API, isolamento e persistência local testados | Banco transacional multi-instância, e-mail, QA multiusuário/dispositivos |
| Dashboard / menus / busca | Inspeção de navegação e fontes; busca corrigida | Validação visual e navegação ponta a ponta |
| Clientes / biblioteca da marca | Inspeção de CRUD local, filtros e contexto | Persistência de produção, validação completa de edições e uploads |
| Biblioteca | Correções de seleção/upload e inspeção de CRUD | Cota de armazenamento local, armazenamento de arquivos externo, E2E |
| Calendário | Datas, filtro de período e reagendamento integrado à aprovação testados | Publicador real, retentativas de aprovação, E2E |
| Aprovações / equipe | API e persistência testadas com reinício em processo isolado | E-mail transacional, aceitação de convite e login reais, banco de produção |
| Analytics | Testes de períodos, agregação e indisponibilidade; guardas de requisição | Adaptadores reais de métricas, cobertura visual dos gráficos/exportações |
| Automações | Testes dos seis modelos, parser KLIC e validação | Executor persistente, gatilhos reais, execução de ações/condições/esperas, histórico real de execução |
| KLIC textual / voz | Revisão de chamadas, cancelamento e histórico; leitura do router de voz | Testes reais de provedor, microfone, reprodução e permissão em dispositivos |
| Radar | Revisão de fontes, erro e requisições concorrentes | Teste das fontes externas em produção e revisão visual |
| Conexões | Testes de controle de acesso e revisão OAuth | Conectar contas reais, renovação segura de tokens, coleta real de métricas/publicação |
| Configurações / notificações | Revisão de persistência local e estados de disponibilidade | Aplicação de todas as preferências em seus módulos; entrega e leitura de notificações persistentes |
| Logs / histórico | CSV, filtros e persistência local de governança | Auditoria centralizada, retenção, backups de produção |
| Assinaturas / planos | Inspeção de regras de assentos e atualização de plano | Checkout, faturamento e webhooks reais; não foi efetuada nenhuma cobrança |
| Responsividade / desempenho | Nenhuma mudança de layout; TypeScript validado | QA desktop/tablet/mobile, console, acessibilidade com leitor, perfil de desempenho |
| Imagem / Vídeo | Fora do escopo, arquivos conferidos por hash | Não auditados nem modificados |

## Bloqueadores de produção confirmados no código

1. A autenticação local deixou de ser simulada, porém produção ainda depende de banco transacional/armazenamento compartilhado de sessões, HTTPS, configuração operacional de proxy e provedor oficial de e-mail. A limitação de tentativas é por processo e deve migrar para armazenamento compartilhado antes de escalar horizontalmente.
2. Governança passou a usar arquivo privado persistente, adequado a um servidor local único. Produção ainda precisa de volume durável, backups, controle de acesso do sistema operacional e banco transacional para múltiplas instâncias. Os registros iniciais legados não foram substituídos por dados supostamente reais.
3. `server/integrations.ts` mantém tokens em memória e não possui coleta implementada de métricas; `/sync` devolve explicitamente indisponibilidade. Persistência segura de tokens, refresh, escopos e aprovação dos provedores precisam ser concluídos.
4. Publicação retorna 501: ainda não há publicador implementado. Agendar no calendário não comprova publicação na rede.
5. Automações salvam/validam configuração; não existe executor de gatilhos e ações. Nenhum histórico de execução foi inventado.
6. Convites são registrados, mas não enviados por e-mail; a aceitação não implementa um sistema completo de credenciais.
7. Conteúdos e arquivos dependem de localStorage. Cotas, persistência entre dispositivos e concorrência multiusuário não estão resolvidas. Alguns perfis/contextos iniciais continuam sendo exemplos legados, não métricas verificadas.
8. `/api/capabilities` mede a presença de variáveis de ambiente, não a saúde ou implementação completa de cada serviço. Flags não certificam funcionamento.

## Testes e execução

- `npm run lint`: aprovado (`tsc --noEmit`).
- `npm test`: 36 testes aprovados na continuação, incluindo autenticação completa, rejeição de acesso direto, retomada em outro processo, rollback de escrita, conflito de gravação, arquivo inválido, privacidade HTTP, períodos e reagendamento sem aprovação implícita. O runner compila somente dependências de testes em diretório temporário validado e o remove ao terminar.
- Testes HTTP usam um servidor Express isolado em porta aleatória local; não alteram o servidor ativo, contas conectadas, dados do usuário ou recursos externos.
- `npm run build`: aprovado na continuação, após liberação de acesso. Permanece aviso de bundle principal acima de 500 kB (741,73 kB minificado, 204,21 kB gzip); não se trata de falha de compilação, mas exige análise de desempenho.
- Sem validação visual automatizada nesta etapa; não foram certificados console, acessibilidade ou responsividade em navegadores/dispositivos.
- Não houve envio real de conteúdo, e-mail, cobrança, execução automática, commit ou push.

## Próxima etapa necessária

Resolver identidade/autenticação e persistência de produção, preservando as APIs existentes. Preservar o estado do servidor legado antes de iniciar o backend atualizado. Depois implementar executor/publicador/adaptadores reais, configurar provedores, executar testes ponta a ponta com contas de teste autorizadas e validar visualmente cada módulo. Não tratar esta lista como concluída por testes unitários passarem.
