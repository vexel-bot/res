# Prova pontual do renderizador Canvas existente

13/11/2026. Teste auxiliar de pesquisa; nenhuma integração de produção foi implementada. US$ 0 de API, rede HTTP/HTTPS bloqueada no navegador. Não produziu outro anúncio nem modificou os fontes do baseline.

## Artefatos

- [Recibo original](canvas-probe-result.json).
- [Manifesto: hashes, ambiente e arquivos](canvas-probe-manifest.json).
- [Fontes existentes e fontes tipográficas com licenças](orbita-runtime-source.zip).
- [Script de reprodução](canvas-probe.cjs). Apenas os caminhos de entrada/saída foram parametrizados na cópia; lógica do probe preservada.
- [Verificação do pacote e reprodução](archive-verification.json).

O ZIP contém quatro arquivos de projeto e sete arquivos de fontes/licenças. Não inclui chaves, envs, recibos de contas ou vídeos de terceiros. Seus hashes e os de seus arquivos são dos bytes originais. Os hashes do script/recibo em texto normalizam CRLF para LF, conforme o manifesto, para tolerar a conversão de fim de linha do Git. O fonte já estava associado ao [ensaio independente](https://github.com/vexel-bot/res/releases/tag/orbita-independent-2026-11-12).

## Procedimento e resultado original

Com Playwright 1.63.0, Chromium 153.0.8010.12, Node v22.15.0 em Windows x64, abrir o HTML local e esperar `ORBITA.ready`. Solicitar os tempos `3.4, 7.9666666667, 8, 8.1, 11.4, 15.9, 8, 3.4` segundos. São **oito solicitações no laço principal, seis tempos distintos**, mais uma comparação de 3,4 s em página nova.

As repetições coincidiram por SHA-256 do PNG e o quadro em página nova também. Todas as amostras tinham alfa mínimo/máximo 255. A luminância RGB ponderada média passou de aproximadamente 111,63 a 219,56 entre as amostras de 7,9667 e 8 s. Esse é um sinal localizado, não um teste integral de fotosensibilidade nem de todo o movimento.

O recibo mede 4,26 s para as solicitações e a comparação. Não mede exportação de 480 quadros, montagem ou mix. A versão do ambiente foi capturada imediatamente depois, e não instrumentada no recibo original. Hashes podem variar entre navegadores, plataformas, renderização e fontes; repetir o experimento mede também essa condição.

## Como reproduzir

Em checkout com as dependências locais já instaladas, extrair o ZIP para um diretório de trabalho; manter `src/fonts` junto do HTML. Usar o Chromium da versão Playwright registrada. Não é necessário configurar provedor ou chave de API.

```powershell
node docs/studios/research/2026-11-13-motion-quality-investigation/probes/canvas-probe.cjs "CAMINHO-EXTRAIDO/src/orbita.html" ".codex-runtime/clicko-dev/motion-quality-probe-replay"
```

O script grava PNGs e `result.json` no diretório de saída. Não usar o diretório de evidência original como destino. Conferir hashes e licenças pelo manifesto; a segunda execução de verificação usou uma extração separada, com resultados registrados em `archive-verification.json`.

## Alcance

Suporta repetibilidade nos pontos observados e a possibilidade de reutilizar o fonte. A saída opaca pode ser correta para uma cena completa. Camada transparente exige teste distinto. Esta prova não estabelece qualidade editorial, fluidez de todo o vídeo, áudio, aprovação de espectadores, equivalência a After Effects ou superioridade sobre o Craft.
