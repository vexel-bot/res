// Exercícios de decupagem do Segundo Cérebro, agrupados por problema de montagem.
export const decoupageTopics = [
  {
    id: "space",
    title: "Espaço, escala e cobertura",
    techniques: [
      {
        name: "Plano de situação e reorientação",
        practice: "Mostre entrada, fila e balcão no geral. Quando um detalhe mudar a geografia aparente, volte a um quadro que situe a pessoa.",
        check: "Em reprodução muda, de onde ela veio e para onde vai?",
      },
      {
        name: "Plano-mestre, médio e detalhe",
        practice: "Obtenha a ação completa, um plano com rosto e mão e um detalhe do contato. Para uma busca de pedido, mostre o gesto e o resultado com o mesmo número.",
        check: "Dá para montar de intenção a contato e resultado com margem antes e depois do gesto?",
      },
      {
        name: "Inserto e plano de cobertura",
        practice: "Insira o número de um pedido entre a pergunta e a resposta. Para mostrar a fila enquanto a voz continua, planeje também a volta ao balcão.",
        check: "O plano acrescenta informação clara e sua ação pertence ao momento mostrado?",
      },
      {
        name: "Eixo e direção em tela",
        practice: "Trace a linha cliente–atendente ou a direção de deslocamento. Escolha o lado das câmeras. Ao cruzar, use movimento visível ou um novo plano geral para reorientar.",
        check: "Os personagens ainda parecem olhar um para o outro? A direção de deslocamento continua legível?",
      },
      {
        name: "Campo, contracampo e plano subjetivo",
        practice: "Mostre o olhar da atendente, corte para o pedido na direção sugerida e depois mostre a reação. Se for um plano subjetivo, enquadre a partir da posição de quem olha.",
        check: "Quem viu o pedido e em que momento?",
      },
      {
        name: "Bloqueio de cena e revelação no plano",
        practice: "Posicione a atendente à frente de um painel. Faça seu deslocamento revelar o status, com posição final definida para a leitura.",
        check: "A cena mostra a relação espacial e o dado continua legível no celular?",
      },
    ],
    sources: [
      "https://ualresearchonline.arts.ac.uk/id/eprint/21187/",
      "https://www.acmi.net.au/education/school-program-and-resources/film-it-cinematography/",
    ],
  },
  {
    id: "continuity",
    title: "Continuidade, foco e virada",
    techniques: [
      {
        name: "Corte no movimento",
        practice: "No plano aberto, comece o alcance da mão. Entre no detalhe durante o mesmo gesto e preserve posição e direção aparente na emenda.",
        check: "Vê-se um alcance e um contato completos, sem repetição ou salto?",
      },
      {
        name: "Match cut gráfico e ponto de atenção",
        practice: "No Mirante, passe de prego a mão, pessoa e fachada pelo detalhe circular. Compare os quadros da emenda e ajuste a posição do foco antes de recorrer a uma transição.",
        check: "Qual foi o primeiro elemento percebido depois do corte e que relação ele sugere?",
      },
      {
        name: "Corte na reação e justaposição",
        practice: "Compare o mesmo rosto depois de uma fila de alertas ou de uma lista resolvida. Em material real, use a reação que corresponde ao acontecimento mostrado.",
        check: "Que emoção a pessoa leu e qual quadro a motivou?",
      },
      {
        name: "Corte de contraste",
        practice: "Depois de três planos cheios de solicitações, corte para uma pessoa parada diante de uma única pendência. Reserve tempo para localizar a mudança.",
        check: "O espectador aponta a mudança dramática quando o flash ou a batida são retirados?",
      },
      {
        name: "Retorno de motivo",
        practice: "Plante um objeto com uma função reconhecível. Quando ele voltar, mostre a ação que lhe dá outra função, como as janelas do Mirante passando a representar meses.",
        check: "Qual pista da abertura ganhou novo significado e o que no quadro prova essa relação?",
      },
    ],
    sources: [
      "https://www.amc.com/blogs/better-call-saul-q-and-a-director-michael-morris-on-the-enormous-deaths-that-led-to-the-birth-of-saul-goodman--1055132",
      "https://www.acmi.net.au/education/school-program-and-resources/film-it-editing/",
    ],
  },
  {
    id: "reading",
    title: "Tempo, comparação e interface",
    techniques: [
      {
        name: "Elipse e antes/depois",
        practice: "Mostre o envio e a resposta com o mesmo identificador. Indique tempo decorrido quando for decisivo e preserve o passo que demonstra o mecanismo.",
        check: "A pessoa sabe o que foi omitido e quanto tempo parece ter passado?",
      },
      {
        name: "Jump cut e montagem de progressão",
        practice: "No mesmo enquadramento, salte entre estados da bancada de montagem de um pedido. Cada salto precisa deixar legível qual etapa avançou.",
        check: "É possível ordenar as etapas e ouvir a fala completa?",
      },
      {
        name: "Montagem paralela",
        practice: "Alterne cliente enviando um pedido e atendente recebendo. Preserve o número ou uma indicação temporal. Para condições independentes, sinalize qual está em quadro.",
        check: "O público sabe o que foi simultâneo e o que pertence a cada condição?",
      },
      {
        name: "Comparação lado a lado",
        practice: "Aos 23–30 s de Startups, mantenha resultados e ofertas na mesma posição e destaque preço e entrega em sequência. Preserve a janela de leitura após o último dado.",
        check: "A pessoa explica por que 3 para 14 pedidos não identifica qual mudança causou a diferença?",
      },
      {
        name: "Decupagem de interface",
        practice: "Em Meu ISP, passe do mapa à nova rede, ao gesto na lista e ao portal. Em outra demo, identifique o estado inicial, o contato e a confirmação com um mesmo referente.",
        check: "Sem voz, dá para apontar onde agir e o que confirmou a ação?",
      },
    ],
    sources: [
      "https://www.adobe.com/creativecloud/video/post-production/cuts-in-film.html",
      "https://www.khanacademy.org/partner-content/pixar/before-the-story/storytelling",
    ],
  },
  {
    id: "sound-cuts",
    title: "Passagens entre imagem e som",
    techniques: [
      {
        name: "Corte em J e em L",
        practice: "Em J, ouça a atendente antes de trocar da fila para o rosto. Em L, mantenha o fim da fala da atendente sobre o resultado no celular.",
        check: "A sobreposição ajuda a chegar ao próximo plano sem confundir quem fala?",
      },
      {
        name: "Corte no ataque, no pulso e na palavra",
        practice: "Marque contato, acento da música e palavra indispensável em pistas distintas. Compare alinhar o corte ao contato ou à frase musical e deixe a informação legível.",
        check: "O público localiza o gesto e repete a palavra indispensável?",
      },
      {
        name: "Ponte sonora e ponto de escuta",
        practice: "Da rua para dentro da loja, preserve por um instante um som reconhecível e ajuste distância e presença conforme a perspectiva.",
        check: "Quem assiste percebe a troca de espaço e ainda entende a fala em mono?",
      },
      {
        name: "Crescendo, pausa e prova",
        practice: "Acumule sinais do problema e retire competição antes do estado que prova a mudança. Estude o recuo da Sol antes da entrada da solução e preserve a leitura da demonstração.",
        check: "Quem assiste identifica a virada e consegue explicar qual estado novo apareceu?",
      },
    ],
    sources: [
      "https://helpx.adobe.com/sg/premiere/desktop/edit-projects/trim-clips/perform-j-cuts-and-l-cuts.html",
      "https://filmsound.org/murch/stretching.htm",
    ],
  },
] as const;

export type DecoupageTopic = typeof decoupageTopics[number]["id"];
