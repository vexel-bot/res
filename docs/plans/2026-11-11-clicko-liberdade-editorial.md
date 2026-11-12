# Liberdade editorial do Claude na Clicko

## Comparação com o Reel

O [post de Matheus Gobbi](https://www.instagram.com/p/DflIbFny1zw/) descreve um tutorial de edição com Claude. O player expôs duração de 60,115 s e um quadro do apresentador em um ambiente real. Ao avançar pelos tempos, a captura permaneceu no mesmo quadro. O áudio e os passos internos da demonstração não puderam ser verificados. A publicação comprova a referência a edição com Claude e a presença de filmagem. A ferramenta usada, a ordem dos passos e a autonomia da execução ficam indeterminadas.

A lógica comum é analisar material, decidir o corte, executar no editor e conferir o resultado. Quando já existe filmagem, a imagem, a fala, a atuação e os acontecimentos fornecem pontos de corte. Uma composição motion do zero exige escolher ou criar material, desenhar a ação e definir o ritmo antes de montar. Dar ao modelo a mesma instrução genérica nos dois casos produz tarefas com graus diferentes de abertura. Uma integração documentada de Claude Code com Premiere entrega timeline e transcrição ao modelo, além de comandos de montagem. A documentação de visão da Anthropic descreve entradas por imagem. [PrimCut](https://docs.primcut.app/features/primcut-mcp) · [Claude Vision](https://platform.claude.com/docs/en/build-with-claude/vision)

## O que a auditoria encontrou

| Limitação no fluxo nativo | Efeito | Alteração |
| --- | --- | --- |
| A sessão inspecionava imagens e quadros do rascunho. Faltava abrir o clipe bruto em tempos escolhidos. | O editor precisava importar antes de avaliar o material, ou decidir a partir do nome e da timeline. | Inspeção local de fontes registradas com duração, resolução, taxa de quadros, presença de áudio e até seis pontos por folha. Os pontos usam o tempo da fonte. |
| A transcrição existia em outro fluxo. | O Claude na sessão Craft não recebia o que foi dito ou o momento da fala. | Leitura de transcrições prontas ou revisadas por segmento ou palavra, com tempos, checagem do workspace e vínculo ao checksum da fonte. |
| A finalização autônoma estava restrita ao EffectCraft. O FilmCraft já oferecia exportação MP4. | A sessão de montagem podia salvar a edição e ainda depender de uma exportação manual. | A ferramenta de finalizar aparece nos editores de vídeo que anunciam MP4. O FilmCraft também recebe a opção de planejamento mais longo. |
| A busca ignorava o menu dos comandos, e os materiais no contexto traziam principalmente IDs e tipos. | O modelo gastava rodadas para encontrar operações ou distinguir fontes. | Busca pelos termos no ID, rótulo, categoria e menu. Materiais incluem o título da biblioteca. |
| O sistema induzia a comparação de direções em todo brief motion e a demonstração de produto em qualquer pedido. | Um pedido de ajuste simples ou uma peça atmosférica podia herdar passos desnecessários. | Efeitos, legendas, cortes, cenas e uso do repertório ficam a critério do editor, conforme o pedido. |

Na inspeção local, o catálogo de comandos editáveis tinha 692 entradas do FilmCraft e 665 do EffectCraft. A contagem indica superfície anunciada pelo motor. Ela não certifica que todos os comandos tenham paridade com Premiere ou After Effects. Os controles de projeto isolado, arquivos registrados, validade das operações e orçamento permanecem no backend.

## Limites que continuam visíveis

- Os quadros de origem e a transcrição dão evidência para decidir. A sessão ainda não recebe a reprodução contínua nem escuta a mixagem.
- A leitura de transcrição aproveita o que foi preparado na Clicko. A sessão Craft ainda não inicia uma transcrição automaticamente.
- Motion composto em camadas pode ser criado no EffectCraft. Planos filmados inéditos, voz e música precisam existir como fontes ou vir de um processo de geração disponível.
- A edição fica no motor do projeto. O agente ainda não alterna sozinho entre FilmCraft e EffectCraft nem transfere uma sequência completa entre eles.
- Os efeitos, legendas e cortes dependem dos comandos disponíveis no motor escolhido. A antiga rota de aplicação de legendas por fora do motor continua rejeitada pela guarda que exige edição nativa.

## Comparação para a próxima rodada

Use o tema ÓRBITA nos dois exercícios. Na filmagem, forneça a mesma gravação bruta e transcrição para medir corte de fala, legibilidade e fidelidade das legendas. Na criação, forneça o mesmo briefing e os mesmos materiais para medir progressão entre cenas, composição, leitura e som. Em cada exercício, registre as ações que o Opus escolheu, o que o motor executou, o que precisou de ajuste e o que apareceu no MP4. Compare qualidade, tempo e custo dentro de cada exercício.

## Validação local

O FilmCraft real abriu uma fonte MP4 de teste, retornou quadros em 0,2 s e 1,3 s, recuperou uma palavra temporizada de uma transcrição já registrada, rejeitou uma consulta com checksum diferente, importou o clipe, criou uma faixa e uma legenda nativas e exportou a revisão em MP4. O teste simulou as decisões do modelo e usou as ferramentas reais. Gasto de API de US$ 0. A checagem TypeScript também passou.

Uma rodada ampliada encontrou falta de espaço no disco durante a preparação do SQLite. Após liberar arquivos temporários da pesquisa, a prova específica passou e a Clicko local voltou a responder. O teste antigo da rota de aplicação de legendas continua incompatível com a guarda de edição nativa.

## Teste ao vivo da ÓRBITA no FilmCraft

O Opus 5.5 via Anthropic direta recebeu dois cortes motion existentes da ÓRBITA, sem fala. A sessão tinha teto de US$ 1,50 e liberdade para escolher as tomadas, as transições, o som e a duração. O modelo fez seis inspeções de fonte, salvou seis lotes, conferiu duas folhas de prévia e chamou a exportação. A edição e o render usaram o FilmCraft real. Houve 28 chamadas e custo medido de US$ 0,7813152, sem exposição incerta. Tempo total de 3 min 13 s, com render de 12,8 s.

A abertura usa o círculo e a frase do corte anterior. A transição leva ao plano de Saturno e reaproveita a transformação do planeta na inicial da marca. Categoria e convite ficaram legíveis na amostra a 300 px. O MP4 mede 10,83 s em 540 × 960, 24 fps, com AAC. A faixa mediu média −33,5 dBFS e pico −18,5 dBFS, abaixo do pico de −10,1 dBFS da principal fonte. A verificação não encontrou trechos pretos com o limiar configurado de 120 ms. A sessão testa remontagem de material existente. Legenda de fala e criação de novas cenas não fazem parte deste caso.

O editor rejeitou quatro tentativas, por bloqueio de sincronismo, parâmetros de timeline.move e referência a uma faixa inexistente. O Opus salvou lotes posteriores e concluiu sem intervenção. Os erros mostram onde melhorar os esquemas dos comandos e a apresentação dos identificadores de faixa.

Sessão 343ac277-30c9-405a-89b2-1743b6a170c7. Projeto 0f9be0a9-801b-4db9-a91b-98b3073bc674. Render 630ae467-5bbf-4ccf-be32-f5abefbf72c1. SHA-256 eabc47cb72040ed7952cb656ebff948455e589d9f7a8a78dedfd57f5f02a3a53.
