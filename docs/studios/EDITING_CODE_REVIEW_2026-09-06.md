# Revisão da edição de vídeo do res — 6 de setembro de 2026

**Conclusão: o res possui uma base funcional de edição, mas ainda não demonstra edição autônoma em qualquer cenário, preservação geral de fatos ou redundância real de geração de vídeo.** A principal prioridade é corrigir a fronteira entre instruções do usuário, resposta da IA e compilação. Trocar o gerador não corrige essa fronteira.

Revisão do estado de trabalho em `C:\Users\edugu\Downloads\res`, sobre HEAD `965a9bb`, incluindo alterações locais ainda não commitadas. O caminho OneDrive indicado inicialmente corresponde a outro projeto e não foi usado como alvo. Escopo exclusivo: estúdio de edição, recursos, planejamento, render e geração de mídia. Nenhum código de produção foi alterado nesta revisão. Foram adicionados este relatório e artefatos de reprodução.

O skill solicitado, **Code Review**, não foi encontrado nas pastas de skills disponíveis, inclusive no cache de plugins. A revisão foi realizada diretamente. O skill **OpenAI Docs** foi usado para verificar a alternativa de vídeo da OpenAI em documentação oficial.

## 1. Achados prioritários

### P1 — Texto gerado pode contradizer um fato obrigatório e continuar pronto

**Local:** `backend/app/services/studios/contextual_editing.py:939`, em conjunto com `backend/app/services/studios/gemini_editing.py:393`.

Reprodução: enviar roteiro e `lockedFacts` com **“Não garante resultado.”**; simular uma resposta estruturada válida com `onScreenText: "Garante resultado."`. O job termina com sucesso, o plano retorna `ready`, e a legenda contém a afirmação contraditória. O fato obrigatório continua armazenado, mas não impede a alteração de sentido.

O contrato valida a estrutura e exige `preserveMessage=true`; isso não verifica o significado. O compilador insere o texto recebido. A revisão do recibo de render verifica cobertura de operações e identificadores, explicitamente sem verificar correção semântica ou perceptual (`contextual_editing.py:1235`).

**Impacto:** um vídeo tecnicamente exportável pode comunicar uma promessa oposta à fornecida pelo cliente, mesmo no modo de preservação de mensagem.

**Correção proposta:** vincular afirmações a trechos e fatos de origem antes da compilação. Para fatos imutáveis, permitir inicialmente texto literal aprovado e transformações explicitamente delimitadas. Novas paráfrases exigem verificação de contradição e evidências; incerteza deve manter o texto original ou produzir alternativa. Um segundo parecer de LLM pode ajudar, mas não constitui garantia factual. Incluir números, unidades, datas, sujeitos, negações, ressalvas e relações entre cenas na validação.

### P1 — A IA consegue eliminar técnicas obrigatórias

**Local:** `backend/app/services/studios/gemini_editing.py:395`.

Reprodução: o usuário exige `requiredTechniques=["tracking"]`; o modelo devolve lista vazia. O serviço substitui a lista original. Resultado observado: `ready`, sem impedimentos, embora tracking seja explicitamente indisponível no renderizador contextual.

**Impacto:** a verificação de capacidades funciona apenas para as exigências que sobreviveram à resposta do modelo. A aplicação pode entregar um plano que omite silenciosamente parte do pedido.

**Correção proposta:** separar exigências obrigatórias do usuário e sugestões da IA. Mesclar técnicas sem apagar requisitos originais; preservar também a precedência de ordem explícita e recursos fixados. Quando houver conflito, exigir alternativa concreta. O modelo não deve poder reclassificar um requisito como opcional.

### P1 — Uma cena omitida pela IA perde a legenda vinculada pelo usuário

**Local:** `backend/app/services/studios/gemini_editing.py:377–393`; preenchimento posterior em `backend/app/services/studios/contextual_editing.py:545`.

Reprodução: uma cena tem transcrição revisada e `captionFromTranscript=true`. A resposta do modelo contém `beats=[]`. A preservação de transcrições percorre apenas as cenas devolvidas pela IA. Depois, o planejador cria uma cena padrão sem esses vínculos.

Resultado observado: plano `ready`, nenhuma legenda e `sourceTranscripts={}`. A vinculação exigida pelo usuário desaparece sem impedimento. O mesmo mecanismo também perde decisões de seleção vinculadas à cena omitida; esse segundo caso foi identificado por inspeção, não por uma reprodução separada.

**Correção proposta:** mesclar as cenas pela identidade original, mantendo todas as cenas com instruções vinculadas pelo usuário. Respostas incompletas devem conservar o estado anterior ou retornar erro explícito. Cobrir omissão parcial, omissão total, IDs repetidos, IDs inventados e retorno fora de ordem.

### P1 — O planejador não recebe o conteúdo da transcrição vinculada

**Local:** `backend/app/services/studios/gemini_editing.py:328–340` e `backend/app/services/studios/contextual_assembly.py:13`.

Reprodução: vincular uma transcrição revisada, sem copiar manualmente seu texto para outro campo. Capturar o contexto enviado ao planejador. O ID e a revisão estão presentes; **“Não garante resultado.”**, conteúdo real do segmento, está ausente.

No caminho padrão, a análise visual extrai somente o primeiro frame de até 24 clips (`gemini_editing.py:250–294`). O próprio registro informa `first_frame_per_clip` e `notFullVideoAnalysis=true`. Isso é uma amostra real do arquivo, mas não permite observar uma demonstração que acontece mais tarde nem compreender o diálogo a partir do áudio. A carga completa da transcrição ocorre posteriormente, na montagem determinística.

**Impacto:** decisões sobre o melhor momento de demonstração, informação correta e relação imagem/fala podem ser tomadas sem a evidência necessária. Fornecer o roteiro manualmente ajuda, mas não resolve a ausência da transcrição efetiva.

**Correção proposta:** carregar e validar transcrição e revisão antes da chamada. Acrescentar segmentos com timestamps, cobertura observada do vídeo e eventos sonoros efetivamente analisados. Usar detecção de cenas e amostragem temporal orientada por eventos; trechos não analisados devem permanecer identificados. Cachear análises por checksum e versão. Não afirmar análise de todo o vídeo a partir de um frame.

### P2 — Configuração e autoconfiança do modelo não constituem qualificação profissional

**Local:** `backend/app/routers/editing_resources.py:63`; `backend/app/services/studios/gemini_editing.py:480–508`.

O endpoint disponibiliza operações quando a configuração está presente, embora os adaptadores declarem qualificação pendente. Na avaliação de material gerado, `passed=true`, confiança autodeclarada de pelo menos 0,9 e lista vazia de problemas bastam para produzir `visualReview=passed` e `draft_material_ready`.

Existe revisão humana explícita e não se inventa aprovação humana. Ainda assim, o caminho automático pode admitir material sem evidência de que esse limiar detecta alterações de rosto, mãos, roupa ou continuidade. Trata-se de um resultado de verificação do modelo, sem calibração demonstrada para esses casos.

**Correção proposta:** distinguir `configured`, `executable`, `qualified` e resultado da avaliação de cada arquivo. Reutilizar os contratos existentes de benchmark, registro e evidências de provedores; acrescentar perfil específico para edição. Fixar também versão do avaliador e política. Qualificar por operação e tipo de material. A revisão humana da bateria inicial serve para medir os erros da automação, sem criar uma aprovação humana fictícia em cada job.

## 2. Respostas aos exemplos do produto

| Necessidade | Evidência e estado atual | O que falta |
| --- | --- | --- |
| Colocar a logo do Facebook no vídeo | Upload/acervo aceita uma marca arbitrária como imagem; composição pode usar esse asset como camada | Demonstrar o caso com arquivo oficial obtido e validado, transparência, proporção e identidade corretas |
| Buscar automaticamente a logo correta | Resolver consulta acervo e devolve alternativas de importação quando não encontra | Conector de origem oficial e aquisição integrada ao plano; descoberta não pode ser confundida com arquivo já disponível |
| Usar logo vetorial | Importação de logos aceita PNG, JPEG e WebP | Conversão segura de SVG, sem scripts/rede externa, preservando transparência e proporções, ou importação raster preparada |
| Gerar Homero e mantê-lo igual em três cenas | Há contrato para referências e geração/edição Gemini | Não há vídeo real qualificado dessa sequência nem prova de identidade consistente entre planos |
| Trocar somente a roupa | Existe pedido de transformação e aplicação localizada do intervalo | Verificação real de rosto, mãos, roupa, movimento, fundo e emendas; prompt não garante que só a roupa mudou |
| Obter uma fonte ausente | Consulta Google Fonts, importação e seleção de arquivo; evidência anterior de render com arquivo baixado | Encadear automaticamente necessidade → família/variante → aquisição → uso na cena, com cobertura de caracteres e versão |
| Aplicar estilos diferentes | Técnicas e perfis parametrizáveis, cores, proporções, texto e motion básico | Composição de perfis por cena; hoje múltiplos perfis podem retornar `reference_profiles_conflict` |
| Qualquer técnica profissional | Cortes, camadas, máscaras estáticas, keyframes, textos e áudio têm implementações | Tracking, rotoscopia, máscaras temporais, rampas de velocidade, estabilização e 3D não são capacidades do renderizador contextual |
| Qualquer duração/formato de arquivo | Caminho contextual tem limites explícitos; acervo novo valida vídeo MP4 | Normalização de entradas adicionais e medição de projetos longos/complexos; limites de código não provam qualificação em todos os extremos |
| Independência de fornecedores | Dois adaptadores de planejamento; render e acervo não dependem da LLM | Só Gemini implementa geração/transformação de mídia no registro novo; falta um segundo adaptador de mídia qualificado |

Uma logo exata deve entrar como arquivo rastreável na composição. Gerar uma imagem aproximada da logo não satisfaz a exigência de usar o recurso oficial. O código já marca material gerado com `official=false`, o que deve ser preservado.

Para personagens, a biblioteca de referências deve conter identidade visual, proporções, roupa, expressões, paleta e variações aprovadas. Cada cena precisa declarar o que permanece e o que muda. A qualidade deve ser demonstrada nos frames e nas transições, inclusive quando o personagem vira de costas, sofre oclusão ou aparece em outro enquadramento. Não há uma integração genérica que garanta qualquer personagem em qualquer situação.

O acervo atual não é uma busca irrestrita da internet: `resolve_resource` consulta o catálogo; `missingResources` gera impedimento para adicionar material. A configuração padrão de hosts de download contém apenas `fonts.gstatic.com`. Manter a validação de origem, redirecionamentos, tamanho, formato, checksum e isolamento por cliente ao ampliar os conectores.

## 3. O que já merece ser aproveitado

O renderizador contextual executa operações tipadas com FFmpeg, incluindo múltiplas camadas, fonte por arquivo, máscara estática, transformações animadas e mixagem. Operações desconhecidas podem ser bloqueadas antes do render. Montagem e acervo continuam disponíveis sem uma LLM.

Jobs registram provedor, modelo, revisão do documento e checksums de materiais. Há persistência do ID remoto e da resposta, proteção contra reaplicação em revisão antiga e tratamento conservador de submissão com resultado desconhecido. Não há troca automática de provedor após timeout incerto. Essas garantias devem ser mantidas ao adicionar um gerador.

A montagem a partir de transcrição é conservadora: mantém todos os clips e não corta segmentos falados no caminho implementado. Contudo, preservar cada frase isolada não demonstra que qualquer reordenação preserve o significado global. A seleção atual exige um único intervalo retido e restrições sobre a trilha principal; não equivale a edição livre de entrevista ou multicâmera.

HyperFrames permanece em um caminho separado. Sua projeção rejeita fontes personalizadas nesse fluxo, direcionando-as ao renderizador contextual. Portanto, a equivalência completa entre prévia e exportação nos dois renderizadores ainda não está demonstrada.

## 4. Validação executada nesta revisão

**Suíte existente: 59 testes aprovados, 2 avisos, 184,96 segundos.** Arquivos executados: `test_contextual_editing.py`, `test_editing_resources.py` e `test_editing_ai_providers.py`. Incluem render local e verificações de integração; respostas de provedores externos continuam simuladas nos respectivos testes.

**Novos testes de aceitação adversariais: 4 falhas reproduzidas, 14,41 segundos**, usando o endpoint neutro `/editing-ai-jobs`. Falhas correspondem aos quatro achados P1 acima. Uma primeira execução pelo endpoint legado apresentou as mesmas quatro falhas. Isso demonstra lacunas da orquestração diante de respostas possíveis do modelo; não mede a frequência com que Gemini cometeria esses erros.

Artefatos em `artifacts/validation/editing-code-review-20260906/`:

- `test_review_probes.py`: reproduções com respostas de IA simuladas e extração local de frames.
- `probes.xml`: resultados dos quatro testes de aceitação que falharam no endpoint novo.
- `controls.xml`: resultados dos 59 testes existentes.
- `run-probes.ps1`: execução isolada e repetível; saída 1 é esperada enquanto as lacunas não forem corrigidas.

Os testes usaram diretórios temporários novos para evitar o banco relativo recriado pelo `conftest.py`. Nenhuma API generativa paga foi chamada. Os testes novos ficam nos artefatos da auditoria, fora da suíte padrão, como reproduções dos problemas ainda abertos.

Foi também inspecionado o relatório anterior em `artifacts/validation/editing-resources-20260906/report.json`: três renders de quatro segundos, com filmagem real e apoio gráfico local, nas orientações vertical, quadrada e horizontal. O próprio relatório declara **zero chamadas generativas externas** e qualificação Gemini pendente. Esses vídeos comprovam composições limitadas, não a geração dos personagens ou transformações solicitados agora. Não foram regenerados nesta revisão.

## 5. Plano de implementação e aceitação

| Ordem | Entrega | Critério para avançar |
| --- | --- | --- |
| 1 | Preservação das instruções e fatos | Corrigir os quatro testes; acrescentar omissões parciais, contradições de números e negações, IDs inválidos e ordem explícita; nenhuma exigência obrigatória desaparece silenciosamente |
| 2 | Entendimento do material | Transcrição revisada, cenas, intervalos e evidências chegam ao planejador; demonstração no meio/final é identificada; cobertura e desconhecidos ficam registrados |
| 3 | Aquisição integrada | Resolver logo e fonte ausentes, obter arquivos de origem cadastrada, validar e aplicar em MP4; ambiguidade produz candidatos concretos, sem inventar origem oficial |
| 4 | Geradores intercambiáveis | Segundo adaptador real implementa submissão, consulta, download, cancelamento quando suportado e erros; documentos e timeline permanecem iguais ao trocar o fornecedor |
| 5 | Qualificação de mídia | Gemini e o candidato alternativo geram e transformam cenas da mesma bateria; registrar todos os resultados, falhas, consumo, latência e revisão visual, sem selecionar só exemplos bons |
| 6 | Cobertura profissional por técnica | Tracking, rotoscopia e demais extensões entram individualmente, com arquivos de referência, resultado esperado e avaliação do export; o catálogo só anuncia o escopo validado |

**Bateria base: 7 cenários × 3 proporções = 21 casos.** Apresentação, tutorial de tela, entrevista, demonstração de produto, narrativa com arquivo, fotografias e vídeo sem fala. Cada caso deve ter roteiro, arquivos com checksum, fatos, objetivo, identidade, plano, operações, export e avaliação vinculados. Usar durações diferentes e conteúdos cuja ação relevante esteja em diferentes posições do clip.

**Casos adicionais obrigatórios:** mesmo material com dois objetivos; fonte com acentos; marca não prevista no código; personagem em pelo menos três cenas consecutivas; troca de roupa com partes preservadas; áudio original; material ausente; ambiguidade de logo; técnica indisponível; perda de conexão antes/depois de obter ID remoto; mudança de configuração durante job; revisão antiga; edição localizada sem mudança nas demais cenas.

Para geração e transformação, começar com cenas curtas dentro dos limites declarados por cada adaptador e ao menos três tentativas por caso crítico e provedor. Registrar a dispersão dos resultados. Esse piloto não é uma certificação estatística universal; amplia-se a amostra conforme os tipos de falha observados. Não impor geração nativa quadrada se o fornecedor não a suporta: declarar a composição ou o recorte utilizado no export quadrado e verificar seu efeito no enquadramento.

**Avaliação técnica:** duração e quantidade de frames, decodificação, presença visual real dos elementos esperados, fonte por checksum, legibilidade de texto, sincronização de legendas e áudio, fala inteligível e loudness. Comparar as regiões preservadas e as emendas no vídeo transformado. Exportar MP4 com sucesso e listar IDs de camadas não basta.

**Avaliação editorial:** clareza, continuidade, ritmo, correspondência entre fala e imagem, manutenção de ressalvas e identidade. Revisar vídeos completos com áudio. Arquivar falhas de rosto, mãos, roupa, texto e mudanças não solicitadas. A avaliação humana inicial deve calibrar a avaliação automática; confiança numérica do modelo não deve ser apresentada como taxa de acerto observada.

**Política de execução:** Gemini continua principal, GPT limitado a testes locais. Consumo de produção deve ser observado por operação, sem introduzir teto financeiro não solicitado. Orçamento de testes, credenciais e registros ficam separados. Nenhuma troca de provedor após resultado incerto deve reenviar silenciosamente o pedido original; reconciliar o job conhecido primeiro.

## 6. Alternativa de vídeo da OpenAI

A documentação oficial de criação de vídeo informa que a **API Sora está programada para encerrar permanentemente em 24 de setembro de 2026**. O adaptador legado do repositório já contém essa data. Nesta revisão, em 6 de setembro, isso impede recomendar Sora como investimento duradouro para redundância de vídeo. [Referência oficial de criação de vídeo](https://developers.openai.com/api/reference/typescript/resources/videos/methods/create).

Ter uma chave da API OpenAI não integra automaticamente um gerador ao contrato novo nem demonstra adequação a essa bateria. Um candidato alternativo deve ser escolhido por operações efetivas, referências visuais, continuidade, ciclo de jobs, limites, qualidade e custo por resultado aprovado. Esta revisão não executou um comparativo de qualidade entre fornecedores; não há base aqui para declarar um vencedor universal em vídeo.

**Decisão recomendada:** corrigir primeiro os quatro problemas de preservação e contexto, integrar a aquisição de recursos e então qualificar outro gerador com a mesma bateria do Gemini. A promessa de produto defensável é editar e gerar dentro de capacidades verificadas, com alternativas para o que estiver fora delas. “Qualquer vídeo em qualquer hipótese” não é uma conclusão sustentada pelo código ou pelos testes atuais.
