# Acervo e direção contextual com Gemini

Estado em 6 de setembro de 2026. Escopo exclusivo: edição de vídeo do res.

## O que está conectado

O painel de edição contextual permite importar arquivos, pesquisar o acervo privado, buscar famílias no Google Fonts, escolher a fonte do projeto, adicionar som por cena e solicitar direção ou materiais ao Gemini. Os arquivos entram no armazenamento existente como `LibraryAsset`; as revisões usam `CreativeDocument`; a execução usa os jobs e workers existentes.

O caminho novo executa composição com `builtin.ffmpeg-contextual-v1` versão 1.2.0. Oferece múltiplas trilhas, enquadramento, texto, legendas, máscaras estáticas, posição/escala/rotação/opacidade com easing, fade, congelamento, velocidade constante, cor e mixagem. Os componentes de repertório combinam essas capacidades com proporções e durações ajustáveis. Gemini recebe o documento, os recursos e as fichas executáveis para justificar suas decisões. Recursos ausentes geram impedimentos antes do render.

Para transformação, o cliente escolhe o material, uma referência opcional, o pedido e um intervalo de 3 a 10 segundos. A resposta é verificada tecnicamente e submetida à avaliação visual automática. Resultado inconclusivo fica pendente de revisão humana real. A aplicação exige o mesmo documento/revisão e as mesmas origens. Em vídeo, o áudio original é reincorporado; o áudio inventado pelo gerador é descartado.

Uma transformação aprovada pode substituir a cena ou uma parte de um clip simples, mantendo os trechos anterior e posterior, outras trilhas e legendas. Divisão de clips já animados, congelados ou com efeitos exige replanejamento; não há perda silenciosa dessas operações. O usuário deve aplicar a transformação diretamente à cena antes de incorporar outros materiais ou alterar a revisão que originou o job. Materiais de geração livre podem ser incorporados como apoio visual.

## Acervo e arquivos

- Tipos: fontes TTF/OTF, logos/imagens/referências PNG/JPEG/WebP, vídeo MP4, áudio WAV/MP3/FLAC. SVG, arquivos executáveis e pacotes ZIP não são aceitos por este importador.
- Metadados: descrição, tags, origem, condições de uso, versão, variante tipográfica, características técnicas e checksum. Uma marca nova não exige código novo.
- Deduplicação de arquivos importados por conteúdo no mesmo workspace e tipo. Materiais derivados conservam sua própria linhagem.
- Download HTTPS limitado a 100 MB, hosts cadastrados, DNS público fixado na conexão e redirecionamentos revalidados. FFprobe fica restrito a protocolos locais.
- A fonte selecionada é materializada por ID/checksum. Falta de arquivo ou glifo produz erro explícito. A prévia tipográfica carrega o mesmo arquivo no navegador; a exportação usa esse arquivo em Pillow/FFmpeg.
- A busca prioriza recursos do documento e depois o acervo. Google Fonts é o primeiro conector de descoberta; outras origens precisam ser cadastradas e importadas. Não há busca irrestrita na internet nem compras automáticas.

## Ambientes e execução

Configurações no `.env.example`:

| Variável | Função |
| --- | --- |
| `STUDIO_GEMINI_ENABLED` | Ativa os adaptadores nativos novos |
| `STUDIO_GEMINI_TEST_KEY` | Chave exclusiva de development/test |
| `STUDIO_GEMINI_PRODUCTION_KEY` | Chave exclusiva de production |
| `STUDIO_GEMINI_TEST_BUDGET_USD` | Reserva conservadora para testes; padrão zero |
| `GOOGLE_FONTS_API_KEY` | Consulta oficial de famílias/variantes |
| `STUDIO_RESOURCE_HOSTS` | Lista JSON de hosts HTTPS permitidos |

Instalar `backend/requirements.txt` no backend e no worker de mídia, incluindo `fonttools==4.61.1`. O manifesto `workers/media-cpu/worker.manifest.json` inclui `editing_gemini`. Os segredos ficam no backend/worker; nunca em variáveis `VITE_*`. Não existe fallback para chaves legadas ou GPT. O startup de produção rejeita habilitação dos adaptadores OpenAI.

Modelos fixados: `gemini-3.8-flash`, `gemini-3.1-flash-lite-image` (com `gemini-3.1-flash-image` disponível para qualificação comparativa) e `gemini-omni-1.1-flash`. Antes de uma nova submissão, o adaptador consulta o modelo nativo e valida a identidade retornada. Não existe atualização silenciosa. O status `configured` informa configuração, não certificação visual.

No job são persistidos ambiente, revisão, checksums, modelo, identificação da tarifa, início de submissão, ID do provedor, resposta, consumo e avaliação. Reenvios preservam esses dados. Quando existe ID conhecido, uma nova tentativa consulta a operação. Quando o POST tem resultado desconhecido e nenhum ID foi recebido, o sistema exige reconciliação; não promete exatamente uma execução em um provedor sem idempotência comprovada. Cancelar ou repetir o job não apaga esse registro. O asset e seu vínculo de resultado são persistidos na mesma transação.

O endpoint `GET /api/v1/studios/v1/editing/usage` apresenta os últimos 100 jobs do workspace, consumo retornado pelo provedor, consumo de verificação, imagens/segundos entregues, bytes armazenados, tempo de processamento e tentativas. Consumo ausente permanece desconhecido. As reservas locais são conservadoras, não uma fatura. Produção não possui teto mensal nem limite financeiro por vídeo neste fluxo. A estimativa de CPU do render não representa o custo total da geração.

## Evidências e limites da entrega

`backend/scripts/qualify_editing_resources.py` baixou uma variante Roboto do domínio oficial e renderizou material real existente em três proporções. A galeria local está em `artifacts/validation/editing-resources-20260906/index.html`, acompanhada dos MP4, frames e recibos em `report.json`. Os frames foram inspecionados: texto acentuado legível, apoio com máscara e composição nos três formatos. O apoio é uma imagem de teste criada localmente, não resultado de IA.

Os testes automatizados exercitam importação, isolamento entre clientes, revisão, fonte no MP4, motion combinado, seleção de acervo pelo planejador, áudio, retentativas e versão antiga. No teste de transformação, FFmpeg produz uma origem com áudio de 440 Hz e um candidato simulado com áudio de 880 Hz; o arquivo final precisa manter 440 Hz. O teste verifica também os intervalos anterior/transformado/posterior. Respostas Gemini nesses testes são simuladas: elas validam a integração, não a qualidade do modelo.

**A qualificação profissional completa ainda não está concluída.** Faltam chamadas reais com credencial de testes separada, avaliação de preservação de rosto/mãos/roupa em movimento, emendas entre transformações e a matriz completa de sete cenários nos três formatos. A análise automática inicial do planejador usa o primeiro frame de até 24 clips e os textos/transcrições fornecidos; esse método não equivale à análise integral de todos os vídeos e sons. O recibo registra a cobertura.

HyperFrames continua no caminho de componentes registrados, com suas próprias restrições. O plano V2 agora compila curvas Bézier registradas, câmera de composição, blur de camada, parallax limitado, overshoot e tipografia cinética; um smoke real do HyperFrames 0.8.31 verifica essas operações no MP4. Solicitações não suportadas são rejeitadas. Não foram certificados tracking, rotoscopia, estabilização, máscaras temporais, rampas de velocidade ou 3D. A interface não deve apresentar essas capacidades como disponíveis por mera semelhança de um resultado gerado.

As observações de creators/moonsol e as tendências continuam no repertório datado existente, com ingestão manual e deduplicação; esta implementação não ativa coleta contínua do Instagram nem treinamento automático.

### Verificações de implementação desta entrega

- Backend: a rodada combinada teve 71 testes aprovados, três falhas por falta de memória no x264 e um smoke de HyperFrames não executado por ausência de `CLICKO_HYPERFRAMES_SMOKE_CLI`. Após limitar os threads de decodificação/codificação e filtros no renderizador UGC, os dez testes desse renderizador passaram novamente, junto de dois testes adicionais de recursos/modelo. Os oito testes do worker passaram com o manifesto 0.2.0. Não há falha funcional conhecida restante nos testes executados.
- Interface: dois testes Playwright aprovados, incluindo escolha de alternativa antes do render e aplicação localizada sem aprovação humana inventada.
- TypeScript e build de produção aprovados. Neste Windows com pouca memória disponível, o build usou `NODE_OPTIONS=--max-old-space-size=512` e o TypeScript usou 768 MB. O build mantém o aviso existente de tamanho do bundle.
- Ruff aprovado nos arquivos novos e nas verificações de nomes/importações dos caminhos modificados. Os bancos dos testes ficaram em diretórios temporários, separados dos dados do projeto.
- Gemini real e Google Fonts Developer API permanecem desabilitados/sem credenciais neste ambiente. A fonte da galeria foi obtida pelo CSS público oficial e o downloader validado; isso não simula uma consulta autenticada à Developer API.

## Fontes oficiais de referência

- [Google Fonts Developer API](https://developers.google.com/fonts/docs/developer_api).
- [Gemini Omni: edição de vídeo e limitações](https://ai.google.dev/gemini-api/docs/omni).
- [Modelo Gemini Omni Flash](https://ai.google.dev/gemini-api/docs/models/gemini-omni-flash).
- [Preços Gemini](https://ai.google.dev/gemini-api/docs/pricing). Referência `google-standard-2026-09-06`: Flash US$0,75/US$3,75 por milhão de tokens de entrada/saída até dezembro de 2026; imagem 1K aproximadamente US$0,067 de saída; vídeo 720p aproximadamente US$0,10 por segundo de saída. Entradas e verificação são adicionais. Revalidar a tarifa antes de comparar faturamento futuro.
- [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html).
