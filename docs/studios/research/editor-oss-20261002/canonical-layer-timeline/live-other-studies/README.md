# Timeline real: organização e comparação

05/10/2026. Verificação na aplicação existente em Downloads, usando o navegador de laboratório já aberto e os projetos canônicos/autênticos da rodada native14. A seleção e o scrubbing passaram nas duas linguagens que ainda não tinham sido observadas nesta timeline. Não houve nova composição, edição persistida, render ou chamada paga nesta verificação.

| Projeto | Linhas confrontadas com a API | Target selecionado pela timeline | Frames observados com MP4 decodificado e inspetor |
|---|---:|---|---|
| organization-a | 22 | word-0 | 0, 139 e 449; Home/End na régua |
| comparison-a | 25 | result | 0, 244 e 449; Home/End e entrada 450 limitada a 449 |

Cada registro qualificado conserva todos os IDs, cenas e intervalos [início, fim) dos botões e os confronta com o documento da API. O target selecionado no inspetor coincide com o ID do botão. A régua, o campo do inspetor, a mensagem de propriedades calculadas e o tempo do vídeo concordam no frame solicitado. A verificação espera vídeo decodificado, pausado e fora de seek, com tolerância inferior a meio frame; não altera o player por JavaScript nem usa estado interno do React.

Os dois documentos permaneceram exatamente iguais antes/depois na API, na revisão 2/versão 1. Os bytes das prévias exibidas conservam os SHA-256 e tamanhos dos MP4s originais: organização `f2eae2907b62bebd648a5142e851de6253f367594b7f68e5a06a224be8687d63` (591.346 bytes); comparação `409f0916ab33a58241b1deed17848e09e87e544399261978cdf141e6527d2a4a` (624.796 bytes). Ambos têm 1080 × 1920, 30 fps e 15 s. Não foi necessário copiar novamente os MP4s para este diretório.

[Verificação e fontes atuais](verification.json), [estado das revisões humanas](human-review-current.json), [captura de organização](organization-a-ui.png), [captura de comparação](comparison-a-ui.png). [Observador passivo](../../../../../../scripts/validation/editor-canonical-studies-observe.ps1), executado em PowerShell 7. Os 76 hashes do checkpoint de carregamento continuam iguais; o observador é uma nova ferramenta de validação, sem alterações de produto nesta rodada. Os oito testes/typecheck da correção de carregamento não foram repetidos, pois suas fontes permaneceram iguais; estes registros acrescentam prova de UI com APIs e mídia reais.

## Tentativas que não contam como passe

- `organization-a-initial.json`: o primeiro comando usou Windows PowerShell 5.1, que interpretou incorretamente os caracteres UTF-8 do seletor. A régua ficou ausente no registro. O observador agora exige PowerShell 7; a prova está em `initial-verified`.
- `organization-a-selected-word.json`: o clique antes de rolar não abriu o inspetor. O clique qualificado ocorreu depois de `scrollintoview` e novo snapshot; não foi substituído por um evento DOM artificial.
- `comparison-a-selected-result.json`: a observação de 20 s terminou com o inspetor ainda carregando. A mesma consulta foi observada depois com HTTP 200 e duração de 23.317,4 ms, sem reiniciar, navegar novamente ou repetir o clique. `selected-result-settled` registra a resposta completa. Isso revela latência a investigar, não prova tempo de resposta aceitável.

Algumas strings capturadas pelo CLI contêm caracteres de substituição. Os IDs, números, intervalos, SHA e mensagens ASCII usados nas verificações estão íntegros; as duas capturas foram inspecionadas visualmente. Outros painéis fizeram consultas com HTTP 503 e abortos durante seu ciclo de vida. Estes registros não certificam saúde de todos os endpoints nem velocidade geral de abertura.

## Trabalho que continua necessário

As três comparações cegas seguem `not_assessed`, sem nota humana. A verificação cobre seleção de dois targets e navegação pausada nos frames registrados; não qualifica estética, todas as camadas editáveis, reprodução contínua ou autonomia. O aceite dirigido e os três novos briefs continuam pendentes. A fonte do vídeo anterior da interface permanece no checkpoint histórico próprio.

A UI ainda apresenta fonte `font/woff2` e som `audio/wav` como “Take 1/2”, com “Prévia pendente”, embora os documentos preservem seus tipos corretos. As capturas tornam essa classificação incorreta um próximo ajuste concreto. A latência do inspetor e o carregamento dos painéis de apoio também precisam ser investigados. Integração/avaliação de geradores externos e limpeza de clones recusada continuam abertas no objetivo original.
