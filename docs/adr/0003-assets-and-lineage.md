# ADR 0003 — Assets, versões e lineage

Status: aceito em 2026-08-15.

## Decisão

Metadados e permissões de assets pertencem ao banco; binários são acessados pelos endpoints de assets e não incorporados ao documento criativo. Conteúdos, campanhas e documentos guardam origem, versão da memória de marca, versões e derivações.

## Consequências

- A Brand Asset Library pode servir editores diferentes sem duplicar arquivos.
- Remix, restauração e exportação preservam a origem auditável.
- Uploads locais e bancos de desenvolvimento permanecem ignorados pelo Git.

