# Recuperação do EffectCraft e diagnóstico do anúncio

O ensaio anterior consumiu respostas da Anthropic sem chegar ao salvamento definitivo da sessão interativa. A revisão entregue saiu de uma chamada curta de recuperação. Ela precisou de complementação local porque o modelo atingiu o limite de saída no CTA. Esses eventos medem limitações do fluxo e não permitem concluir qual seria a qualidade de uma sessão interativa completa.

| Limitação observada | Efeito | Alteração |
| --- | --- | --- |
| O rascunho existia em um diretório temporário até a resposta final. | A sessão validou e pré-visualizou lotes, mas os perdeu ao fechar o diretório. | Cada lote reaberto pelo EffectCraft grava um checkpoint privado com checksum. O original só recebe a revisão quando a sessão conclui. A tela permite retomar ou baixar um ZIP com o projeto e seus materiais. |
| O leitor exigia o último marcador da transmissão. | Um corte da conexão podia descartar uma resposta já concluída. A causa exata do corte anterior permanece indeterminada. | Uma resposta com todos os blocos fechados, motivo de parada e uso final pode ser aceita sem o marcador. Se falta conteúdo, o rascunho fica disponível. A Clicko pode fazer uma continuação curta, uma vez, se o pior caso da chamada pendente ainda couber no teto da geração. |
| Cada quadro retornava como uma imagem separada e era reenviado nos turnos seguintes. | Antes do último envio, a estimativa conservadora de entrada chegou a 129.147 tokens e deixava só 1.913 tokens de saída. | O Opus pode pedir até seis quadros em uma folha. A Clicko mantém a referência e as prévias recentes e encurta a conversa quando falta espaço no orçamento. Um turno truncado pode continuar a partir do rascunho. |
| Na recuperação anterior, o script truncado retornou erro do motor e mesmo assim o lote foi salvo como sucesso. | O MP4 inicial tinha apenas a captura importada e um fundo sem o anúncio. | Tanto o editor manual quanto a sessão de IA rejeitam lotes cujo resultado do motor contém erro. Um arquivo exportável deixou de mascarar a falha do script. |
| O planejador só aplicava a edição. | A exportação dependia de outro comando do operador. | A ferramenta finish_project salva a revisão e inicia o MP4 nativo. A repetição do mesmo pedido consulta o mesmo recibo e a mesma exportação. |

## Validação local

O teste usa a API da Clicko e o EffectCraft real em Docker, com a Anthropic simulada. Ele aplica um lote, provoca duas respostas interrompidas e confirma que o projeto original permanece na mesma revisão. O ZIP do rascunho contém o arquivo nativo recuperável. Uma nova requisição com a mesma chave reabre esse rascunho, confere os quadros, aplica a animação e pede a exportação. A Clicko salva uma revisão e entrega o MP4. Repetir a requisição devolve os mesmos recibos sem chamar o modelo. Gasto de API de US$ 0.

## Diagnóstico do MP4 anterior

| Intervalo | Observação | Decisão para o próximo corte |
| --- | --- | --- |
| 0–4 s | O grafismo da frente cobre as letras finais de “PRÓXIMO” e “CORTE” enquanto o espectador tenta ler. O objeto que provoca a oclusão não volta na demonstração. | Usar um elemento que atravesse a imagem, revele a frase completa rapidamente e reapareça como cursor ou linha de corte na demonstração. Conferir leitura nos quadros antes, durante e depois da revelação. |
| 4–9,6 s | A captura prova a divisão de um clipe em dois. A maior parte do intervalo mantém o mesmo enquadramento de interface, e o corte entra como outro bloco visual. | Mostrar a ação em seu enquadramento legível. Ligar o estado anterior e o posterior pelo mesmo clipe, com uma aproximação que comece antes do corte e mantenha as duas partes visíveis depois. |
| 9,6–15 s | A cartela recupera as cores e mostra o CTA. Os retângulos voltam sem retomar visualmente o corte demonstrado. | Transformar as duas partes já vistas no grafismo de saída. Usar a consequência da divisão para chegar ao CTA. |
| Faixa sonora | O MP4 tem AAC. A análise mediu volume médio de −38,1 dB e pico de −25,8 dB. A prova não tinha locução. | Ouvir o render em volume comum de celular e alinhar um acento ao momento da divisão, com nível audível e sem saturação. |

A análise editorial aplica inferências de legibilidade, causalidade e precisão de quadro à evidência do arquivo. A referência usa uma pessoa como primeiro plano e mantém um sujeito identificável. O vídeo da Clicko preservou o efeito gráfico de oclusão e perdeu essa continuidade. A próxima prova deve demonstrar o mesmo material antes, durante e depois do corte. Exibir mudanças de quadro ou obter um MP4 válido comprova execução técnica. Compreensão e qualidade percebida precisam de avaliação do vídeo.

A sessão atual observa amostras de imagem. Ela depende de mídia registrada, das ferramentas instaladas e do orçamento aprovado. A folha de quadros não transmite áudio nem prova o movimento entre amostras. Um reinício ou uma resposta incompleta ainda pode exigir retomada. O checkpoint permite recuperar a edição mesmo quando o saldo impede uma nova chamada.

[Referência de tipografia em profundidade](https://www.instagram.com/reel/DdwS-6oRvL8/)
