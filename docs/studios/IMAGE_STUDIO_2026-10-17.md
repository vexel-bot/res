# Estúdio de Imagens — implementação de 17/10/2026

## Estado da entrega

Interface e integração de Imagens implementadas no checkout local, com criação e edição separadas, prévia ampla, referências, histórico, avaliação visual, download, Biblioteca e assistência da KLIC. O PhotoCraft e o Departamento Criativo originais permanecem disponíveis como caminhos avançados/editoriais.

**Não declarar qualificação comercial ou geração ponta a ponta concluída neste ambiente.** O provedor de imagem está desabilitado e sem credencial neste serviço; o runtime PhotoCraft/WASM não está provisionado; a automação do navegador está desativada no Work. A política de cotas foi confirmada pelo usuário e implementada: uma unidade por solicitação de imagem aceita, mesmo quando o job falha ou é cancelado. Não houve chamada paga de teste nem exposição de chaves.

## Análise e reaproveitamento

- `DepartmentStudio` e `departmentApi` continuam responsáveis pelos pedidos editoriais anteriores, carrosséis, produção e revisões já existentes. Não foram removidos.
- `CraftStudio`, `useCraftStudio`, `useCraftBrowser` e `craftApi` permanecem responsáveis por edição nativa, camadas, cores, formatos, texto, arquivo `.pcraft`, versões, undo/redo, recuperação, IA por comandos e exportação.
- `ProductDataProvider`, a sessão da Clicko e o proxy assinado preservam o contexto de usuário/workspace/cliente. O estado da nova tela é desmontado quando esse contexto muda; URLs privadas são revogadas e leituras descartadas.
- `productApi` fornece documentos, revisões, assets e jobs. `ClickoSelectMenu`, a tipografia de sistema e o tema existente foram reutilizados.
- `useKlicClient` e `useKlicPageDetails` conectam a assistência textual à KLIC existente. A sugestão aparece separadamente e só substitui a descrição depois da ação explícita “Usar esta sugestão”. Nenhum chat global foi reconstruído.
- Foi encontrada geração/edição real em `editing_resources` + `gemini_editing`, com jobs, referências autorizadas, preservação de origem, armazenamento, orçamento e revisão humana. Essas rotas já existiam, mas não estavam incluídas em `studio_app`.
- A rota antiga `/api/ai/image-edit` apenas devolve a origem como se tivesse editado. A derivação antiga `/api/v1/assets/{id}/derive` retorna 410 e o `/api/ai/generate-image` legado não oferece o ciclo persistente de jobs. **Nenhuma dessas rotas é usada pela nova tela.** Não foram modificadas fora do escopo.

## Funcionalidades conectadas

1. **Criar imagem:** descrição, finalidade e enquadramento desejado; estilo, instruções adicionais, preservação e contexto visual de marca sob demanda. A configuração é salva no briefing existente, sem reconstruir composição nativa.
2. **Editar imagem:** selecionar/upload de PNG/JPEG/WebP, descrição da alteração e instruções do que preservar. A origem é identificada e permanece armazenada; o resultado é outro asset.
3. **Referências:** até três referências, autorização explícita de uso/envio e vínculo ao documento. Materiais com revisão visual pendente ou uso restrito não são liberados automaticamente.
4. **Upload:** usa o catálogo/armazenamento já existentes. O fluxo da interface aceita arquivos de até 12 MB; o backend continua validando formato, pixels, conteúdo e seus próprios limites. Nenhuma segunda biblioteca foi criada.
5. **Jobs:** envio com `Idempotency-Key`, acompanhamento de estados/progresso reais, cancelamento e retry admitido pelo backend. Antes do POST, o navegador guarda o pedido exato com chave isolada por usuário/workspace; se a resposta for incerta, “Verificar pedido” repete essa mesma identidade. A criação de rascunho com resposta incerta é conciliada por `correlationId` antes de novo POST. Cada novo job aceito desconta uma unidade da cota de imagens, independentemente do resultado. Reenvios com a mesma identidade e tentativas do próprio job não descontam novamente.
6. **Resultados:** somente `succeeded` com `assetId` confirmado apresenta imagem. O blob privado tem checksum conferido quando disponível. Não são usados exemplos ou imagens de estoque para substituir resultados ausentes.
7. **Comparação e continuidade:** original e edição aparecem como arquivos separados. O resultado é salvo pelo servidor na Biblioteca. Download usa o MIME real; após avaliação visual, é possível continuar editando, reutilizar como referência ou vinculá-lo como material do PhotoCraft.
8. **Avaliação visual:** `review` registra checksum, decisão e observação do usuário. Isso admite um material para uso, não aprova uma publicação. Uma verificação automática não substitui essa avaliação.
9. **Histórico:** documentos salvos e jobs de imagem do ambiente, com título/data/revisão/status e reabertura. As versões e snapshots nativos continuam no PhotoCraft. O briefing conserva dependências e evidências preexistentes.
10. **KLIC e marca:** aprimoramento textual real por `/api/klic/chat`; inclusão opcional apenas dos dados visuais autorizados disponíveis no contexto atual. Marca sem dados não recebe preferências inventadas.

## Endpoints reutilizados

| Finalidade | Operação existente |
| --- | --- |
| Ambiente e Biblioteca | `GET /api/v1/studios/v1/bridge/session` |
| Criar/listar/reabrir/salvar projeto | `POST/GET /studios/v1/documents`, `GET/PUT /studios/v1/documents/{id}` |
| Disponibilidade e modelo | `GET /studios/v1/editing/ai`, `GET /studios/v1/editing/gemini` |
| Uso do provedor | `GET /studios/v1/editing/usage` |
| Criação e edição por IA | `POST /studios/v1/documents/{id}/editing-ai-jobs` |
| Consultar/cancelar/repetir job | APIs existentes de `/studios/v1/jobs` |
| Upload | `POST /studios/v1/editing/resources/upload` |
| Ler arquivos privados | `GET /assets/{id}`, `GET /assets/{id}/content` |
| Avaliação visual | `POST /studios/v1/editing/resources/{id}/review` |
| Vincular material aprovado | `POST /studios/v1/documents/{id}/editing-resources` |
| Assistência textual da KLIC | `POST /api/klic/chat` |

Os caminhos de `/studios/v1` e `/assets` acima têm prefixo `/api/v1`. Não foram criados serviços de IA, endpoints equivalentes ou contratos de banco paralelos.

`backend/app/studio_app.py` registra **somente sete rotas** já existentes de recursos/imagem, mantendo autenticação pelo bridge. Requisições de geração/edição devem corresponder ao módulo ativo; um contexto Imagens não executa `generate_video`, `edit_video` ou `plan` por esse caminho. O endpoint genérico `/jobs` não admite criações/edições de imagens que contornem a entrada com cota. Outros endpoints de produção/aquisição não foram expostos por essa alteração.

## Regra comercial confirmada e aplicada

- Uma unidade de `image_generations` por novo job de criação/edição de imagem aceito. O consumo permanece em caso de falha de processamento, indisponibilidade da fila após registro ou cancelamento.
- O proxy reserva a unidade **antes** de enviar a solicitação, usando o mesmo pool do plano e os limites individuais existentes. Contador e recibo são persistidos juntos no snapshot atômico da governança, sem outro banco/serviço de cobrança.
- A confirmação exige resposta de sucesso com o job, documento, operação e chave esperados. Uma rejeição explícita antes da admissão libera a reserva; não é um estorno por falha de geração.
- Falha de transporte, timeout, resposta 5xx ou confirmação inválida mantêm a reserva pendente. A interface orienta a conferir o mesmo pedido; não há liberação automática que permita gasto duplicado. Esse caso exige conciliação pelo mesmo identificador antes de tratar a unidade como consumo confirmado.
- Reenvios com a mesma chave, documento e conteúdo não descontam novamente, inclusive após reinício ou esgotamento posterior da cota. Alterar documento/conteúdo mantendo a chave é conflito. A identidade acompanha o workspace/cliente do backend, não somente uma aba ou usuário do navegador.
- As tentativas internas e a ação de repetir o **mesmo job** não criam outro consumo. Uma nova geração/edição com nova chave corresponde a outro pedido e consome outra unidade. Downloads, leitura, upload e cancelamento não acrescentam unidades de geração.
- Pedidos simultâneos com a mesma chave são serializados; chaves distintas disputam o saldo de forma síncrona antes do envio. Caminhos com segmentos URL-encoded também são contabilizados. A guarda do bridge acompanha as formas JSON aceitas pelo FastAPI (`application/json`, `+json` e ausência de Content-Type), inclusive para impedir uso da aba Vídeo ou da fila genérica como desvio da admissão de imagens.
- Falha de persistência impede o envio ou mantém o recibo durável anterior para recuperação. Não são retornadas mensagens internas do armazenamento.
- Não houve mudança de preços, quantidades de plano, pagamentos ou regras de outros recursos. As rotas legadas permanecem fora desta integração; a regra aqui vale para a nova admissão do Estúdio de Imagens. A conciliação de **storage_bytes** do object storage Python com a governança Node continua fora desta implementação de cota de geração.

## Limites reais e pendências

- **Credencial/provedor:** verificação local encontrou `gemini_enabled=False` e nenhuma credencial de imagem configurada. A interface informa indisponibilidade e não inicia geração. Não foi copiada a credencial da KLIC nem alterado `.env`.
- **Parâmetros:** o adaptador real fixa `imageSize=1K` e uma saída por chamada. Não aceita escolha de qualidade, seed, lote de variações ou dimensões exatas. A proporção é uma orientação textual explicitamente identificada como tal; dimensões de composição continuam no editor nativo. Não foram adicionados controles inoperantes.
- **Operações sem ferramenta dedicada:** remoção de fundo, expansão, substituição de objetos e preservação são instruções ao modelo, não recursos garantidos ou máscaras pixel a pixel. Resultados devem ser avaliados.
- **Native/WASM:** PhotoCraft exige os builds/codecs/recursos existentes descritos em `workers/craft/README.md`. Não foi possível qualificar pixels, camadas e exportação nativos aqui.
- **Cotas comerciais:** o contador `image_generations` está ligado à nova admissão conforme a regra confirmada acima, com testes HTTP de persistência, concorrência e isolamento. O orçamento financeiro do provedor continua sendo uma proteção independente. A cota Node de armazenamento (`storage_bytes`) ainda não foi conciliada com o object storage Python; não apresentar essa integração como implementada.
- **Aprovação/publicação:** usa somente o caminho editorial existente para conteúdos vinculados. Um projeto avulso não recebe vínculo de publicação fictício. Avaliar material não aprova post.
- **Validação visual:** a habilidade Computer Use retornou “Local browser use is disabled in Work settings”. Não houve inspeção visual desta nova tela em claro/escuro ou desktop/mobile e não foi usado outro controlador para contornar essa configuração. CSS contém os temas, breakpoints e redução de movimento, mas isso não equivale a QA visual.

## Arquivos desta etapa

- Novos: `src/studios/image/ImageStudio.tsx`, `imageApi.ts`, `imageModel.ts`, `image-studio.css`, `imageModel.test.ts`.
- Integração: `src/studios/ClickoStudioView.tsx`, somente o encaminhamento da área Imagem; a implementação de Vídeo não foi editada.
- Backend: `backend/app/studio_app.py`, inclusão seletiva de rotas existentes e guarda de contexto de operação.
- Cota de imagens: `server/studios/imageQuota.ts`, `server/studios/proxy.ts` e `server/governance.ts`; reutilização do contador e snapshot atômico existentes. Campo opcional de recibos mantém leitura dos snapshots anteriores, sem migração de banco ou novo arquivo de cobrança.
- Testes de cota: `server/studios/imageQuota.test.ts`, nove cenários mais o teste agregador.
- Testes: `backend/tests/test_image_frontend_contract.py`; atualização da asserção de rota em `tests/unit/craftState.test.ts` para reconhecer o novo componente e a preservação do Departamento/PhotoCraft.
- Este relatório. Nenhuma alteração em banco, variáveis de ambiente, autenticação, preços/quantidades dos planos, pagamentos, chat global, Biblioteca global ou implementação de Vídeo.

## Verificações

- Testes de modelo: 10 casos de limites, upload, contratos, não substituição de composição nativa, persistência de referências, autorização explícita, preservação de restrições, jobs, opt-in da marca, resultado confirmado e recuperação idempotente.
- `npm test` — **174 testes aprovados**, sem falhas, incluindo a nova suíte de cota (nove cenários e agregador). Os 10 testes de modelo de Imagem também foram executados após o ajuste defensivo para projetos legados sem `provenance`.
- `npm run lint` — TypeScript sem erros.
- `npm run build` — frontend, servidor e worker compilados.
- Recuperação/rotas Craft: 7 testes passaram.
- Contrato HTTP novo: 5 testes passaram com banco e object storage temporários, provider isolado somente na fronteira de chamada, sem rede paga. Criação/edição produzem PNGs de fixture, percorrem o ciclo de job/armazenamento/revisão, preservam os bytes originais, deduplicam a solicitação e rejeitam cliente diferente, revisão obsoleta, provedor desabilitado, operação de outro módulo e orçamento insuficiente.
- Backend: `PYTHONPATH=backend .venv/Scripts/python.exe -m pytest backend/tests/test_image_frontend_contract.py backend/tests/test_video_frontend_contract.py backend/tests/test_clicko_studio_bridge.py backend/tests/test_studio_department.py backend/tests/test_craft_studios.py backend/tests/test_craft_lifecycle.py -q` — **34 testes aprovados**. O teste de orçamento admite `retrying` ou `failed`, conforme o agendador existente, mas exige bloqueio antes de qualquer chamada ao provedor ou criação de resultado.
- A primeira rodada da suíte ampla teve um teste de contexto KLIC interrompido sob carga simultânea. A execução isolada dos quatro testes de contexto passou; as repetições completas passaram, incluindo a rodada posterior à cota (174/174).
- Ajustes finais de acessibilidade móvel: alvos de toque de 44 px, texto de ações de pelo menos 12 px e campos de 16 px, sem alterar navegação global. Esses ajustes têm build/TypeScript verificados, mas continuam sujeitos à inspeção visual pendente.
- `git diff --check` — sem erros de whitespace; Git informa somente conversão LF/CRLF nos arquivos rastreados.
- O serviço local foi recarregado somente após confirmar zero jobs ativos. `/health/ready` confirmou o serviço; `/image` respondeu 200; a nova rota sem sessão respondeu 401, não 404. Não foram criados projetos/imagens de teste no workspace do usuário.
- Após a regra de cota confirmada, a prévia Node/Python foi recarregada. Verificação HTTP local: `/image` 200, serviço `ready` e pedido sem chave retornando `422 IMAGE_REQUEST_INVALID`, sem alteração do saldo antes/depois. Nenhuma geração paga ou job de teste foi criado no ambiente real.

O resultado destes testes não substitui a chamada real ao provedor configurado, a revisão de pixels nativos ou o QA visual pendente.

## Método de trabalho

A habilidade **Sites**, no fluxo local, orientou o reaproveitamento do checkout e a separação entre implementação, prévia e publicação. Nenhum projeto foi registrado ou publicado pelo conector. A habilidade **Computer Use** orientou a tentativa de QA, que respeitou a desativação da automação local no Work. Não foi gerada uma imagem artificial para substituir a inspeção da interface real.
