# Pacote de revisão das integrações sociais

Cada pasta contém o roteiro verificável do provider. Antes de enviar uma revisão, substitua somente os campos marcados como pendentes por dados oficiais confirmados. Nunca coloque tokens, client secrets, cookies, chaves privadas ou credenciais pessoais nestes documentos ou em gravações.

Evidências mínimas para todos os providers:

1. página pública `/integrations` e documentos `/privacy`, `/terms`, `/data-deletion`, `/support` em HTTPS;
2. tela Contas Conectadas antes da autorização;
3. redirecionamento para o domínio oficial do provider;
4. consentimento e seleção do recurso;
5. retorno à Clicko com status real;
6. execução da capability solicitada e tratamento de erro/revogação;
7. desconexão sem exposição de credenciais.

O screencast deve ocultar e-mails pessoais, IDs internos desnecessários, cookies, DevTools, URL contendo `code`/`state` e qualquer secret.
