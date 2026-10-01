# Checkpoint de validação UGC — 30/08/2026

## Resultado

O plano dos dez anúncios foi detalhado e as copies experimentais foram criticadas. O critério de
aprovação por média foi substituído por requisitos obrigatórios. Nenhum anúncio final UGC está
aprovado nesta etapa. A meta de CX continua ativa; testes automatizados não substituem CX-0.

Plano: `docs/studios/UGC_CREATIVE_VALIDATION_PLAN_AND_REVIEW_2026-08-30.md`.

## Evidências de conteúdo

- Lotes v1/v2: 20 kits existentes, cada um com planejamento, PNG, ZIP de cinco páginas, animatic e manifesto.
- Auditoria offline `artifacts/validation/ugc-ad-acceptance/audit-20260830-verified/`: integridade
  20/20; aprovação no pré-check estrito 0/20. Inclui JSON, revisão legível e snapshot do avaliador.
- Hash do avaliador: `5d7922f9d429e4bc53b84642837bf5f42c2f1ad3aa3c93a46042649e029c230d`.
- Digest do corpus congelado: `c75d4adaefcf21e05247166081085cb6ee6b0e456bafc0565524b3d5a9b44040`.
- Diagnóstico v3: dois casos gerados pelo Qwen local, ambos reprovados. Corrigida a divergência
  entre roteiro e falas, ainda sem duração/completude satisfatórias.
- Retry real do café com feedback: reprovado antes do render porque CTA e cinco direções visuais
  excederam o contrato. O runner preservou o relatório-fonte, criou um novo relatório e reavaliou
  os nove casos herdados. Auditoria `audit-20260830-retry/`: 9/10 kits íntegros, 0/10 no pré-check;
  o décimo kit não existe porque a revisão falhou fechada. Nenhum resultado antigo foi sobrescrito.
- Inspeção visual de um PNG v3: texto legível e marcador explícito de inferência pendente, mas CTA
  contém instrução interna de revisão. Layout de teste, não direção de arte de campanha aprovada.
- Sem inferência de imagem, rosto, voz clonada ou lip-sync. Sem publicação ou mudança na VPS.

## Regressão executada nesta etapa

| Checagem | Resultado | Escopo/limite |
|---|---|---|
| Pytest: UGC, provider, contratos de inteligência e corpus sintético | 34 aprovados | `tests-20260830.xml` |
| Pytest: decodificação sem corte e saída truncada | 2 aprovados | `decoding-tests-20260830.xml` |
| Pytest: feedback e retry imutável/reavaliação | 2 aprovados | `revision-tests-20260830-latest.xml` |
| Ruff dos seis arquivos focados | Aprovado | Sem afirmar lint global do worktree |
| `npm run lint` | Aprovado | TypeScript |
| `npm run test:cx-contracts` | 6/6 | Contratos de navegação/ação |
| `npm run audit:cx-strict` | Aprovado | 362/362 controles executáveis cobertos |
| `npm run build` | Aprovado | Warning de chunk maior que 500 kB permanece |
| Playwright: Studio, Presenter, Image Lab e Video Studio autenticados | 4/4 | Quatro cenários selecionados, não a suíte inteira |

Os três segmentos Pytest totalizam 38 testes distintos; não constituem uma execução monolítica.
Os XMLs estão em `artifacts/validation/ugc-ad-acceptance/`. Permanecem dois warnings preexistentes
de campos `copy` no Pydantic. A suíte de 27 E2E e os seis checks axe registrados em 29/08 são
evidência histórica, não nova execução nesta etapa.

Auditoria de rotas atual: 45 registros, 59 URLs, zero conflitos/órfãs; 753 controles, 672 wired,
7 submits, 74 desabilitados com motivo. Sem desabilitados sem motivo no inventário automatizado.
Esses números não provam que toda tarefa seja fácil para uma pessoa real.

## Limites e próximo corte

1. Encurtar a saída da revisão e retestá-la no modelo real, sem afrouxar o contrato nem aceitar
   oferta inventada ou texto truncado.
2. Percorrer o corpus no fluxo autenticado com save, job, derivação, revisão e recuperação de falhas.
3. Executar geração audiovisual somente com providers e gates de licença/hardware/consentimento aprovados.
4. Coletar CX-0 com dez participantes reais e avaliação assistiva/manual; não simular essa evidência.

Voicebox fica adiado por orientação expressa do usuário: sem clonagem, instalação ou mudança de
prioridade. As alegações de 23 idiomas e equivalência a outras ferramentas ainda não foram verificadas.
Figma reconectado, mas nenhuma mudança nesta etapa; qualquer edição futura será exclusivamente por MCP.
