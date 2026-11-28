# Estúdio de Vídeo

**Fluxo principal.** O usuário preenche o briefing e envia os materiais. O Claude dirige a edição e pode criar cenas à parte. A Clicko recebe manualmente o plano do Claude, guarda os dados do trabalho e passa ao MoneyPrinterTurbo os clipes preparados para montagem. O resultado fica disponível no projeto para download.

| Etapa | Responsabilidade | Código |
|---|---|---|
| Briefing e materiais | Criar projeto, anexar clipes prontos e faixa de áudio, importar o plano e acompanhar o resultado | [VideoAssemblyStudio.tsx](https://github.com/vexel-bot/res/blob/main/src/studios/video/VideoAssemblyStudio.tsx) |
| Autenticação | Encaminhar a chamada com o contexto autorizado de conta e cliente | [proxy.ts](https://github.com/vexel-bot/res/blob/main/server/studios/proxy.ts) |
| Admissão | Receber `POST /studios/v1/video/documents/{id}/assemblies`, validar a revisão e os materiais, e enviar o trabalho à fila | [studio_video.py](https://github.com/vexel-bot/res/blob/main/backend/app/routers/studio_video.py) · [timeline_editor.py](https://github.com/vexel-bot/res/blob/main/backend/app/services/studios/timeline_editor.py) |
| Montagem | Preparar os clipes na ordem e no enquadramento pedidos, concatenar com MoneyPrinterTurbo e aplicar a mixagem | [moneyprinterturbo.py](https://github.com/vexel-bot/res/blob/main/backend/app/providers/studios/moneyprinterturbo.py) · [Worker de mídia](https://github.com/vexel-bot/res/blob/main/workers/media-cpu/Dockerfile) |
| Entrega e acervo | Registrar a exportação e listar os materiais do projeto. O download passa pelas permissões existentes | [studio_video.py](https://github.com/vexel-bot/res/blob/main/backend/app/routers/studio_video.py) · [assets.py](https://github.com/vexel-bot/res/blob/main/backend/app/routers/assets.py) |

O Claude define a ordem, os intervalos de origem e a duração em quadros a 30 fps. Uma cena com motion chega como clipe pronto. A faixa opcional de áudio contém a mixagem final, com a duração do filme.

## Briefing com repertório audiovisual

Selecione no projeto os conhecimentos de direção pertinentes e baixe `direcao-claude.json`. Os cartões escolhidos entram em `directionNotes`, com técnica, exemplo, verificação e fonte. A seleção vale para aquela exportação do projeto. O arquivo é autocontido para consulta dos cartões pelo Claude. As referências em vídeo ou fichas longas do cofre local podem acompanhar o briefing como anexos.

O arquivo inclui `scriptDirection` com a preparação da pergunta inicial, as evidências por cena e a verificação na primeira exibição. Em **Objetivo do roteiro no briefing**, escolha anúncio de resposta direta, conteúdo explicativo ou história de marca para incluir um exemplo e um ensaio A/B do formato. A opção **Claude define pelo briefing** é a inicial.

Abra **Técnicas práticas de decupagem** e marque os temas do corte. Cada tema selecionado vai em `decoupageNotes`, com exercícios, perguntas de revisão e fontes. O Claude recebe o texto necessário mesmo fora do ambiente local e escolhe como usar o repertório. As seleções de roteiro, direção e decupagem começam vazias quando se abre um projeto.

O Claude devolve as decisões editoriais em texto e a montagem no formato `assembly`. A Clicko aceita o objeto de montagem diretamente ou dentro da propriedade `assembly` de um JSON. O motor usa os IDs, os intervalos em quadros e a mixagem.

Os resumos de roteiro, decupagem e som estão em `scriptDirection.ts`, `decoupageTechniques.ts` e `directionNotes.ts` no diretório do Estúdio de Vídeo. Para ampliar o acervo, atualize as fontes e os ensaios no cofre audiovisual. Registre a evidência no aprendizado de produção.

## Verificação e continuidade

O fluxo local foi validado em navegador e API. Houve teste real do worker em Linux e download de materiais de projeto antigo com as rotas Craft desativadas. A instalação e a validação no ambiente publicado seguem como próximas etapas. Consulte o [[Roadmap]], o [[Devlog]] e o [guia operacional](https://github.com/vexel-bot/res/blob/main/docs/studios/MONEYPRINTERTURBO.md).

Para voz, narração, decupagem, trilha, ambiência e efeitos, consulte o [cofre audiovisual](obsidian://open?vault=Clicko%20-%20Segundo%20C%C3%A9rebro&file=00%20In%C3%ADcio).
