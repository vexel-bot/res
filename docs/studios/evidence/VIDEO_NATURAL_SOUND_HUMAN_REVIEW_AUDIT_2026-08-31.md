# Video Studio — revisão humana do mix fixado

Data: 31/08/2026. Repositório: `C:\Users\edugu\Downloads\res`.
Continua o checkpoint 32 e a vertical de vídeo assistido do plano mestre.

## Resultado

A revisão de vídeo com perfil `natural-foley-only` agora exige que a pessoa
responsável ouça e avalie o MP4 fixado antes de aprová-lo. A escuta não virou uma
tela ou aprovação paralela: ela é salva na mesma transação da decisão criativa.
Solicitar ajustes continua disponível sem concluir os critérios; quando a
avaliação está completa, falhas ou itens inconclusivos também podem acompanhar a
solicitação.

O formulário cobre quatro perguntas explícitas: ausência percebida de fala,
ausência percebida de música, coerência do som natural com a ação e equilíbrio do
mix. Não existe opção de voz, narração, clonagem ou música. A interface deixa claro
que se trata de testemunho humano sobre a escuta, e não de resultado de modelo ou
liberação de direitos.

## Vínculo e integridade

`StudioListeningReviewRecordV1` é um contrato provider-neutral e contém:

- ID da avaliação e da revisão;
- documento e versão;
- asset e SHA-256 do render ouvido;
- SHA-256 canônico do snapshot imutável;
- revisor autenticado e horário do servidor;
- quatro resultados e confirmação de escuta integral;
- resultado agregado `pass` ou `needs_changes`;
- `publicationAdmitted=false` literal.

Antes de aceitar a avaliação, o servidor bloqueia documento e revisão, confirma o
snapshot atual e materializa novamente o asset privado. O hash dos bytes precisa
ser idêntico ao render fixado. O registro e a decisão são gravados juntos no log
de domínio já existente; falha em qualquer parte não deixa aprovação parcial. Uma
edição posterior invalida a revisão pelo mecanismo existente. Uma nova revisão
não herda a escuta anterior.

O endpoint mantém autenticação e isolamento do workspace da revisão. O slice não
cria uma nova matriz de papéis: mantém a política de membros usada pelas decisões
criativas atuais. Refinar `content:approve` em papéis separados continua sendo uma
decisão transversal de produto, não uma permissão inventada só para áudio.

## Gate que permanece fechado

Uma escuta humana positiva **não** abre preflight, pacote ou agendamento do perfil
sem voz. O servidor continua retornando
`studio_publication_natural_sound_evidence_pending`, porque ainda faltam:

- licenças verificadas, não apenas declarações de origem;
- detector de fala qualificado sobre o mix final;
- detector de música qualificado sobre o mix final;
- uma admissão server-owned que reúna essas provas e o registro humano no mesmo
  hash.

Isto evita que um checkbox no documento ou uma aprovação genérica substitua
evidência acústica. O perfil UGC continua com publicação desabilitada.

## UX e estados

O botão de aprovação permanece indisponível até o MP4 passar pela verificação de
hash no browser, a confirmação de escuta estar marcada e os quatro critérios
estarem em `pass`. Uma falha mantém “Solicitar ajustes” disponível. Depois da
decisão, o painel apresenta o resultado e o prefixo do hash, sem permitir editar o
registro histórico.

Conflito de snapshot continua apontando para uma nova revisão. Divergência do MP4
tem mensagem própria, orientando gerar outra prova. Falha/incompletude da escuta
não é apresentada como conflito. Os controles têm Action Contract e alvos de 44
px; em 390 × 844 os campos viram uma coluna, sem overflow horizontal.

## Verificação

- **16/16** testes backend de render/revisão/publicação passaram.
- O backend recusou aprovação sem escuta, hash declarado divergente e bytes do
  render alterados depois do preview; aceitou e devolveu um registro imutável de
  `needs_changes` ligado ao arquivo restaurado.
- Isolamento entre workspaces permaneceu 404.
- E2E autenticado com MP4 e áudio reais passou em **57,8 s**: aprovação começou
  bloqueada, um critério reprovado manteve o bloqueio, quatro passes habilitaram a
  decisão, e reload da API devolveu revisor, versão, hashes e
  `publicationAdmitted=false`.
- O mesmo E2E confirmou que preflight, pacote e agendamento continuaram bloqueados
  após a escuta positiva.
- Axe A/AA não encontrou violações na tela de revisão; 390 × 844 não teve overflow.
  Screenshot: `artifacts/validation/video-review-listening-mobile.png`.
- TypeScript, build de produção, Ruff e `git diff --check` passaram. O build mantém
  o aviso conhecido de chunk JavaScript acima de 500 kB.
- Audit estrito: **432 controles canônicos executáveis**, zero controles sem Action
  Contract, zero URLs órfãs e zero owners conflitantes.

O E2E usa uma fixture técnica e preenche a avaliação apenas para provar o fluxo; não
é uma escuta humana de conteúdo de produção. Portanto os dez anúncios continuam em
**0/10 aprovados para produção**.

## Arquivos, compatibilidade e rollback

Foram ampliados os contratos e o serviço de revisão, extraída a verificação comum
do vídeo fixado, atualizado o OpenAPI tipado e ligado o painel à Review Room. Não
há migration, nova tabela, provider, modelo, dependência, VPS ou Figma. Revisões de
visual/carrossel e vídeos legados sem o perfil acústico mantêm o comportamento
anterior.

Rollback remove o painel, o campo opcional da decisão e a exigência condicional. O
novo tipo de evento pode permanecer no log como histórico inerte; não deve ser
apagado. A verificação extraída continua utilizável pelo fluxo de publicação.

## Próximo corte seguro

Qualificar os detectores no mix final e implementar a admissão acústica server-owned
que combine direitos, detecção e escuta no mesmo hash. Isso ainda depende de corpus
e fontes autorizadas reais. Também faltam take autorizado, sincronismo perceptual e
revisão humana real dos casos UGC. Voicebox e toda voz continuam adiados.

