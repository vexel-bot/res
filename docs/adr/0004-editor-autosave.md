# ADR 0004 — Documento criativo e autosave

Status: aceito em 2026-08-15.

## Decisão

Visual, carrossel e vídeo são modos de um documento criativo compartilhado. Alterações locais são agrupadas e salvas com debounce; salvamento explícito e exportação continuam disponíveis. A versão do documento é enviada nas mutações para permitir detecção de conflito.

## Consequências

- Tipografia, elementos, efeitos e motion são painéis, não aplicações separadas.
- Focus Mode muda apenas o shell.
- Reduced motion remove deslocamentos sem ocultar conteúdo ou estado.

