# Montagem de vídeo com MoneyPrinterTurbo

Na Clicko, abra **Studios → Vídeo → Criar Vídeo** e salve o briefing. Baixe o briefing para o Claude. Ele pode decidir o ritmo, escrever o roteiro, escolher materiais e criar cenas à parte. Envie os clipes prontos e a mixagem final à Clicko, passe os IDs ao Claude e cole o plano devolvido na tela do projeto. O pedido também pode ser enviado pela API autenticada do Studio.

O plano tem formato de tela, uma lista de clipes em ordem e o ID opcional da mixagem. Em cada clipe, `startFrame` é o início no material original e `durationFrames` é o tempo que ele ocupa no filme. Os quadros usam a base de 30 por segundo. A opção `contain` preserva todo o enquadramento e acrescenta barras quando necessário. `cover` preenche a tela pelo centro. Efeitos, transições, tipografia e legendas autorais podem vir incorporados aos clipes. A mixagem deve corresponder à duração do corte. O áudio original dos clipes deve entrar nessa mixagem quando fizer parte da edição.

Projetos antigos aparecem para consulta. O download usa o mesmo armazenamento e as permissões da Clicko. O arquivo histórico dos projetos de imagem está em **Ferramentas adicionais → Projetos anteriores de imagem**.

## Executar

- **Local.** No ambiente Python 3.11 da Clicko, execute `python backend/scripts/provision_moneyprinterturbo.py`. A montagem também requer FFmpeg e ffprobe. Inicie a Clicko pelo perfil local existente.
- **Produção.** Construa `workers/media-cpu/Dockerfile` no contexto do repositório. Substitua o processo que atende a fila `studio.media.cpu` pelo novo worker, valide a montagem e configure `STUDIO_MONEYPRINTERTURBO_WORKER_ENABLED=true` no serviço da API com filas isoladas. O worker já inclui a revisão do MoneyPrinterTurbo. O endpoint autenticado `/api/v1/studios/v1/video/assembly-capability` mostra se a API aceita novos trabalhos.
- **Verificação.** Execute `python -m pytest backend/tests/test_moneyprinterturbo_assembly.py` com `PYTHONPATH=backend`. O teste verifica corte, áudio, reenvio, download e isolamento entre clientes.

O endpoint `POST /api/v1/studios/v1/video/documents/{documentId}/assemblies` recebe `expectedRevision`, `assembly` e o cabeçalho `Idempotency-Key`. A Clicko guarda o plano e os checksums dos materiais antes de encaminhar o trabalho. A montagem usa o concatenador do MoneyPrinterTurbo com os clipes já enquadrados e cortados. Isso preserva os tempos definidos pelo Claude.
