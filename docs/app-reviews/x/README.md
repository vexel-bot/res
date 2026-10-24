# X

- **Função demonstrada:** conectar perfil, ler dados públicos e publicar texto conforme o plano da API.
- **Scopes:** `tweet.read`, `tweet.write`, `users.read`, `offline.access`; `media.write` só quando o pipeline oficial de upload estiver disponível.
- **OAuth:** Authorization Code com PKCE S256.
- **Callback:** `${PUBLIC_APP_URL}/api/integrations/oauth/callback`.
- **Reviewer:** autorizar conta de teste, confirmar perfil, publicar texto de teste quando o tier permitir, validar refresh/revogação e desconectar.
- **Pendente externo:** domínio/URLs oficiais e confirmação do plano/quota compatíveis; nenhuma contratação pode ser feita automaticamente.
