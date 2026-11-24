# Análise de referências e repertorio de motion da Clicko

No editor nativo de vídeo, selecione o Claude e indique a referência e o trecho a adaptar.
A referência pode ser um vídeo da biblioteca do mesmo workspace ou uma referência temporal cadastrada.
O Claude pode consultar as evidências sem inserir o arquivo na montagem.

- `analyze_motion_reference` analisa até 30 segundos via rea-video e devolve cortes, transições, quadros-chave e marcas de ritmo candidatas.
- `search_repertoire` encontra receitas do OpenMotion por problema visual. Cada uma tem fonte, operações sugeridas e um teste visual.
- `compare_motion_reference` renderiza três pares de quadros, em colunas sincronizadas por deslocamento de tempo.
- `record_editorial_lesson` guarda uma correção fundamentada para revisão no guia de edição da Clicko.

Informe se um evento depende de sincronismo perceptivo com o áudio. Os quadros alinhados ajudam a checar a imagem e as marcas de áudio precisam de verificação no trecho reproduzível.

## Configuração local

No Windows, execute os comandos a partir da raiz da Clicko com FFmpeg e FFprobe disponíveis.

```powershell
python -m venv .codex-runtime/rea-video/venv
.codex-runtime/rea-video/venv/Scripts/python.exe -m pip install -r backend/requirements-rea-video.txt
```

A Clicko detecta esse ambiente automaticamente. Para uma instalação em outro caminho, defina `STUDIO_CRAFT_REA_VIDEO_BINARY` no processo que roda a API da Clicko. Em Linux, a mesma estrutura usa `venv/bin/rea-video`. A imagem media-cpu tem sua própria instalação. O REA roda sem inferência remota, OCR ou separação de áudio. O upstream pode baixar o pequeno modelo auxiliar de detecção de rostos na primeira execução.

As receitas incluem o commit do OpenMotion usado como fonte. Seus parâmetros são pontos de partida. A confirmação de que funcionam com outro material depende de uma edição renderizada e revisada na Clicko.
