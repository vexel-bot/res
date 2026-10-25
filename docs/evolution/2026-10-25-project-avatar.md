# Apresentação ligada à aparência e à fala final

Estado: orquestração e interface implementadas. A qualificação dos modelos reais e a aceitação audiovisual da montagem continuam pendentes.

## Experiência no projeto

Um projeto de vídeo com aparência e voz selecionadas apresenta uma etapa de apresentação após a narração. O cliente informa como a pessoa ou personagem deve se apresentar, solicita a preparação, acompanha o progresso e pode cancelar. Uma apresentação concluída é carregada pela rota autenticada de arquivos da marca, com reprodução e download privados. A orientação de apresentação fica salva com o pedido.

O pedido usa a imagem autorizada da versão escolhida e o áudio final da narração. A amostra de cadastro da voz não serve como fala final. A aparência e a voz são independentes: pessoa ou personagem podem usar uma voz clonada autorizada ou uma voz licenciada configurada. O código não troca a voz por um timbre padrão nem contrata um serviço remoto como alternativa.

Se o texto foi alterado depois da síntese, é preciso concluir a nova narração. Se o modelo ou o equipamento não estiver disponível, os materiais permanecem salvos e o pedido explica a indisponibilidade. Uma apresentação previamente concluída pode ser reaberta com o motor offline, desde que a autorização, o texto e a origem dos materiais continuem válidos.

## Admissão e montagem

O servidor monta um plano imutável que reúne projeto, direção, imagem, áudio, duração, versões do elenco e versões do motor e do perfil de execução. O cliente não pode reduzir a duração informada ou substituir o documento para obter outra execução. Documento de contexto, job e referência no projeto são gravados na mesma transação com controle de revisão.

O proxy Node reserva minutos antes de admitir uma geração de avatar e assina documento, chave do pedido, operação e duração no token de integração. O Python confere esse vínculo. Repetir um pedido usa a mesma reserva e o mesmo job; sucesso ajusta a reserva para a duração do resultado, enquanto cancelamento ou rejeição definitiva a libera. Uma resposta perdida não é tratada como prova de rejeição. A rota genérica de jobs continua bloqueada para escapar dessa admissão.

Uma apresentação concluída e coerente com os materiais atuais pode alimentar a primeira montagem FilmCraft. O vídeo da marca anteriormente selecionado permanece como outro clipe. O documento mantém as referências de aparência e voz, e a página de apresentação recebe a duração do avatar. A aprovação de publicação continua separada dessa preparação privada.

## Evidência e limites

Os testes de backend exercitam planejamento, proveniência do áudio, combinações de aparência/voz, repetição de pedidos, adulteração de duração/documento/plano, conflitos de revisão, isolamento, revogação, cancelamento e admissão assinada. O teste de passagem à montagem verifica os contratos HTTP/DB e os comandos enviados, com o adaptador e a exportação nativos substituídos por fixtures explícitas.

Os testes do proxy exercitam reserva, repetição após resposta perdida, liquidação por duração e cancelamento. Os testes da interface usam o aplicativo e sua sessão locais, com respostas de projeto e geração simuladas. A reprodução usa um clipe silencioso criado por FFmpeg, sem pessoa gerada.

Na rodada final passaram 18 testes de backend, 12 testes de proxy/governança e seis testes de interface. TypeScript, Ruff e build passaram. A captura do painel foi inspecionada. O registro de Evolução foi consultado pela sessão real do Node, com checksum igual ao documento local. Uma rodada anterior atingiu o timeout de navegação na primeira abertura enquanto os testes de backend rodavam em paralelo; a rodada final, no aplicativo reiniciado e sem essa concorrência, passou integralmente. Isso não constitui uma avaliação de desempenho sob carga.

Esses testes não qualificam semelhança de rosto ou voz, naturalidade, português, gestos, sincronismo labial ou qualidade do vídeo. Nenhum cadastro, provedor ou modelo real foi aprovado automaticamente. Continuam pendentes:

- Configuração e qualificação dos runtimes e pesos em equipamento compatível, com amostras autorizadas.
- Teste audiovisual completo do modelo até a exportação FilmCraft, com conferência de áudio, enquadramento e duração.
- Encadeamento de falas longas em segmentos qualificados. O perfil LongCat atual permanece limitado a 3,72 segundos pelo seletor; o código não corta a fala para fazê-la caber.
- Geração de uma nova versão da montagem depois de uma entrega existente. Este caminho prepara a primeira montagem; os históricos existentes não são reescritos.
- Fluxos de montagem com somente voz sobre material da marca, sem aparência, e criação generativa de novas poses/imagens com identidade.

## Fontes no sistema

- backend/app/routers/studio_project_avatar.py
- backend/app/services/studios/project_avatar.py
- backend/app/routers/studio_department.py
- server/studios/proxy.ts
- server/studios/videoQuota.ts
- backend/tests/test_project_avatar.py
- server/studios/videoQuota.test.ts
- src/studios/department/ProjectAvatar.tsx
- tests/team-sync/project-avatar.spec.ts
