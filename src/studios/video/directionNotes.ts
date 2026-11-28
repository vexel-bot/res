// Resumos do cofre audiovisual destinados ao briefing que sai da Clicko.
export const directionNotes = [
  {
    id: "decupagem",
    title: "Decupagem",
    technique: "Defina o que o público sabe antes e depois da cena. Escolha tomadas para situar, demonstrar a ação e mostrar sua consequência. Leve o olhar de um plano ao seguinte pelo gesto, posição ou forma. Sustente a informação decisiva até ela poder ser comparada.",
    example: "Startups, 42 s, 23–30 s. Os resultados e as duas ofertas permanecem juntos enquanto o destaque passa do preço à entrega. Na Sol, 38–49 s, a pilha de envelopes cede à pessoa diante da caixa de entrada.",
    check: "Veja o trecho sem áudio no tamanho de um celular. Localize quando a última evidência fica legível e que conclusão os quadros permitem.",
    source: "https://ualresearchonline.arts.ac.uk/id/eprint/21187/",
  },
  {
    id: "narracao",
    title: "Narração",
    technique: "Defina ponto de vista e a pergunta que cada fala responde. Distribua evidência e explicação entre imagem, texto e voz. Leia em voz alta, troque termos abstratos por ações e reserve tempo para ligar causa e consequência.",
    example: "Na Sol, a narração passa da facilidade de receber e-mails à dificuldade de começar o trabalho. Startups transforma uma estatística abstrata em duas ofertas de marmita que o público pode comparar.",
    check: "Compare a mesma frase antes e depois da evidência. Em primeira exibição, peça que alguém explique a ideia com palavras próprias.",
    source: "https://transom.org/2021/how-to-build-your-editorial-muscles/",
  },
  {
    id: "voz",
    title: "Voz",
    technique: "Dê a quem lê um interlocutor, uma intenção por frase e a palavra que carrega o contraste. Marque respirações, nomes, siglas e números. Grave a mesma frase com duas intenções e mantenha o restante do corte ao comparar.",
    example: "Meu ISP, perto de 7 s. A fala de virada precisa soar como apresentação de algo que acaba de se tornar possível. Teste o nome do produto e o ritmo de convite antes de produzir toda a locução.",
    check: "Ouça a voz isolada e na mixagem em celular. Confira intenção, pronúncia, palavras mascaradas e pausas antes de aprovar as tomadas.",
    source: "https://transom.org/2014/story-workshop-spring-2014-insights/",
  },
  {
    id: "efeitos",
    title: "Efeitos sonoros",
    technique: "Selecione o acontecimento que merece som. Decida se o ataque orienta, marca o contato ou confirma o resultado. Use timbre, textura, distância e duração coerentes com o ponto de escuta.",
    example: "Meu ISP, na entrada da rede na lista do Wi-Fi. O sino pode marcar o estado novo. No Mirante, o metal do prego encontra um novo significado quando a chave volta ao quadro.",
    check: "Alterne o ataque presente, ausente ou deslocado. A melhor opção ajuda a localizar o evento e preserva a palavra indispensável.",
    source: "https://filmsound.org/murch/stretching.htm",
  },
  {
    id: "trilha",
    title: "Trilha sonora",
    technique: "Marque a progressão dramática antes de buscar música. Escolha pela articulação das frases musicais, densidade, instrumentação e pontos de edição. Proteja o tempo de leitura e a palavra da virada.",
    example: "Mirante — A parede, 12,3 s. A entrega contém duas viradas comparáveis, com rarefação e com subida musical. Em Baby Driver, Edgar Wright ensaiou ação e efeitos sobre a frase musical ainda no storyboard.",
    check: "Compare o mesmo trecho em níveis de reprodução equivalentes. Marque a descoberta e confira se ritmo, voz e ação continuam claros.",
    source: "https://assets.cdn.bbcmaestro.com/edgar-wright-filmmaking-course-notes-08c8.pdf",
  },
  {
    id: "ambiencia",
    title: "Ambiência e sons de fundo",
    technique: "Dê um fundo contínuo ao lugar e selecione acontecimentos distantes que o caracterizem. Use tom de sala nas emendas, mude perspectiva de escuta quando a narrativa pedir e reserve silêncio deliberado para um ponto de atenção.",
    example: "Mirante — A parede, 8–10,8 s. Use a faixa de ambiente para comparar presença da sala após a montagem acelerada. Em Sound of Metal, a perspectiva sonora muda junto com a experiência do personagem.",
    check: "Ouça solo e na mixagem. Procure emendas, loops, perda de perspectiva e mascaramento em fones, mono e alto-falante de celular.",
    source: "https://sbiff.org/sound-of-metal/",
  },
] as const;

export type DirectionTopic = typeof directionNotes[number]["id"];
