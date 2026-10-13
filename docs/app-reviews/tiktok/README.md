# TikTok

- **Função demonstrada:** conectar perfil, consultar dados básicos e iniciar Direct Post de vídeo por URL somente quando a auditoria/capability permitir.
- **Scopes:** `user.info.basic`, `video.list`, `video.publish`.
- **Callback:** `${PUBLIC_APP_URL}/api/integrations/oauth/callback`.
- **Reviewer:** conectar conta de teste, mostrar as opções de privacidade retornadas por `creator_info/query`, realizar publicação marcada como teste no modo aprovado e desconectar.
- **Pendente externo:** verificação da conta, app, Login Kit, Content Posting API, domínio/prefixo de mídia e auditoria do Direct Post.
