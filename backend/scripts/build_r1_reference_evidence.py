# ruff: noqa: E501 -- the reference corpus intentionally keeps long Portuguese observations intact.
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Unit:
    unit_id: str
    title: str
    creator: str
    source_url: str
    rights: str
    source_kind: str
    summary: str
    structure: tuple[tuple[float, float, str, str], ...]
    character: str
    world: str
    image: str
    edit: str
    motion: str
    sound: str
    strengths: tuple[str, ...]
    limitations: tuple[str, ...]
    principle: str
    counterexample: str
    acceptance_test: str
    difficulty: str
    visual_phases: tuple[tuple[float, float, str, str], ...]
    source_start: float = 0.0
    source_end: float | None = None


UNITS: tuple[Unit, ...] = (
    Unit(
        "instagram-DTRBJoOAUl1",
        "Três cuidados contra deepfakes",
        "@paulo.ia",
        "https://www.instagram.com/reels/DTRBJoOAUl1/",
        "Pesquisa por acesso autenticado; copyright do criador; referência, não asset de produção.",
        "instagram_reel",
        "Um alerta de segurança demonstra o próprio risco ao trocar continuamente a identidade visual do apresentador, antes de entregar três ações práticas.",
        (
            (0, 6.56, "hook", "impossibilidade de distinguir o real"),
            (6.56, 13, "promise", "três ações de proteção"),
            (13, 28.04, "proof", "verificar autor e fonte"),
            (28.04, 37.88, "application", "senha familiar contra fraude"),
            (37.88, 40.8, "open_end", "a evolução da IA mantém a urgência"),
        ),
        "Um apresentador olha para a câmera e mantém gesto e posição enquanto identidades públicas sintéticas ocupam o rosto; a continuidade corporal faz a transformação parecer uma prova, não um adereço.",
        "O mesmo corredor de convenção/aeroporto permanece reconhecível. A repetição do lugar estabiliza a leitura enquanto a identidade muda.",
        "Plano vertical médio, fundo profundo e centralidade facial. A mudança de rosto é o foco; título e legendas queimadas sustentam leitura sem áudio.",
        "Abertura de alta frequência visual; os cortes e trocas desaceleram quando a fala vira checklist. O argumento, e não uma régua fixa de três segundos, governa as mudanças.",
        "Face replacement e continuidade de pose incorporam a tese. O efeito é estrutural porque remover a troca enfraqueceria a mensagem.",
        "Voz frontal inteligível sobre música baixa; a progressão ordinal organiza a atenção. A transcrição automática erra o encerramento e não deve ser tratada como citação.",
        (
            "demonstração incorporada ao argumento",
            "cenário constante reduz custo cognitivo",
            "conselhos concretos pagam a promessa do hook",
        ),
        (
            "uso de rostos reconhecíveis eleva risco de consentimento e confusão",
            "o encerramento fica truncado na versão capturada",
            "o alcance exibido é metadado de plataforma, não causalidade provada",
        ),
        "Quando o risco é visual, faça a imagem executar o risco enquanto a voz nomeia o mecanismo.",
        "Trocar rostos apenas para causar surpresa, sem conectar a transformação à afirmação verbal.",
        "Sem som, uma pessoa deve identificar o risco em até quatro segundos; com som, deve repetir duas ações de proteção ao final.",
        "alta: performance travada, composição, tracking e revisão ética",
        (
            (0, 6.56, "identity_demo", "trocas de identidade provam o hook"),
            (6.56, 13, "presenter_title", "promessa ordinal"),
            (13, 28.04, "presenter_checklist", "dicas um e dois"),
            (28.04, 37.88, "presenter_checklist", "senha familiar"),
            (37.88, 40.8, "presenter_outro", "encerramento"),
        ),
    ),
    Unit(
        "instagram-DcuHK9ChRrP",
        "Tutorial de depth map para vídeo",
        "@paulo.ia",
        "https://www.instagram.com/reels/DcuHK9ChRrP/",
        "Pesquisa por acesso autenticado; exemplos de filmes e ferramentas exigem direitos próprios para reutilização.",
        "instagram_reel",
        "O vídeo parte de exemplos reconhecíveis de profundidade e transforma o conceito em um fluxo prático: referência, mapa de profundidade, personagem, geração e acabamento.",
        (
            (0, 12, "hook", "efeito cinematográfico e promessa de reprodução"),
            (12, 31, "concept", "separação entre câmera e profundidade"),
            (31, 50, "demonstration", "captura de paisagem e criação do depth map"),
            (50, 70, "build", "personagem e composição"),
            (70, 90.67, "payoff", "geração, acabamento e resultado"),
        ),
        "Apresentador atua como instrutor e âncora de continuidade; a tela dividida mantém rosto e evidência simultaneamente.",
        "A paisagem própria funciona como matéria-prima e como palco do resultado, ligando aquisição, composição e geração.",
        "Split-screen, inserts de referência, gravações de interface, mapa em escala de cinza e comparação antes/depois tornam uma transformação abstrata verificável.",
        "Alterna explicação e execução. Cada mudança visual coincide com uma nova dependência do processo, reduzindo a sensação de tutorial como lista solta.",
        "Depth map tem função geométrica; character sheet e composição têm função de continuidade. Interfaces são evidência de processo, não decoração.",
        "Voz conduz etapas; efeitos de interface e música ficam subordinados. Nomes de ferramentas na transcrição automática requerem conferência humana.",
        (
            "cadeia causal visível",
            "tela dividida preserva autoridade e prova",
            "resultado é preparado por etapas observáveis",
        ),
        (
            "dependência de serviços e licenças mutáveis",
            "alguns exemplos de cinema são apenas referência",
            "muita densidade de ferramentas para audiência iniciante",
        ),
        "Mostre o estado de entrada, a transformação intermediária e o estado de saída para toda técnica ensinada.",
        "Exibir somente o prompt e o resultado, ocultando as decisões intermediárias que explicam por que funcionou.",
        "Um revisor deve reconstruir a ordem de produção apenas assistindo às imagens sem áudio.",
        "alta: captura, composição 2.5D, geração e continuidade",
        (
            (0, 12, "reference_split", "referências estabelecem o efeito"),
            (12, 31, "concept_diagram", "câmera versus profundidade"),
            (31, 50, "landscape_depth", "paisagem vira mapa"),
            (50, 70, "character_composite", "personagem entra no espaço"),
            (70, 90.67, "generated_payoff", "resultado e acabamento"),
        ),
    ),
    Unit(
        "instagram-DcRjR01BFVM",
        "Jornada de produto apresentada como missão",
        "@paulo.ia",
        "https://www.instagram.com/reels/DcRjR01BFVM/",
        "Pesquisa por acesso autenticado; imagens de evento e marcas permanecem referência editorial.",
        "instagram_reel",
        "Uma apresentação de produto usa a metáfora de missão espacial para organizar origem, obstáculos, lançamento e convite final.",
        (
            (0, 15, "hook", "missão e ambição"),
            (15, 38, "origin", "problema e começo da jornada"),
            (38, 62, "tension", "construção e obstáculos"),
            (62, 82, "launch", "produto e prova de evento"),
            (82, 96.4, "cta", "convite e próximo passo"),
        ),
        "O fundador alterna entre presença em palco e figura dentro da metáfora. A performance real entrega credibilidade; o astronauta carrega escala emocional.",
        "Palco, dashboard e paisagem lunar formam três níveis: prova real, produto e metáfora. A alternância precisa deixar claro qual nível está falando.",
        "Planos de evento, telas de produto e CGI lunar contrastam escala humana e ambição. Luz de palco funciona como ponte cromática para o espaço.",
        "A montagem cresce de origem para lançamento; os inserts de produto chegam depois que a metáfora estabelece a jornada.",
        "CGI espacial dramatiza progresso, mas depende da correspondência entre cada etapa da missão e um fato do produto.",
        "Fala de palco e trilha aspiracional sustentam aumento de escala; crowd/event ambience oferece prova de presença.",
        ("metáfora recorrente cria unidade", "prova de evento ancora CGI", "progressão temporal dá sentido à montagem"),
        (
            "metáfora pode prometer mais que a evidência",
            "dashboard aparece brevemente",
            "autoria de cada asset precisa de ledger",
        ),
        "Uma metáfora visual deve reaparecer com mudança de estado sempre que o argumento avança.",
        "Usar astronauta, foguete ou universo como B-roll genérico para qualquer narrativa de crescimento.",
        "Cada plano metafórico deve mapear para um beat factual nomeável e nenhum fato crítico pode depender só da metáfora.",
        "muito alta: cobertura de evento, produto, CGI e mixagem",
        (
            (0, 15, "mission_metaphor", "estabelece escala"),
            (15, 38, "stage_origin", "origem e problema"),
            (38, 62, "journey_crosscut", "obstáculos"),
            (62, 82, "launch_proof", "produto e evento"),
            (82, 96.4, "mission_cta", "convite final"),
        ),
    ),
    Unit(
        "instagram-DciIBRYBHBK",
        "Distribution is the final boss",
        "@mep.io_",
        "https://www.instagram.com/reels/DciIBRYBHBK/",
        "Pesquisa por acesso autenticado; clipes de terceiros e marcas são evidência editorial, não assets liberados.",
        "instagram_reel",
        "Um ensaio visual argumenta que criar um bom produto não basta: distribuição, embalagem e repetição vencem o último obstáculo.",
        (
            (0, 9, "hook", "distribution como chefe final"),
            (9, 28, "problem", "bons produtos invisíveis"),
            (28, 49, "proof", "fundadores, mídia e exemplos"),
            (49, 69, "framework", "sistema de distribuição"),
            (69, 87, "cta", "playbook e comentário"),
        ),
        "O narrador não precisa aparecer continuamente; fundadores e exemplos assumem papéis de prova dentro da argumentação.",
        "O mundo é uma superfície editorial preto/branco com janelas de arquivo, interfaces e marcas; a coerência vem da gramática, não de um lugar físico.",
        "Tipografia grande, mural de mídia, cards, logos e screenshots. O contraste alto prioriza tese e evidência.",
        "Cortes são motivados por mudança de proposição. Repetições e escalas de layout criam aceleração sem duração fixa.",
        "Motion organiza hierarquia e causalidade: palavra-chave, prova, sistema e CTA ocupam camadas distintas.",
        "Voz com cadência assertiva; impactos e música marcam proposições. Sound design ajuda a transformar cards em eventos.",
        ("cada visual tem função argumentativa", "gramática gráfica consistente", "CTA é preparado pelo framework"),
        (
            "clipes de terceiros elevam risco de direitos",
            "densidade visual pode superar leitura",
            "o argumento de distribuição precisa de evidência além de exemplos selecionados",
        ),
        "Num ensaio faceless, cada mudança de layout deve corresponder a uma mudança lógica: afirmação, prova, contraste ou conclusão.",
        "Mudar cards rapidamente apenas para manter movimento, sem alterar a função lógica da tela.",
        "Congele qualquer frame: o revisor deve saber se está vendo tese, prova, contraste ou CTA.",
        "alta: pesquisa, design editorial, motion e mix",
        (
            (0, 9, "thesis_type", "tese em tipografia"),
            (9, 28, "problem_archive", "invisibilidade e falha"),
            (28, 49, "proof_wall", "exemplos e mídia"),
            (49, 69, "system_cards", "framework"),
            (69, 87, "offer_cta", "playbook"),
        ),
    ),
    Unit(
        "instagram-DcsuFSGhnlw",
        "Anatomia de um vídeo viral",
        "@mep.io_",
        "https://www.instagram.com/reels/DcsuFSGhnlw/",
        "Pesquisa por acesso autenticado; análise reutiliza o próprio vídeo do criador como objeto.",
        "instagram_reel",
        "O vídeo anterior é reproduzido dentro de uma timeline didática enquanto rótulos HOOK, IDEA, BUILD, VALUE e CTA revelam sua arquitetura.",
        (
            (0, 12, "hook", "promessa de desmontar o vídeo"),
            (12, 27, "idea", "nomeia a ideia central"),
            (27, 47, "build", "acompanha construção"),
            (47, 69, "value", "explica entrega de valor"),
            (69, 87.79, "cta", "fecha análise e ação"),
        ),
        "O editor/narrador ocupa papel de analista. O vídeo original vira personagem-objeto cuja transformação estrutural é acompanhada.",
        "A timeline de edição é o cenário; os rótulos acumulados dão memória espacial ao espectador.",
        "Vídeo dentro do vídeo, playhead, faixas coloridas e rótulos persistentes conectam fala a uma posição temporal concreta.",
        "A montagem mantém sincronização entre o exemplo e sua explicação. O formato é um comentário audiovisual, não uma mera reação.",
        "Motion serve como anotação: cores e blocos indicam fronteiras funcionais. Acumulação mostra o todo ao final.",
        "Voz analítica, reprodução do áudio-fonte e efeitos de interface precisam de ducking para não competir.",
        (
            "metalinguagem observável",
            "taxonomia aparece no próprio tempo",
            "o espectador vê e ouve a prova simultaneamente",
        ),
        (
            "a taxonomia em cinco partes pode simplificar casos complexos",
            "o vídeo analisado é do mesmo ecossistema",
            "cores precisam de legenda e acessibilidade",
        ),
        "Ao ensinar estrutura, projete a estrutura sobre o tempo real do exemplo e preserve o contexto suficiente para o público verificar.",
        "Nomear HOOK e CTA depois do fato sem demonstrar o ponto exato em que expectativa abre e fecha.",
        "Dois anotadores devem marcar as cinco fronteiras com diferença máxima de dois segundos e justificar divergências.",
        "média-alta: captura temporal, composição e mix de fonte",
        (
            (0, 12, "timeline_hook", "objeto e promessa"),
            (12, 27, "timeline_idea", "rótulo IDEA"),
            (27, 47, "timeline_build", "rótulo BUILD"),
            (47, 69, "timeline_value", "rótulo VALUE"),
            (69, 87.79, "timeline_cta", "rótulo CTA"),
        ),
    ),
    Unit(
        "instagram-Dcq32xNgO1d",
        "Dinastias indianas em um projeto de After Effects",
        "@mep.io_",
        "https://www.instagram.com/reels/Dcq32xNgO1d/",
        "Pesquisa por acesso autenticado; imagens históricas, logos e UI exigem origem individual.",
        "instagram_reel",
        "Uma história sobre bilionários e dinastias é apresentada dentro do ambiente do projeto, convertendo o arquivo de edição em prova de craft e produto.",
        (
            (0, 14, "hook", "riqueza e dinastia"),
            (14, 38, "context", "personagens e relações"),
            (38, 61, "escalation", "cards, retratos e dados"),
            (61, 75, "craft_proof", "timeline e composição"),
            (75, 83.08, "cta", "comentário para receber projeto"),
        ),
        "Figuras históricas assumem função de personagens por retratos e relações; o editor aparece indiretamente por meio do projeto aberto.",
        "After Effects funciona como moldura e bastidor. Cards de jornal, retratos e telefone formam microcenários editoriais.",
        "Grids de retratos, cards, UI móvel e composições aninhadas. Um banner azul de CTA permanece na base.",
        "A narrativa alterna história e prova técnica. O CTA persistente compete com parte do espaço vertical, mas cria continuidade comercial.",
        "Paralaxe, máscaras, hierarquia tipográfica e aninhamento transformam arquivo em cena. A técnica deve servir à relação entre personagens.",
        "Narração sustenta causalidade; clicks, whooshes e impactos podem revelar mudança de escala da composição.",
        (
            "bastidor vira credencial",
            "retratos são organizados por relação",
            "oferta está integrada ao objeto entregue",
        ),
        (
            "banner persistente reduz área narrativa",
            "origem dos retratos precisa de ledger",
            "densidade de informação pode parecer showcase",
        ),
        "Quando o produto é o arquivo de edição, permita que o espectador veja decisões reais sem deixar a interface dominar a história.",
        "Mostrar dezenas de layers apenas como prova de complexidade, sem explicar sua função narrativa.",
        "Um revisor deve apontar a função de cada família de layer e encontrar a origem/licença de cada retrato.",
        "alta: pesquisa, motion editorial e empacotamento",
        (
            (0, 14, "portrait_hook", "personagem e escala"),
            (14, 38, "relationship_cards", "contexto"),
            (38, 61, "editorial_escalation", "dados e hierarquia"),
            (61, 75, "ae_proof", "projeto aberto"),
            (75, 83.08, "persistent_cta", "oferta"),
        ),
    ),
    Unit(
        "instagram-DaJVyavI65T",
        "Papiros de Herculano e Vesuvius Challenge",
        "@paulagusmaof_",
        "https://www.instagram.com/reels/DaJVyavI65T/",
        "Pesquisa por acesso autenticado; fontes científicas mostradas precisam ser verificadas individualmente.",
        "instagram_reel",
        "Uma explicação científica apresenta o problema físico dos papiros carbonizados, a técnica de leitura virtual, a descoberta e sua escala histórica.",
        (
            (0, 18, "hook", "livros antigos que não podem ser abertos"),
            (18, 47, "context", "Herculano, erupção e preservação"),
            (47, 82, "mechanism", "tomografia e desenrolamento virtual"),
            (82, 120, "proof", "competição, pesquisadores e leitura"),
            (120, 152.1, "implication", "1.800 rolos e memória perdida"),
        ),
        "Apresentadora mantém contato com a câmera e atua como guia. Pesquisadores e artefatos entram como sujeitos de evidência, não substitutos dela.",
        "Home office coerente serve de base; vulcão, papiros, scans e manchetes surgem como camadas de investigação.",
        "Plano médio recorrente com inserts e overlays. O retorno ao rosto reinicia contexto depois de blocos técnicos densos.",
        "A progressão é problema → mecanismo → prova → implicação. Inserts duram o suficiente para leitura, embora algumas fontes precisem de locator mais explícito.",
        "Motion simples de recorte, escala e texto estabelece relações entre objeto físico e reconstrução digital.",
        "Voz conversacional; trilha discreta; nomes próprios e números na transcrição automática precisam de revisão.",
        ("cadeia explicativa completa", "apresentadora ancora evidência", "implicação final amplia stakes"),
        (
            "locators das fontes não ficam persistentes",
            "algumas imagens científicas podem ser confundidas com mera ilustração",
            "duração exige ritmo de leitura cuidadoso",
        ),
        "Num explainer científico, represente separadamente objeto, método, evidência obtida e implicação.",
        "Usar imagens de laboratório genéricas enquanto a voz descreve uma técnica específica.",
        "Uma pessoa deve distinguir em quatro frames: o papiro, o método de leitura, o resultado e a escala da descoberta.",
        "média-alta: pesquisa factual, visual sourcing e clareza",
        (
            (0, 18, "presenter_mystery", "problema"),
            (18, 47, "history_evidence", "contexto"),
            (47, 82, "method_visualization", "mecanismo"),
            (82, 120, "research_proof", "resultado"),
            (120, 152.1, "presenter_implication", "stakes"),
        ),
    ),
    Unit(
        "instagram-DZiYEzBvZOc",
        "Your Name como ensaio sobre esquecimento",
        "@odaniels2036",
        "https://www.instagram.com/reels/DZiYEzBvZOc/",
        "Análise crítica por acesso autenticado; montagem contém obra cinematográfica protegida e não pode abastecer geração ou publicação.",
        "instagram_reel",
        "Um vídeo-ensaio reinterpreta o romance como guerra contra tempo e esquecimento, usando imagens do filme para acompanhar revelações e conclusão emocional.",
        (
            (0, 18.8, "thesis", "esquecimento como antagonista"),
            (18.8, 41.36, "reveal", "separação temporal e tragédia"),
            (41.36, 59.72, "escalation", "guerra contra universo e preço"),
            (59.72, 85.44, "climax", "nomes, memória e declaração"),
            (85.44, 115.1, "resolution", "busca, reencontro e tese"),
        ),
        "Taki e Mitsuha são tratados como objetivos, obstáculos e memória compartilhada. A narração interpreta performance já existente; não cria nova atuação.",
        "Cidade, interior, montanha e céu atravessado pelo cometa carregam tempo e distância. A análise depende totalmente do mundo da obra protegida.",
        "Montagem de cenas do anime com legendas grandes centralizadas. Cross-cuts acompanham a revelação narrada e privilegiam rostos, mãos e paisagem.",
        "A sequência emocional progride com a causalidade da obra. Alguns cortes ilustram a frase; os melhores antecipam ou completam uma ideia visualmente.",
        "Tipografia e reenquadramento vertical garantem legibilidade, mas podem cobrir composição original.",
        "Narração emotiva, música e áudio do filme constroem intensidade; a mistura corre risco de mascaramento e de dupla manipulação emocional.",
        ("tese interpretativa consistente", "escalada ligada a revelações", "motivos visuais retornam no payoff"),
        (
            "direitos impedem reutilização como asset",
            "a transcrição automática erra nomes",
            "interpretação é inferência, não intenção documentada do autor",
        ),
        "Uma montagem emocional deve acompanhar a mudança da pergunta dramática, não apenas palavras-chave da narração.",
        "Copiar cenas de uma obra protegida para obter emoção pronta ou imitar sua expressão visual.",
        "Reescreva o mapa usando apenas descrições abstratas; se a progressão sobreviver sem os frames protegidos, o princípio é transferível.",
        "alta editorial; proibitiva para reutilização direta por direitos",
        (
            (0, 18.8, "romance_setup", "tese"),
            (18.8, 41.36, "temporal_reveal", "tragédia"),
            (41.36, 59.72, "cosmic_conflict", "preço"),
            (59.72, 85.44, "hand_motif", "clímax"),
            (85.44, 115.1, "search_resolution", "reencontro"),
        ),
    ),
    Unit(
        "instagram-DbBddW3JNKD",
        "IShowSpeed: do quarto à final da Copa",
        "@simplyougrow",
        "https://www.instagram.com/reels/DbBddW3JNKD/",
        "Análise crítica por acesso autenticado; arquivo pessoal e eventos esportivos exigem direitos individuais.",
        "instagram_reel",
        "Um discurso retrospectivo organiza uma montagem de transformação: improviso doméstico, crescimento público, palco global e conselho motivacional.",
        (
            (0, 12.6, "origin", "quarto e persona inicial"),
            (12.6, 24.8, "transformation", "caos vira palco global"),
            (24.8, 34.96, "proof", "performance e gratidão"),
            (34.96, 45.64, "lesson", "persistência"),
            (45.64, 60.96, "resolution", "desafios e impulso final"),
        ),
        "O próprio sujeito fornece arco, voz e performance. A vulnerabilidade retrospectiva dá sentido às imagens de arquivo.",
        "Quarto doméstico, ruas, estádio e multidão funcionam como escala crescente do mesmo percurso.",
        "Arquivo vertical e horizontal, multidões e palco. O contraste de escala importa mais que uniformidade plástica.",
        "Montagem cronológica-emocional: imagens antigas comprovam a origem; imagens de massa pagam a transformação.",
        "Motion é mínimo; reframing e legendas servem à legibilidade. O principal efeito é o contraste documental.",
        "Fala original conduz a edição; pausas, gritos e reação de público preservam autenticidade. Música deve evitar esmagar o discurso.",
        (
            "transformação demonstrada por escala",
            "voz primária reduz explicação externa",
            "arquivo é escolhido por causalidade",
        ),
        (
            "proveniência fragmentada",
            "mensagem motivacional pode virar commodity",
            "arquivo selecionado favorece uma narrativa de sucesso",
        ),
        "Para representar transformação, contraste estados observáveis do mesmo personagem, ambiente ou capacidade.",
        "Montar carros, multidões e luxo genéricos sobre qualquer fala de persistência.",
        "Cada plano deve receber rótulo origem, obstáculo, prova ou consequência; planos sem função são removidos.",
        "média: curadoria e mix; alta exigência de direitos",
        (
            (0, 12.6, "home_archive", "origem"),
            (12.6, 24.8, "scale_jump", "transformação"),
            (24.8, 34.96, "crowd_proof", "prova"),
            (34.96, 45.64, "speech_hold", "lição"),
            (45.64, 60.96, "resolve_montage", "encerramento"),
        ),
    ),
    Unit(
        "instagram-Dbhmn9eOiXN",
        "Diagrama estático de arquitetura de IA",
        "@hackproduct",
        "https://www.instagram.com/reels/Dbhmn9eOiXN/",
        "Pesquisa por acesso autenticado; metadados e imagem permanecem referência; autoria dos elementos precisa de verificação.",
        "instagram_reel",
        "Uma árvore visual de arquitetura de IA permanece praticamente estática por 9,43 segundos, oferecendo densidade mas pouca direção temporal.",
        ((0, 1, "reveal", "diagrama aparece"), (1, 8.4, "hold", "leitura livre"), (8.4, 9.43, "exit", "encerramento")),
        "Não há personagem nem voz; o espectador precisa criar sozinho a rota de leitura.",
        "O cenário é o próprio canvas informacional. Não existe relação com espaço físico ou progressão narrativa.",
        "Diagrama central com múltiplos ramos e texto pequeno. A versão vertical comprime a informação.",
        "Quase nenhuma montagem; uma duração única não acompanha a hierarquia de leitura.",
        "Motion mínimo e sem destaque sequencial. A informação espacial não é convertida em explicação temporal.",
        "Sem fala detectada; qualquer trilha não resolve a ausência de direção semântica.",
        ("visão geral em um único quadro", "pode servir como mapa de consulta pausável"),
        (
            "texto pequeno",
            "sem rota de atenção",
            "sem contexto, prova, voz ou progressão",
            "contraexemplo de informação despejada",
        ),
        "Diagramas complexos em vídeo precisam transformar hierarquia espacial em uma sequência de foco, relação e síntese.",
        "Manter uma imagem densa parada e assumir que duração equivale a compreensão.",
        "Cinco espectadores devem reconstruir a mesma ordem de três ideias sem pausar; se não, falta direção temporal.",
        "baixa de produção; baixa eficácia explicativa",
        (
            (0, 1, "diagram_reveal", "entrada"),
            (1, 8.4, "static_hold", "leitura sem guia"),
            (8.4, 9.43, "diagram_exit", "saída"),
        ),
    ),
    Unit(
        "blender-charge-factory-invasion",
        "Charge — invasão e confronto na fábrica",
        "Blender Studio / Blender Animation Studio",
        "https://www.youtube.com/watch?v=UXqq0ZvbOnk",
        "Filme aberto do Blender Studio; confirmar licença específica do projeto antes de reutilizar assets. Análise da janela 00:40–01:52.",
        "open_film_sequence",
        "Um invasor recupera um módulo de energia numa fábrica, aciona a segurança e transforma uma ação furtiva em confronto físico.",
        (
            (0, 8.29, "setup", "entrada furtiva e objetivo visual"),
            (8.29, 21.96, "acquisition", "módulo recuperado e ameaça introduzida"),
            (21.96, 36.79, "confrontation", "robô bloqueia saída"),
            (36.79, 47.25, "escalation", "tiros, faíscas e mudança de cobertura"),
            (47.25, 62.29, "struggle", "contato físico e disputa do objetivo"),
            (62.29, 72, "turn", "vantagem muda e sequência entrega próximo beat"),
        ),
        "O homem tem objetivo legível pelo olhar e pelas mãos; o robô é definido por postura, luz e precisão mecânica. Blocking converte força relativa em geometria.",
        "Corredores industriais, prateleiras, vapor e máquinas criam rotas, oclusão e perigo. O módulo verde é prop-objetivo e âncora cromática.",
        "Luz motivada por luminárias e pelo módulo; paleta verde/cinza interrompida por alerta e faíscas. Alternância entre detalhe do objetivo, reação e espaço de ameaça.",
        "Cortes aceleram com a detecção e luta; inserts estabelecem causa antes de reação. A sequência preserva orientação por eixos e eyelines apesar da fumaça.",
        "CGI é o meio integral, mas efeitos têm função física: energia, impacto, material e visibilidade. Partículas respondem a contato e direção.",
        "Ambiência industrial estabelece volume; servo, energia, disparo e impacto diferenciam agente e ameaça. Silêncio relativo antes da detecção prepara a virada.",
        ("prop concentra objetivo", "cenário produz ação e cobertura", "cor e som mantêm causalidade"),
        (
            "threshold de pixel superdetecta flashes como cortes",
            "fumaça pode ocultar orientação",
            "atribuição exige créditos de equipe, não apenas estúdio",
        ),
        "Projete a ação como disputa por um objeto dentro de uma geometria que oferece e retira opções.",
        "Gerar combate em corredor genérico sem objetivo, zonas, eixos ou consequência material.",
        "Sem diálogo, três revisores devem identificar objetivo, ameaça, mudança de vantagem e direção de saída.",
        "muito alta: direção de ação, animação, luz, FX e som",
        (
            (0, 8.29, "stealth_entry", "aproximação"),
            (8.29, 21.96, "energy_prop", "aquisição"),
            (21.96, 36.79, "security_reveal", "bloqueio"),
            (36.79, 47.25, "firefight", "escalada"),
            (47.25, 62.29, "close_struggle", "disputa"),
            (62.29, 72, "advantage_turn", "virada"),
        ),
        source_start=40,
        source_end=112,
    ),
    Unit(
        "blender-sprite-fright-forest-reveal",
        "Sprite Fright — descoberta dos sprites na floresta",
        "Blender Studio / Blender Animation Studio",
        "https://studio.blender.org/films/sprite-fright/",
        "Filme e materiais abertos do Blender Studio; análise da janela aproximada 01:40–03:30, com créditos coletivos.",
        "open_film_sequence",
        "Campistas encontram pequenos cogumelos aparentemente dóceis; a curiosidade individual vira encontro de grupo e prepara a inversão de ameaça.",
        (
            (0, 17.96, "setup", "campistas e sinais discretos no chão"),
            (17.96, 33.04, "discovery", "uma personagem se aproxima"),
            (33.04, 54.33, "reveal", "sprites ganham presença e resposta"),
            (54.33, 72.5, "group_reaction", "grupo se reúne e interpreta"),
            (72.5, 92.71, "false_safety", "criaturas parecem engraçadas e sociáveis"),
            (92.71, 110, "foreshadow", "detalhes de blocking preparam mudança"),
        ),
        "O ensemble tem silhuetas, figurinos e atitudes distintas. A personagem curiosa inicia contato; reações em grupo distribuem informação e comicidade.",
        "A floresta tem escala em camadas: pés gigantes, vegetação, clareira e sprites minúsculos. Cogumelos e lixo humano conectam personagens ao ecossistema.",
        "Luz quente atravessa folhagem; vermelho dos chapéus chama atenção antes do rosto das criaturas. Baixos ângulos deslocam o ponto de vista para a escala dos sprites.",
        "Planos de descoberta alongam expectativa; reação individual antecede plano de grupo. Repetição de cogumelos estabelece padrão antes de variação.",
        "Animação de olhos, peso, squash e contraste de escala dá personalidade sem exposição verbal extensa.",
        "Ambiência florestal, pequenos movimentos e pausas criam delicadeza; vozes e reações do grupo alteram a leitura da criatura.",
        (
            "revelação por escala e ponto de vista",
            "ensemble reage de modos diferentes",
            "foreshadow nasce de props e blocking",
        ),
        (
            "a janela inclui setup além da revelação estrita",
            "corte detectado por pixel não distingue movimento de folhagem",
            "humor depende de timing cultural",
        ),
        "Revele criatura e mundo por uma cadeia: indício, aproximação, mudança de escala, reação e nova regra.",
        "Mostrar imediatamente o monstro em plano explicativo, sem permitir que espaço, som e personagem façam a descoberta.",
        "Sem narração, espectadores devem ordenar indício, descoberta, falsa segurança e presságio usando somente quadro e som.",
        "muito alta: ensemble, animação, production design e som",
        (
            (0, 17.96, "camp_setup", "sinais"),
            (17.96, 33.04, "ground_discovery", "aproximação"),
            (33.04, 54.33, "sprite_reveal", "mudança de escala"),
            (54.33, 72.5, "ensemble_reaction", "interpretação"),
            (72.5, 92.71, "comic_exchange", "falsa segurança"),
            (92.71, 110, "forest_foreshadow", "presságio"),
        ),
        source_start=100,
        source_end=210,
    ),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ffprobe_duration(path: Path) -> float:
    process = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True,
        check=True,
        text=True,
    )
    return float(json.loads(process.stdout)["format"]["duration"])


def detect_scene_boundaries(path: Path, threshold: float = 0.18) -> list[float]:
    process = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(path),
            "-filter:v",
            f"select='gt(scene,{threshold})',metadata=print:file=-",
            "-an",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    boundaries: list[float] = []
    for line in process.stdout.splitlines():
        if "lavfi.scene_score" in line:
            continue
        if "pts_time:" in line:
            try:
                boundaries.append(float(line.split("pts_time:", 1)[1].split()[0]))
            except ValueError:
                pass
    if not boundaries:
        # Some FFmpeg builds write metadata to stderr in showinfo form.
        for line in process.stderr.splitlines():
            if "pts_time:" not in line:
                continue
            try:
                boundaries.append(float(line.split("pts_time:", 1)[1].split()[0]))
            except ValueError:
                pass
    return sorted({round(item, 3) for item in boundaries if item > 0})


def find_phase(unit: Unit, midpoint: float) -> tuple[str, str]:
    for start, end, label, description in unit.visual_phases:
        if start <= midpoint < end or (midpoint == end and end == unit.visual_phases[-1][1]):
            return label, description
    return "unclassified", "human review required"


def source_paths(unit: Unit, input_root: Path) -> tuple[Path, Path | None, dict[str, Any]]:
    if unit.source_kind == "instagram_reel":
        code = unit.unit_id.removeprefix("instagram-")
        folder = input_root / code
        video = folder / "video.mp4"
        transcript_path = folder / "transcript.json"
        metadata_path = folder / "metadata.json"
        return video, transcript_path, json.loads(metadata_path.read_text(encoding="utf-8"))
    filename = "charge-sequence.mp4" if "charge" in unit.unit_id else "sprite-sequence.mp4"
    return input_root / "cinema" / filename, None, {}


def timeline(
    unit: Unit, duration: float, transcript_path: Path | None, boundaries: list[float]
) -> list[dict[str, Any]]:
    if transcript_path:
        transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
        segments = transcript.get("segments") or []
        if segments:
            result: list[dict[str, Any]] = []
            cursor = 0.0
            for segment in segments:
                raw_start = float(segment["start"])
                start = max(cursor, raw_start)
                end = min(duration, float(segment["end"]))
                if end <= start:
                    continue
                if start > cursor:
                    gap_label, gap_description = find_phase(unit, (cursor + start) / 2)
                    result.append(
                        {
                            "shot_id": f"{unit.unit_id}-u{len(result) + 1:03d}",
                            "start_ms": round(cursor * 1000),
                            "end_ms": round(start * 1000),
                            "duration_ms": round((start - cursor) * 1000),
                            "boundary_type": "non_speech_coverage",
                            "beat": gap_label,
                            "visual_function": gap_description,
                            "observation_confidence": 0.50,
                            "entry_reason": "previous machine speech segment ended",
                            "exit_reason": "next machine speech segment begins",
                            "human_review_required": True,
                        }
                    )
                label, description = find_phase(unit, (start + end) / 2)
                result.append(
                    {
                        "shot_id": f"{unit.unit_id}-u{len(result) + 1:03d}",
                        "start_ms": round(start * 1000),
                        "end_ms": round(end * 1000),
                        "duration_ms": round((end - start) * 1000),
                        "boundary_type": "speech_aligned_editorial_unit",
                        "beat": label,
                        "visual_function": description,
                        "dialogue_machine_unverified": segment["text"].strip(),
                        "observation_confidence": 0.72,
                        "entry_reason": "speech segment or semantic phase boundary",
                        "exit_reason": "next speech segment or semantic phase boundary",
                        "human_review_required": True,
                    }
                )
                cursor = end
            if cursor < duration:
                label, description = find_phase(unit, (cursor + duration) / 2)
                result.append(
                    {
                        "shot_id": f"{unit.unit_id}-u{len(result) + 1:03d}",
                        "start_ms": round(cursor * 1000),
                        "end_ms": round(duration * 1000),
                        "duration_ms": round((duration - cursor) * 1000),
                        "boundary_type": "coverage_tail",
                        "beat": label,
                        "visual_function": description,
                        "observation_confidence": 0.55,
                        "entry_reason": "machine transcript ended",
                        "exit_reason": "source ended",
                        "human_review_required": True,
                    }
                )
            return result

    points = [0.0, *[item for item in boundaries if item < duration], duration]
    result = []
    for index, (start, end) in enumerate(zip(points, points[1:], strict=False)):
        label, description = find_phase(unit, (start + end) / 2)
        result.append(
            {
                "shot_id": f"{unit.unit_id}-s{index + 1:03d}",
                "start_ms": round(start * 1000),
                "end_ms": round(end * 1000),
                "duration_ms": round((end - start) * 1000),
                "boundary_type": "pixel_change_candidate",
                "beat": label,
                "visual_function": description,
                "observation_confidence": 0.68,
                "entry_reason": "automated scene-change candidate",
                "exit_reason": "next scene-change candidate",
                "human_review_required": True,
            }
        )
    return result


def markdown(unit: Unit, duration: float, digest: str, metadata: dict[str, Any], cut_count: int) -> str:
    structure = "\n".join(
        f"| {start:0.2f}–{end:0.2f}s | `{role}` | {purpose} |" for start, end, role, purpose in unit.structure
    )
    strengths = "\n".join(f"- {item}" for item in unit.strengths)
    limitations = "\n".join(f"- {item}" for item in unit.limitations)
    platform_note = ""
    if metadata:
        platform_note = (
            f"- Metadados capturados: `{metadata.get('capturedAt', 'unknown')}`. "
            "Contagens e legenda são contexto instável, não evidência causal.\n"
        )
    return f"""# {unit.title}

**Unidade:** `{unit.unit_id}`  
**Status:** análise de máquina concluída; revisão humana pendente  
**Fonte:** [{unit.creator}]({unit.source_url})  
**Duração analisada:** {duration:0.3f}s  
**SHA-256 temporário:** `{digest}`  
**Direitos:** {unit.rights}

## Proveniência e limites

- A fonte foi acessada para pesquisa em 2026-09-01 e permaneceu fora do repositório.
{platform_note}- O checksum identifica a cópia temporária usada nesta análise; o ledger registra sua exclusão.
- Transcrição, detecção de mudança visual e segmentação são assistência de máquina e exigem conferência.
- Observação descreve o que aparece/soa; intenção e causalidade são inferências explicitamente marcadas.
- O mapa registrou {cut_count} candidatos de mudança visual por diferença de pixels. Flashes, motion e movimento de câmera podem gerar falsos positivos.

## Mensagem e estrutura

{unit.summary}

| Janela | Função | Progressão |
|---|---|---|
{structure}

## Personagem, atuação e voz

{unit.character}

## Cenário, objetos e mundo

{unit.world}

## Fotografia e composição

{unit.image}

## Montagem e retenção

{unit.edit}

## Texto, motion, CGI e VFX

{unit.motion}

## Música, ambiência e relação som-imagem

{unit.sound}

## O que funciona

{strengths}

## Falhas, limites e dificuldade

{limitations}

**Dificuldade estimada:** {unit.difficulty}.

## Destilação transferível

**Princípio:** {unit.principle}

**Contraexemplo:** {unit.counterexample}

**Teste de aceitação:** {unit.acceptance_test}

## Classificação epistêmica

| Afirmação | Classe | Confiança |
|---|---|---:|
| Duração, ordem temporal e elementos visíveis/sonoros descritos | observação assistida por máquina | 0,72 |
| Direitos e autoria declarados na fonte | declaração documentada, pendente de revisão jurídica quando indicado | 0,80 |
| Função dramática, intenção de corte e efeito de retenção | inferência analítica | 0,60 |
| Desempenho ou viralidade causado por uma técnica | não estabelecido | 0,10 |

## Revisão humana obrigatória

- [ ] Conferir cada boundary contra o vídeo.
- [ ] Corrigir a transcrição e nomes próprios.
- [ ] Validar créditos e direitos de todos os inserts.
- [ ] Confirmar ou rejeitar cada inferência de intenção.
- [ ] Registrar decisão e identidade do revisor no pacote R1.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize the evidence-backed R1 reference pilot.")
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    generated_at = datetime.now(UTC).isoformat()
    for unit in UNITS:
        video_path, transcript_path, metadata = source_paths(unit, args.input_root)
        if not video_path.exists():
            raise FileNotFoundError(video_path)
        duration = ffprobe_duration(video_path)
        boundaries = detect_scene_boundaries(video_path)
        shots = timeline(unit, duration, transcript_path, boundaries)
        unit_dir = args.output_root / "corpus" / unit.unit_id
        unit_dir.mkdir(parents=True, exist_ok=True)
        shot_document = {
            "schema_version": "studio.reference-shot-map.v1",
            "unit_id": unit.unit_id,
            "source_url": unit.source_url,
            "source_kind": unit.source_kind,
            "source_window_seconds": {"start": unit.source_start, "end": unit.source_end},
            "duration_ms": round(duration * 1000),
            "source_checksum_sha256": sha256(video_path),
            "boundary_model": {
                "method": "ffmpeg scene score plus speech-aligned editorial units",
                "threshold": 0.18,
                "pixel_change_candidates_ms": [round(item * 1000) for item in boundaries],
                "warning": "Candidates are not asserted as editorial cuts until human review.",
            },
            "shots": shots,
            "coverage": {
                "starts_at_zero": bool(shots and shots[0]["start_ms"] == 0),
                "ends_at_duration": bool(shots and shots[-1]["end_ms"] == round(duration * 1000)),
                "overlap_count": 0,
                "gap_count": 0,
            },
            "generated_at": generated_at,
            "human_review_status": "pending",
        }
        (unit_dir / "shots.json").write_text(
            json.dumps(shot_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (unit_dir / "analysis.md").write_text(
            markdown(unit, duration, sha256(video_path), metadata, len(boundaries)), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
