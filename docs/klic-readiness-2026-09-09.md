# KLIC — implementação multimodal e avaliação de prontidão

Data: 09/09/2026. Projeto: `C:\Users\pedro\Downloads\res`.

## Resultado executivo

**NÃO PRONTA PARA LANÇAMENTO.** A base conversacional, os pipelines de arquivos e a integração de voz foram implementados e tiveram validação local. Entretanto, a chave `GEMINI_API_KEY` não está configurada no ambiente avaliado. Portanto, não foi possível aprovar geração real, interpretação visual, compreensão dos documentos pelo modelo ou Speech-to-Text real.

As duas vozes do Google Cloud Text-to-Speech foram exercitadas contra o serviço real e retornaram MP3s. Isso comprova síntese no servidor, não a jornada completa de conversa falada no navegador.

- `npm run lint`: aprovado; este comando executa `tsc --noEmit`, não um linter ESLint separado.
- `npm test`: **56 testes aprovados, zero falhas**, aproximadamente 14,9 segundos na última execução.
- `npm run build`: aprovado, incluindo frontend, servidor e worker de processamento.
- `npm audit --omit=dev`: zero vulnerabilidades conhecidas reportadas na execução.
- Worker compilado de produção: executado com TXT UTF-8, resultado correto.
- Navegador: Markdown, envio repetido, histórico/reload, alternância de conversas, falha/retry, scroll manual e anexos TXT/CSV exercitados em ambiente isolado.

Os testes com respostas controladas estão explicitamente separados da aplicação normal. Não constituem evidência de inteligência ou precisão do provedor real. A aplicação normal mantém erros reais quando a integração está indisponível; nenhum provedor fictício foi introduzido no caminho de produção.

## 1. Arquitetura encontrada

O projeto usa React 19, TypeScript, Vite, Express, Google GenAI e Google Cloud TTS. Já existiam:

- `AIChatContext` e `AIChatView`, com compositor, modos, histórico local, favoritos, ações e integração com outras áreas.
- Núcleo KLIC com adapters operacionais, escopos de workspace/usuário/cliente, permissões, memória e rastreamento.
- Autenticação/governança no backend e repositório JSON atômico reutilizável.
- Integração real Gemini no servidor, endpoints legados e serviços específicos de imagem/vídeo.
- Google Cloud TTS com vozes configuradas; fallback real de síntese do navegador.
- Captura baseada no reconhecimento de fala do navegador e gerenciamento de reprodução.

Problemas identificados no caminho conversacional:

- O histórico do navegador era a principal fonte de conversas; uma nova conversa era representada por recorte de mensagens, sem entidade persistida própria no servidor.
- Contexto conversacional e anexos de turnos anteriores não tinham um pipeline unificado e persistente.
- Documentos não possuíam leitura funcional equivalente aos formatos oferecidos pela interface.
- Respostas não tinham renderização completa e segura de Markdown.
- Havia riscos de duplicação, requisições concorrentes, respostas tardias em outro contexto e recursos de áudio pendentes.
- O endpoint de síntese precisava receber a mesma proteção de autenticação/permissão do restante da KLIC.

Não foi reconstruída a identidade visual da KLIC nem substituídos os serviços de criação de imagem/vídeo. Os ajustes de interface foram vinculados a funcionalidades: renderização, anexos, estados, histórico e controles de recuperação.

## 2. Implementação realizada

### Conversas e persistência

Foi criada uma entidade de conversa no servidor, com título, ID, datas e mensagens próprias. Cada mensagem tem autor, ID, `requestId`, conteúdo, estado e seus anexos.

O repositório reutiliza a escrita atômica existente e guarda as conversas em `.clicko-data/conversations`, fora de pastas públicas. O diretório de cada escopo deriva de workspace, usuário e cliente. Alterar um ID de conversa ou arquivo não concede acesso a outro escopo.

O frontend passa a consultar o servidor como fonte de verdade. Apenas a seleção da conversa fica no armazenamento local. Quando não há conversas no servidor, o histórico legado do mesmo escopo pode ser importado; o backup local original é preservado. Os binários antigos que não estavam persistidos não são reconstruídos nem apresentados como recuperados.

Foram implementados listar, criar, ler, limpar, favoritar, baixar anexos, enviar, cancelar, tentar novamente e importar o histórico legado. A limpeza remove também a revisão `.previous` das conversas correspondentes.

A listagem mantém cache limitado de metadados e verifica a revisão do arquivo. Isso evita reler os binários de todas as conversas a cada atualização da lista. Alterações feitas por outra instância invalidam esse cache, com teste de regressão.

### Envio, estados e streaming

- Trava síncrona no compositor e no hook para impedir clique duplo/Enter repetido.
- Um processamento ativo por usuário/workspace no servidor.
- IDs estáveis e deduplicação no backend.
- Mensagem otimista imediata, reconciliada com a versão persistida.
- Fluxo NDJSON com eventos de aceitação, fase, fragmento, conclusão e erro.
- Decodificação incremental UTF-8 e atualização visual agrupada a cada 50 ms.
- Retry da última resposta falha/cancelada reutiliza os IDs, sem duplicar a pergunta.
- Cancelamento interrompe a requisição; a reconciliação aguarda a conclusão do cancelamento no servidor.
- Falha não persistida devolve texto/anexos ao compositor; falha persistida mantém a mensagem no histórico.
- Hidratação e troca de escopo têm proteção contra respostas atrasadas.

A mensagem temporária e a resposta parcial não são confundidas com uma resposta concluída. Uma geração abandonada por reinicialização pode ser marcada como interrompida na leitura seguinte.

### Contexto

O backend monta o contexto a partir da conversa pertencente ao usuário, e não aceita o histórico arbitrário do cliente como fonte de verdade.

Há uma janela recente de até 48 mil caracteres, recuperação lexical de até quatro trechos anteriores de 1.500 caracteres, seleção de trechos de documentos, manifesto de imagens e dados operacionais limitados. Preferências já autorizadas do núcleo KLIC continuam sendo incluídas. Conteúdo de arquivos, histórico e fontes é tratado como dado não confiável, não como instrução de sistema.

Os documentos extraídos permanecem relacionados aos IDs e nomes dos anexos. Imagens anteriores relevantes podem ser reenviadas ao modelo. Arquivos mencionados pelo nome são priorizados. O prompt informa omissões e trechos parciais, sem inventar resumos do conteúdo que ficou fora da janela.

Esta estratégia é limitada por caracteres/payload, não um tokenizer específico do modelo nem uma busca semântica vetorial. Referências muito antigas ou ambíguas não têm garantia de recuperação perfeita. A precisão em conversas longas precisa ser avaliada com o provedor real.

### Renderização e compositor

`react-markdown` e `remark-gfm` renderizam títulos, parágrafos, listas, negrito, itálico, links, citações, tabelas, divisores e código. HTML bruto não é executado; URLs inseguras são descartadas; links externos usam `noopener noreferrer`. Imagens remotas provenientes de Markdown não são carregadas automaticamente.

Tabelas têm área própria de scroll, textos quebram dentro do espaço disponível e blocos de código preservam leitura. O Markdown é memoizado para não reprocessar todas as respostas concluídas a cada fragmento novo.

Enter envia e Shift+Enter cria linha, respeitando composição IME. O campo cresce até a altura máxima existente. Não envia texto vazio sem anexos. Após enviar, o compositor é limpo. Acompanhamento automático do scroll para quando o usuário sobe manualmente; existe retorno à resposta mais recente.

### Anexos reais

O pipeline é: seleção → validação no cliente → envio autenticado → validação no servidor → worker de extração → persistência → seleção de contexto → modelo → resposta persistida.

| Formato | Processamento implementado | Limitação explícita |
|---|---|---|
| PNG, JPEG, WebP | Validação de MIME, tamanho e assinatura; payload binário encaminhado ao Gemini | Análise visual real não executada sem a chave |
| PDF | `pdf-parse`/PDF.js, texto por página e seleção de trechos | Sem OCR; PDF sem texto legível gera erro; máximo 80 páginas |
| TXT | Decodificação UTF-8 estrita e seleção de trechos | Binário/encoding inválido é recusado |
| DOCX | `mammoth.extractRawText`, com inspeção prévia do ZIP | Extração textual, não reprodução de layout/imagens incorporadas |
| CSV | ExcelJS, detecção básica de vírgula/ponto e vírgula/tabulação | Arquivos ambíguos exigem normalização; não há suporte declarado a todos os dialetos |
| XLSX | ExcelJS, abas, linhas, células e estatísticas numéricas por coluna | Fórmulas não são executadas; utiliza resultados já salvos |
| MP3, WAV, WebM, OGG | MIME/assinatura e encaminhamento para transcrição Gemini | Integridade básica não substitui decodificação completa; STT real pendente |

Não foi anunciado suporte a DOC, XLS, ZIP arbitrário, macros ou outros formatos sem leitor implementado.

O processamento de documentos fica em worker separado, com limite de tempo, heap e concorrência. Falhas dos parsers não expõem stack traces ou mensagens internas: somente mensagens de validação da aplicação podem atravessar essa fronteira.

Depois do envio, arquivos são acessados por endpoint autenticado, não por URL pública. Prévias e reprodução de anexos usam blobs carregados sob demanda, com revogação das URLs temporárias.

### Voz

A captura usa `getUserMedia`/`MediaRecorder` e envia o áudio ao endpoint autenticado de transcrição. Configura cancelamento de eco e redução de ruído. Há estados de conexão, escuta, processamento, fala, pausa e encerramento.

- Apenas uma captura/transcrição por vez.
- Detecção de silêncio para concluir a fala; limite de gravação de 60 segundos.
- Sem fala por 15 segundos: orientação explícita, sem inventar transcrição.
- A transcrição concluída entra na mesma conversa textual.
- O microfone é encerrado antes da reprodução, evitando captura simultânea da saída sintetizada.
- Encerramento, troca de escopo e desmontagem cancelam captura/transcrição/reprodução e liberam tracks, AudioContext, timers e URLs.
- Promises de reprodução interrompida são liquidadas, evitando processos pendentes.
- TTS Google existente preservado; fallback de síntese do navegador permanece como fallback real, não voz Google simulada.

O cliente dá suporte aos containers de gravação WebM/OGG quando disponíveis. Navegadores sem esses recursos recebem erro claro; compatibilidade ampla com Safari/iOS não foi aprovada. Interrupção física automática por fala sobreposta não foi prometida: o controle de interrupção existe, mas captura e reprodução simultâneas são evitadas.

## 3. Limites operacionais

| Recurso | Limite atual |
|---|---|
| Mensagem textual | 32.000 caracteres |
| Anexos por envio | 4 |
| Tamanho total por envio | 6 MiB |
| Anexos armazenados por conversa | 24 MiB |
| Conversas por escopo | 100 |
| Mensagens por conversa | 1.000 |
| Texto extraído de arquivo | 500.000 caracteres |
| PDF | 80 páginas |
| XLSX/CSV | 20 abas; 20.000 linhas; 200 colunas; 120.000 células |
| ZIP de DOCX/XLSX | 24 MiB descompactados e até 2.000 entradas |
| Workers | Até 4 simultâneos; heap de 128 MiB por worker; prazo de 15 s |
| Geração | Prazo de 90 s; cliente cancela em 100 s; até 64 mil caracteres de resposta |
| Transcrição isolada | Prazo de 45 s |
| Contexto | Limite de 220.000 bytes de JSON textual; até 4 binários e 12 documentos selecionados |
| Rate limit conversacional | 12 operações de geração/transcrição por minuto por usuário/workspace |
| Voz | 40 requisições por minuto por usuário/workspace; TTS com timeout de 20 s |

O orçamento de heap do worker não é um limite global absoluto para memória nativa/RSS. O armazenamento e os bloqueios de requisições são locais ao processo/servidor. Implantação horizontal requer armazenamento compartilhado adequado, locks e rate limit distribuídos.

Anexos persistentes duram enquanto a conversa existir; não foi inventada uma política de expiração automática. A política de retenção, backups, criptografia de disco e quota global precisa ser definida para lançamento. Não houve migração para outro banco de dados.

## 4. Arquivos e integrações

Principais arquivos desenvolvidos:

- `src/klic/conversation.ts`: contratos e validação compartilhada.
- `src/klic/useConversations.ts`: histórico, envio, streaming e reconciliação.
- `src/klic/KlicMarkdown.tsx` e `.css`: renderização segura e responsiva.
- `src/klic/ChatAttachment.tsx`: acesso autenticado e prévias.
- `server/klic/conversations.ts`: persistência e janela de contexto.
- `server/klic/conversationRouter.ts`: endpoints e orquestração.
- `server/klic/attachments.ts`: leitores e recuperação de trechos.
- `server/klic/attachmentProcessing.ts`, `attachmentWorker.ts`, `attachmentErrors.ts`: isolamento, limites e erros públicos.
- `server/klic/conversations.test.ts`: regressões e integração HTTP.
- `scripts/klic-ui-fixture.ts` e `scripts/fixtures/klic/*`: ambiente exclusivamente de teste, sem importação no produto.

Arquivos existentes integrados/ajustados: `server.ts`, `server/klic/router.ts`, `server/voice/router.ts`, `server/voice/providers/googleCloudTtsProvider.ts`, `src/context/AIChatContext.tsx`, `src/components/AIChatView.tsx`, `src/hooks/useKlicVoice.ts`, `scripts/run-audit-tests.cjs`, `package.json`, `package-lock.json` e `.env.example`.

Foram preservadas as alterações já presentes na árvore de trabalho. A árvore contém mudanças de tarefas anteriores; o `git diff` total não deve ser atribuído a esta entrega. Também foram concluídos reparos pontuais pendentes em Configurações e um ajuste exclusivamente de tipagem do ícone de navegação. Não foi feito commit, push, reset ou descarte de mudanças do usuário.

Integrações utilizadas:

- Google GenAI, por `generateContentStream` e `generateContent`, no servidor. API de referência: [Google Generate Content](https://ai.google.dev/api/generate-content).
- Google Cloud Text-to-Speech, reutilizando as vozes configuradas do projeto.
- `react-markdown` e `remark-gfm`; referência de segurança: [react-markdown](https://github.com/remarkjs/react-markdown#security).
- `pdf-parse` 2.4.5, Mammoth, ExcelJS e fflate para leitura real de arquivos.

## 5. Testes e evidências

### Automatizados

Os 56 testes incluem a suíte preexistente de autenticação, governança, persistência, permissões, Analytics, automações, tema e temporização da KLIC, além dos novos testes conversacionais.

Cobertura nova comprovada:

1. Persistência de UTF-8/emojis e anexos; isolamento por usuário/workspace/cliente; rejeição de path traversal; metadados públicos sem binários; limpeza.
2. Janela de histórico limitada, recuperação de trechos e exclusão de respostas falhas do contexto.
3. Cache de listagem invalidado por atualização externa e filtragem de erros internos de parser.
4. CSV e DOCX reais; recusa de arquivo vazio, inválido, MIME conflitante, UTF-8 inválido, PDF corrompido, extensão não suportada e tamanho/quantidade excedidos.
5. XLSX com múltiplas abas, números, texto, datas e resultados salvos de fórmulas.
6. PDF textual, PDF sem texto, execução de worker e abort.
7. Requisições simultâneas, resposta 429, cancelamento e IDs preservados.
8. Integração HTTP autenticada: NDJSON, UTF-8, contexto anterior, conversa independente, deduplicação, erro/retry, reinicialização do repositório, download privado e proteção da voz.
9. Quatro anexos mistos numa mensagem (PNG, CSV, TXT e PDF), encaminhamento binário da imagem e reutilização no turno seguinte, sem carregar anexos no próximo compositor.
10. Áudio anexado e endpoint de transcrição com provedor controlado, comprovando encadeamento — não qualidade de STT real.

Os testes do provedor controlado verificam os prompts/arquivos recebidos. Não medem a veracidade das respostas de um modelo real.

### Navegador

Ambiente isolado em loopback, com dados temporários separados da conta real:

- Texto português com parágrafos, acentos e emoji, Shift+Enter e Enter repetido: uma pergunta exibida.
- Resposta longa com 70 parágrafos e streaming progressivo.
- Renderização visível de títulos, listas, tabela, citação, código, links e caracteres especiais.
- Inspeção DOM: nenhuma tag script ou link `javascript:` dentro da resposta.
- Reload: uma ocorrência da pergunta e último parágrafo preservado.
- Nova conversa e alternância para uma conversa existente pelo painel.
- Falha controlada e retry: pergunta preservada e erro legível, sem nova pergunta duplicada.
- Scroll manual durante geração: controle de retorno à última resposta disponibilizado.
- Seleção de TXT/CSV, remoção individual, reanexação, envio conjunto, compositor limpo e anexos preservados depois de reload.
- Viewport de 390×844: inspeção visual da conversa longa; sem overflow horizontal. Viewport de 1280×720: DOM sem overflow horizontal.
- Console da última sessão limpa: nenhuma entrada `warn`/`error` capturada. Um conflito de porta HMR do servidor de testes foi corrigido usando porta exclusiva.

No servidor normal, a ausência do Gemini produziu erro real e recuperável, sem resposta fictícia.

### Serviços reais

- Google TTS, voz feminina: `audio/mpeg`, 12.672 bytes.
- Google TTS, voz masculina: `audio/mpeg`, 11.712 bytes.
- Worker compilado `dist/attachmentWorker.cjs`: TXT com português/emoji extraído corretamente.
- Não foi registrada ou enviada fala do usuário durante a validação. Os áudios de TTS usaram apenas frases sintéticas de teste.

O servidor auxiliar de testes foi encerrado; o servidor normal permaneceu ativo e `/api/health` respondeu `ok`. A ferramenta bloqueou a remoção dos quatro diretórios temporários da fixture no Windows. Eles contêm somente os dados controlados de QA e ficaram em `C:\Users\pedro\AppData\Local\Temp`, com os nomes `clicko-klic-ui-O7VulW`, `clicko-klic-ui-Ru2HNf`, `clicko-klic-ui-sxRerL` e `clicko-klic-ui-XVESra`. A limpeza desses diretórios está pendente; os históricos reais da aplicação não foram apagados.

### Erros encontrados e corrigidos durante a validação

- Parser PDF anterior falhando em arquivo vazio: atualização do parser e extração de texto por página, com teste de PDF vazio.
- Promises de reprodução sem liquidação ao interromper áudio: cancelamento explícito.
- Corrida entre cancelar geração e reler estado: espera pela finalização no servidor.
- Ações durante hidratação e respostas tardias: guardas de geração/escopo.
- Erros internos potencialmente expostos pelo nome do arquivo/parser: allowlist de mensagens públicas.
- Leituras repetidas de binários na listagem: cache de metadados limitado e validado por revisão.
- Captura/reprodução atravessando troca de contexto: encerramento na mudança de escopo/conversa.
- Conflito de HMR da fixture: porta exclusiva, confirmado pelo console limpo.
- Ajustes de tipos e erro estrutural preexistente necessários para que o projeto voltasse a passar no typecheck.

## 6. Segurança e performance

Endpoints conversacionais e TTS exigem autenticação/permissão. Conversas/arquivos têm ownership por escopo; origem diferente é recusada quando enviada pelo navegador. Os testes cobrem negativas de autenticação, escopo e origem.

Credenciais permanecem no servidor. A inspeção dos valores configurados contra o bundle frontend não encontrou os valores de credenciais verificados. Também não encontrou a resposta da fixture no bundle. Essa inspeção não equivale a pentest global ou prova de ausência de todos os possíveis segredos do projeto.

Validação existe no frontend e backend. DOCX não gera HTML executável, fórmulas não são executadas, Markdown bruto não executa scripts e anexos não ficam em diretório público. Não foi implementado antivírus ou sandbox de sistema operacional; os workers constituem isolamento de processamento, não uma fronteira de segurança absoluta contra falhas das bibliotecas.

O build ainda emite aviso de chunk frontend acima de 500 kB: aproximadamente 936,9 kB minificado / 264,8 kB gzip para o chunk principal. Não foi reestruturado o empacotamento de toda a Clicko para ocultar esse aviso. Há memoização de Markdown, batching de streaming, extração em worker, limites e cache de listagem, mas não foi executado benchmark de carga multiusuário, heap prolongado ou aparelhos físicos de baixo desempenho.

## 7. Configuração e operação

Para executar os caminhos reais de chat, visão e STT, configurar **no servidor** `GEMINI_API_KEY` válida. `KLIC_CHAT_MODEL` permite selecionar o modelo disponível no projeto Google; o default implementado é `gemini-2.5-flash`. Confirmar disponibilidade, limites e permissões do modelo na conta antes de homologar. Não usar variável `VITE_*` para segredo.

Para TTS: `KLIC_GOOGLE_TTS_ENABLED=true`, credenciais Google válidas e, quando necessário, `GOOGLE_CLOUD_PROJECT`. Neste ambiente, flag e arquivo de credenciais existiam e as duas sínteses reais passaram. Nenhuma credencial foi incluída neste relatório.

Implantação prevista:

1. Usar versão de Node compatível; validado em Node 24.15.0. `pdf-parse` requer Node `>=20.16.0 <21` ou `>=22.3.0`.
2. Instalar dependências pelo lockfile e executar `npm run lint`, `npm test`, `npm run build`.
3. Iniciar pela raiz do projeto, com `NODE_ENV=production`, usando `npm start`.
4. Incluir `dist/attachmentWorker.cjs` e dependências de runtime; o build não embute todas as dependências externas.
5. Manter `.clicko-data` em volume privado e persistente. Não expor backups nem credenciais pelo servidor estático/proxy.
6. Configurar HTTPS, limites de corpo/tempo e streaming sem buffering no proxy. Desativar o bypass de desenvolvimento para homologação real de autenticação.
7. Não publicar `scripts/klic-ui-fixture.ts` como serviço de produto. A fixture fornece respostas marcadas como controladas e serve exclusivamente a QA.

## 8. Validações ainda necessárias

- Configurar Gemini e executar perguntas reais em português, follow-ups, conversas extensas e referências a anexos anteriores.
- Executar compreensão real de PNG/JPEG/WebP, PDF, TXT/DOCX, CSV/XLSX e mistura de anexos; comparar respostas com resultados esperados.
- Testar MP3/WAV/WebM/OGG reais, duração longa, silêncio, ruído, corrupção além da assinatura e qualidade de transcrição.
- Testar permissão de microfone concedida, negada e revogada; pausas, cancelamento, navegação, retorno e ausência de tracks residuais.
- Exercitar reprodução audível no navegador, interrupção no meio, retomada e conversa completa sem feedback acústico.
- Executar perda de rede e timeout real de ponta a ponta, não apenas abort/falha de provedor controlado.
- Executar jornada prolongada alternando todas as modalidades com o modelo real.
- Homologar browsers/dispositivos alvo, incluindo compatibilidade de codecs, dispositivos físicos e temas; os testes de viewport realizados não cobrem toda essa matriz.
- Definir retenção, quotas globais, restauração de backup e arquitetura de produção de uma ou múltiplas instâncias; realizar carga e revisão de segurança independente.

## 9. Matriz de prontidão para produção

As classificações abaixo avaliam o recurso completo, não somente a existência de um botão ou endpoint.

| Item | Classificação | Evidência e ressalva |
|---|---|---|
| Chat por texto | NÃO APROVADO | Envio, dedup, contexto, histórico e UI testados com provedor controlado; geração real bloqueada pela chave ausente |
| Qualidade/renderização das respostas | APROVADO COM RESSALVAS | Markdown e segurança visual aprovados localmente; qualidade semântica do modelo não avaliada |
| Streaming | APROVADO COM RESSALVAS | NDJSON, UTF-8, batching e cancelamento testados; stream real Gemini/proxy não homologado |
| Contexto | APROVADO COM RESSALVAS | Janela, trechos e isolamento comprovados; coerência longa e recuperação real pendentes |
| Histórico | APROVADO COM RESSALVAS | Criar/listar/alternar/reload testados; matriz multi-browser e migração de todos os legados pendente |
| Persistência | APROVADO COM RESSALVAS | Repositório/restart/ownership/cache testados; retenção e escala de produção pendentes |
| Voz | NÃO APROVADO | Máquina de estados implementada; jornada física completa não executada |
| Speech-to-Text | NÃO APROVADO | Endpoint e encadeamento testados com provedor controlado; Gemini real indisponível |
| Text-to-Speech | APROVADO COM RESSALVAS | Duas sínteses reais Google retornaram MP3; reprodução audível e todos os browsers não homologados |
| Interrupção de voz | NÃO APROVADO | Cancelamento/limpeza implementados; prova com áudio tocando e microfone real pendente |
| Envio de áudio | NÃO APROVADO | Validação/persistência/transcrição controlada testadas; compreensão real pendente |
| Imagens | NÃO APROVADO | Binário encaminhado e reaproveitado no contexto em teste; análise visual real pendente |
| PDFs | NÃO APROVADO | Extração e erros aprovados localmente; uso do conteúdo pelo modelo real pendente; sem OCR |
| Documentos | NÃO APROVADO | TXT/DOCX extraídos; respostas reais baseadas neles não homologadas |
| CSV | NÃO APROVADO | Parser, estatísticas e upload/reload testados; interpretação real e dialetos extensos pendentes |
| XLSX | NÃO APROVADO | Abas/células/estatísticas/resultados salvos testados; perguntas analíticas reais pendentes |
| Múltiplos anexos | APROVADO COM RESSALVAS | Quatro tipos no HTTP e TXT/CSV no navegador; raciocínio multimodal real pendente |
| Tratamento de erros | APROVADO COM RESSALVAS | Falha, retry, abort, limites e ownership testados; perda real de rede e todos os timeouts pendentes |
| Responsividade | APROVADO COM RESSALVAS | 390 px e 1280 px sem overflow horizontal observado; matriz completa de browsers/dispositivos pendente |
| Performance | APROVADO COM RESSALVAS | Worker, limites, cache e batching; aviso de bundle grande e ausência de carga/heap prolongados |
| Segurança | APROVADO COM RESSALVAS | Auth/escopo/origem/XSS/arquivos privados e audit verificados; não é pentest ou homologação operacional completa |
| Estabilidade geral | NÃO APROVADO | Testes locais verdes, porém modalidades críticas ainda sem jornada real completa |

**Avaliação final: NÃO PRONTA PARA LANÇAMENTO.** O próximo passo obrigatório é configurar o provedor de chat/STT e executar a rodada real multimodal e de voz, seguida da homologação operacional. O sucesso do build e dos testes controlados não substitui essa aprovação.
