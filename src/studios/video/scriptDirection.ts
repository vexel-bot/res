// Orientações de roteiro extraídas do Segundo Cérebro para briefings portáveis.
export const scriptGuidance = {
  approach: [
    "Defina o que o espectador precisa reconhecer cedo e a pergunta concreta que vale acompanhar. Escolha o gancho e a ordem em que a informação chega conforme o objetivo do filme.",
    "Ligue cada decisão a uma consequência observável. Quando houver uma virada, plante uma pista verdadeira e mostre o que permite reinterpretá-la. Dê tempo para ler a prova.",
    "No trecho decisivo, proponha duas versões que mudam uma escolha de cada vez. Indique a pergunta aberta de primeira exibição e o que uma resposta equivocada revelaria.",
  ],
  scenePlan: [
    "Entrada e saída da cena, o que o público já sabe e o que precisa perceber a seguir.",
    "Ação e consequência. Quais materiais, planos ou estados da interface comprovam a mudança.",
    "Último quadro útil de saída, primeiro quadro útil de entrada e onde o olhar precisa chegar. Indique a janela de leitura e o papel da fala ou do som.",
  ],
  review: "Na primeira exibição, peça a alguém sem contexto que reconte o que mudou e indique a prova antes de perguntar se gostou. Registre a hipótese de A/B e o que foi verificado no corte.",
  references: [
    {
      work: "Harry Potter e a Pedra Filosofal",
      passage: "Capítulos 11 e 17, incidente da vassoura e revelação final.",
      lesson: "O gesto de Snape admite duas leituras. A nova informação muda a causa atribuída ao incidente e permite voltar à pista observada.",
      source: "https://www.harrypotter.com/features/plot-twist-did-you-guess-the-identity-of-the-man-with-two-faces",
    },
    {
      work: "Dollar Shave Club",
      passage: "Apresentação da assinatura na abertura e percurso pelo depósito.",
      lesson: "A oferta chega cedo. Ações e objeções dão assunto para o restante do filme.",
      source: "https://www.youtube.com/watch?v=ZUG9qYTJMsI",
    },
  ],
};

export const scriptFormats = [
  {
    id: "ad",
    title: "Anúncio de resposta direta",
    focus: "Declare o benefício e as condições no ponto em que o público precisa deles. Mostre a ação do produto e o resultado que ela realmente permite. Feche com um próximo passo claro.",
    example: "Em um localizador fictício, uma atendente procura o pedido 214. Digita o número, toca em Buscar e encontra o mesmo pedido com o status legível. O convite para ver a demonstração vem depois desse resultado.",
    variation: "Compare abrir pelo benefício ou pela busca frustrada. Preserve prova, condições, duração e CTA.",
    question: "Que ação o produto permitiu, onde foi demonstrada e o que você faria agora?",
  },
  {
    id: "explainer",
    title: "Conteúdo explicativo",
    focus: "Comece por um caso reconhecível. Abra espaço para um palpite e mostre os dados que permitem revisar a hipótese. Entregue a ideia e dê ao espectador uma maneira de aplicá-la em outro caso.",
    example: "Em Startup Enxuta, 3 e 14 pedidos sustentam a pergunta inicial. As duas ofertas exibem preço e entrega. O destaque nas duas mudanças explica por que o próximo teste precisa manter uma delas fixa.",
    variation: "Compare nomear as duas mudanças antes do palpite ou nomear a segunda no momento de revê-lo. Preserve os dados em quadro e o próximo teste.",
    question: "Qual foi sua primeira hipótese, que dado mudou sua leitura e o que você testaria agora?",
  },
  {
    id: "brand",
    title: "História de marca",
    focus: "Mostre um desejo concreto, um obstáculo e a decisão que permite avançar. Se a marca ou o produto entrar na cena, deixe sua contribuição aparecer na ação ou em sua consequência.",
    example: "Em The Bear & the Hare, o presente deixado na entrada da toca se revela um despertador. O mesmo objeto explica por que o urso consegue chegar à festa.",
    variation: "Compare plantar o objeto antes da virada ou mostrá-lo apenas no desfecho. Preserve a decisão e a consequência.",
    question: "Qual escolha tornou o desfecho possível e que detalhe da abertura ganhou sentido?",
    source: "https://www.blinkink.co.uk/projects/the-bear-the-hare",
  },
] as const;
