# Checkpoint 36 — qualificação acústica verificável

Data: 31/08/2026. Repositório: `C:\Users\edugu\Downloads\res`.

## Entrega

O gate acústico não aceita mais `benchmarkStatus=passed` e
`workerAdvertised=true` como prova suficiente. A nova cadeia tipa e vincula por
SHA-256 política, corpus privado, bytes de áudio, evidência de direitos,
previsões por caso, provider/modelo, worker, licença, conversão e avaliador.

O verificador relê assets e arquivos de direitos sob uma raiz explícita, bloqueia
path traversal, recompõe as matrizes de fala/música e recalcula falso negativo,
falso positivo e inconclusivos. Métrica declarada diferente da recomputada falha.
Somente resultado `passed` pode receber recibo HMAC; o backend revalida assinatura,
key id, provider, versão, modelo, pesos e digest do recibo na execução e publicação.

Arquivos centrais:

- `backend/app/domain/studios/acoustic_qualification.py`
- `backend/scripts/evaluate_acoustic_qualification.py`
- `benchmarks/studios/acoustic/acoustic-presence-ptbr-policy.v1.json`
- `benchmarks/studios/acoustic/README.md`

## Estado honesto

A política PT-BR está em `draft`. Seus limites são proposta de risco do produto,
não alegação científica. Não existe corpus autorizado, run candidato, worker ou
provider real promovido. O registry continua vazio; YAMNet/VAD segue apenas
pesquisa e a Review Room continua indisponível. Fixtures não qualificam modelo e
os anúncios permanecem 0/10 aprovados.

Não houve voz, música, clonagem, modelo real, migration, VPS, Docker ou Figma.

## Provas

- 28/28 testes backend focados;
- adulteração de bytes, métricas e assinatura bloqueada;
- revogação da promoção revalidada na publicação;
- Ruff, TypeScript e build passaram;
- audit estrito: 443 controles executáveis, zero órfãos/conflitos;
- contratos de experiência: 6/6.

Rollback remove módulo/CLI e os dois campos opcionais de configuração, preservando
eventos históricos inertes. Não restaurar o gate antigo em produção.
