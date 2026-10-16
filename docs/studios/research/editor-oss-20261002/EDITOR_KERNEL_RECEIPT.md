# Recibo do incremento de comandos e inspeção

## Comportamento entregue

O endpoint `POST /api/v1/studios/v1/documents/{id}/editor/commands` recebe `EditorCommandV1`. A união permite substituir/inserir keyframe em track de receita existente, mudar pivô de coreografia, mudar pai de rig existente em espaço local ou desfazer o comando que gerou a revisão atual. Lotes são atômicos. O compilador e os validadores existentes admitem os parâmetros; autor e revisão são vinculados no servidor. Nada executa JS/CSS/XML do planejador.

Documento canônico, projeção legada, plano aplicado, grafo e manifesto são persistidos juntos. Comandos usam compare-and-swap mesmo em SQLite. Recibo e direção anterior ficam no ledger existente; não há tabela, migração SQL ou segundo formato de projeto. Replay devolve o mesmo recibo, inclusive após outras revisões. Reuso de chave com payload ou autor diferente conflita. Desfazer produz nova revisão e requer que o comando ainda esteja vinculado à revisão atual; não restaura snapshots sobre edições posteriores.

Parenting preserva x/y locais e pode mudar posição mundial. O pai precisa ser um grupo existente na cena; ciclos são rejeitados. Pivôs só são editáveis nas receitas que efetivamente os executam. Comandos requerem Remotion contextual V2 já aplicado; não convertem projetos ou trocam motores. Versões de execução obsoletas continuam exigindo o fluxo existente de recompilação.

`GET .../editor/inspection?frame=N` retorna o documento e plano reais, tracks authored, valores locais calculados, nós/pais, cenas, intervalos, receitas, histórico e hashes. O Video Studio oferece seleção, frame inteiro, controles, atualização após conflito e render da revisão inspecionada. A seleção permanece após salvar. MP4 no painel só é associado quando sua revisão coincide; geometria mundial, fonte final medida e pixels continuam responsabilidades do renderer. O player HTML pede um tempo; isso não constitui prova de decodificação exata do frame.

## Evidência

- `editor-command-tests.xml`: 15 testes aprovados, sem falhas ou skips: replay histórico, concorrência de pedidos iguais/diferentes, autoridade de workspace, autor, lote inválido sem persistência parcial, target/frame inválido, ciclos, coordenadas locais, easing/hold e undo; inclui duas exportações reais.
- `editor-regression-tests.xml`: 44 testes aprovados nas suítes atuais de receitas nativas, editorial V2, grafo e comandos. Esse recibo foi obtido antes dos últimos ajustes de diagnóstico/proveniência no serviço; a suíte do incremento foi repetida depois.
- `editor-real-render-tests.xml`: duas fixtures aprovadas pela API, comando, job, Remotion e finalização FFmpeg reais, checksum do MP4 e QC. Dispatch Celery fica controlado no teste; renderização e arquivos não são mocks. Quando outro trabalho ocupa a reserva de mídia, o teste aguarda até 120 s; se continuar ocupado, é skip explícito, sem alegar prova.
- `editor-render/shape/evidence.json`: edição do deslocamento inicial para 80 px; pixels dos frames 0/4/14 comprovam início, interpolação e repouso final.
- `editor-render/rig/evidence.json`: lote com keyframe e reparenting de hero para g2. Coordenadas locais (10, 20), pais g0 → g1 → g2; translação base mundial (100, 140). Pixels nos mesmos três frames confirmam aplicação única das transformações.
- Ambos são 15 frames, 320 × 320, 30 fps, sem fala ou asset externo usado. Não medem 1080p, 15 s, realtime ou p95.
- `editor-browser/fixture.json` e `after-browser.json`: API local e workspace isolado, sem mocks. Via UI, keyframe 48 → 64 gerou revisão 3; pivô x 0.5 → 0.25 gerou revisão 4; desfazer gerou revisão 5 com pivô x 0.5 e keyframe 64. Scrub no frame 12 mostrou 4.611 px locais. Capturas não são aprovação estética.

Render antigo não pode receber revisão humana após edição; os testes verificam rejeição antes de qualquer nota sintética ser persistida. Nenhuma avaliação humana real foi preenchida ou capacidade promovida a comercial/render_verified.

## Arquivos de aplicação

`backend/app/domain/studios/editor_commands.py`, `backend/app/services/studios/editor_commands.py`, `backend/app/routers/studio_editor.py`; inclusão aditiva em `backend/app/main.py`. UI em `src/studios/EditorInspectionPanel.tsx` e CSS próprio, montada em `VideoStudio.tsx`. Testes e scripts do incremento são novos. Outros arquivos locais modificados pertencem ao trabalho já existente ou ao outro chat.

## Pendências do objetivo maior

O diagnóstico de picos foi implementado depois deste recibo, com [66 testes finais aprovados](MOTION_DERIVATIVE_RECEIPT.md), cálculo por curva e proteção contra avaliações legadas. Tipografia com fonte final medida; matte arbitrário; estudos de 15 s/1080p e avaliação humana ainda precisam completar os critérios do briefing. Falha previamente reproduzida de OffthreadVideo em trim/speed de vídeo não foi corrigida por este incremento. Nenhuma conclusão de qualidade foi inferida de testes de contrato.

Os clones de pesquisa continuam em `tmp/editor-oss-study-20261002` (~3.7 MiB lógicos). A revisão automática rejeitou a remoção recursiva com `blocked by policy`. A limpeza não foi contornada e não foi declarada concluída.
