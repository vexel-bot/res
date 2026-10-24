# Google / YouTube

- **Função demonstrada:** conectar o canal autorizado e exibir estatísticas oficiais do canal.
- **Scope atual:** `https://www.googleapis.com/auth/youtube.readonly`.
- **API:** YouTube Data API v3. Upload não é solicitado nem anunciado.
- **Callback:** `${PUBLIC_APP_URL}/api/integrations/oauth/callback`.
- **Reviewer:** autorizar com uma conta de teste que possua canal, retornar à Clicko, confirmar o canal e carregar o snapshot real de métricas.
- **Pendente externo:** domínio/branding oficiais, publicação do consent screen e eventual verificação Google. Não misturar credenciais Gemini/KLIC com OAuth do YouTube.
