# Modelo de conhecimento editorial transferível para o res

**Status:** proposta de pesquisa, sem ingestão, migração ou alteração de código. **Base:** [15 Reels iniciais](./INSTAGRAM_EDITING_VIEWING_LOG_2026-09-30.md) e [30 Reels adicionais](./INSTAGRAM_EDITING_VIEWING_LOG_EXPANSION_2026-09-30.md), observados em 30/09/2026. A seleção foi intencional, não uma amostra estatística. O player estava mudo e vários vídeos foram amostrados por momentos, portanto as hipóteses de áudio e os intervalos não observados permanecem sem validação.

As [12 fichas estruturadas de operação](./INSTAGRAM_EDITING_OPERATION_CARDS_2026-09-30.json) oferecem uma versão legível por máquina deste modelo. Estão marcadas `research_only_not_ingested` e `knowledge_only`; não representam técnicas já instaladas ou aprovadas no produto.

## A mudança de unidade: de “estilo” para operação causal

O res precisa aprender **como** uma passagem produz uma percepção: que elemento persiste, que estado muda, qual material torna a mudança possível e como se reconhece a falha. “Usar efeito cinematic” ou “usar Higgsfield” não é conhecimento editorial suficiente. Um procedimento é recuperável por intenção e condições, independentemente de marca da ferramenta ou categoria de produto.

Exemplo: “revelação por oclusão” significa que um objeto físico encobre temporariamente a região que muda. Em [Ishift](https://www.instagram.com/creators/reel/Ddb0HfwRd93/), a mão cobre o rosto; a troca ocorre durante a cobertura; o rosto reaparece alinhado em outro estado. Isso pode ser realizado com cortes, máscara, geração ou composição, desde que a geometria e o gesto passem no teste. O sistema não deve memorizar “maquiagem” como requisito da técnica.

```text
brief + identidade + materiais
  → intenção narrativa e ação observável
  → busca de operações por efeito perceptivo e pré-condições
  → seleção de material e plano de captação/geração
  → grafo de camadas, tempo, espaço, áudio e fonte de cada elemento
  → render e evidências observadas
  → avaliação humana e correção executável
  → registro de sucesso/falha com versão da técnica
```

Um Reel de referência entra no primeiro estágio como **evidência e hipótese**. Ele não deve autorizar automaticamente a chamada de um provedor nem contaminar o master com assets de terceiros.

## Estado real do repositório e lacuna proposta

O projeto já possui `EditingTechniqueV1`, `TechniqueExampleV1` e `EditingObservationV1` em `backend/app/domain/studios/contextual_editing.py`. Há campos de finalidade, pré-requisitos, situações adequadas/inadequadas, parâmetros, capacidades exigidas, exemplos com intervalo, verificação, qualificação (`knowledge_only`, `implemented`, `render_verified`) e fonte. O repertório é buscado em `backend/app/services/studios/editing_repertoire.py`; o plano contextual registra `knowledge_ids` e `editorial_evidence`. A rota `/knowledge/documents` em `backend/app/routers/knowledge.py` guarda conteúdo pesquisável, metadados e citações. Isso é uma base aproveitável, mas **nenhum desses fatos prova que as 45 observações deste estudo foram ingeridas ou que o planejador já aprendeu as operações**.

| Necessidade revelada pela pesquisa | Existe parcialmente | Extensão proposta para uma etapa posterior |
|---|---|---|
| Fonte, intervalo, observação e `audio_verified` | `TechniqueExampleV1` | Distinguir frame observado, fala/texto do autor e inferência do pesquisador; guardar cobertura temporal e lacunas. |
| Adequação e pré-requisitos | `EditingTechniqueV1` | Expressar pré-condições testáveis: placa limpa, landmarks compatíveis, sujeito segmentável, área legível, licença e resolução. |
| Intenção, operação e evidência de execução | `ContextualEditPlanV1` | Amarrar cada decisão a uma versão de técnica, assets, parâmetros, camadas, evento de corte e evidência no render. |
| Qualificação `knowledge_only`/`implemented`/`render_verified` | `EditingTechniqueV1` | Acrescentar resultados por **brief e material diferentes**, reprovação humana, falhas e limites da generalização. |
| Busca semântica de documentos | `/knowledge/search` | Manter o texto como contexto; usar ficha estruturada para elegibilidade e execução. Similaridade textual sozinha não garante que o material suporte a técnica. |

Não convém pôr toda a pesquisa em um campo de prompt livre. O planejador pode propor, mas a composição deve referenciar operação registrada e parâmetros validáveis; a revisão deve enxergar por que ela foi escolhida.

## Ficha mínima de conhecimento

Este é um **exemplo de formato futuro**, não um contrato já implementado:

```yaml
id: occlusion_reveal_face_v1
version: 1
perceptual_goal: "a mudança acontece enquanto a mão encobre o rosto"
narrative_function: "transformar o mesmo personagem sem perder identidade"
source_evidence:
  - url: https://www.instagram.com/creators/reel/Ddb0HfwRd93/
    observed_samples_seconds: [0, 7, 20, 33, 46, 57]
    observation: "mão cobre o rosto; corte/alinhamento revela maquiagem"
    author_claim: "o seletor de transição mostrado é Ishift"
    inference: "a oclusão esconde o ponto de troca"
    audio_verified: false
input_contract:
  materials: ["plano antes", "plano depois"]
  identity_anchor: "mesmo rosto/personagem"
  geometry: "posição, escala e orientação facial compatíveis no ponto de troca"
  action: "mão atravessa a região que muda"
  rights: "assets próprios ou licenciados"
operation_graph:
  - "selecionar o frame de cobertura máxima"
  - "alinhar antes/depois nesse frame"
  - "trocar estado durante a cobertura"
  - "ajustar duração/curva apenas depois do alinhamento"
failure_signals:
  - "olhos/nariz saltam de posição"
  - "mão aparece em duas posições incompatíveis"
  - "o corte é visto antes de a mão cobrir o rosto"
render_checks:
  - "inspecionar frames imediatamente antes, durante e depois da oclusão"
  - "reproduzir em velocidade normal e tela de celular"
qualification: knowledge_only
```

**Precisão do exemplo:** as posições não representam visão contínua; são pontos/trechos amostrados. O texto da fala não foi transcrito do áudio. O campo `qualification` só pode subir após implementação, render, revisão e teste fora da referência.

## Vocabulário editorial, com pré-condições e controles

| Família de operação | Evidência principal | Entrada necessária | Transformação observável | Falha a rejeitar |
|---|---|---|---|---|
| Corte por ação/gesto | [junk journaling](https://www.instagram.com/creators/reel/DdtuxMNBtxr/), [humor no sofá](https://www.instagram.com/creators/reel/DdcB5_Ux7Bw/) | gesto ou tarefa real, início/meio/fim | trocar escala no ponto em que a ação continua | sequência sem ação interna, gesto interrompido sem propósito |
| Motivo recorrente | [matcha e street style](https://www.instagram.com/creators/reel/DdW0UoSxXsX/), [bola dourada](https://www.instagram.com/paulo.ia/reel/Dd5Md7NMj7P/) | objeto, cor, personagem ou forma identificável | variar ambiente mantendo a âncora | correspondência abstrata que o espectador não reconhece |
| Oclusão de passagem | [Ishift](https://www.instagram.com/creators/reel/Ddb0HfwRd93/) | duas tomadas alinháveis e elemento que encobre | trocar estado sob cobertura | salto de landmarks ou troca visível fora da oclusão |
| Máscara entre variantes | [X-ray](https://www.instagram.com/moonsol.design/reel/Ddv4nmHIsWI/) | original + variante registrada | máscara móvel revela só uma região | fundo muda fora da máscara; contorno pulsa |
| Texto em profundidade | [texto atrás da pessoa](https://www.instagram.com/creators/reel/DdwS-6oRvL8/) | sujeito recortável, placa base, espaço negativo | intercalar texto entre base e recorte | texto cruza corpo ou perde leitura |
| Janela editorial e keyframes | [travel dump](https://www.instagram.com/moonsol.design/reel/DSUcRaKAXYb/) | moldura recortada e conteúdo longo atrás | deslocar conteúdo sob abertura fixa | vazamento de borda, parallax inconsistente |
| Interface como cenário | [cartão de mapa](https://www.instagram.com/moonsol.design/reel/DRjjvOogSZg/), [Story de café](https://www.instagram.com/moonsol.design/reel/Ddbbg3MIl6u/) | layout e conteúdo próprios, hierarquia de leitura | inserir foto, cartão e cutout em zonas | interface falsa confundida com função real; informação ilegível |
| Mundo visual e personagem | [Dalí](https://www.instagram.com/paulo.ia/reel/DdXSz0yMUdX/), [promo do podcast](https://www.instagram.com/paulo.ia/reel/DdRkmq4M_7e/) | ficha de personagem, cenário, ação e estados | atravessar espaços/estilos preservando identidade | personagem, figurino e direção mudam sem motivo |
| VFX de evento localizado | [urso/flores/livros](https://www.instagram.com/paulo.ia/reel/DAD81xdOC8j/), [gato flutuante](https://www.instagram.com/paulo.ia/reel/DdHHUNrRCch/) | placa estável, objeto/referência e ação concreta | fenômeno entra, ocupa espaço e causa reação | sombra/escala/contato incoerente; objeto aparece do nada |
| Inventário antes da geração | [objetos flutuantes](https://www.instagram.com/paulo.ia/reel/Dcy8nVrM7Wx/), [bolso jeans](https://www.instagram.com/moonsol.design/reel/DdgvqW_oiBN/) | referências separadas, ordem de profundidade, direitos | compor/animar elementos específicos | identidade do objeto varia a cada frame |
| Canvas contínuo | [carrossel musical](https://www.instagram.com/moonsol.design/reel/Ddlg5vgIeTv/) | dimensões proporcionais aos painéis e motivo transversal | dividir uma composição longa em painéis | emendas desalinham; texto fica cortado |
| Prova na explicação | [Edits Assistant](https://www.instagram.com/creators/reel/Dd6fcwKRC9V/), [tutorial Work](https://www.instagram.com/paulo.ia/reel/Dd2EAaIBeRg/) | apresentador e tela real pertinente | trazer o exemplo quando a frase pede prova | screenshot decorativo, sem ligação com a alegação |

“Usar IA” não é uma operação nessa tabela. IA pode fabricar uma variante, preencher uma placa, animar uma imagem ou gerar uma cena; a decisão editorial continua sendo o contrato perceptivo entre entrada e saída.

## Como o sistema deve aprender sem copiar o Reel

1. **Ingestão de evidência.** Registrar URL, autor, data de observação, intervalo visto, tipo de peça (resultado, tutorial, bastidor), áudio verificado ou não, texto visível e declaração da legenda em campos distintos. Não incorporar fotografia, música, marca ou prompt privado como material de produção.
2. **Extração de operação.** Descrever antes/depois, âncora, gatilho, geometria, tempo e função narrativa. Se a demonstração omite um passo, registrar lacuna; não completar por imaginação.
3. **Abstração.** Remover detalhes acidentais como “café”, “xadrez” ou “CapCut” quando o mecanismo vale para outros objetos. Preservar dependências reais: mãos, placa limpa, variantes alinhadas, direitos e legibilidade.
4. **Seleção no planejamento.** Consultar por objetivo e material disponível. Uma técnica só é elegível se pré-condições forem satisfeitas ou se um plano de captação/geração resolver a pendência com custo e direitos conhecidos.
5. **Execução rastreável.** Resolver fontes, versões, parâmetros, ordem de camadas, intervalos, transformações, áudio e hashes. O sistema deve conseguir explicar o corte ou máscara executados, não apenas o nome do efeito pedido.
6. **Aprendizagem por resultado.** Anotar observações do render e avaliação humana; distinguir falha do material, falha da composição e escolha editorial ruim. Corrigir a ficha ou reduzir sua elegibilidade quando falhar em outros briefs.

## Portões de avaliação da transferência

**Teste A — mesma técnica, outros materiais.** Escolher três briefs de setores diferentes, como alimento, vestuário e ferramenta digital, usando imagens, textos e marcas próprios. Para cada brief, selecionar duas operações apropriadas sem mudar o código das operações. Um caso de recusa (material inadequado) é parte do teste; o sistema deve explicar a pendência e oferecer alternativa.

**Teste B — contraste editorial.** Com os mesmos materiais, produzir duas montagens de ritmo e lógica distintos. Revisores cegos para a variante avaliam ação observável, continuidade, clareza, ritmo, materialidade, acabamento e adequação à marca. A melhora frente à montagem “clipes concatenados” deve aparecer na reprodução normal, não só em stills escolhidos.

**Teste C — fidelidade de execução.** Conferir plano versus MP4 em pontos de corte, geometria, camadas e eventos sonoros. Pelo menos início/meio/fim e frames de máscara/transição são obrigatórios. Como a pesquisa do Instagram foi sem áudio, qualquer regra de som permanece hipótese até teste com escuta do master.

**Promoção de técnica:** `knowledge_only` significa evidência suficiente para propor e pesquisar; `implemented` exige operação executável e testada; `render_verified` exige caso renderizado, revisão e evidências armazenadas. Para alegar generalização, é necessário resultado positivo em múltiplos briefs/materiais e registro de falhas. Um Reel popular ou um único demo não basta.

## Decisão futura sobre Higgsfield

O [tutorial de freeze motion](https://www.instagram.com/moonsol.design/reel/DdjIM_qo-jL/) mostra uma imagem anexada ao ChatGPT e uma chamada “@ Higgsfield”. Isto indica um **fluxo de plugin exibido no vídeo**; não demonstra que há MCP, API, licença comercial, preço previsível, callback de job ou correspondência de qualidade para o res. A decisão de integração deve vir **depois** de uma prova separada com: contrato de entrada/saída e proveniência; parâmetros e referência de identidade; previsibilidade de custo, cancelamento e retomada; termos de uso comercial; e comparação visual controlada contra os provedores já integrados. O julgamento editorial deve pedir “gerar uma ação com as propriedades X” e só então escolher provedor elegível.

## Próximos artefatos de conhecimento recomendados

O caderno de observações é o **registro de fonte**. As [fichas de tutoriais](./INSTAGRAM_TUTORIAL_WORKFLOWS_2026-09-30.md) são o **manual de operação**. A [gramática editorial](./INSTAGRAM_EDITING_GRAMMAR_2026-09-30.md) é a **taxonomia de escolha**. A proposta presente define o **contrato de aprendizagem e avaliação**. Antes de implementar, revisar as fichas com uma segunda pessoa, escutar exemplos de som e escolher um conjunto legalmente utilizável de materiais para os testes cruzados. Nenhum desses documentos representa aprendizagem automática já ocorrida no produto.
