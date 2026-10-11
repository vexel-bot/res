# Vídeo de teste pelo Studio — 01/10/2026

## Resultado entregue

O Studio real produziu duas versões do estudo tipográfico **Dê forma à ideia**, com texto, grafismos e desenho de som originais. Foi usado `remotion.contextual-v2`, com finalização FFmpeg, sem mocks de API, chamadas pagas, compras ou execução do Alight Motion.

- Workspace isolado: `Laboratório Motion 01-10` (`4812f2c0-1a2a-4f6d-967d-17b370c8d849`).
- Conteúdo em rascunho: `a680d18c-f05e-4bf7-93f2-14a91a1f068b`.
- Documento: `d7e181c0-9621-4a3c-8b13-f7b0d92f3eb4`.
- Plano final: `45513d04-9765-43cc-9307-74be7a6a602b`.
- Job final: `1b82d342-a0c7-41a5-b3ee-9b18c15797d9`.
- Asset final: `9a9047be-c5e9-4a6c-9b12-eec8426a4b31`.
- Saída: **15 s, 450 quadros, 1080 × 1920, 30 fps, H.264 e AAC**.
- SHA-256: `7fa7d8d7a50be3eae6b3f4f6b720d868dae996e2b014517b570392d6e3766fb6`.
- Tempo do renderer final: 123.484 ms; o primeiro foi de 107.391 ms. Não representam p95 ou homologação de uma coorte.

[Abrir o conteúdo local](http://127.0.0.1:3000/content/a680d18c-f05e-4bf7-93f2-14a91a1f068b/edit?mode=video). A reprodução privada requer a sessão autenticada do workspace de estudo.

Arquivos em `output/studio-motion-test-20261001`: `de-forma-a-ideia.mp4`, `first-render.mp4`, planos, recibos de render, probe, desenho de som original, capturas, contatos e evidências de reprodução.

## Fluxo efetivamente percorrido

API e frontend locais foram iniciados com logs em `tmp/studio-live-api.*.log` e `tmp/studio-live-web.*.log`. Remotion nativo, indicador visual e avaliação do Alight foram habilitados apenas no ambiente dos processos; os padrões de configuração continuam desligados. O worker Alight permaneceu indisponível.

A conta e o workspace de estudo foram criados na interface de autenticação. O [script do estudo](../../../scripts/studio-motion-smoke-20261001.js) usou a sessão do navegador para chamar a API existente: criar conteúdo, enviar um WAV original, criar o documento, registrar direitos sobre o áudio e compilar o plano tipado. Não houve escrita direta desses objetos no banco.

Nos dois renders, o botão **Gerar vídeo** do painel de edição foi acionado. O próprio Studio aplicou o plano, persistiu a composição, criou o job e apresentou o export privado na aba **Saída**. As leituras diretas posteriores do banco foram usadas para auditoria e para recuperar uma cópia local do artefato já gerado. O checksum da cópia foi conferido contra o recibo.

## Erros auditados e intervenções

1. A ferramenta de navegador inicialmente sofreu timeout; o diagnóstico da CLI não indicou falha de instalação. O navegador integrado também não pôde inicializar seus assets. O teste prosseguiu com `agent-browser` e a abertura visível em Chrome local.
2. O e-mail de estudo com domínio reservado `.test` recebeu HTTP 422. A validação do schema confirmou a causa; foi substituído por um endereço fictício no domínio `example.com`, sem envio de mensagens.
3. O primeiro pedido de plano recebeu `editing_v2_multiple_heroes`. O contrato exige um único protagonista por cena; os papéis foram corrigidos.
4. O primeiro **Gerar vídeo** recebeu `editing_visual_preflight_required`, antes de criar qualquer job. Os achados eram protagonista pequeno e duas colisões de texto. Foram corrigidos hierarquia, intervalo e posição; o próximo pré-voo ficou sem achados bloqueadores.
5. O primeiro render completou tecnicamente. Os quadros amostrados revelaram uma quebra indesejada em “UMA IDEIA”, textos auxiliares extensos e o círculo atravessando “MOTIVO”. Um novo plano reduziu o título, encurtou os auxiliares e alterou a trajetória. Gerou outro job e checksum, mantendo o primeiro export disponível.
6. A tentativa inicial de `play()` sem interação foi recusada pela política do navegador. Foco e tecla de reprodução iniciaram o player normalmente. As evidências registram chegada a 15 s, velocidade 1×, áudio habilitado e volume 1. Isso comprova reprodução; não equivale a escuta crítica ou avaliação humana.
7. Houve falta de recursos do Windows ao abrir uma segunda sessão de navegador; uma consulta mostrou aproximadamente 245 MiB livres de memória física. A sessão duplicada criada para este teste foi fechada, e o navegador do estudo foi substituído por uma sessão visível. Nenhum navegador do usuário foi encerrado.

Essas decisões editoriais foram fornecidas pelo agente, incluindo a direção inicial. O estudo **não demonstra planejamento autônomo**. As correções estão nos planos e neste registro; não há edição oculta do MP4 depois do render.

## Verificação e limites

Os dois jobs concluíram com QC técnico `passed`. O export final tem um stream de vídeo e um de áudio, duração e proporção corretas, sincronização de início/fim dentro do contrato e nenhum intervalo preto detectado. O áudio recebeu normalização pelo fluxo existente. Há um aviso de silêncio excessivo da política UGC: o desenho de som usa efeitos pontuais e pausas; não foi preenchido com música apenas para eliminar o aviso.

Ambas as versões foram reproduzidas integralmente a 1× no player real, sem erro de mídia, com áudio habilitado. O player tinha largura de 241 px e altura de 300 px; também foram examinados quadros extraídos em 270 × 480. As correções de quebra de linha e sobreposição são visíveis no contato final. A verificação do arquivo exportado e do probe é técnica; não certifica preferência estética, clareza 4/5 ou qualidade sonora perceptiva.

**Funcionamento técnico:** demonstrado neste estudo. **Qualidade visual humana:** não avaliada; sem notas preenchidas. **Autonomia:** render automático de direção fornecida, com intervenções registradas; planejamento e qualificação geral pendentes. **Alight:** zero jobs reais, sem promoção. **APIs pagas:** US$ 0 adicionais; nenhum consumo do teto compartilhado de US$ 10.

O resultado é um estudo gráfico para testar o fluxo. Não constitui anúncio com oito segundos de ação filmada, comparação cega entre motores, aprovação comercial, exemplo `render_verified` da nova biblioteca ou conclusão dos três casos de qualificação. Ainda há uma estrutura tipográfica deliberadamente simples; o estudo não comprova que o sistema atingiu a linguagem dos creators analisados.

O teste também expôs limitações da experiência: durante o modo local de execução síncrona, a interface exibe “Enfileirando render” enquanto o renderer já trabalha; a sondagem do difusor indisponível levou de aproximadamente 30 a 77 segundos em algumas leituras. Esses tempos estão nos logs. São diagnósticos para uma melhoria posterior, sem atribuí-los a falha do compositor.

A janela de Chrome visível foi aberta, mas a sessão de controle começou a sofrer timeouts `os error 10060` durante sua sincronização. Portanto, não se declara que a última janela visível carregou a aba Saída ou que seu blob foi confirmado por checksum. As reproduções completas registradas acima aconteceram na sessão funcional anterior do Studio. A API permaneceu `ready`, com banco acessível; o MP4 final é entregue diretamente para permitir o teste mesmo diante dessa limitação de navegador.
