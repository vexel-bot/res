# Clicko · Etapa 2: integração dos agentes e experiência audiovisual

> Revisão posterior: consulte o [parecer atualizado de conclusão](STAGE2_COMPLETION_REVIEW_2026-10-22.md).
> Ele registra falhas encontradas/corrigidas e novas verificações. As contagens e
> evidências deste documento abaixo pertencem à rodada original.

Data: **22/10/2026**. Checkout: `C:\Users\pedro\Downloads\res`.
Esta entrega é um incremento sobre a produção local anterior, não uma reconstrução.
**R$ 0 em serviços externos; nenhuma inferência generativa foi executada.**
Sem novos pacotes, pesos, credenciais, migração destrutiva, alteração de dados reais,
deploy, commit ou push. A árvore já continha muitas alterações de etapas anteriores;
não se atribui todo o diff a esta implementação.

## 1. Verificação do ponto de partida

Foram relidos o pedido, o relatório multiagente de 22/10 e a implementação real.
Os relatórios de infraestrutura de 20/21 continuam como referência histórica; não
substituem os ensaios novos. Hardware e artefatos foram verificados novamente.

| Item esperado | Estado efetivamente encontrado | Tratamento nesta etapa |
| --- | --- | --- |
| KLIC única, Gemini e voz | Fluxos presentes; perfil local bloqueia chamadas pagas | Preservados; novas intenções e seleção chegam ao caminho local |
| Agentes audiovisual/visual | Classes e regras operacionais, não modelos autônomos | Reutilizados, com edição contextual e mais operações verificáveis |
| Orquestração | Planos, revisão, aplicação, recibo e delegação de formas já reais | Mais metadados/histórico e consulta individual de tarefa |
| Modelos gratuitos | Nenhum runtime/peso instalado; Free Tier não comprovado | Nenhum instalado/chamado; Ollama configurável continua preparado |
| Motion editável | Três cenas-modelo, nove camadas, keyframes e MP4 | Revelação por palavra, acabamento, controles e comandos ampliados |
| Imagem/vídeo | Pillow e FFmpeg operacionais; editor canônico existente | Reutilização de materiais no painel e ensaio entre módulos |
| Craft | Artefatos nativos/WASM ausentes nos três motores | Não anunciados como operacionais nem substituídos |
| Interface | Painéis integrados, mas sem homologação autenticada completa | Novos controles compilados; o navegador ainda exige sessão legítima |

`scripts/agents/audit-environment.ps1` foi corrigido para executar também no
Windows PowerShell legado: aspas do Python e WSL não instalado não abortam o
levantamento. Evidência: `.codex-runtime/step2-hardware.json`.

Windows 11 Home, i7-12650H, aproximadamente **7,71 GiB de RAM visível**, cerca de
1,62 GiB livre na nova medição, Intel UHD integrada, aproximadamente 199 GiB livres.
O valor CIM de 1 GiB não comprova VRAM dedicada. Node 24.15.0, Python 3.12.14,
Pillow 12.3.0, NumPy 2.4.4 e FFmpeg privado disponíveis. Ollama/llama-server,
Torch/DirectML/Diffusers/Transformers, Rust e Docker continuam indisponíveis; WSL
não tem distribuição funcional. Nenhuma recomendação anterior de modelo foi
convertida em alegação de desempenho comprovado.

O preflight Craft foi reexecutado: PhotoCraft, FilmCraft e EffectCraft retornam
`blocked-missing-build`; sem artefatos nativos/browser e sem Docker Linux.
O código de saída 2 do preflight registra esse bloqueio, não aprovação.
Evidência: `.codex-runtime/step2-craft.json`.

## 2. Arquitetura final e comunicação

```text
Conversa KLIC existente + contexto de documento/camada
             |
             v
Roteador Express → permissões → JWT da ponte Studios
             |
             v
Tarefa durável de planejamento → AudiovisualAgent / ImageAgent
             |                         |
             |          formas editáveis solicitadas pelo audiovisual
             v
Plano estruturado → revisão humana → validação → aplicação otimista
             |
             v
CreativeDocument + versões + assets privados → Pillow / FFmpeg → PNG / MP4
```

Continua existindo **uma única conversa**, não três chats. A KLIC apresenta o
plano e o link do projeto. A aplicação exige revisão no Studio; não há loop de
agentes nem publicação automática de operações vindas de modelos.

O contrato `AgentTaskRequest` aceita `selectedLayerIds` (até 24, sem duplicação),
valida pertencimento ao documento e vincula o pedido à revisão esperada. O
contexto vai do painel à conversa e à chamada do backend, sem compartilhar dados
de outros workspaces. Chaves de replay de pedidos antigos sem seleção continuam
com o mesmo fingerprint. Operações arbitrárias/shell continuam recusadas.

Cada tarefa agora expõe ID, projeto/workspace, responsável, instrução, papel,
seleção, provedor/modelo, datas, resultado/erro, custo externo zero, limites,
eventos de início/delegação/conclusão/cancelamento e revisão aplicada. O recibo de
aplicação existente é a autoridade: não se altera o resultado do plano para
inventar outra execução. Consulta individual:

`GET /api/v1/studios/v1/documents/{documentId}/agent-tasks/{taskId}`.

Permanecem: escopo autenticado, bloqueio de camada/trilha/clipe, validação de
asset/checksum/direito, snapshot, revisão otimista, invalidação de aprovação,
limites operacionais e admissão financeira existente. Planejamento tem uma
tentativa admitida e não é executável como job de mídia.

## 3. Modelos realmente utilizados

**Nenhum modelo de linguagem, imagem ou vídeo inferiu nesta entrega.**

Os especialistas usam `clicko.local-tools`, com `inference: none` e
`planning: deterministic_rules`. Isso produz planos de um subconjunto conhecido,
não interpretação criativa livre. A configuração separada por papel e o
adaptador Ollama da etapa anterior continuam disponíveis para pesos locais
efetivamente instalados; não houve download nem fallback pago.

Gemini conversacional/voz não foi substituído. Sua gratuidade não foi presumida,
e sua operação remota não foi homologada nesta etapa de orçamento zero.
Os testes de contrato com saída LLM simulada continuam separados da mídia real.

## 4. Motion Design e comandos disponíveis

Criação por regras: solicitação textual → até três cenas → cartões, destaques,
títulos independentes → composição/timeline canônica. O exemplo de 15 s foi
executado com três cenas, texto, gradiente, entrada/saída e keyframes.

Novidades verificáveis:

- Revelação **palavra por palavra**, sem destruir a camada de texto. Layout das
  palavras é fixo; Canvas, still Pillow e máscara FFmpeg respeitam o intervalo.
- Limite explícito de 32 palavras por camada em revelação, com duração validada.
- Fonte do sistema regular/negrito; sem download de fontes. A projeção para o
  canvas legado converte 400/700 para seus rótulos normal/bold sem mudar o original.
- Alterações por camada selecionada ou primeira/segunda/terceira cena.
- Cor hexadecimal ou cores nomeadas da marca para textos/cartões; sombra 2D.
- Transição suave por opacidade, dinamismo com escala/rotação e movimento X.
- Alterar duração retima keyframes, cenas e intervalo da revelação de texto.
- Escolha de cena na interface, duplicação independente e controles de
  propriedade/quadro/valor/easing/remoção/adição de keyframes.

Exemplos aceitos:

1. Selecione um título: “Faça o texto aparecer palavra por palavra”.
2. “Deixe a primeira cena mais dinâmica”.
3. “Adicione uma transição suave na primeira cena”.
4. “Mude a cor dos cartões para coral”.
5. Selecione um título: “Troque a fonte para regular do sistema”.
6. “Mude a duração para 20 segundos”, em motion sem mídia que precise de trim.

Pedido singular ambíguo solicita seleção/cena em vez de escolher um alvo ao acaso.
“Mais moderno” não tem interpretação livre comprovada. Fontes externas,
perspectiva/câmera 3D, gráficos avançados e efeitos Craft não foram anunciados.
Sombras/rotação/escala são **2D**, não cartões tridimensionais reais.

Na inspeção do still foi identificado e corrigido um defeito de linha de base:
desenhar cada palavra pelo topo da tinta deixava palavras curtas elevadas.
Agora compartilham a linha de base; há teste específico e novos renders após a correção.

## 5. Projetos editáveis e interface

Mesmo formato `CreativeDocumentV1`/`CreativeCompositionV1` e estilo local
`studio.local-layer.v1`, com campos opcionais retrocompatíveis. Nada é convertido
destrutivamente para MP4. Texto, propriedades, animação e referências continuam
no documento; as entregas são assets separados.

O painel existente tem seleção por camada/prévia, posição/tamanho/cor/tempo,
ordem, duplicação/exclusão, undo/redo de rascunho, salvar/reabrir/restaurar versão,
monitor/timeline, histórico e exportação. Foram acrescentados controles de
alinhamento, peso, gradiente, sombra, revelação e keyframes. Hit-test da prévia
agora inverte rotação/escala para não selecionar a caixa antiga.

Os menus/tokens/fontes compartilhados foram reutilizados. Os novos controles
reorganizam colunas em telas estreitas; não há novas fontes nem identidade visual.
O assistente KLIC existente continua acessível sem criar outro histórico.
Salve alterações locais antes de aplicar um plano ou abrir a montagem canônica.

**Homologação visual autenticada pendente:** a rota real
`http://127.0.0.1:3018/studios/video/motion` foi aberta pelo navegador e mostrou
“Acesse sua conta”. Não foram criados conta, licença, cookie ou bypass para
prosseguir. Build/tipagem e contratos não equivalem a validar toda a UI em
desktop/mobile e temas claro/escuro. A inspeção de mídia descrita abaixo é separada.

## 6. Integrações de vídeo e imagem

Vídeo mantém trim/cortes, timeline e mídia/áudio do editor canônico, overlays,
legendas de texto fornecido, keyframes, fades, job/cancelamento e MP4 H.264/AAC.
Os novos comandos alimentam o mesmo compilador. Montagem não é descrita como
geração de cenas cinematográficas inéditas; esta segue indisponível sem gerador.

Imagem mantém crop, redimensionamento de camada, brilho/contraste/saturação,
texto/formas, rotação/opacidade, composição, histórico e PNG local. Novo painel
de biblioteca reutiliza assets do mesmo ambiente nos Studios. Importar salva
uma única revisão antes da inserção, preservando a referência original.

Um teste real cria/exporta um cartão no Image Studio, anexa o PNG ao motion pelo
mesmo armazenamento privado e verifica os mesmos bytes do original. Direitos,
checksum e isolamento continuam no servidor. Modelos de geração de imagem e
remoção automática de fundo permanecem indisponíveis de maneira explícita.

## 7. Aceitação de ponta a ponta

`scripts/agents/stage2-live.ts` inicia um roteador KLIC/ponte Express transitório,
usando a configuração de governança própria de testes e **o backend real** do
perfil isolado `dev:local`. O fixture não é a sessão/licença comercial do navegador.
Não modifica a governança de clientes. Seu fallback de modelo é uma sentinela
que falha e conta chamadas, não uma resposta simulada usada para criar mídia.

O cenário solicitado foi executado:

1. Mensagem de 15 s sobre tecnologia/inovação entra na conversa KLIC real.
2. Roteador chama o backend por JWT; audiovisual solicita seis formas ao visual.
3. Plano por regras é revisado/aplicado: três cenas, nove camadas, 360 quadros/24 FPS.
4. Edição QA explícita reduz o projeto para **640×360**, sem achatar camadas,
   para reduzir o tempo de renderização nesta máquina. Não se promete desempenho em 4K.
5. Nova conversa/comando ativa texto por palavras e dinamismo da primeira cena.
6. Still real, job e exportação MP4 v1.
7. Comando troca a cor somente do título selecionado; os outros oito elementos
   são comparados e permanecem idênticos.
8. Segundo job/MP4 v2; v1 continua disponível byte a byte.
9. Cinco snapshots anteriores e documento na **revisão 6**.
10. Serviço reiniciado; `stage2-verify.py` recupera documento e ambos os MP4s,
    confere hashes, duração, codec/dimensões e decode integral sem erro.

Entregas em `.codex-runtime/step2-validation/`:

| Arquivo | Verificação |
| --- | --- |
| `motion-v1.mp4` | 15 s, 640×360, H.264/AAC; SHA-256 `634e6e7cfa299a924c2c27dc1313a9d939490ae315728375a3ad43ad599a094a` |
| `motion-v2.mp4` | 15 s, 640×360, H.264/AAC; SHA-256 `2411dcb4ac23beba91443701220dac0edeb599d6f0b6d3a0b98503679a89d045` |
| `document-v1.json`, `document-v2.json` | Camadas, cenas, keyframes e estado do projeto, não vídeo fechado |
| `klic-creation.json`, `evidence.json` | Conversa, plano, delegação, tarefas/jobs e histórico real de QA |
| `verification.json` | Hashes, decode e persistência após reinício |
| `rendered-frame.png` | Frame extraído do MP4, não substituto da exportação |
| `browser-playback.png` | Reprodução no player de QA, não imagem do editor autenticado |

No navegador, o arquivo final chegou a `currentTime=15`, `duration=15`,
`ended=true`, `readyState=4`, 640×360 e nenhum erro de mídia. Leitura real salva
em `browser-evidence.json`. O player de QA foi usado só para esse ensaio, sem
sessão falsa nem apresentação como interface dos Studios.

Uma rodada anterior também renderizou duas versões em 1280×720; os arquivos de
entrega acima pertencem à rodada final menor, após a correção da linha de base.
O render CPU em 720p foi mais lento; nenhum benchmark de GPU/tempo real foi alegado.

## 8. Testes e regressões

| Verificação final | Resultado |
| --- | --- |
| Python, onze módulos audiovisuais/financeiros/agentes | **103 aprovados, 0 falhas/erros, 18 pulados** (121 casos) |
| Node/TypeScript | **236 aprovados**, 0 falhas |
| Privacidade Vite, mesma execução npm | **2 aprovados**, 0 falhas |
| Tipagem e build | `npm run lint` / `npm run build` aprovados |
| Python estilo/imports | `ruff check backend/app` e arquivos novos aprovados |

Os 18 pulos seguem a fixture histórica FFmpeg pelo PATH/libx264, ausente neste
ambiente. O FFmpeg privado usa libopenh264; os testes canônicos/novos renders reais
usaram sua descoberta central. Os pulos não foram transformados em aprovações.

Cobertura adicional: tarefa individual/auth/isolamento; seleção inválida;
esclarecimento; alvo restrito; bloqueios; replay; eventos/delegação/aplicação;
retiming dos metadados; layout/revelação/linha de base; compartilhamento de PNG;
duas renderizações; original/versão anterior; duplicação independente e seleção
transformada. Contratos LLM simulados são identificados e não evidenciam inferência.

A suíte global Python não foi reexecutada nem declarada aprovada. Seu resultado
histórico de 21/10 (860 aprovados/292 falhas/113 pulados) permanece uma referência
antiga. Nesta etapa não foram feitas mudanças em fixtures para ocultar falhas.

Logs: `.codex-runtime/step2-core-final.xml/.log`, `step2-node.log`,
`step2-types-final.log`, `step2-build-final.log`, `step2-live-final.log`.

## 9. Arquivos desta etapa

- Contratos: `backend/app/domain/studios/{agents,local_composition}.py`.
- Planejamento/coordenação: `services/studios/{local_agents,local_editing,agent_orchestrator}.py`.
- Render: `providers/studios/{local_composition,timeline_ffmpeg}.py`.
- Projeção retrocompatível: `services/studios/compatibility.py`.
- API: `routers/studio_agents.py`.
- KLIC: `server/klic/localProduction.ts`, contexto em `src/klic/{pageContext,useKlicClient}.ts`.
- UI: `src/studios/local/{LocalProductionStudio,LocalLayerControls,LocalMonitor}.tsx`,
  `localApi.ts`, `localModel.ts`, `local-production.css`.
- Testes: `backend/tests/test_local_agent_stage2.py`, extensão dos dois testes TS locais/KLIC.
- Operação/provas: `scripts/agents/{audit-environment.ps1,stage2-live.ts,stage2-verify.py}`.
- README, CHANGELOG e este relatório.

## 10. Indisponibilidades e próxima etapa

Continuam pendentes: inferência real gratuita/local, benchmark do modelo e
qualidade de interpretação livre, cancelamento real do compute Ollama, Craft
compilado/licenciado/qualificado, geração cinematográfica, segmentação automática,
câmera/perspectiva 3D, gráficos/efeitos avançados e homologação visual completa após
login. Voz Gemini não foi chamada por não haver gratuidade comprovada.

Próxima etapa recomendada: primeiro, ensaiar a UI com **sessão legítima** em ambos
os temas e tamanhos; em seguida liberar RAM e autorizar um runtime/modelo pequeno
com licença/origem verificadas para homologar JSON, qualidade, memória e latência.
Só depois expandir a interpretação dos agentes. A produção local determinística
funciona independentemente desses modelos e não deve ser anunciada como autonomia por IA.

Iniciar: `npm run dev:local`; consultar: `npm run dev:status`; parar:
`npm run dev:stop`. O serviço final permanece em 3018/8018, loopback, dados QA
isolados e provedores pagos desligados. Não há deploy/push.
