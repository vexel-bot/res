# Avaliação de rostos e vozes na biblioteca

## O que mudou

A biblioteca apresenta a ação **Revisar cadastro** para responsáveis e administradores da marca. Cada versão em preparação tem uma avaliação própria: o responsável examina uma prévia privada, registra correspondência da aparência ou da voz, qualidade e observações. Nenhuma nota numérica de qualidade é inventada pelo formulário.

Versões com capacidade de avatar pedem uma prévia em vídeo para permitir observar o movimento. Vozes aceitam áudio ou vídeo para escuta. A amostra enviada no cadastro, por si só, não comprova a qualidade de uma geração. O formulário permite anexar uma prévia produzida e examinada pelo responsável; ele não executa o modelo nem comprova automaticamente a origem da prévia.

A avaliação e a decisão sobre a versão são etapas separadas. Aprovar requer uma avaliação recente aprovada, comentário e confirmação explícita do responsável. Uma avaliação recente com pendências impede usar uma aprovação anterior. As avaliações registradas podem ser consultadas após fechar e reabrir a página; suas prévias são carregadas pela rota autenticada quando solicitadas.

O servidor mantém a decisão de autorização. Usuários sem o papel necessário não podem registrar avaliações nem aprovar versões. A aprovação confere novamente a autorização vigente e se todas as prévias da avaliação continuam disponíveis na marca. Excluir uma prévia após a avaliação impede aprovar a versão com aquela evidência.

## O que essa aprovação significa

A versão aprovada pode ser escolhida no pedido dos Studios, sujeita às autorizações atuais. Essa decisão não instala, aprova ou habilita um provedor generativo. A geração com LongCat e os candidatos de clonagem de voz continua dependente da qualificação real de inferência, recursos e qualidade. Nenhuma versão de pessoa ou voz real foi aprovada automaticamente nesta implementação.

## Verificações

- 13 testes direcionados de backend: cadastro, permissões, avaliação, autorização, aprovação e bloqueio após remoção da prévia.
- 2 testes de interface: registro e retomada de avaliação de voz; aprovação explícita separada; bloqueio quando a avaliação mais recente de aparência está com pendências.
- Os testes de interface usam catálogo, mídia e decisões simulados. Não demonstram clonagem de voz, fidelidade facial, sincronismo labial ou qualidade do modelo.
- O build de produção passou; as permissões e a entrada deste documento foram conferidas pela sessão real do localhost reiniciado.

## Fontes da implementação

- src/studios/identity/IdentityReview.tsx
- src/studios/identity/IdentityLibrary.tsx
- backend/app/routers/studio_identity_library.py
- backend/app/services/studios/identity.py
- backend/tests/test_studio_identity_library.py
- backend/tests/test_identity_activation_gate.py
- tests/team-sync/identity-review.spec.ts

## Prontidão do localhost

O reinício nesta etapa revelou que o inicializador interrompia cada sondagem após um segundo. A rota de prontidão verifica dependências e a sessão do bridge, podendo precisar de mais tempo em uma inicialização fria. O inicializador agora compartilha uma única requisição em andamento, aguarda até 15 segundos por sondagem e conserva o prazo total de inicialização. O comando de status aguarda o mesmo orçamento, sem encerrar silenciosamente antes da resposta.

Passaram cinco testes do controle e da sondagem, incluindo resposta demorada, ausência do serviço, timeout explícito, tentativas sem sobreposição e rejeição de uma resposta HTTP 200 que não declare prontidão. O ambiente reiniciado respondeu `ready` com sessão e bridge disponíveis.
