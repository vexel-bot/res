# Como manter o cofre

Abra a pasta **Clicko - Desenvolvimento** do repositório como um cofre no Obsidian e comece em [[00 Início]].

1. Quando uma mudança alterar a forma de usar ou operar um fluxo, atualize sua nota no [[Mapa do produto]]. Aponte para o código e para o teste que representa o comportamento.
2. Atualize o [[Roadmap]] com o estado e a evidência. Para uma funcionalidade validada só em desenvolvimento, anote o ambiente.
3. No [[Devlog]], registre **data, mudança, motivo, verificação, commit ou PR e próximo passo**. Faça a atualização junto com o código quando possível.

Guarde no Git as notas Markdown do cofre técnico. O diretório local `.obsidian` guarda preferências do aplicativo. Para apontar para materiais de clientes, use referências de acesso controlado. O cofre audiovisual guarda as notas de direção e os links locais para os vídeos de trabalho.

## Codex e Claude Code

O repositório carrega as mesmas instruções nos dois assistentes. O Codex lê `AGENTS.md`, e o Claude Code usa `CLAUDE.md` para importar esse arquivo. As instruções dizem quando consultar cada cofre e quais aprendizados registrar ao concluir uma tarefa.

O cofre audiovisual costuma estar em `Documents/Clicko - Segundo Cérebro` na pasta pessoal. Se estiver em outro lugar, use a variável local `CLICKO_AUDIOVISUAL_VAULT` para indicar a pasta. A sessão precisa ter acesso a ela. Em uma sessão remota, disponibilize as notas necessárias no ambiente dessa tarefa.

Exemplo. Em um teste de locução, o resultado da comparação entre duas leituras vai ao cofre audiovisual. Se o teste resultar também em uma nova opção de mixagem no Studio, a mudança do produto e sua verificação vão ao cofre técnico.
