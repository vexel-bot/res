# ADR 0002 — Estado de servidor e fronteira da API

Status: aceito em 2026-08-15.

## Decisão

O Express permanece como host do frontend e proxy local para a API FastAPI. Requisições funcionais usam `/api/v1`, token bearer e `X-Correlation-ID`. O estado local atual é preservado como compatibilidade durante a migração; métricas ausentes são apresentadas como ausentes, nunca estimadas.

## Consequências

- O navegador não precisa conhecer a porta da API.
- Autenticação, isolamento por workspace e validação continuam no backend.
- A migração de cada módulo pode ocorrer por fatias sem destruir os dados locais existentes.

