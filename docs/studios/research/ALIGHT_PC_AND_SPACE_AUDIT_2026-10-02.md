# Alight no PC e auditoria de espaço — 02/10/2026

O usuário autorizou trocar a prova exclusivamente em Android físico por uma prova também em emulador Android no Windows. A intenção é usar Alight como motor principal. Essa intenção não constitui evidência de importação, exportação automática ou qualidade visual.

## Espaço recuperado

Auditoria inicial: C: com 1.596.776.448 bytes livres, único disco local encontrado; Windows 11 Home, aproximadamente 8 GB de RAM, Intel i5-12450H, hipervisor presente. Propriedades de virtualização retornadas pelo WMI são inconclusivas sob o hipervisor; não houve mudança de BIOS ou recursos do Windows.

`npm cache clean --force` terminou com código 0. `python -m pip cache purge` terminou com código 0 e informou 358 arquivos removidos. Depois dos comandos, o disco tinha 16.339.730.432 bytes livres: aumento observado de 14.742.953.984 bytes, aproximadamente 14,7 GB decimais. A medida é diferença de espaço do volume, não soma exata dos arquivos apagados; processos em execução também podem alterar o disco.

Recibo: `output/space-cleanup-20261002/cleanup-receipt.json`. O tamanho anterior de caches foi auditado antes da exclusão. Projetos, modelos locais, bancos, mídia, histórico do Codex e downloads pessoais foram preservados. A exclusão recursiva em lote dos caches de navegador foi rejeitada pela revisão automática com `blocked by policy`, sem razão detalhada, e não foi executada. Não houve limpeza de perfis do navegador.

Pontos grandes mantidos: Chrome completo aproximadamente 16,7 GB, res aproximadamente 23,5 GB, `.candidate-build` aproximadamente 8,1 GB. A inspeção mostrou pesos de modelos e evidência de licenças/dependências dentro do suposto build; por isso não foi tratado como descartável.

## Plataforma e instalação

A [documentação oficial do Alight](https://support.alightmotion.com/hc/en-us/articles/10537455340177-Minimum-requirements-to-install-Alight-Motion) não oferece suporte nativo a Windows. A [página do BlueStacks para Alight](https://www.bluestacks.com/pt-br/apps/video-players/alight-motion-on-pc.html) orienta instalar a versão Android pela Google Play no emulador. O [requisito mínimo do BlueStacks 5](https://support.bluestacks.com/hc/en-us/articles/360056129211-System-requirements-for-BlueStacks-5) é 5 GB livres e 4 GB de RAM; há [suporte a Hyper-V](https://support.bluestacks.com/hc/en-us/articles/4415238471053-System-requirements-for-BlueStacks-5-on-Hyper-V-enabled-Windows-10-and-11).

Pacote consultado: `BlueStack.BlueStacks`, versão 5.22.166.1003, instalador oficial `ak-build.bluestacks.com`, tamanho observado por HTTP HEAD 3.736.512.576 bytes, SHA256 esperado `dbe8b99d3d06f520865d7add1c8651b4841d55bef07fb04c9f2d025263adcab7`, conforme [manifesto do winget](https://github.com/microsoft/winget-pkgs/blob/master/manifests/b/BlueStack/BlueStacks/5.22.166.1003/BlueStack.BlueStacks.installer.yaml).

A primeira tentativa pelo winget ficou sem progresso no DeliveryOptimization: log apontou download iniciado e arquivo temporário de zero bytes. O processo desta tentativa foi encerrado após verificar seu PID e linha de comando. O servidor respondeu HTTP 200; foi iniciada transferência direta do mesmo instalador oficial. Download, assinatura e instalação são etapas distintas e precisam de confirmação própria. Não contar o início do download como instalação concluída.

## Integração

- `renderEngine` no contrato de produção preserva serialização antiga quando `current`; a escolha explícita é aplicada ao resultado do planejador antes de compilar e calcular hashes.
- Produção verifica flag, owner/admin e disponibilidade antes de reservar orçamento ou iniciar planejamento; retomadas e render repetem a verificação. Divergência entre plano e motor gera erro, sem fallback.
- Studio apresenta seletor e pendências, prefere Alight apenas em novas direções experimentais sem motor anterior, e exige novo plano quando a escolha diverge do plano atual.
- Worker aceita `android_emulator_ui` explicitamente. Perfil, calibração e recibo diferenciam `real_emulator` de `real_device`; o padrão físico continua compatível.
- Emulador exige vendor, versão, caminho absoluto/hash do binário e hardware Android observados, vinculados à calibração. Mudança desses vínculos invalida disponibilidade. Nenhum compilador XML ou driver real foi inventado.

O diagnóstico inicial no modo emulador foi indisponível: ADB, emulador, perfil, compilador e importação ausentes. Ainda não há exportação do Alight nem qualificação visual/autônoma. A instalação e a prova no aplicativo precisam ser registradas depois da execução.

## Resultado da tentativa real

O download direto terminou com tamanho e SHA256 esperados; Authenticode retornou `Valid`, assinante Now.gg, INC. O instalador foi iniciado com `-s`, conforme manifesto do winget. O log local `C:/Users/edugu/AppData/Local/Bluestacks/BlueStacks-Installer_5.22.166.1003.log` registrou `Preinstall checks failed: -14`, `Space required InstallDir: 500 MB`, `Space required DataDir: 5120 MB`, rollback e saída -14. Durante a extração, o espaço caiu para cerca de 2,5 GB. Não houve instalação confirmada, `HD-Player.exe` não foi encontrado, e o processo terminou.

A tentativa inicial via DeliveryOptimization concluiu o arquivo em segundo plano, depois do encerramento do winget. Há duas cópias de 3.736.512.576 bytes: `C:/Users/edugu/Downloads/res/tmp/BlueStacksFullInstaller_5.22.166.1003_amd64_native.exe` e `C:/Users/edugu/AppData/Local/Temp/WinGet/BlueStack.BlueStacks.5.22.166.1003/DO4498.tmp`. A revisão automática rejeitou tanto a remoção do temporário do winget quanto a remoção individual da cópia dentro do workspace com `blocked by policy`; nenhum desses comandos de exclusão foi executado. Não houve tentativa de contornar a rejeição com outro shell ou API de arquivos. Isso limita a limpeza adicional. O recibo posterior registra o espaço efetivamente restante, distinto dos 16,3 GB disponíveis logo após limpar caches.

Verificação do software: 46 testes focados de Alight/produção passaram; após acrescentar a vinculação do runtime do emulador, 17 testes do worker passaram. Essas contagens se sobrepõem e não devem ser somadas. 11 testes de interface passaram, incluindo ausência de envio de produção quando Alight está indisponível; TypeScript, Ruff dos módulos novos e `git diff --check` passaram. Testes apenas de software: zero jobs reais no Alight, nenhuma aprovação humana e nenhuma promoção.

## Segunda tentativa: emulador instalado, autenticação pendente

Na continuação de 02/10/2026, o volume já tinha 17.839.501.312 bytes livres. O mesmo instalador assinado foi executado novamente. O log registra `Installation completed 100%`, `Installer background worker completed. Result: 0` e `Exiting with error code 0`, às 11:19:19 -03:00. Foram encontrados `C:/Program Files/BlueStacks_nxt/HD-Player.exe` e `HD-Adb.exe`, versão 5.22.166.1003. A primeira tentativa malsucedida permanece documentada acima e no recibo original; esta é uma tentativa distinta.

O launcher Android foi observado em execução. ADB retornou `emulator-5554 device`, Android `7.1.1` e hardware `qcom`. Esses valores são observações de descoberta, não um perfil homologado. Às 11:23:01 o Player registrou `reason Close_by_user`, seguido de encerramento com código zero; o fechamento foi auditado antes da reabertura. Houve uma falha de ativação da janela e detecções de interação local durante navegação; a janela foi relocalizada e o estado foi atualizado, sem reutilizar coordenadas antigas. Um aviso do Docker apareceu sobre a janela; nenhuma ação foi executada no aviso por esta tarefa.

A busca no launcher local encontrou Alight Motion e seu botão `Instalar do Google Play`. O botão abriu a Play Store; a atividade Android observada passou a `com.google.android.gms/.auth.uiflows.minutemaid.MinuteMaidActivity`, evidência de que a instalação chegou à autenticação Google. O login foi solicitado ao usuário para execução direta no emulador. A [documentação oficial de download](https://support.alightmotion.com/hc/en-us/articles/16177753891857-How-can-I-download-the-app), consultada novamente nesta continuação, direciona ao Google Play e Apple App Store; não foi identificado nela um APK oficial direto. O pacote esperado pela ficha oficial é `com.alightcreative.motion`; instalação e versão efetiva do Alight ainda precisam ser observadas no emulador.

O backend local, em `.env` ignorado pelo Git, foi configurado com `STUDIO_ALIGHT_MOTION_ENABLED=true`, `STUDIO_ALIGHT_EXECUTION_MODE=android_emulator_ui` e o caminho do ADB instalado. Nenhum perfil de qualificação foi preenchido. O probe real, com o emulador conectado, continua com `available: false` e bloqueios `device_profile_missing`, `validated_compiler_missing` e `validated_import_missing`. Logo, conexão ADB não habilitou render nem promoção.

O espaço livre posteriormente subiu para cerca de 76,7 GB durante outra atividade local. Essa diferença não é atribuída à limpeza desta tarefa. Os dois instaladores não foram removidos por esta tarefa. Não houve novo gasto em API, compra ou assinatura.

Recibo desta tentativa: `output/space-cleanup-20261002/alight-pc-second-attempt.json`. Próximas evidências necessárias: login feito pelo usuário, instalação observada, versão efetiva, projeto mínimo, importação editável real, exportação recuperada e validação do driver/compilador. **Zero vídeos produzidos no Alight até este registro.** O ensaio anterior continua identificado como Remotion.

### Tentativa pelo Chrome, solicitada pelo usuário

Foi aberta no Chrome a página oficial `https://play.google.com/store/apps/details?id=com.alightcreative.motion`. O navegador já estava autenticado. O botão `Instalar` exibiu a seleção de dispositivo, com apenas um telefone pessoal cadastrado; nenhum emulador foi oferecido. A lista foi conferida e a janela de instalação foi fechada sem enviar instalação para o telefone. A aba oficial permaneceu aberta para continuação. Não foi feita troca de conta, entrada de credenciais ou alteração de segurança. O login existente no Chrome não demonstrou um vínculo da instância Android com essa conta. A próxima etapa continua sendo o login direto na Play Store do BlueStacks e a posterior verificação de compatibilidade e instalação.

## Instalação do Alight confirmada e primeira abertura

Após o usuário informar a instalação, o `dumpsys package` confirmou `com.alightcreative.motion`, versão `5.0.273.1028425`, versionCode `1028425`, minSdk `24`, targetSdk `36`, e instalador `com.android.vending`. O Player.log registra instalação às 12:36:16 -03:00. A tela da Play Store mostrou `Abrir`; o launcher apresentou o ícone instalado. O aplicativo foi aberto pelo launcher, e a atividade observada passou a `com.alightcreative.app.motion.activities.main.MainActivity`.

A dica inicial do BlueStacks foi dispensada. O Alight apresentou consentimento de privacidade (`Nós valorizamos a sua privacidade`, com opções de aceitar ou personalizar). Nenhuma preferência foi escolhida pela automação; foi solicitado ao usuário resolver o consentimento diretamente no aplicativo. Ainda não foi criado projeto nem exportado vídeo.

Enquanto essa etapa depende do usuário, `workers/alight-motion/prepare_discovery.py` gerou seis materiais para a prova: fontes de teste próprias de 24 e 60 fps, objeto neutro com transparência, referência sonora de 15 segundos com evento em 1 segundo, fonte IBM Plex Mono e sua licença OFL existente no repositório. Manifesto e probe em `output/alight-discovery-20261002/` registram hashes, origem e finalidade. Os seis checksums foram verificados. As imagens de teste de sinal não contam como filmagem nem aprovação estética; `evidenceKind` permanece `preparation_only`, `filmedActionSeconds` permanece zero. Ruff do script passou.

Limitação observada na comunicação: chamadas `shell wm size` retornaram `error: closed`, código 1; `getprop` e `dumpsys package` funcionaram em outras chamadas. Um diagnóstico `logcat -d` permaneceu aguardando dispositivo e foi interrompido após identificar seu processo e linha de comando. A causa ainda não foi estabelecida. `dumpsys window displays` observou `init=1600x900`, `cur=900x1600`; não houve alteração de resolução. Memória livre observada: aproximadamente 725 mil KiB em um total de 8.106.040 KiB. Esses sinais precisam de investigação antes de homologar automação; não foi adotada uma explicação presumida ou substituição silenciosa de comandos.

O worker segue indisponível por falta de perfil, compilador e importação validados. Instalação e abertura foram demonstradas; composição, importação editável, render, revisão visual e autonomia ainda estão pendentes. Nenhuma despesa adicional em APIs ou assinatura.

## Conexão da instalação ao sistema

Na continuação solicitada para inserir o Alight no sistema, foi implementada descoberta real de instalação no worker, exposta pelo endpoint existente de motores e exibida no Studio. `applicationProbe` contém apenas pacote fixo, versão, instalador, quantidade de ambientes conectados e horário de observação. Sem um perfil, ele consulta o pacote apenas quando há exatamente um Android conectado. Falha de consulta mantém instalação desconhecida; pacote ausente é um diagnóstico separado. Não existe seleção automática de um telefone entre múltiplos dispositivos nem retorno integral do `dumpsys` com dados de conta.

O Studio mostra a versão efetiva e oferece `Atualizar conexão com Alight`. A atualização também alimenta o estado usado pelo seletor de edição. Instalação observada não libera o botão de render nem concede capacidades. O provider e o fluxo de jobs existentes continuam exigindo o perfil e o driver de importação/exportação homologados. Nenhum componente Remotion foi renomeado como Alight; nenhum XML importável foi inventado.

Verificação real pelo proxy do Studio: `GET /api/v1/studios/v1/workspaces/4812f2c0-1a2a-4f6d-967d-17b370c8d849/render-engines` retornou HTTP 200, `installed: true`, versão `5.0.273.1028425`, instalador `com.android.vending`, um ambiente conectado, `available: false` e as três pendências de perfil/compilador/importação. A consulta usou somente a identidade fictícia e o workspace isolado do ensaio anterior; nenhum token foi impresso ou persistido. Script reproduzível: `scripts/validation/probe-alight-studio.py`. Evidência: `output/alight-discovery-20261002/studio/api-observation.json`.

Backend e web foram iniciados em modo local, com logs na mesma pasta. O health check confirmou backend pronto, banco acessível e Redis não requerido. A aba do Studio foi criada no Chrome, mas o controle da aba falhou por timeout e, na recuperação, `Debugger unattached`; por isso não há afirmação de inspeção visual do painel nessa sessão real. A interface foi validada por três testes Playwright focados, incluindo instalação sem qualificação e atualização que remove a versão quando o aplicativo deixa de ser encontrado. A suíte focada dos três módulos backend passou; TypeScript e Ruff passaram. O primeiro comando pytest usou o diretório incorreto e falhou no import de `app`; foi corrigido executando a partir de `backend`. Um erro de sintaxe no novo teste Playwright foi corrigido antes do resultado aprovado.

A tela de consentimento foi novamente observada no aplicativo; nenhuma escolha foi automatizada. Esse era o estado naquele momento; a continuação abaixo registra a configuração concluída pelo usuário. **A ligação de descoberta ao Studio está funcionando; o render automático do Alight permanece não demonstrado.**

### Continuação: oferta fechada e projeto criado no aplicativo

O usuário confirmou que havia concluído a privacidade. A página inicial foi observada, e foi iniciada a criação de `res Alight - prova 01`. A oferta `Edite sem limites!`, com opções de teste gratuito, semanal e anual, foi fechada pelo X no canto superior esquerdo. Nenhum teste, assinatura ou compra foi iniciado. Houve anúncio intermediário e retorno à configuração; uma nova confirmação de criação abriu o editor.

Configuração efetivamente usada: 9:16, 540 × 960, 30 fps, fundo cinza claro. No menu consultado foram vistos 540p, 360p e 270p. Isso não comprova que resoluções superiores são impossíveis nem identifica a causa de sua ausência nesse menu. O projeto é prova de descoberta abaixo do requisito final de 1080 × 1920.

Uma camada de texto própria foi criada com `res Alight • prova 01`, em Roboto Regular, cor preta. O texto e o caractere `•` apareceram na prévia. Marca d'água do Alight foi observada na composição. Não foram testados movimento, máscaras, filmagem, importação de fontes ou reuso de receitas nessa prova.

O painel real `Exportar e Compartilhar` apresentou vídeo MP4 em 540p/30 fps e opções de PNG, sequência de imagens e GIF. `Pacote do Projeto` e envio à nuvem apresentaram cadeado; nenhum pacote editável foi obtido. Ao acionar exportação de vídeo, apareceu um anúncio com contagem regressiva. Acionar o botão de exportação ainda não comprova arquivo concluído ou recuperado.

A transferência dos materiais preparados por `HD-Adb.exe push` terminou com código 1 sem diagnóstico textual. A auditoria seguinte confirmou `emulator-5554 device`, mas `shell ls` retornou código 1 e `error: closed`. A causa permanece não determinada; materiais não foram declarados transferidos. Descoberta de pacote via ADB e transferência de arquivos são capacidades distintas.

Estas interações foram dirigidas pelo agente na interface, fora de um job do worker. Não contam como execução autônoma, perfil homologado ou aprovação visual. Custo adicional em API: US$ 0.

#### Primeira exportação recuperada e auditada

A exportação terminou na tela `Compartilhar vídeo`; `Salvar` apresentou confirmação. O Gerenciador de Mídia do BlueStacks encontrou somente o arquivo desta prova e o exportou para o Windows. Arquivo recuperado: `output/alight-discovery-20261002/studio/res Alight - prova 01 [265FEBE].mp4`, 87.404 bytes, SHA256 `76f6c08f63e56d08502613997fc93e928e0f870fdf976de9faa5ec3191f21ee8`, duração 2,033333 s, H.264 a 30 fps e uma faixa AAC.

Na tela de compartilhamento, o texto apareceu girado. O probe identificou vídeo codificado em 960 × 540 e matriz de exibição de −90°. A extração de um quadro com FFmpeg, respeitando essa matriz, mostrou 540 × 960 com o texto horizontal, correspondente à composição do editor. Portanto, a observação da prévia isolada não sustenta uma falha no conteúdo exportado. A causa interna da reprodução incorreta no aplicativo não foi investigada.

Uma cópia silenciosa foi normalizada com FFmpeg em `alight-prova-01-normalizado.mp4`, com pixels em 540 × 960 e sem metadados de rotação pendentes. Isso não aumenta a resolução nem qualifica o motor. A existência de uma faixa AAC na exportação deve ser considerada na integração: usar somente o vídeo antes da mixagem planejada para evitar áudio duplicado. O recibo `alight-first-export-receipt.json` preserva o probe, checksums, limitações e intervenções.

Resultado: criação, texto, exportação e recuperação reais demonstradas em um projeto mínimo de aproximadamente dois segundos. Importação editável, materiais, fontes, máscaras, movimento, 15 segundos, 1080 × 1920, render pelo worker, qualidade visual e autonomia continuam pendentes. A marca d'água permanece visível; nenhuma assinatura foi contratada.

#### XML disponível em outro caminho; recuperação pendente

Ao reabrir o aplicativo, a lista de projetos mostrou `Carregar arquivo XML` e o projeto salvo. O menu de três pontos do projeto → `Exportar` abriu uma variante do painel com opção `XML`, sem o cadeado observado no pacote. Selecionar XML exibiu estimativa de 714 bytes; a exportação abriu uma solicitação Android `Ativar Compartilhar por proximidade`, com nome e visibilidade do dispositivo e aviso sobre ativar temporariamente Wi-Fi e Bluetooth.

Nenhuma escolha foi feita nessa solicitação de privacidade. O usuário foi orientado a fechá-la diretamente; a skill computer-use proíbe atuar em solicitações de permissão de segurança ou privacidade. Assim, **a opção de exportação XML foi observada, mas o XML ainda não foi recuperado, lido ou reimportado**. O cadeado do pacote não comprova que toda exportação editável exige assinatura. Não preencher compilador ou perfil antes de obter e validar a referência real.

#### Continuação: ADB habilitado pelo usuário, transporte e XML reais

A investigação comparou o HD-Adb 1.0.36 com platform-tools oficial 37.0.1,
baixado com checksum registrado. Ambos listavam o emulador, mas operações de
arquivo falhavam enquanto a configuração ADB do BlueStacks estava desativada.
A tentativa de servidor isolado na porta 5040 encontrou outro processo nessa
porta; ele não foi encerrado. Um servidor de diagnóstico separado na porta 5038
funcionou, mas não resolveu o acesso a arquivos. Não foi atribuída a falha à
versão do cliente. O usuário ativou ADB na interface do BlueStacks e confirmou
`Feito`. Depois disso, push, pull e listagem funcionaram com o HD-Adb instalado.

Os seis materiais próprios foram transferidos para
`/sdcard/Download/res-alight-discovery` e recuperados. Todos os SHA-256 coincidiram
com o manifesto. `materials-transfer-receipt.json` registra o resultado. Isso
comprova transporte, não importação das seis mídias no compositor.

Uma tentativa de leitura direta da URI do FileProvider retornou
`SecurityException`, embora o comando shell tenha retornado código zero.
A recusa foi preservada; não houve root, acesso ao armazenamento privado ou
alteração de permissões. Foi criado o receptor próprio `org.res.alightbridge`,
sem permissões e sem rede, que usa somente a concessão temporária de leitura de
um compartilhamento Android `ACTION_SEND`. O build reutilizou um Java já
instalado e ferramentas oficiais com checksums; não instalou Android Studio ou
outro emulador. O APK foi compilado, assinado, verificado e instalado. A identidade
de desenvolvimento e os produtos do build foram excluídos do Git.

O Alight compartilhou um XML real de 912 bytes, SHA-256
`25e4b3e9d1d7b7d0b4e8fdd324a0a1993c6e3000c50676af14a39377a8038d52`.
A referência versionada está em
`workers/alight-motion/references/5.0.273.1028425/text-original.xml`, com recibo
e proveniência. O XML contém cena 540 × 960 a 30 fps, 2032 ms, uma camada de
texto Roboto e posição. Não contém filmagem, máscara ou referência a mídia.

Uma cópia foi transferida de volta e aberta pela opção real `Carregar arquivo
XML`. O seletor Android não listou a pasta enviada por ADB na categoria Downloads;
a navegação pelo armazenamento interno → Download encontrou o arquivo. A
importação abriu uma composição editável com o texto e os parâmetros originais.
Isso demonstra importação do projeto mínimo de texto, sem comprovar os demais
tipos de camada, fontes externas ou fidelidade completa.

Na cópia importada, foram criados dois keyframes de posição X: −270 no início e
270 em dois segundos, Y 480. Uma exportação MP4 dessa cópia foi recuperada por
ADB como `studio/alight-keyframe-reference.mp4`. A cópia silenciosa normalizada
é `studio/alight-keyframe-normalizado.mp4`. Quadros intermediários em
`alight-keyframe-contact.png` mostram o texto entrando progressivamente pela
esquerda. A análise confirma movimento no vídeo, não aprovação estética. A
prévia de compartilhamento voltou a mostrar rotação, enquanto os quadros
decodificados respeitando a matriz mostram a orientação correta.

Houve anúncios intersticiais durante o caminho de exportação e ao fechar a
prévia. Uma navegação abriu a ficha de outro aplicativo na Play Store; voltou-se
sem instalar. Um anúncio apresentou artefatos de decodificação; a causa interna
não foi estabelecida. Essas interrupções devem entrar no diagnóstico e no teste
do driver, sem contornar anúncios ou declarar um perfil estável. Nenhuma compra
ou assinatura foi feita. API adicional: US$ 0.

Estado atual: transferência, XML real, reimportação de texto e exportação com
movimento comprovados por descoberta dirigida. O worker continua sem perfil,
compilador e ciclo automático homologados; não foi habilitado por essas provas.
Estética, 15 segundos, 1080 × 1920, materiais e máscaras completas, três linguagens
e 30 jobs reais permanecem pendentes.

#### Compilador de descoberta e variante parametrizada

O XML com keyframes foi recuperado pelo receptor em transferência distinta,
UUID `d2b661a9-079e-43e1-a2b6-83283ae0ebd2`, 1019 bytes, SHA-256
`730152f4f7188a1656b5121b675e0fe223bd5accfd6f8c94ac3d4935c833aadf`.
Foi preservado como `text-linear-motion.xml`, com proveniência versionada. Os
keyframes reais usam `t="0.007874"` e `t="0.992126"`; a interpretação temporal
do offset de 16 ms foi registrada como inferência, sem inventar um formato de curva.

O módulo backend `alight_text_compiler.py` fixa esse checksum e aceita somente
parâmetros tipados de texto, título e duração/entrada. Não aceita XML livre,
comandos ou efeitos. O CLI `compile_text_reference.py` gera projeto e recibo,
incluindo IDs de cena/elemento, digest de parâmetros e checksum de saída.
Não está homologado nem registrado como compilador de produção do worker.

A variante `res - compilacao 15s`, texto `Criar. Mover. Testar.`, gerou XML com
SHA-256 `70f2c1a68a6069cabe87ba34c0931d7f115e67b8197f74a13b4d969a05aaa21d`.
O Alight aceitou a importação e mostrou a nova composição editável. A reprodução
chegou a 00:14:29; nesse instante a prévia estava sem o texto. Esse resultado
precisa de auditoria da interpolação/hold antes de declarar a variante correta.
Não foi recuperado um render dessa variante nem concedida aprovação. A prioridade
seguinte solicitada pelo usuário passou à integração e ao diagnóstico da distância
visual; a interpretação de timing permanece pendente.

Sete testes do novo compilador passaram, cobrindo referência adulterada, dados
escapados, invalidade de caracteres/intervalos, recursos não implementados e
invalidação por mudança de parâmetros. Ruff passou. Erros de caminhos relativos
na primeira chamada de lint foram corrigidos usando a raiz do repositório.
Consulta real do Studio voltou a retornar HTTP 200, instalação confirmada e
`available: false` com as três pendências. Nenhum job Alight foi atribuído ao Studio.
