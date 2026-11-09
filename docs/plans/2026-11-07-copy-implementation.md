# Fundação de copy integrada à Clicko — 07/11/2026

## O que está disponível

Nos Studios de vídeo e nos projetos do departamento criativo, o painel “Produto, estratégia e copy do anúncio” registra uma preparação MANUAL versionada por projeto/documento. Não busca sites, não extrai fatos automaticamente, não gera anúncios por LLM e não cadastra APIs.

O painel contém produto/público, oferta/provas/limites, estratégia/copy, roteiro/revisão e referências de edição. Exibe lacunas e o critério de cada etapa. Preenchimento não é prova de veracidade. Salvar não aprova: primeiro o texto é salvo, depois as confirmações humanas autorizam a aprovação dessa versão. Alterar texto invalida confirmações anteriores. São armazenadas autoria, horário e snapshots de cada versão no histórico de eventos.

Rotas autenticadas: GET/PUT /api/v1/studios/v1/copy/{project|document}/{id}. O escopo segue o projeto e o cliente atuais. Conflito de revisão não sobrescreve versão nova. Pedido repetido é reconhecido. A exportação entrega JSON da copy aprovada com sua versão. O contexto dos planejadores de edição de vídeo passa a receber a preparação vinculada ao documento ou projeto, quando existente; informação ausente continua desconhecida.

## Fluxo do cliente e lacunas

1. Informar produto, público, oferta, condições e provas; enviar materiais autorizados e rosto quando necessário. Rosto sozinho é insuficiente.
2. Descoberta manual com fontes e lacunas: implementada nesta fundação. Extração controlada de páginas/documentos, separação automática fato/declaração/hipótese e confirmação do cliente: futuras.
3. Estratégia, variantes de ângulo/hook, redação e revisão especializada: protocolo especificado pelo Copy Squad. Ainda não há execução automática desses agentes de copy no produto.
4. Roteiro audiovisual: registro manual implementado; tabela estruturada de fala/texto em tela/cena/claim/fonte/passagem: próxima implementação.
5. Aprovação e handoff: versão e JSON disponíveis. Aplicação automática dessa copy à voz e produção ainda precisa de um contrato executável entre os módulos.
6. Voz: existem integração TTS OpenRouter e rotas com binding de voz selecionada. Isso não equivale à voz do cliente clonada e qualificada no fluxo completo.
7. Rosto/avatar: há planejamento/aparência, casting e providers condicionados a runtime. Não foi qualificado um fluxo rosto enviado → apresentador falando → anúncio pronto neste trabalho.
8. Edição: comandos canônicos e nativos validados e amostras de frames existem. A LLM não navega livremente pelo sistema nem transforma capacidades ausentes em efeitos prontos.
9. Exportação técnica e avaliação humana da peça são distintas. Não houve geração nova nem aprovação criativa de vídeo nesta entrega.

## Referências de edição recuperadas

Corpus registrado de45Reels de @creators, @paulo.ia e @moonsol.design em docs/studios/research/INSTAGRAM_EDITING_VIEWING_LOG_2026-09-30.md e expansão. A pesquisa histórica registra amostragem visual e player mudo, não avaliação sonora. Não houve nova visualização nesta sessão.

- @creators: apresentador como âncora, demonstração e inserts de prova quando a mensagem os exige; atribuir autoria a cada criador, não à conta curadora.
- @paulo.ia: continuidade de personagem/objeto/pergunta, mundo específico, preparação e revelação. Não copiar simplesmente uma sequência de imagens bonitas.
- @moonsol.design: estado inicial → gatilho → estado final com alinhamento e transformação espacial. Muitos exemplos são tutoriais, não peças prontas de anúncio.

O painel permite preencher a direção de referência a partir dessas três lentes. Não instala um preset que reproduz todos os efeitos. A timeline canônica executa cortes, enquadramento e keyframes simples. Máscaras, clean plates, oclusão de texto atrás da pessoa e morphs pedem material preparado ou outro motor qualificado. Sem esse mecanismo, registrar lacuna ou fallback; não rotular fade como transformação.

## Próximo lote de até US$5 (proposto, não liberado nem consumido)

Crédito Anthropic para qualidade de copy, separado de vídeo, voz e infraestrutura: atéUS$1 para análise do dossiê/lacunas;US$1,50 para estratégia e hipóteses de hooks;US$1 para copy/roteiro;US$1 para revisão factual/CUB e correção;US$0,50 de reserva. TotalUS$5. Cada chamada futura deve registrar hipótese, versão, expectativa e evidência. Duas tentativas sem melhora: parar e diagnosticar. Não gastar com voz/cenas antes de aprovar produto, oferta e texto.

## Contrato desejado entre copy e direção

Por trecho: id, fala, texto em tela, função narrativa, claimId, fonte, material exigido, âncora, estado inicial, gatilho, estado final, operação executável, fallback e critério de revisão. Duração da voz será medida após síntese; não estimar frame perfeito por contagem de palavras. Material sintético não comprova resultado real de produto.

## Verificação

Testes sem provider: persistência parcial, replay, conflitos, isolamento de cliente, aprovação sem texto salvo rejeitada, lacunas bloqueando aprovação, nova versão invalidando revisão, histórico preservado e preparação antes de render de projeto. O teste instala um planejador que lança erro se chamado: nenhuma rota dessa fundação faz inferência.
