# ADR-001 — Studios como bounded context no monorepo

**Status:** aceito  
**Data:** 2026-08-23

## Contexto

O produto já possui shell aprovado, autenticação, workspaces, marca, Radar, campanhas, aprovação, publicação e analytics, além de um backend FastAPI funcional. Studios precisa evoluir sem duplicar esses domínios ou provocar uma reescrita das telas.

## Decisão

Criar uma fronteira lógica de Studios dentro do repositório e monólito modular atuais. A migração seguirá strangler:

- contratos versionados entre sistema principal e Studios;
- domínio e casos de uso isolados de framework/provider;
- adapters sobre modelos, rotas e UI atuais;
- rotas canônicas preservadas;
- extração por vertical slice, não por reorganização massiva de pastas.

O sistema principal fornece contexto tipado e continua dono de autenticação, workspace, marca, Radar, campanha, aprovação e publicação. Studios é dono de brief aplicado, documento criativo, composição, versões, render e jobs de criação.

## Alternativas rejeitadas

- Segundo repositório/serviço agora: contratos ainda não estão estáveis e aumentaria custo/duplicação.
- Reescrita completa: risco alto de regressão e perda das capacidades existentes.
- Apenas mover arquivos: não cria ownership, contratos, autorização ou confiabilidade.
- Incorporar uma aplicação open source completa: transfere a arquitetura e UI do produto a um terceiro.

## Consequências

Positivas:

- mantém produto operacional e UX aprovada;
- permite providers substituíveis;
- reduz conflitos de ownership por contrato;
- cria caminho futuro para workers/serviços separados quando justificado.

Custos:

- adapters e dual-read/dual-write temporários;
- coexistência controlada de implementações;
- testes de compatibilidade e rollback obrigatórios.

## Critérios para reconsiderar serviço/repositório separado

- contratos estáveis e versionados;
- deploy/escala de mídia ou GPU independentes;
- requisitos próprios de segurança/infra;
- cadência de release materialmente diferente;
- evidência de que a separação reduz complexidade total.

## Verificação

- testes de import/dependência;
- nenhuma nova entidade de auth/workspace/brand/campaign;
- E2E sistema principal → Studio → review/publicação;
- routes/shell atuais continuam passando.
