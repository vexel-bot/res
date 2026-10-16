# Alight Motion: aprendizado e possibilidades para o res

Data: 2026-10-01. Escopo: pesquisa documental em fontes oficiais e inspeção do compositor nativo local. Nenhuma instalação, compra, integração ou exportação no aplicativo foi realizada. Não houve consumo de APIs pagas.

## Conclusão

O Alight Motion é uma referência pertinente para a camada de motion design e acabamento. A recomendação é transformar suas técnicas documentadas em operações reutilizáveis do res e usar o aplicativo, se disponível em dispositivo compatível, como bancada manual de comparação. Não há evidência suficiente nesta pesquisa para adotá-lo como worker de render automático.

Esta conclusão é uma hipótese de engenharia e direção, não uma aprovação visual. A documentação mostra capacidades; somente vídeos comparáveis e revisão humana poderão demonstrar melhora no nosso sistema.

## Capacidades documentadas e lacunas locais

| Técnica | Evidência oficial | Situação auditada no caminho nativo do res | Aplicação proposta |
|---|---|---|---|
| Desfoque de movimento | Desfoque proporcional à mudança de posição, escala e rotação [1] | `hybrid.tsx` aplica `filter: blur(...)`, um desfoque espacial; não há acumulação temporal de poses nessa implementação | Entradas rápidas de produto e tipografia com rastro coerente com a trajetória; parada nítida para leitura |
| Câmera e profundidade | Câmera em X/Y/Z, foco e paralaxe por distância [2] | Transformações executadas no renderer são translação X/Y, rotação e escala; não há câmera de perspectiva com Z nesse arquivo | Separar primeiro plano, produto e fundo; câmera compartilhada com perspectiva e foco controlados |
| Hierarquia de movimento | Camadas parent/child e objetos de controle invisíveis [3] | A árvore de nós e grupos já é renderizada | Planejar movimentos coordenados, preservando a posição relativa de texto, produto e grafismos |
| Curvas de animação | Curvas por intervalo, overshoot e opções de elasticidade [4] | Há interpolação e Bézier cúbica; as entradas dos componentes nativos ainda usam uma curva fixa | Parametrizar antecipação, aceleração, acomodação e pausa de leitura conforme a função narrativa |
| Revelação vetorial | Drawing Progress permite controlar o desenho de contornos [5] | Há caminhos SVG com `strokeDashoffset` e máscaras de revelação | Fazer um traço conduzir o olhar até a ação ou ao produto, com continuidade entre planos |
| Distorção por mapa | Displacement Map desloca pixels conforme os canais do mapa [6] | O renderer auditado não executa esse efeito; a projeção rejeita `editorialEffects` genéricos | Experimento posterior para refração localizada ou transição motivada, com limites de distorção da marca |

A existência de propriedades no plano não comprova execução do efeito. O ponto de observação desta auditoria foi o caminho de pixels do compositor nativo, não todas as capacidades possíveis de Remotion ou FFmpeg.

Arquivos inspecionados:

- `workers/remotion-benchmark/src/hybrid.tsx`: interpolação, montagem, máscaras, tipografia, hierarquia, filtros e geometria.
- `backend/app/providers/studios/remotion_projection.py`: validação da projeção e rejeição explícita de recursos ainda não qualificados.
- `backend/app/domain/studios/contextual_editing_v2.py`: contratos editoriais e limites dos comandos de câmera.

## O que deve virar conhecimento executável

Cada técnica estudada deve gerar uma ficha com fonte, objetivo visual, assets necessários, relações entre camadas, intervalo, trajetória, curva, máscara, evento sonoro, limites e critério de falha. O planejador deve escolher essa operação por intenção e fornecer parâmetros; o renderer executará apenas operações registradas.

Exemplo de ficha proposta, ainda não implementada:

```yaml
technique: product_pass_and_settle
intent: conduzir a atenção da ação para o produto
assets: [produto_autorizado_recortado, fundo, elemento_primeiro_plano]
relationships: produto e assinatura no mesmo grupo; oclusor separado
motion: antecipação breve; passagem rápida; desaceleração; pausa legível
mask: produto passa atrás do elemento de primeiro plano
sound: efeito curto alinhado à passagem; impacto discreto na acomodação
limits: manter geometria do logotipo; limitar rastro; preservar área de leitura
failure: entrada sem motivação, rastro na pausa ou produto ilegível
```

Os campos descrevem decisões e verificações, não o formato XML do Alight Motion. A técnica não deve substituir uma ação filmada necessária por zoom em fotografia. Ela deve estabelecer uma relação entre ação, produto, movimento e som.

## Integração: possibilidades e evidência insuficiente

**Uso manual:** o aplicativo pode servir para construir referências dirigidas e comparar movimentos. A ficha da App Store lista camadas, máscaras, vetores e exportação em MP4 e sequências PNG [7]. Uma referência feita por uma pessoa deverá constar como intervenção manual no Studio.

**XML e pacotes:** há um artigo oficial indexado sobre importação/exportação de XML [8] e um guia de Project Package por link/QR, importado no aplicativo [9]. Isso não comprova compatibilidade com nosso documento, inclusão de todos os materiais ou renderização em servidor. A abertura direta do artigo XML retornou 404 nesta consulta; a evidência foi o conteúdo indexado, com atualização de 2023 e coleta antiga. O recurso precisa ser confirmado na versão instalada antes de projetar um adaptador. Não foi encontrado um schema oficial nesta pesquisa.

**API/MCP/worker:** buscas nos domínios oficiais por API, SDK e renderização não localizaram documentação oficial de uma interface para render automático. Trata-se de resultado limitado da pesquisa, não de prova de inexistência. Uma futura integração depende de uma interface suportada, reprodutibilidade, observação de erros, custos e direitos de uso.

**Windows e disponibilidade:** a central de ajuda informa que Windows não é compatível [10]. Há divergência sobre Mac: o mesmo artigo nega suporte a macOS, enquanto a descrição atual da App Store menciona Mac [7]. Esta pesquisa não resolveu essa divergência; ela não altera a limitação do nosso ambiente Windows. Não há fundamento aqui para instalar emulador ou tornar automação de interface parte da produção.

**Custo:** a versão gratuita inclui marca d'água; assinaturas removem essa marca e habilitam recursos adicionais [7]. Não foi confirmado preço brasileiro. Uma assinatura não foi adquirida nem deve ser confundida com o orçamento compartilhado de US$ 10 em APIs da fase.

## Próximo ciclo sugerido

### Candidatura a motor principal

O usuário propôs também usar o Alight Motion como motor principal. Essa possibilidade deve permanecer aberta e ser distinguida em dois modos:

- **Edição e exportação assistidas:** uma pessoa trabalha no aplicativo e devolve o resultado ao Studio. Os recursos de composição e exportação documentados sustentam a candidatura, mas ainda não foi feito um teste prático. Toda intervenção deverá ser registrada.
- **Execução autônoma de jobs do Studio:** o sistema envia materiais e parâmetros, inicia a exportação, acompanha erros e recebe o arquivo. Não há uma interface oficial para esse ciclo identificada nesta pesquisa. Importação manual de XML não comprova essa capacidade.

A prova antes de uma substituição deverá validar: (1) entrada de um projeto editável com materiais e fontes corretos; (2) alteração reproduzível de texto, marca, duração e enquadramento; (3) exportação e retorno ao Studio, incluindo cancelamento e recuperação de falha; (4) comparação visual com o renderer atual, usando os mesmos materiais; (5) registro da versão do aplicativo, checksum, tempo, custo e intervenções. O modo assistido pode ser aceito como assistido; não comprovará autonomia.

A central oficial documenta erros de exportação por limites de recursos do dispositivo e quantidade de streams simultâneos. Isso exige medir capacidade no dispositivo real da prova; não demonstra que nossos projetos falharão. Fonte: [1037 Codec Init Failed](https://support.alightmotion.com/hc/en-us/articles/13065525178897-1037-Codec-Init-Failed).

Decisão nesta etapa: candidato a compositor principal, ainda não homologado. A pesquisa não autoriza declarar um adaptador pronto, retirar o renderer atual ou presumir melhora visual.

1. Parametrizar a coreografia dos componentes existentes: curvas por movimento, pivôs e grupos; manter continuidade de posição e tamanho entre planos.
2. Prototipar desfoque de movimento temporal sobre camadas gráficas, medindo também custo de render e comportamento junto a máscaras. Desfoque CSS não será aceito como equivalente.
3. Prototipar câmera de profundidade em composição controlada. Fazer a geometria observada e a auditoria refletirem as transformações realmente executadas.
4. Só então avaliar um efeito de refração ou distorção localizado. Não bloquear o ciclo inicial com uma biblioteca inteira de efeitos.

Os experimentos devem usar os mesmos materiais em uma versão atual e uma dirigida. Três estudos curtos podem isolar: passagem do produto com oclusão; tipografia coordenada com ação; continuidade de um grafismo entre planos. São diagnósticos de técnica, não substitutos dos três casos de qualificação comercial.

Depois dos estudos, aplicar as operações escolhidas a montagens completas, com áudio, assistidas em velocidade normal e tamanho de celular. Registrar plano, versão, checksum, intervenções e achados executáveis. Usar a comparação cega existente e manter QC técnico, qualidade visual e autonomia separados. Não promover um componente a `render_verified` somente por reproduzir uma receita documental.

## Fontes primárias

1. [Motion Blur](https://support.alightmotion.com/hc/en-us/articles/10537118778129-Motion-Blur).
2. [Camera Objects Guide](https://support.alightmotion.com/hc/en-us/articles/10536993608977-Camera-Objects-Guide).
3. [Layer Parenting and Null Objects](https://support.alightmotion.com/hc/en-us/articles/10536997444369-Layer-Parenting-and-Null-Objects).
4. [Animation Easing Curves](https://support.alightmotion.com/hc/en-us/articles/10536934703889-Animation-Easing-Curves).
5. [Drawing Progress](https://guide.alightmotion.com/effects/drawing-progress).
6. [Displacement Map](https://guide.alightmotion.com/effects/displacement-map).
7. [Alight Motion na App Store, descrição do desenvolvedor](https://apps.apple.com/us/app/alight-motion/id1459833443).
8. [How do I import and export XML? — conteúdo indexado; abertura direta indisponível nesta consulta](https://support.alightmotion.com/hc/en-us/articles/14718704039825-How-do-I-import-and-export-XML).
9. [How do I back up my projects?](https://support.alightmotion.com/hc/en-us/articles/13724965664785-How-do-I-back-up-my-projects).
10. [Minimum requirements to install Alight Motion](https://support.alightmotion.com/hc/en-us/articles/10537455340177-Minimum-requirements-to-install-Alight-Motion).
