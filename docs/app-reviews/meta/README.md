# Meta — Facebook e Instagram

- **Função demonstrada:** conectar Páginas administradas e contas profissionais do Instagram, ler metadados/insights e publicar somente nos formatos implementados.
- **Scopes:** `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `pages_manage_engagement`, `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`, `instagram_manage_comments`.
- **Justificativa:** cada scope corresponde, respectivamente, à descoberta do recurso, leitura operacional, publicação, gestão de interação e recursos equivalentes da conta profissional. Remova do pedido qualquer scope cuja tela não possa ser demonstrada.
- **Callback:** `${PUBLIC_APP_URL}/api/integrations/oauth/callback`.
- **Reviewer:** entrar com usuário de teste autorizado, abrir Contas Conectadas, conectar Facebook/Instagram, selecionar a Página/conta, confirmar status, executar a capability aprovada e desconectar.
- **Pendente externo:** Business/domínio verificados, URLs públicas, usuários de teste, Data Use Checkup e App Review. O envio final pode exigir declaração empresarial humana.
