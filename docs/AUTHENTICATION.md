# Autenticação da Clicko

## Implementado

- Cadastro pessoal com nome, e-mail, senha e aceite obrigatório.
- Senha armazenada somente como hash `scrypt` com salt aleatório.
- Login com erro genérico, limitação de tentativas e opção “Lembrar de mim”.
- Sessão opaca em cookie `HttpOnly`, `SameSite=Strict` e `Secure` em produção. O frontend não lê nem persiste o token.
- Logout revoga a sessão atual; redefinir senha revoga todas as sessões anteriores da identidade.
- Rotas internas e integrações exigem sessão. Headers de workspace/usuário só são aceitos em processos de teste isolados.
- Troca de Perfil/Workspace permitida somente entre associações da identidade autenticada.
- Tokens de verificação e recuperação aleatórios, armazenados como hash, de uso único e com validade.
- Migração assistida: perfis legados podem ser reivindicados somente pelo fluxo de recuperação enviado ao e-mail já registrado.

## Configuração

`AUTH_EMAIL_VERIFICATION_REQUIRED="false"` mantém ativação imediata enquanto não existe entrega transacional. Para exigir confirmação, configure a entrega de e-mail, altere para `true` e use links no formato:

- `/verify-email?token=TOKEN`
- `/reset-password?token=TOKEN`

`AUTH_DEV_EXPOSE_TOKENS="true"` permite testar esses dois fluxos somente no ambiente local: a API devolve o token à própria interface. Nunca habilite essa opção em produção.

## Bypass local de autenticação

`CLICKO_DEV_AUTH_BYPASS="true"` permite abrir a aplicação com um contexto padrão já
existente sem preencher o Login. A configuração só é aceita quando `NODE_ENV` é exatamente
`development`; em teste, preview e produção o fluxo normal continua obrigatório.

`CLICKO_DEV_AUTH_BYPASS_PROFILE="company"` define o contexto inicial Corporativo e
`"personal"` define o Pessoal. Durante o bypass, os dois perfis padrão aparecem no seletor;
a troca é validada no servidor e persistida apenas em cookie `HttpOnly`. Não há parâmetro de
URL, flag `VITE_*`, e-mail ou senha especial. O bypass não cria usuário, conta, role ou
permissão e deve permanecer desabilitado fora do ambiente local.

## Pendência externa

O projeto ainda não possui um provedor de e-mail transacional definido. Por isso o backend não afirma que enviou mensagens. Antes de habilitar verificação obrigatória em produção, conecte o provedor oficial da Clicko, envie os links acima exclusivamente ao destinatário e remova qualquer exposição de tokens de desenvolvimento.

O armazenamento atual é adequado a uma única instância local. Produção deve usar banco transacional, política de retenção, backups e um armazenamento compartilhado/revogável de sessões.

## Documentos jurídicos

A interface exige o aceite e reserva a apresentação dos documentos. Os textos jurídicos definitivos de Termos de Uso e Política de Privacidade precisam ser fornecidos e aprovados pela Clicko; nenhuma cláusula foi inventada no código.

## Validação

`npm test` cobre: rota privada sem sessão, rejeição de headers falsos em runtime, senha fraca, aceite obrigatório, origem cruzada, cadastro, verificação, uso único do token, hash sem senha em claro, recuperação sem enumeração explícita, redefinição, revogação de sessão, login com a nova senha, logout e reivindicação de perfil legado.
