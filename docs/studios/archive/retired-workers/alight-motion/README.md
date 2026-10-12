# Worker experimental do Alight Motion

Este diretório oferece a entrada do worker e o contrato de integração. **Não contém um compilador do formato do Alight, driver de interface homologado ou projeto exportado pelo aplicativo.** O motor permanece indisponível até a prova real no aplicativo. Em 02/10/2026 o usuário autorizou também o teste em emulador Android no Windows. Nenhuma compra ou assinatura foi autorizada.

## Consulta e configuração

Na raiz do repositório:

```powershell
python workers/alight-motion/worker.py probe
```

Para expor o experimento ao owner/admin do Studio, configure o backend e reinicie-o:

```dotenv
STUDIO_ALIGHT_MOTION_ENABLED=true
STUDIO_ALIGHT_EXECUTION_MODE=physical_android_ui
STUDIO_ALIGHT_ADB_PATH=adb
STUDIO_ALIGHT_PROFILE_PATH=C:/absolute/path/to/qualified-profile.json
STUDIO_ALIGHT_WORKER_TIMEOUT_SECONDS=900
```

A flag vem desativada. Sem perfil, o painel informa a falta de dispositivo, importação e compilador. A leitura usa `/api/v1/studios/v1/workspaces/{workspaceId}/render-engines`. Flag habilitada não registra um provider sem disponibilidade comprovada.

Sem perfil homologado, o worker também descobre a instalação do pacote fixo `com.alightcreative.motion` quando existe exatamente um Android conectado no ambiente selecionado. O endpoint acima expõe `applicationProbe` com versão e instalador observados, horário e número de ambientes conectados. Ele não expõe a saída integral do ADB nem dados da conta Google. Uma falha de comunicação deixa `installed: null`; pacote ausente e consulta falha são diagnósticos distintos. Vários dispositivos exigem seleção por perfil, sem adivinhar um destino.

No Studio, **Atualizar conexão com Alight** repete a leitura real e atualiza também a disponibilidade usada pelo seletor de edição. `installed: true` não habilita render, não qualifica capacidades e não conta como um job. O usuário precisa concluir consentimentos e permissões diretamente no aplicativo antes da descoberta de composição/importação; o worker não resolve autenticação ou preferências de privacidade.

O perfil de exemplo é deliberadamente inválido para execução. Preencha valores observados no dispositivo, incluindo Android, versão do app, resolução efetiva, idioma e recursos habilitados. Arquivos de driver, calibração e referências devem estar dentro da pasta do perfil, com SHA-256 verificados. Mudança de qualquer arquivo ou versão exige nova homologação.

## Prova antes de escrever o compilador

1. Em Android real dedicado, registrar ambiente, permissões e recursos. Obter o nome do pacote no próprio dispositivo.
2. Criar um projeto mínimo com vídeo, imagem recortada, fonte com caracteres portugueses, texto, máscara, sobreposição e áudio de referência.
3. Exportar uma referência editável. Confirmar por reimportação como materiais e fontes são vinculados. Preservar original e variante como arquivos versionados de referência autorizada.
4. Conferir exportação silenciosa, duração, proporção, resolução, vídeo com fps distintos, trim, velocidade constante, máscara e fontes.
5. Demonstrar mudanças automáticas de texto, material e duração. A exportação manual inicial serve para descoberta; não aprova jobs automáticos.
6. Só então implementar o compilador e seletores do driver. A presença de XML em uma descrição comercial não autoriza inferir o formato. Coordenadas precisam de perfil e teste específicos.

`manifest.json` é transporte interno `studio.alight-transport.v1`, **não um arquivo importável do Alight**. Contém documento, plano executável, receitas, assets/fontes com hashes, saída, job e política de áudio. O código do compilador pertence ao driver instalado pelo operador, nunca ao planejador.

## Interface do driver homologado

O perfil aponta para um módulo Python local, pinado por checksum, com `Driver(worker, profile)`:

- `execute(stage, bundle, root, destination, remaining_seconds, is_cancelled)` executa uma etapa de `validate → compile → transfer → import → export → retrieve → verify`.
- Cada retorno precisa de `confirmed: true`, `observationPath` relativo ao pacote e `observationSha256`. A observação deve registrar o estado efetivamente visto, por exemplo hierarquia UI e captura, com identidade do job e horários. Evidências são copiadas para armazenamento durável.
- `confirm_resume(previous_checkpoint, bundle)` deve verificar o estado atual da interface e o projeto/job. O worker somente reentra no ciclo depois dessa confirmação. Etapas já cumpridas precisam ser idempotentes e reconfirmadas; o driver não pode inferir sucesso pela existência de um arquivo antigo.
- `receipt(bundle, destination)` inclui `jobId`, `packageDigest`, `videoSha256`, `evidenceKind: real_device`, `manualInterventions: []`, `watermarkVerifiedAbsent: true` e evidência de integridade entre jobs. `crossJobIntegrityVerified` só é verdadeiro depois de verificar o projeto exportado, o diretório isolado e a origem do arquivo. Não se deve preencher esse campo só porque os hashes coincidem.
- `cancel()` retorna `true` somente depois de observar a interrupção no dispositivo. Se a confirmação faltar, o dispositivo entra em quarentena.

A calibração pinada registra `evidenceKind`, `automated`, `profileId`, `appVersion`, `compilerVersion`, `driverSha256`, `testedCapabilities`, pelo menos dois arquivos `samples[{path, sha256}]` e os checks `editableImport`, `assetBindings`, `fontBindings`, `textChange`, `assetChange`, `durationChange`, `silentExport`, `basicComposition`, `mixedSourceFpsTrim`, `constantSpeed`, `aspectPreservation`, `maskOverlap`. Todos dependem de execução real auditada. Não preencher com fixtures.

As capacidades básicas são `composition.video`, `composition.image`, `composition.text`, `composition.mask`, `composition.trim`, `composition.constant_speed`. Recursos de receitas são homologados separadamente, conforme a [biblioteca de técnicas](../../docs/studios/ALIGHT_MOTION_TECHNIQUES.md).

Um plano também declara suas capacidades por tipo de camada, componente nativo e efeito: `composition.{kind}`, `native.{component}.v{version}` e `effect.{kind}`. Elas precisam constar da calibração real. Conexão e importação básicas não autorizam executar qualquer componente com uma aproximação.

## Prova autorizada no PC

Use `STUDIO_ALIGHT_EXECUTION_MODE=android_emulator_ui`, ou `python workers/alight-motion/worker.py probe --execution-mode android_emulator_ui`. Esse modo não exige um telefone. A instalação do emulador não homologa o render: o perfil precisa declarar `executionMode: android_emulator_ui`, e a calibração precisa ter `evidenceKind: real_emulator`, com as mesmas verificações, materiais, hashes e amostras de importação editável. Recibos preservam o ambiente executado. Drivers simulados continuam sendo apenas testes de software.

Na edição contextual, o seletor **Motor da nova edição** vincula `renderEngine` à produção e ao plano compilado, sem permitir que a resposta do planejador troque a escolha. Para novas direções experimentais sem motor anterior, o seletor prefere Alight. Projetos anteriores conservam seu vínculo; mudar o seletor exige um novo plano. Indisponibilidade é verificada antes da aquisição/planejamento pagos e de cada retomada.

## Operação, falhas e som

Um bloqueio exclusivo impede jobs simultâneos no mesmo serial. Cada tentativa tem limite de 900 segundos; o processo supervisor também encerra um driver que não respeite esse prazo. Há uma única repetição para `device_disconnected` ou `temporary_io_failure`, após interrupção confirmada e retomada comprovada. Falhas desconhecidas param para auditoria.

Logs ficam em `backend/storage/alight-worker/`: `.worker.log`, checkpoints `.json`, falhas `.failure.json` com causa e horário, observações por job, bloqueios e quarentenas por dispositivo. Um reinício abrupto pode deixar o bloqueio. Antes de recuperação, verificar processo, dispositivo, exportação e journal; não remover a quarentena apenas para fazer o indicador ficar disponível. Recuperações humanas precisam aparecer no registro operacional. Não há comando de recuperação cega.

Cancelamento pelo supervisor mata o processo e coloca o dispositivo em quarentena porque a interrupção física não foi confirmada. O arquivo cancelado não é publicado. O áudio exportado pelo app é recusado: a composição visual silenciosa passa por ffprobe, e o FFmpeg existente aplica as faixas e a normalização uma única vez.

Probe rejeita arquivo parcial, duração, resolução, fps ou codec incorretos. Recibo com outro job, checksum divergente ou ausência de verificação de marca d'água também falha. Geometria de camadas fica `unavailable` enquanto não houver medição; tempos do plano são `declared_plan`, nunca observação de pixels.

## Campanha de qualificação

Endpoints owner/admin sob `/api/v1/studios/v1/workspaces/{workspaceId}/engine-campaigns`: criar/listar campanha; vincular `/cases`; listar `/candidates`; criar/ler `/comparisons`; registrar `/comparisons/{id}/review`; registrar `/trials`; promover `/promote`.

O endpoint existente de render recebe `provider: alight-motion.contextual-v1`, `engineCampaignId` e `engineLanguage`. Job e inscrição na campanha são gravados na mesma transação antes do enqueue. Não é permitido inscrever resultados depois da execução ou trocar o caso depois de iniciar sua coorte. Dez inscrições por linguagem incluem os erros. Alteração do projeto pode invalidar evidência; não apaga falhas.

Promoção exige três estudos com revisão humana 4/5 nos quatro eixos, preferência cega pelo Alight, fidelidade revisada nos dois motores, 30 jobs reais (10 por linguagem), 29 sucessos automáticos, p95 ≤10 minutos, recuperação transitória e integridade demonstradas. Recibos e disponibilidade precisam pertencer ao perfil atual. Novos documentos criados depois da promoção podem optar pelo perfil qualificado via `engineProfile`; projetos existentes mantêm seu vínculo. Não há fallback automático.

Testes com drivers simulados aprovam apenas software e falhas. Não são importação/exportação do Alight nem qualidade visual demonstrada.

## Compilação de descoberta com referência real

`compile_text_reference.py` usa o módulo backend `alight_text_compiler` e a
referência real `references/5.0.273.1028425/text-linear-motion.xml`, cujo SHA-256 é
fixado no código. A referência foi exportada do aplicativo instalado e contém
uma camada de texto com dois keyframes X. O compilador modifica somente título,
texto, duração e intervalo de entrada; preserva fonte, posição, dimensões e
estrutura. Não aceita XML, comandos, curvas ou recursos não demonstrados.

```powershell
python workers/alight-motion/compile_text_reference.py --parameters <parameters.json> --output <pasta-da-prova>
```

O JSON usa `scene_id`, `element_id`, `title`, `text`, `duration_ms` e `entry_ms`.
O recibo vincula esses IDs, parâmetros, digest e checksum do XML. Saída: 540 ×
960, 30 fps, até 15 segundos, sem áudio definido no projeto. A interpretação do
offset de 16 ms nos keyframes é identificada como inferência e deve ser conferida
na reexportação. O módulo não é registrado como compilador homologado do worker,
não substitui o documento ou suas receitas e não concede disponibilidade ao motor.
As capacidades de filmagem, máscara, fonte externa e 1080p continuam pendentes.
