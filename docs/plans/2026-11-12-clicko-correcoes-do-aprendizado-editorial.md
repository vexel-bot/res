# Clicko · correções do aprendizado editorial · 12/11/2026

## Escopo e capital

Implementação das limitações confirmadas na investigação anterior. **US$ 0 de chamadas de geração, planejamento ou avaliação por LLM.** Os testes substituem respostas dos modelos por respostas simuladas e executam o EffectCraft real. A consulta pública à NASA é gratuita e não usa a chave Anthropic/OpenRouter. Nenhum anúncio pago novo foi produzido. O limite/saldo do Console não foi alterado.

## O que mudou e o que foi comprovado

| Limitação encontrada | Correção aplicada | Prova e alcance |
|---|---|---|
| Índice incompleto e procedimentos omitidos | Índice completo, preservação de `operations`, busca no repertório amplo e por espaço | As cinco fichas omitidas estão consultáveis. Técnicas de outro espaço não vazam. Operações legadas são identificadas como procedimentos a adaptar. |
| Pesquisa guardada fora do fluxo nativo | 15 famílias de linguagem e 36 fichas das observações anteriores chegam à consulta; recuperação inicial relevante | Fontes, cobertura, hipótese, contraexemplo e estado de evidência conservados. Carregamento não transforma observação parcial em validação estética. |
| Método e gosto sem continuidade entre projetos | Guia versionado por projeto/espaço, situação/correção/quando usar/quando evitar; ferramentas para ler e propor lições | Preferência aprovada aparece em outro projeto do mesmo espaço. Versão antiga é recusada. Modelo não sobrescreve uma preferência aprovada. Históricos preservam versões. |
| Rejeição podia ser confundida com sucesso técnico | Feedback de revisão permanece separado de teste técnico e é recuperado na sessão | Um render tecnicamente válido continua marcado como revisão solicitada após rejeição. |
| Revisão com momentos estáticos esparsos | `review_clip`, taxa nativa por padrão, quadros consecutivos paginados, áudio medido, transcrição existente e trecho reproduzível | Fixture com clarão de um quadro e pulso sonoro mostra o quadro correto e o evento medido. Cache invalida quando o nativo muda. Cada página tem identidade própria na biblioteca de prévias. |
| Especialistas limitados a uma resposta | Ciclo de descoberta, inspeção, edição, revisão e correção em cópias isoladas; comandos executados são reaplicáveis | Dois especialistas em paralelo corrigem erro real de propriedade com keyframes. Tentativa rejeitada não deixa camada residual. Somente a contribuição escolhida entra na timeline. |
| Compatibilidade presumida com Adobe | Ferramenta de contrato nativo e notas de compatibilidade da versão; erros voltam ao editor para correção | `setValue` em propriedade animada é recusado; `setValueAtTime`, `setValueAtKey` e easing funcionam no ensaio real. Isso não certifica todos os scripts de After Effects/Premiere. |
| Busca de material restrita ao cadastro | Busca pública de imagens Commons, alternativa de metadados NASA, origem/atribuição preservadas e aquisição pelo importador existente | Teste simulado cobre descoberta, aquisição elegível e isolamento. Consulta real NASA passou. Commons respondeu 403 por política de robôs; não foi contornada. |
| Conhecimento e prévias podiam se perder na compactação | Snapshot editorial participa do prefixo estável; a retomada conserva estado e última página temporal da revisão atual | Testes de compactação mantêm versão do guia, plano e pixels, sem pares de ferramentas incompletos. |
| Nova prévia poderia ser interrompida antes do motor | Espera do encaminhamento alinhada ao orçamento de execução da revisão | A rota de prévia tem espera de 730 s para uma execução interna de até 600 s. Exportações de 30 e 45 s passaram localmente. |

O Opus continua escolhendo linguagem, duração, camadas, cenas, efeitos e exportação. As fichas oferecem procedimentos e contraexemplos. Não foi criado um molde obrigatório de vídeo nem uma frequência fixa de cortes. O enxame continua experimental e é escolhido no fluxo existente.

## Validação executada

1. **30 testes passaram em 195,06 s**, cobrindo repertório, guias, memória, revisão temporal, histórico, finanças e agente, incluindo os dois renders nativos de **30 e 45 segundos**. Comando reproduzível no PowerShell, a partir da raiz:

   ```powershell
   $env:PYTHONPATH='backend'
   $env:CLICKO_TEST_REAL_CRAFT='1'
   python -m pytest backend/tests/test_craft_material_search.py backend/tests/test_craft_editorial_knowledge.py backend/tests/test_craft_review.py backend/tests/test_craft_history_finance.py backend/tests/test_craft_agent.py backend/tests/test_craft_direction.py backend/tests/test_craft_swarm_real.py -o addopts='-q' --tb=short
   ```

   O teste de rede adicionado posteriormente é opt-in e fica ignorado nesse comando. As 30 verificações anteriores continuam incluídas. Há dois avisos preexistentes de Pydantic sobre o nome `copy`.

2. **Consulta real NASA: um teste passou em 7,64 s.** Executada em banco temporário isolado; registra candidatos reais e conserva direitos individuais como não verificados. Não baixa mídia nem declara inspeção visual.

   ```powershell
   $env:CLICKO_TEST_PUBLIC_MEDIA='1'
   python -m pytest backend/tests/test_craft_material_search.py::test_live_nasa_metadata_adapter -o addopts='-q' --tb=short
   ```

3. **Dois testes do encaminhamento passaram.** Use `NODE_ENV=test`, como no executor de auditoria do repositório. A primeira invocação sem esse ambiente foi recusada pela autenticação; com o ambiente correto os testes passaram, sem mudança na autenticação.

   ```powershell
   $env:NODE_ENV='test'
   node --import tsx --test server/studios/proxy.test.ts
   ```

4. **`npx tsc --noEmit` passou.**
5. **Interface real:** projeto separado `QA editorial local — 12 novembro`; uma preferência restrita a esse projeto foi salva e permaneceu após recarregar. Sem erros JavaScript. A prova simulou indisponibilidade de WASM para conferir o caminho com edição/render no servidor em um computador limitado. Não certifica o motor WASM no navegador. Captura local: `.codex-runtime/clicko-dev/editorial-guide-qa.png`.

## Critérios para os próximos resultados

Preservar o foco do plano do conselho: compreensão da oferta, progressão de ações, identidade, legibilidade, CTA, movimento e som. Custo e tempo devem acompanhar a qualidade; quantidade de tokens, efeitos ou camadas não é nota de qualidade.

- Registrar versão do repertório, guias, materiais, revisão, decisões, comandos, erros, correções e evidências recebidas pelo diretor.
- Avaliar se o público entende **o que é a ÓRBITA**, **o que está sendo oferecido** e **o que deve fazer**, antes de perguntar preferência estética.
- Comparar com a referência por mecanismo observado: o que muda no quadro, o motivo do corte, continuidade, curvas, hierarquia de texto, luz/sombra e alinhamento de eventos sonoros. Não atribuir áudio ouvido a uma fonte avaliada sem escuta.
- Medir tempo total, retrabalho e custo verificável por modelo/etapa. Sem chamadas nesta rodada, não há novo valor de qualidade por dólar a estimar.
- Só promover uma técnica como reproduzida após prova local correspondente. Compreensão e acabamento artístico exigem avaliação do vídeo resultante; testes técnicos não aprovam automaticamente a peça.

## Limites que permanecem explicitamente abertos

- O modelo recebe imagens temporais, medições e transcrição disponível. Não recebe percepção auditiva direta nesta integração; inteligibilidade e qualidade musical continuam sem certificação automática. A prévia permite avaliação humana com som.
- EffectCraft/FilmCraft são implementações independentes. A compatibilidade completa com os aplicativos Adobe não foi implementada nem demonstrada. A descoberta/correção reduz erros de contrato, sem criar operações ausentes.
- A busca pública nova cobre imagens de um provedor e candidatos de metadados de outro. Não é um mecanismo universal de extração de filmes, entrevistas, livros ou páginas. NASA pode conter materiais de terceiros; esses candidatos não são habilitados automaticamente para aquisição.
- As 15 famílias e as 36 fichas são repertório consultável; não comprovam domínio de qualquer gênero. A transferência estética e a comparação com edição pela IDE precisam de experimentos em peças novas, preservando avaliação independente e os materiais.
- Os ensaios locais usaram decisões simuladas. Não foi observado o comportamento de um Opus real com essas mudanças, nem alegado que o próximo anúncio já atingirá o nível das referências.

Origem da integração pública: [MediaWiki Search](https://www.mediawiki.org/wiki/API:Search), [Imageinfo](https://www.mediawiki.org/wiki/API:Imageinfo), [NASA API](https://images.nasa.gov/docs/images.nasa.gov_api_docs.pdf) e [condições de uso de mídia NASA](https://www.nasa.gov/nasa-brand-center/images-and-media/). Diagnóstico preservado no [atlas de 11/11](../studios/research/CLICKO_EDITING_INVESTIGATION_AND_STYLE_ATLAS_2026-11-11.md).
