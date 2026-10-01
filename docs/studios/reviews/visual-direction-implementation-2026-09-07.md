# Direção visual: implementação e qualificação parcial

## Atualização de escopo — 8 de setembro

O usuário determinou que o agente não produza vídeos nem forneça materiais ao sistema. Os próximos testes de implementação usam respostas simuladas; aquisição e escolha devem ser responsabilidades do res. O download acionado no navegador não foi incorporado ao acervo. Os vídeos de qualificação anteriormente previstos não serão executados pelo agente sob essa orientação.

Implementado adicionalmente: descoberta por necessidade no fluxo V2, limite por lote e registro de indisponibilidade; serviço de aquisição com domínios do provedor e importador existente, mantendo arquivos pendentes de inspeção; correção limitada de respostas inválidas recebidas; crítica visual compatível baseada em frames, explicitamente parcial. A aquisição ainda precisa ser ligada a uma seleção semântica qualificada e à inspeção automática antes de se anunciar resolução autônoma completa.

## Estado da entrega

### Fechamento do fluxo de materiais — 8 de setembro

O caminho novo de produção agora exige inspeção de imagem/filmagem por necessidade, inclusive quando o planejador fornece um asset do acervo diretamente. O res consulta o projeto/acervo e o conector, obtém candidatos pelo importador validado e agenda inspeção através dos jobs duráveis de planejamento existentes. Não depende de o agente fornecer um arquivo.

A inspeção recebe pixels do arquivo imutável (imagem ou seis amostras do trecho de vídeo), critérios numerados e duração exigida. Cada resposta deve citar amostras existentes e cobrir todos os critérios. Ausência de evidência, confiança abaixo do limiar ou duração insuficiente leva a alternativa. A produção examina até três candidatos; submissões incertas não são repetidas. A aplicação usa o contrato existente de escolha de material e preserva revisão de documento, checksum, modelo, consumo e histórico de jobs. A aprovação automática é específica da finalidade, critérios e duração; revisão humana permanece pendente.

Limites: amostras não comprovam continuidade integral, tracking ou eventos não observados. Pexels precisa de credencial configurada. Conectores adicionais e modelos ainda dependem da configuração e qualificação próprias. Esta implementação foi testada com respostas simuladas e imagem sintética isolada; nenhum vídeo foi produzido e nenhum material real foi fornecido ao res nesta rodada, conforme orientação do usuário. A qualidade visual ao vivo não foi certificada.

Testes adicionais: contratos de inspeção, critérios desconhecidos, referências inventadas, duração insuficiente, execução de job com candidato fora do documento, idempotência, fluxo acervo → inspeção → aplicação e falha sem reenvio. Os arquivos principais são `material_inspection.py` (domínio/serviço), `production_materials.py`, `material_acquisition.py` e a integração ao executor de edição existente.

Em implementação. O piloto anterior continua reprovado. Esta etapa não produziu os dois vídeos autônomos exigidos pelo plano nem demonstrou melhora editorial sobre a referência.

O teste controlado em `artifacts/validation/visual-direction-controlled/controlled.mp4` foi produzido por um job real do res, com compilação V2, HyperFrames e FFmpeg. Sua cena foi escrita como fixture técnica; **não demonstra planejamento autônomo**. `audit.json` e os quatro JPEGs foram extraídos desse MP4. O frame 30 foi inspecionado: texto acentuado, moldura e curva são visíveis. A presença de sombra e a equivalência visual completa ainda exigem comparação controlada mais específica.

## Implementado

- Blueprint opcional e versionado nos beats: mensagem, evidência, representação, materiais, região de interesse, hierarquia, critérios e alternativas descartadas. Novos pedidos da interface exigem blueprint; contratos antigos permanecem opcionais.
- Bloqueio de composições que substituam uma filmagem exigida por texto/formas, ou omitam a necessidade de arquivo para um elemento de mídia sem asset. Isso verifica estrutura, não pertinência semântica do material.
- Modo de produção visual sem síntese de voz. Interface permite escolher esse escopo. O roteiro permanece na rastreabilidade; não há criação de música ou efeitos nesse caminho.
- Oito fichas selecionadas do motion-vox entram no repertório existente como conhecimento, com versão e digest de origem. Regras de estilo não são universais e fichas não certificam execução.
- Cinco fontes incorporadas com arquivos, checksums, licenças integrais e eixos variáveis. Importação pelo catálogo existente, com deduplicação por conteúdo.
- Peso tipográfico, espaçamento, entrelinha, alinhamento, borda, sombra e caminhos quadráticos ligados ao compilador e à projeção gráfica. Curvas participam da revelação por caminho existente.
- Descoberta Pexels autenticada, limitada e sem redirecionamentos. Retorna candidatos explicitamente não inspecionados; não importa nem aprova arquivos. Falta de configuração oferece projeto/acervo/upload.
- Política de auditoria versionada: técnica, visual/editorial e humana separadas. Contraste declarado é apenas preflight; composição complexa permanece fora desse cálculo simplificado.
- Estados extraídos do export em uma passagem FFmpeg, a 300 px, com checksum do vídeo e de cada imagem. Limite de 32 frames/3 MB; cobertura incompleta permanece explícita. Tempos consideram transições, dependências e repetição; taxa de exportação é consultada para mapear os frames.
- Estados exibidos na inspeção da produção. Captura não equivale à comprovação de movimento contínuo ou à aprovação visual.
- API autenticada de revisão humana por render, com notas, ator, histórico, checksum e revisão. Rejeita export antigo; não modifica aprovação de publicação.

## Verificações executadas

- Contratos e compilador V2 + produção: 26 testes passaram na rodada inicial ampliada.
- Auditoria, descoberta, vínculos e importação de fontes: nove testes passaram após corrigir preservação de quebras de linha da licença e saída antecipada do modo visual.
- Oito testes de auditoria passaram novamente após extração em passagem única e mapeamento de FPS.
- Um teste de integração executou o job real HyperFrames, incluindo retentativa idempotente, estado de rascunho e auditoria vinculada ao export.
- TypeScript (`npm run lint`) e Ruff nos arquivos alterados passaram.
- Banco de testes descartável em diretório temporário separado; banco de trabalho não utilizado pelos testes.
- Não houve chamada paga de modelo nesta etapa. Tempo/custo completo de uma nova produção editorial ainda não medido.

## Pendências para a conclusão do plano

1. Conectar descoberta, importação e inspeção de materiais à direção, com seleção por conteúdo observado; o conector de descoberta isolado não cumpre essa etapa.
2. Completar layout medido, conectores vinculados a alvos, câmera de composição e qualificação independente de recortes/grupos/transições.
3. Medir movimento em regiões e verificar ações essenciais. Os checkpoints atuais dão evidência para inspeção, mas não fazem essa avaliação automaticamente.
4. Fechar correção localizada em cada etapa, com até duas tentativas e tratamento separado para resposta inválida, falha técnica e resultado fraco. O ciclo de crítica existente não cobre todos esses casos; o crítico compatível continua sem entrada de vídeo qualificada.
5. Testar a mesma fonte do projeto no preview e no MP4. Importar fontes e renderizar texto acentuado com fonte de fallback são provas diferentes.
6. Produzir distribuição (15–20 s, montagem mista) e outro tema/identidade pelo planejador, sem autoria manual das cenas. Guardar material, plano, manifesto, receipts, consumo e intervenções.
7. Fazer revisão integral dos vídeos e registrar avaliação humana real. Nenhuma nota humana foi preenchida pelo agente.

## Revisão de código desta etapa

Skill `code-review` aplicada aos arquivos novos/alterados. Corrigidos: offsets de transições em observação/crítica; custo de decodificação repetida; checksum de licença afetado por normalização de newline; instruções contraditórias de áudio no modo visual; ausência de vínculo estrutural entre blueprint e mídia.

Conclusão de qualificação: infraestrutura avançou, qualidade editorial final ainda não qualificada. Manter HyperFrames até os testes isolarem uma limitação reproduzível do runtime.
