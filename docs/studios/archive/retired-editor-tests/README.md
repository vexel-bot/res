# Testes dos editores retirados

Este diretório preserva os testes específicos dos componentes e renderizadores
substituídos por PhotoCraft, FilmCraft e EffectCraft. Não é parte da coleção de
testes ativos nem um caminho alternativo de execução.

Em `renderer-suites`, os arquivos completos anteriores às alterações foram
preservados. Apenas definições que importavam/chamavam implementações retiradas
foram removidas das suítes ativas; funções compartilhadas de fixtures e testes
de materiais, documentos, isolamento e publicação foram mantidos. O arquivo
`retirement.json` registra a primeira seleção de 76 definições em 28 arquivos.
Também foram arquivados quatro testes do antigo mix FFmpeg e o fluxo antigo de
autosave/versionamento/exportação de canvas, substituído pela verificação de
arquivo legível e edição antiga indisponível.

Os novos testes estão em `backend/tests/test_craft*.py`, `tests/craft`,
`tests/unit/craftState.test.ts`, `workers/craft/tests`, nos adaptadores Rust e nos
scripts de aceitação real. Retirar testes antigos não comprova equivalência de
todas as funcionalidades; as lacunas de validação estão no status da integração.
