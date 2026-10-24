# Recuperação estrutural audiovisual da Clicko

Data: 21/10/2026. Referência: auditoria técnica de 20/10/2026. Checkout: `C:/Users/pedro/Downloads/res`.

## Conclusão executiva

A etapa implementa correções locais comprováveis, não uma certificação de produção. Express e FastAPI voltaram a se comunicar na prévia. O editor canônico executou exportação real pela fila local, com reprodução e download no navegador. As rotas simuladas foram encerradas, os contratos de imagens foram corrigidos e as proteções financeiras/comerciais ganharam verificações antes da submissão.

Não foi possível recuperar a execução dos três motores Craft sem suas ferramentas de compilação. Geração profissional com fornecedores externos não foi executada: depende de credenciais, autorização financeira e qualificação real. Nenhuma indisponibilidade foi escondida por mídia de exemplo ou sucesso fictício.

## 1. Problemas corrigidos

| Área | Correção e evidência | Limite da afirmação |
| --- | --- | --- |
| Backend local | Origem explícita `8018` não impede mais o autostart. Banco e arquivos de QA separados. `/health/ready` e `/api/ready` responderam 200 com dependências reais. | Perfil local SQLite/pool de threads; não PostgreSQL/Redis em produção. |
| Prontidão | Queda controlada do FastAPI fez Express responder 503; retomada preservou projeto/MP4. | Runtimes opcionais são consultados em capabilities, não inventados como prontos. |
| Rotas antigas | `image-edit`/`video-edit` deixaram de devolver arquivo original/exemplo como edição concluída. `generate-image` antigo também retorna 410. Sem consumo nessas rotas. | Não há redirecionamento automático de URLs soltas para projetos sem autorização/revisão. |
| FFmpeg | Ferramentas compartilhadas, caminho explícito respeitado e encoder detectado. Processamento real com H.264/AAC. | Limites existentes de 10 min, 32 itens, até 1920 px e 60 fps preservados. |
| Vídeo | Timelines, revisões, snapshots, exportação e recuperação mantidos. Crítica aceita `craft_render`/`timeline_render` com artefato de vídeo, checksum e revisão. | Geração de cenas não é apresentada como edição da timeline. |
| Imagens | `aspectRatio`/`imageSize` estruturados até Gemini e conferência da proporção recebida. Lite limitado a 1K; 2K/4K rejeitados nele. | Transporte e ciclo de vida testados offline; nenhuma inferência paga/qualidade fotográfica foi certificada. |
| IA de edição | Pipeline existente `craft_ai` pode aplicar `timeline.replace` canônico com schemas, revisão, materiais vinculados e validação do executor. | O LLM foi substituído por double nos testes; nenhuma conexão foi ativada. |
| Custos | Limites mensais globais/workspace/usuário em produção, reservas duráveis, flags de vídeo e retenção de resultados desconhecidos. | Valores por tarifa são estimativas; faturas de fornecedor não estão conciliadas. |
| Cotas | Imagens por solicitação aceita; somente cenas de IA consomem minutos. JWT da ponte transporta admissão comercial assinada. | Aquisição autônoma sem recibo é bloqueada, não liberada por uma rota alternativa. |
| Craft | Linhagem dos seis conjuntos de fontes conferida; JS/WASM ausentes retornam 404 JSON. | Docker/Rust/bundles não estão instalados; não declarar os motores operacionais. |

## 2. Implementação e reutilização

Foram mantidos React/TypeScript, Express, FastAPI, SQLAlchemy, Celery, o armazenamento privado existente, os contratos canônicos, as conexões LLM cifradas e os adaptadores originais. Não foram instaladas dependências nem substituídos motores nativos. A KLIC e os demais módulos visuais não foram redesenhados nesta etapa.

### Infraestrutura e segurança

- `server/studios/runtime.ts`, `readiness.ts`, `proxy.ts` e `server.ts`: inicialização local, health estrita, streaming preservado e falhas explícitas.
- `backend/app/studio_routes.py`, `main.py`, `studio_app.py`, `http_middleware.py` e `routers/health.py`: rotas comuns, validação de startup, tracing, headers e rate limiting. Produção não executa `create_all` nem aceita modo eager.
- `services/studios/local_queue.py`, `production_queue.py`, `jobs.py` e `routers/studio_video.py`: pool local limitado, tarefas fora do HTTP, limites Celery por perfil, aquisição atômica, proprietário de fila e recuperação sem reenviar chamadas externas desconhecidas.
- A sessão da ponte continua assinada, curta, vinculada ao usuário/workspace/cliente e com permissões conferidas no BFF. O serviço não confia em um token arbitrário do navegador.
- A identidade financeira é registrada pelo servidor a partir da empresa e do usuário SaaS originais. Trocar o cliente/projeto não reinicia os limites financeiros da empresa ou do membro, mesmo com UUIDs distintos no banco isolado de cada cliente. Workers recuperam essa identidade pelo registro durável, não por dados enviados pelo navegador.
- A rota genérica de jobs não aceita envelopes brutos de `editing_ai`/`editing_gemini`, nem mesmo no `app.main`: tarifas, identidade financeira e vínculos de provedor são produzidos exclusivamente pelo serviço de admissão. As rotas canônicas continuam sendo o caminho autorizado.

### Motores e vídeo

- `providers/studios/media_runtime.py` centraliza descoberta. `timeline_ffmpeg.py`, `ffmpeg_utility.py`, `media_probe.py`, `media_proxy.py`, `media_waveform.py` e `voice_reference.py` reutilizam essa descoberta.
- `services/studios/timeline_editor.py` preserva CAS de revisão, referências privadas, snapshots e o mesmo compilador para prévia/exportação. Uma operação de IA possui recibo na mesma transação do salvamento da timeline.
- `services/studios/timeline_ai.py` restringe o comando à timeline tipada; materiais não vinculados, filtros arbitrários, caminhos e funcionalidades não suportadas são rejeitados.
- `services/studios/craft_ai.py` continua usando as conexões/provedores e orçamentos existentes. O novo alvo canônico não cria outro serviço de LLM.
- `src/studios/video/CanonicalVideoEditor.tsx` apresenta a montagem assistida e conserva o pedido/chave antes de POST; resultado desconhecido não autoriza nova submissão automática.
- `providers/studios/craft.py` respeita binário nativo instalado antes de recorrer ao wrapper Docker. `scripts/craft/build.py` apresenta o bloqueio de compilação de forma explícita.

### Imagens

- `domain/studios/editing_resources.py`: parâmetros opcionais compatíveis com jobs antigos.
- `providers/studios/gemini_editing.py`: capacidades por modelo e proporção/tamanho nativos. O Lite fica limitado a 1K; o modelo Flash Image conserva `1K/2K/4K`. No contrato REST `ImageConfig`, o literal é `1K`, não o rótulo descritivo `1024px` do cartão do modelo. O teto do planejamento Gemini acompanha o contrato de até 16.384 tokens.
- `services/studios/gemini_editing.py`: validação na admissão e no resultado, preservando originais, referências/checksums, revisões, armazenamento privado e revisão humana. Não há revisão paga escondida após gerar um candidato: inspeção externa precisa de etapa reservada própria.
- `src/studios/image/imageApi.ts`, `imageModel.ts` e `ImageStudio.tsx`: envio estruturado e descrição honesta da resolução. Nenhum upscale fictício transforma canvas 1080/1920 em resolução de geração.
- Parâmetros foram conferidos na [documentação oficial do Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite-image), na [geração de imagens](https://ai.google.dev/gemini-api/docs/image-generation) e no [contrato REST ImageConfig](https://ai.google.dev/api/generate-content#ImageConfig). A validação considera a quantização nativa de pixels (até 2,5% de tolerância relativa) e registra as dimensões reais, sem alegar dimensões exatas. As capacidades declaradas não são prova de acesso/qualidade na conta do usuário.

### Custo e consumo

- `server/governance.ts`, `server/studios/imageQuota.ts` e `videoQuota.ts`: contadores/recibos no snapshot atômico existente. Replay não duplica consumo; falha de persistência não libera execução sem registro.
- Imagens: falha/cancelamento depois da admissão continua contando, conforme regra confirmada anteriormente.
- Vídeo: usuário confirmou **somente cenas geradas por IA**. A reserva inclui a tolerância técnica de duração de 0,15 s; a conclusão concilia os segundos do artefato. Edição, prévia e exportação não são tarifadas por esse contador.
- Resultados de rede desconhecidos mantêm reserva. A confirmação por job/replay ou operação persistida é reutilizada; não há reenvio automático de POST para adivinhar o que aconteceu.
- `services/studios/external_policy.py` usa os jobs e o lock transacional já existentes para limites mensais. Produção requer os três tetos positivos. Conexões LLM preservam também seu limite próprio.
- A consulta mensal inclui o período da reserva, além da criação do job: uma retomada autorizada de tarefa antiga não desaparece da contabilização do mês atual. Reservas recusadas por limites de categoria não são gravadas como se uma chamada tivesse sido aceita.
- `services/studios/media_usage.py` agrega métricas por workspace/usuário e bytes de ativos ativos, sem contar repetidamente o mesmo arquivo por replay de job.
- `routers/editing_resources.py` expõe reserva, estimativa, fonte do custo e custo informado pelo fornecedor separadamente. `providerReportedCostUsd` não vira zero quando é desconhecido.

## 3. Validações executadas

### Reais, sem inferência paga

- Inicialização Express `3018` → FastAPI `8018`, autenticação existente e sessão da ponte.
- Health 200 com banco/arquivos/pool/FFmpeg; parada controlada do backend produziu 503 no Express; backend retomado com os mesmos arquivos.
- Teste automatizado de timeline: upload de vídeo/áudio/imagem locais, cortes em trechos distintos, texto, sobreposição, rotação/escala/opacidade, fades, trilha, renderização, verificação de pixels e áudio, download/Range, revisão, isolamento, cancelamento e recuperação de entrega.
- Navegador: projeto `QA · Recuperação audiovisual`, revisão 2, título animado, renderização assíncrona, reprodução concluída (`currentTime=3`, `ended=true`) e download.
- FFprobe no download: 1080×1920, H.264 + AAC, duração 3,000 s, 133.612 bytes. Arquivo: `C:/Users/pedro/Downloads/QA · Recuperação audiovisual · revisão 2.mp4`.
- Segunda exportação real: job `f77419d2-05d5-4528-a0f6-4343108fff61`, uma tentativa, 4,188 s de processamento, 3 s de saída, zero segundos gerados por IA e 133.612 bytes. Projeto e resultado continuaram acessíveis após reiniciar o serviço. Captura: `.codex-runtime/studios-recovery/proof/editor-validado.jpg`.
- Integridade upstream Craft: PhotoCraft 1.569 arquivos, FilmCraft 1.236, EffectCraft 1.016, craft-libs 41, craft-fonts 25 e filmcraft-compat 951. Nenhum fonte original desses motores foi reescrito.
- Bundle JS inexistente: 404 `CRAFT_BROWSER_RUNTIME_NOT_BUILT`, não uma página HTML.
- Build de produção Vite/esbuild e tipagem TypeScript aprovados nas execuções realizadas. Resultado final consolidado abaixo.

### Com doubles explicitamente identificados

- Gemini/LLMs: serialização de parâmetros, limites de tokens, recusa de resolução incompatível, validação de aspecto, arquivo privado, revisão e preservação do original. A geração em si não foi executada.
- Planejador de timeline: JSON com comando validado, persistência e replay do recibo sem segunda chamada. O executor/armazenamento são reais; a resposta do modelo é double.
- Ponte/quota: servidor HTTP Express real com fornecedor/FastAPI substituído, persistência de consumo real em diretório temporário. Testa admissão, resultado desconhecido, replay, conciliação e limites de membro.
- Runner Craft: três testes de transporte/isolamento passaram; não equivalem à execução dos binários nativos.

### Consolidação automatizada

- Rodada direcionada final: **93 coletados, 75 aprovados, 18 pulados, zero falhas/erros**. Inclui contratos de imagem/vídeo, permissões, LLMs, orçamento, isolamento, timeline real e as três regressões descritas abaixo. XML: `.codex-runtime/studios-recovery-contracts-final.xml`. Os testes pulados não são apresentados como aprovação.
- Rodada ampliada anterior: **115 coletados, 93 aprovados, 22 pulados, zero falhas**. Foi anterior aos últimos reforços de identidade financeira/admissão e não substitui a rodada final. Não somar rodadas, pois contêm testes repetidos.
- Node/Vite: **229 aprovados**, zero falhas, na nova execução final de `npm test`. Sete testes de `tests/unit/craftState.test.ts` também foram aprovados em execução própria.
- `npm run lint` (TypeScript) e `npm run build` (Vite/esbuild): aprovados novamente. Ruff aprovado nos 34 arquivos Python explicitamente verificados da implementação e dos testes revisados; não é uma afirmação de lint verde em todos os módulos legados.
- **Suíte completa backend não aprovada:** 1.220 coletados, **826 aprovados, 282 falhas, 112 pulados, zero erros de coleta**, em 1.088,897 s. Evidências: `.codex-runtime/studios-recovery-full.xml` e `.codex-runtime/studios-recovery-full.log`.
- Comparação por identificador com `.codex-runtime/cleanup-backend-final.xml`: **279 falhas já estavam presentes**. Entre os bloqueios estão políticas/manifests/artefatos de benchmark ausentes e ambientes de workers especializados não qualificados; 237 falhas da rodada completa foram `FileNotFoundError`. Não foram fabricados arquivos de qualificação para esconder esses bloqueios.
- As **três diferenças novas** da rodada completa foram tratadas e passaram na rodada direcionada: health usa perfil local explicitamente no teste; fixture acústica reutiliza Settings completo; reserva mensal só é registrada depois de todos os limites de categoria aprovarem o pedido. As duas primeiras eram divergências de fixtures; a terceira corrigiu uma mutação real de reserva em preflight recusado.
- A suíte completa não foi repetida após esses últimos ajustes. Portanto, não há resultado global final verde, nem se deve apresentar uma subtração de falhas como se fosse uma nova execução completa. Dois testes antigos de derivação foram substituídos por testes de aposentadoria explícita, não por uma alegação de restauração desse editor.

## 4. O que ainda não funciona e por quê

1. **PhotoCraft/FilmCraft/EffectCraft reais e WASM:** Docker/Rust e artefatos compilados ausentes. Tentativa do builder bloqueada pelo pré-requisito; não instalado software de sistema nem substituído o motor.
2. **Geração profissional de imagens/vídeos:** não testada com fornecedor real por ausência de autorização para chamadas pagas. As credenciais/modelos não foram ativados. Interface mantém indisponibilidade explícita no perfil de QA.
3. **Produção distribuída:** PostgreSQL, Redis e workers de produção não foram provisionados; a versão local usa SQLite/pool. Readiness em modo Celery exige dependências reais, mas isso não é um benchmark de cluster nem validação de failover PostgreSQL.
4. **Qualificação de ASR, voz/avatar e outros workers especializados:** artefatos/modelos/ambientes necessários continuam externos. Não foram criados resultados falsos nem simulações de fala/transcrição.
5. **Faturamento real de fornecedores:** integração de invoice/consulta administrativa não implementada. Estimativas e reservas são auditáveis; resultado externo desconhecido exige comprovação/conciliação, não liberação automática do saldo.
6. **Cota comercial de armazenamento:** bytes são medidos e limites técnicos de mídia são preservados; não foi inventada uma política nova de cobrança de armazenamento/CPU. Contador de vídeo exclui explicitamente exportações locais.
7. **Geração autônoma dentro de produções sem recibo comercial:** bloqueada antes da submissão para não contornar a governança do BFF. Expandir essa integração exige reservar o orçamento/cota da produção e vincular cada job filho ao recibo autorizado.
8. **Registros históricos sem identidade financeira SaaS verificável:** continuam no teto global segundo seu período; não foram atribuídos arbitrariamente a outro cliente/usuário. Continuação em background sem vínculo verificável falha de forma explícita e exige conciliação/mapeamento autenticado. Nenhuma migração de dados de clientes foi improvisada.
9. **Aprovação global de testes:** a dívida e os artefatos ausentes da suíte completa continuam impedindo certificação da plataforma inteira. Os resultados direcionados comprovam apenas os fluxos e limites discriminados neste relatório.

## 5. Próximos passos, sem ativação implícita

1. Provisionar Docker/engine Linux em ambiente de desenvolvimento apropriado ou fornecer binários Craft qualificados; compilar nativo e WASM, verificar licenças, executar testes de pixels/áudio e paridade navegador/servidor.
2. Provisionar PostgreSQL/Redis/workers com backup e migrações revisadas; validar perda de worker, visibilidade da fila, carga e reinício distribuído. O pool local não deve ser apresentado como esse ambiente.
3. Selecionar e autorizar explicitamente uma matriz pequena de modelos de imagem/vídeo, tarifas e tetos. Qualificar com arquivos de referência e critérios de fidelidade/proporção/qualidade; candidatos continuam exigindo revisão.
4. Cadastrar uma conexão OpenRouter existente com Claude como planejador, modelo explicitamente selecionado e orçamento. Primeiro testar schemas/comandos contra executores realmente disponíveis; planejamento não comprova geração/renderização.
5. Integrar recibos comerciais para produções autônomas e uma conciliação administrativa autenticada com evidências do fornecedor. Só então habilitar os fluxos pagos completos.

## 6. Restrições respeitadas

Sem chamadas pagas, contratação, credenciais inventadas, edição de `.env`, migração destrutiva, alteração de produção, deploy, commit ou push. Dados de QA foram mantidos em diretório próprio. O checkout já continha alterações de outros trabalhos; elas foram preservadas. Arquivos de usuário não foram apagados.
