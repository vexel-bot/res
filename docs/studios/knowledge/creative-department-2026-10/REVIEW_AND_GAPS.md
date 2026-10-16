# Revisão, cobertura e lacunas

Esta entrega contém um corpus documental auditável, não uma declaração de análise audiovisual integral. O relatório `coverage.json` verifica contagens, referências, campos e cobertura declarada. Passar esse validador significa integridade dos registros; não significa liberação automática do próximo protótipo.

## Cobertura real da rodada

- 92 candidatos: 46 por autor principal. Links/títulos foram observados em canais e perfis públicos; a entrevista de Alfredo publicada por O Mentor Podcast é identificada como tal.
- 36 unidades selecionadas: 6 YouTube e 6 Instagram por autor principal, mais 2 fontes por referência complementar.
- Os 12 vídeos têm metadados públicos e hashes das legendas utilizadas. Os registros indicam excertos, leitura da legenda ou sinopse; não se deduz áudio a partir do texto.
- Instagram: AS-IG-01 tem imagem estática observada; AS-IG-02 tem somente capa; HZ-IG-01 tem cartões de categorias e conclusão amostrados. Os demais registros usam legendas públicas. As aberturas faladas dos Reels não foram observadas.
- JP-02 analisa um artigo primário detalhado de 2025 sobre Tilt e premissa, substituindo a escolha inicial de uma sinopse curta. A sinopse de 2015 fica apenas como fonte auxiliar para comparação de versão; não foi ouvido seu áudio. A fonte da jornada no The Tilt apresentou falha de acesso e não foi usada para preencher lacunas.
- Software: benchmark de documentação pública, sem execução nos produtos.
- Os nove exercícios são aplicações fictícias de mesa. Não foram executados por agentes em produção nem testados com clientes.

## Afirmações críticas conferidas ou restringidas

| Questão | Tratamento e locator |
| --- | --- |
| Autoria da entrevista de Alfredo | Metadados públicos identificam O Mentor Podcast; AS-YT-06 não é atribuído ao canal oficial de Alfredo. |
| Duração das duas peças de Hormozi | Metadados: HZ-YT-04 = 27s; HZ-YT-05 = 26s. Não são contadas como aulas extensas. |
| Data do caso Nardon | Metadado público `upload_date` = 05/08/2026; a interface local exibiu 04/08. Registrar a base e a diferença possível de fuso, sem ocultá-la. |
| Identificação da Syhus | Descrição oficial de AS-YT-02; erros da transcrição não são tratados como nomes corretos. |
| Fonte de números comerciais | Relatos de autores, sem acesso a dados. Não se usam como resultados garantidos ou benchmarks Clicko. |
| Writing GPS | Artigo de 2022: 17 passos; distinção da versão anterior preservada em AH-01 e F07. |
| Content Inc. | Introdução 2021, artigo de 2025 e sinopse auxiliar de 2015 preservados em JP-01/02 e F09; versões e atribuição a Jay Acunzo não fundidas. |
| Posicionamento | Artigo de preparação janeiro/2026 e artigo de alternativas dezembro/2020 delimitados em AD-01/02. |
| StoryBrand | Texto do guia conferido, inclusive páginas 7–8 e 12–13; edição não confirmada. Brochura em caminho 2014/02 não recebe data presumida. |
| IA e voz | AH-02 registra a restrição da autora à própria escrita; F08 declara a adaptação Clicko e a divergência. |
| Carrosséis | Não inventar número de cartões ou narrativa de slides não observados. AS-IG-02 é capa apenas. |

## Lacunas que impedem declarar a curadoria integral concluída

1. Revisar audiovisualmente os 12 vídeos e os Reels escolhidos: abertura, ritmo, pausas, demonstração visual, som e relação com a legenda. A coleta textual não resolve essas dimensões.
2. Completar a observação dos carrosséis de Alfredo e, se necessário, substituir uma unidade cuja íntegra continue inacessível por outro candidato com cobertura equivalente. A substituição precisa preservar o motivo de seleção e o histórico.
3. As imagens ilustrativas e os diagramas das fontes complementares não receberam revisão visual integral. O caso Joy Cho da sinopse auxiliar não recebe análise aprofundada nem é contado entre as 36 fichas.
4. Realizar a revisão humana prevista na [metodologia](../methodology.md): análise e mapa temporal, incluindo segunda revisão de 10% das unidades críticas. Não existe atestado dessa revisão nesta entrega.
5. Testar compreensão de pedido, direção e entrega com clientes. Os exercícios documentais não comprovam que o usuário entende a experiência.

Pacote prioritário para revisão crítica: AS-YT-01, HZ-YT-01, AH-02 e DM-01, mais a auditoria de versões F07/F09/F12/F14. São quatro unidades com implicações diretas para identidade, métricas, autoria e narrativa. A revisão deve registrar achado, locator, correção e responsável, sem fabricar um sign-off humano.

## Falhas de acesso registradas

O navegador apresentou falhas intermitentes de leitura/navegação e de abertura do ambiente integrado. O agent-browser disponível também apresentou falha de conexão. As legendas e metadados públicos do YouTube foram coletados com yt-dlp 2026.8.19 em diretório temporário isolado, sem cookies, credenciais ou download de vídeo/áudio. O PDF público StoryBrand foi consultado localmente após falhas do leitor web. Nenhuma barreira de acesso foi contornada.

## Retenção e direitos

As notas são transformativas. Os links permitem localizar as fontes; não concedem licença de reutilização. O acervo distribuído não contém mídias, capturas, PDFs originais ou transcrições integrais de terceiros. Hashes de legendas identificam o material usado, não o vídeo original. Fontes vivas não arquivadas têm checksum nulo com motivo declarado.

Arquivos exportados antes desta rodada pertencem ao usuário e são preservados. Downloads e exportações criados pela pesquisa são removidos após extração; `temporary-source-ledger.json` registra hashes e exclusão. Dependências de coleta ficam no diretório de runtime ignorado, sem alterar as dependências do produto.

## Passagem para design

O protótipo não está liberado por este documento. Fontes e conhecimento documentais estão disponíveis para revisão, e os requisitos de experiência estão escritos. A decisão de avançar precisa considerar as modalidades ainda ausentes, versões, revisão crítica e compreensão do cliente. Nenhuma tela nova ou ativação de frontend foi implementada nesta fase.
