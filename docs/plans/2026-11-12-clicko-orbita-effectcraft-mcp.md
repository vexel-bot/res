# ÓRBITA · referência local e comparação Clicko × MCP

## O controle editorial

Anúncio vertical de 18 s para a mostra fictícia ÓRBITA. A copy aprovada aparece em três momentos. “O futuro cabe num curta” abre. A categoria fica legível já no primeiro corte de rosto. A assinatura fecha com “Confira a programação”. Os recortes do curta aberto *Tears of Steel* ilustram o gênero. A peça não anuncia o filme como parte de uma programação confirmada. As imagens foram reenquadradas e graduadas individualmente, sem usar a faixa original. [Filme e procedência](https://studio.blender.org/projects/tears-of-steel/?asset=42) · [Créditos](https://studio.blender.org/projects/tears-of-steel/pages/credits/)

O projeto tem 35 camadas, sete planos de imagem e duas pistas sonoras originais. Cenas abertas e detalhes humanos alternam escala e temperatura de luz. Aos 6,25 s os hologramas deslocam a atenção para o mundo ficcional. Máquina, torre e travessia aceleram o trecho antes do convite. A assinatura ocupa aproximadamente os últimos 4,5 s. Os trechos de origem contêm alguns cortes internos além dos cortes da timeline.

O EffectCraft renderizou 432 quadros a 24 fps em 540 × 960. A inspeção a 300 px mostrou categoria e CTA legíveis. A análise não encontrou quadros quase uniformes. O pico de áudio medido foi −9,01 dBFS. Os oito acentos medidos elevaram a energia de 5,6 a 9,85 dB em janelas de 100 ms. A verificação de áudio usa forma de onda. Não houve avaliação de espectadores.

## Protocolo

O Opus 5.5 recebeu nos dois braços o mesmo briefing, inventário, sete planos, duas pistas e semente nativa com SHA-256 `952761d2293a7ec4381a676eae22ef01c8fa5b1e2c02712ff3db5120e065f815`. A montagem pronta ficou como controle externo. O teto foi US$ 1,50 por braço. As escolhas de cenas, cortes, ritmo e composição ficaram com o modelo.

A Clicko usou o adaptador nativo `clicko-effectcraft-1.0.2+67434e90`. O MCP usou o servidor oficial headless da distribuição v0.8.0, revisão `f953cd2`, no runtime local isolado. A revisão do adaptador está quatro commits à frente. A compilação exata foi interrompida após a validação da distribuição portátil, verificada pelo SHA-256 publicado. O cliente de ensaio envia ao Opus as ferramentas retornadas pelo servidor MCP e encaminha ao servidor os comandos escolhidos pelo modelo. O ensaio compara os caminhos de automação e seus ambientes locais. O controle por quadros conferiu a mesma composição com mídia e texto; diferenças de versão e amostragem limitam a atribuição de diferenças ao transporte. [Distribuição do EffectCraft](https://github.com/storytold/effectcraft/releases/tag/v0.8.0) · [Comparação de revisões](https://github.com/storytold/effectcraft/compare/f953cd2855bf36beffa6a4d608e9bf4b226e9442...67434e90388b6dca4417555346fa6850b6f96033)

Antes das chamadas pagas, a referência passou no render local. O MCP abriu a semente, executou um script em cópia, devolveu PNG e exportou um MP4 local. Renderizou também três quadros da referência para conferir mídia, tipografia e hierarquia.

## Evidência técnica

Na Clicko, a primeira sessão parou sem lote salvo. A chamada após a consulta de capacidades escreveu 159.803 tokens de cache e custou US$ 0,8246732. A consulta oferecia o catálogo completo. A página padrão passou a retornar 24 comandos com continuação, preservando a consulta por operação. No motor real, a primeira página ficou em 16.037 bytes frente a 357.578 bytes do catálogo inteiro de 673 comandos. A tentativa com paginação voltou a parar antes do primeiro lote, desta vez após inspeções das fontes.

## Resultado dos braços

| Caminho | Resultado | Consumo medido |
| --- | --- | ---: |
| Referência local | MP4 de 18 s, 35 camadas editáveis, sete planos e duas pistas | US$ 0 |
| Clicko original | Duas chamadas pagas, inspeção de fontes e capacidades, nenhum lote de montagem | US$ 0,9514642 |
| Clicko com capacidades paginadas | Três chamadas pagas, inspeção de fontes, nenhum lote de montagem | US$ 0,3009552 |
| MCP nativo | O Opus editou, reviu e pediu a exportação de 18 s. Sessão de 362,203 s, incluindo 98,17 s para a chamada de exportação | US$ 0,7543714 |
| **Total** | Sem submissões de cobrança incerta ao encerrar os recibos | **US$ 2,0067908** |

O teto de US$ 1,50 foi escolhido para cada braço usando o limite dos ensaios anteriores. A soma das duas tentativas Clicko ficou em US$ 1,2524194. O erro de estimativa de entrada pode interromper a sessão antes que ela consuma o saldo nominal. A segunda tentativa começa em semente idêntica, pois a primeira terminou sem rascunho. A repetição e a alteração de paginação estão registradas como intervenção no método. Esse braço terminou sem vídeo. O MCP usa o modelo pela API direta e um cliente de experimento que encaminha ferramentas ao servidor oficial. Este teste não executou a aplicação Claude Code.

O MP4 do MCP tem 432 quadros, sete planos em camadas, fundos desfocados, vinhetas, exposições e tipografia. A assinatura e o CTA estão legíveis no fechamento. A categoria só aparece por volta de 15,5 s, enquanto a referência a mostra em 2,67 s. Vários cortes do MCP ocorrem em 2,5, 6,5, 9 e 11,25 s. A pista de acentos continua baseada em 2,25, 6,25, 8, 9,5 e 11 s. A divergência enfraquece o sincronismo. O pico de áudio ficou em −9,39 dBFS e a média em −28,71 dBFS, 3,31 dB abaixo da referência. A inspeção por quadros e sinal de áudio não valida preferência de espectadores ou qualidade de escuta.

O corte MCP também foi importado na Clicko como documento editável `3f87527c-6153-4a0c-bd1e-7dbad35f1d66`, revisão 2. O ZIP exportado preserva o hash do projeto nativo e os nove arquivos de mídia. A referência local está no documento `273e5608-f162-4911-9c40-7df40fecf241`.

O resultado demonstra que o acesso MCP deste motor executa uma montagem mais extensa com menor custo de contexto que o caminho Clicko testado. A semente e os materiais foram os mesmos. As diferenças de ferramentas, contexto, prompts de sistema, versão de distribuição e ambiente de render limitam a atribuição causal. A aprovação como anúncio permanece pendente do cliente.

## Gargalos comprovados e encaminhamento

1. A consulta de capacidades precisava de paginação. A correção está integrada, com teste de recuperação de todas as páginas. A requisição sem filtro preserva acesso ao catálogo por continuação.
2. A sessão Clicko precisa resumir inspeções caras e indexar fontes antes da montagem. A amostra mostrou uma interrupção recorrente após o material ser inspecionado, com nenhum lote salvo. Reapresentar a estrutura inteira e converter bytes em previsão conservadora de tokens consome ou bloqueia o orçamento disponível. A paginação de capacidades resolveu uma parte do volume.
3. O agente precisa conferir a progressão da categoria e a correspondência entre cortes e sons no corte final. O MCP exportou um vídeo tecnicamente completo com essas duas falhas editoriais. O recebimento de um MP4 passa a ser registrado separadamente da aprovação do anúncio.
4. O motor e o computador atuais renderizaram referência e montagem MCP com sete planos, efeitos e áudio. A amostra sustenta continuar corrigindo o fluxo de direção, inspeção e revisão. Uma eventual atualização do EffectCraft deve ter seu próprio ensaio de regressão, pois o ambiente integrado está em v0.8.0 e existem versões públicas posteriores.

[Preparação e render](../../scripts/validation/clicko-orbita-reference.py) · [Executor dos braços](../../scripts/validation/clicko-orbita-compare-mcp.py) · [Medições dos exports](../../scripts/validation/clicko-orbita-compare-render.py) · [Tarifa Anthropic](https://platform.claude.com/docs/en/about-claude/pricing)
