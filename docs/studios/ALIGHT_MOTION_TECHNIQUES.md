# Técnicas de movimento: contratos e qualificação

As nove fichas abaixo integram o repertório existente do Studio. Seus IDs começam com `alight.`, mas as receitas `studio.motion-recipe.v1` descrevem decisões independentes do motor. Nesta implementação, todas permanecem `knowledge_only`. Os recursos descritos na documentação oficial não foram registrados como tutoriais acompanhados nem como renders verificados.

## Evidência e responsabilidade

Há três níveis: documentação consultada; tutorial acompanhado com passos, intervalo, resultado e verificação de áudio; inferência editorial. A fonte documenta o recurso do aplicativo. Objetivo perceptivo, parâmetros propostos e correções são inferências de direção até que estudos reais as validem.

Uma técnica só passa a `implemented` após existir implementação identificada por motor e versão. `render_verified` exige asset e checksum de evidência; nunca resulta apenas de aprovação do teste unitário. As fichas novas não têm exemplo aprovado. O repertório conserva as observações e qualificações anteriores em seus contratos existentes.

| Técnica / capacidade requerida | Condição de uso | Verificação perceptiva | Falha que pede mudança executável |
|---|---|---|---|
| Coreografia / `recipe.choreography` | Um objeto precisa chegar, acomodar-se e permanecer legível | Antecipação, aceleração, acomodação e pausa têm função distinta | Igualar valores no encontro entre intervalos; reduzir overshoot; aumentar pausa |
| Hierarquia / `recipe.layer_rig` | Produto e assinatura precisam conservar relações | Pai mantém o conjunto; filhos têm movimento local coerente | Corrigir pai e pivô; remover transformação duplicada |
| Oclusão / `recipe.occlusion` | Gesto ou objeto cobre uma troca de estado | Corte ocorre sob cobertura; máscara não expõe borda | Corrigir recorte e registro ou mover instante da troca |
| Tipografia / `recipe.typography` | Palavra reforça a ação em área de leitura planejada | Hierarquia, entrada e hold funcionam em celular | Reduzir palavras, ampliar hold, reposicionar área livre |
| Revelação vetorial / `recipe.vector_reveal` | Traço liga uma origem a um destino relevante | Progresso, direção e chegada permanecem contínuos | Mudar endpoint, curva ou eliminar traço decorativo |
| Motion blur / `recipe.temporal_blur` | Camada gráfica tem deslocamento rápido | Rastro acompanha velocidade e desaparece na pausa | Diminuir exposição/amostragem ou antecipar acomodação |
| Câmera com profundidade / `recipe.depth_camera` | Distâncias entre camadas têm lógica espacial | Paralaxe e foco não deformam o produto | Corrigir distâncias ou reduzir perspectiva |
| Refração localizada / `recipe.displacement` | Passagem exige distorção em região delimitada | Marca, texto e bordas permanecem corretos | Excluir área da marca, corrigir mapa, reduzir deslocamento |
| Montagem e som / `recipe.action_sound_cut` | Ação filmada ou tarefa tem consequência observável | Corte liga ações e ataque sonoro coincide com evento visível | Trocar tomada incoerente, ajustar corte ou ataque sonoro |

As seis primeiras são o conjunto de motion inicial. Montagem e som é uma responsabilidade editorial e de mixagem já necessária aos estudos. Profundidade e refração ficam para depois da prova básica de importação, materiais e exportação.

## Contrato executável

Cada receita pertence a uma cena, versão e IDs de elementos existentes. `startFrame` e `endFrameExclusive` são locais à cena. Os `frame` das keyframes são relativos ao início da receita; os frames de eventos sonoros são locais à cena. `sceneId` é acrescentado na persistência. O plano completo contém a resolução dos elementos para camadas do documento, permitindo que o compilador do motor preserve a associação.

`tracks` contém alvo, propriedade, keyframes e curvas cubic-bezier por intervalo. Propriedades possíveis: `x`, `y`, `z`, `rotation`, `scale_x`, `scale_y`, `opacity`, `stroke_progress`. A interpretação espacial precisa ser explicitada no compilador homologado: x/y relativos à composição, pivô relativo ao objeto, escala proporcional, rotação em graus e profundidade na unidade espacial do perfil. Não assumir que coordenadas do projeto exportado seguem essa convenção.

O contrato limita curvas, intervalos, números finitos, progresso 0..1, pivôs 0..1, stagger 0..60 frames, shutter 0..360°, amostras temporais 2..32, mapa de distorção e deslocamento de até 5%. Tipografia exige hold dentro do intervalo; coreografia exige tracks; hierarquia exige pai; oclusão exige alvo que cobre a troca; refração exige mapa. A cena rejeita IDs ausentes e eventos sonoros sem áudio/alvo. O compilador confere se o frame do evento coincide com o ataque executável do áudio.

Exemplo de direção de coreografia, ainda sem evidência de render:

```json
{
  "schemaVersion": "studio.motion-recipe.v1",
  "id": "hero-arrival",
  "version": 1,
  "technique": "motion_choreography",
  "targetIds": ["hero"],
  "startFrame": 0,
  "endFrameExclusive": 90,
  "intent": "Acomodar o produto antes de ler a assinatura",
  "continuityAnchor": "posição final do produto",
  "parameters": {
    "pivot": [0.5, 0.5],
    "tracks": [{
      "targetId": "hero",
      "property": "x",
      "keyframes": [
        {"frame": 0, "value": 0.18, "curve": [0.3, 0, 0.7, 1]},
        {"frame": 6, "value": 0.15, "curve": [0.15, 0, 0.2, 1]},
        {"frame": 24, "value": 0.53, "curve": [0.2, 0, 0.3, 1]},
        {"frame": 36, "value": 0.5, "curve": [0.2, 0, 0.2, 1]},
        {"frame": 90, "value": 0.5}
      ]
    }]
  },
  "verification": ["Sem salto na parada", "Produto nítido e legível durante a pausa"]
}
```

Esse exemplo é receita de conhecimento. Não usar sua presença para anunciar uma técnica como implementada no Alight. O Remotion atual rejeita receitas novas que ainda não executa; não as converte em zoom ou dissolvência. Para comparação de fidelidade, o primeiro ciclo deve usar a direção já compartilhada pelos motores e receitas efetivamente homologadas em ambos.

## Persistência e reprodução

As receitas são persistidas em `CreativeDocument.composition.narrative.editorialV2.motionRecipes` antes de calcular `motionRecipesDigest` e `executableComposition`. Alterar parâmetro muda o hash. O snapshot do job conserva a composição; o pacote inclui o plano validado; o recibo guarda hashes do pacote, vídeo recuperado e vídeo final.

O planejador envia decisões e dados. Não fornece Python, comandos ADB, seletores arbitrários nem XML. Compilação/importação dependem de driver local e formato comprovado. Recursos requeridos fora das capacidades homologadas aparecem como pendência.

O worker pode observar estado da interface, arquivos e propriedades de vídeo. Isso não mede automaticamente posição de camada, origem de cada quadro ou oclusão correta. Essas limitações permanecem explícitas no recibo até existir observação correspondente.

## Fichas de estudo

**Coreografia:** planejar quatro fases antes de escolher uma curva. O deslocamento prepara a atenção para uma pausa de leitura. Testar a mesma receita com produto e texto diferentes, sem editar código. Avaliar a parada em reprodução normal e quadros vizinhos; a chegada não pode virar uma oscilação contínua.

**Hierarquia:** identificar conjunto, filhos, pai e pivô. Mover o rig para preservar a posição relativa da identidade; reservar movimento local ao detalhe que comunica algo distinto. Testar reescala e outra proporção sem desalinhamento. O compilador precisa rejeitar hierarquia circular e pais não suportados.

**Oclusão:** escolher qual objeto justifica esconder a passagem. Definir estado anterior, cobertura, corte e estado posterior. Conferir uma sequência de quadros durante a travessia, além do quadro da troca. Sem recorte suficiente ou registro coerente, adquirir outro material ou corrigir a máscara; não trocar por fade automaticamente.

**Tipografia:** escolher a palavra relevante, área livre, ordem e duração de leitura. Uma entrada por caractere tem outra carga perceptiva que uma entrada por palavra. Testar fonte, acentos, quebras e texto alternativo. A pausa e a hierarquia devem continuar claras quando o vídeo cabe na largura de um celular.

**Vetores:** desenhar origem, percurso e destino. O traço conduz atenção; não precisa preencher toda a composição. Conferir direção do desenho e continuidade quando outra cena assume o ponto de chegada. Se o destino não comunica informação ou conexão, remover o elemento.

**Blur:** relacionar rastro à trajetória e velocidade. Distinguir desfoque temporal de um blur espacial constante. Conferir início, velocidade máxima e parada. Não qualificar CSS blur ou dissolvência como motion blur temporal. Exigir estudo no aplicativo e receita repetível antes de liberar a capacidade.

**Profundidade e refração:** manter como estudos posteriores. A primeira pede distâncias e câmera comuns; a segunda pede mapa e região delimitada. Nenhuma se resolve com foto ampliada. Testar preservação da marca e bordas durante o efeito completo.

**Montagem e som:** definir ações e escalas de plano antes de buscar materiais. Relacionar âncora de continuidade, entrada/saída e motivo de corte. Planejar ambiente, música e ataques por evento. Para ação e produto, o estudo exige oito segundos de ação dentro da imagem; fotografia com movimento externo não atende. FFmpeg continua responsável pelo som final.

## Fontes oficiais e alcance

- [Animation Easing Curves](https://support.alightmotion.com/hc/en-us/articles/10536934703889-Animation-Easing-Curves): recurso de curvas; não comprova a receita editorial acima.
- [Layer Parenting](https://support.alightmotion.com/hc/en-us/articles/10536997444369-Layer-Parenting): hierarquia de camadas.
- [Motion Blur](https://support.alightmotion.com/hc/en-us/articles/10537118778129-Motion-Blur): desfoque ligado a movimento.
- [Camera Objects Guide](https://support.alightmotion.com/hc/en-us/articles/10536993608977-Camera-Objects-Guide): câmera e profundidade.
- [Drawing Progress](https://guide.alightmotion.com/effects/drawing-progress) e [Displacement Map](https://guide.alightmotion.com/effects/displacement-map): efeitos específicos.
- [Project Package](https://support.alightmotion.com/hc/en-us/articles/13724965664785-How-do-I-back-up-my-projects): compartilhamento e recuperação de projetos; não define uma API automática.

O [relatório de pesquisa](research/ALIGHT_MOTION_ASSESSMENT_2026-10-01.md) registra as limitações de descoberta. O [worker](../../workers/alight-motion/README.md) define a prova real e os arquivos necessários para homologação.
