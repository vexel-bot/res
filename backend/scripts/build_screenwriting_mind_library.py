# ruff: noqa: E501 -- curated names and source URLs are evidence data, not executable logic.
from __future__ import annotations

import argparse
import json
from pathlib import Path

MINDS = (
    (
        "jk-rowling-harry-potter",
        "J. K. Rowling e equipe Harry Potter",
        "worldbuilding, mistério e payoff de longo prazo",
        ["Steve Kloves", "Stuart Craig", "David Heyman", "Chris Columbus", "Alfonso Cuarón", "David Yates"],
        ["Harry Potter novels", "Harry Potter film adaptations"],
        ["https://www.jkrowling.com/", "https://www.wgfoundation.org/screenplay-primers"],
    ),
    (
        "duffer-brothers",
        "Duffer Brothers",
        "ensemble, serialização, suspense e contraste tonal",
        [
            "Shawn Levy",
            "Iain Paterson",
            "The writers' room",
            "Tim Ives",
            "Dean Zimmerman",
            "Kyle Dixon",
            "Michael Stein",
        ],
        ["Stranger Things"],
        ["https://www.netflix.com/tudum/stranger-things", "https://www.wgfoundation.org/contentlibrary"],
    ),
    (
        "vince-gilligan-peter-gould",
        "Vince Gilligan e Peter Gould",
        "causalidade, transformação e payoff acumulado",
        [
            "Thomas Schnauz",
            "Gennifer Hutchison",
            "Michelle MacLaren",
            "Michael Slovis",
            "Skip Macdonald",
            "Dave Porter",
        ],
        ["Breaking Bad", "Better Call Saul"],
        ["https://www.televisionacademy.com/shows/breaking-bad", "https://www.wgfoundation.org/contentlibrary"],
    ),
    (
        "phoebe-waller-bridge",
        "Phoebe Waller-Bridge",
        "voz, subtexto, comédia e quebra de quarta parede",
        ["Vicky Jones", "Harry Bradbeer", "Tony Grech-Smith", "Isobel Waller-Bridge"],
        ["Fleabag", "Killing Eve"],
        ["https://www.bafta.org/people/phoebe-waller-bridge", "https://www.wgfoundation.org/screenplay-primers"],
    ),
    (
        "aaron-sorkin",
        "Aaron Sorkin",
        "objetivo, conflito verbal e ritmo",
        ["Thomas Schlamme", "David Fincher", "Alan Poul", "The writers' rooms"],
        ["The West Wing", "The Social Network", "Steve Jobs"],
        [
            "https://www.wgfoundation.org/contentlibrary",
            "https://www.bafta.org/programmes/screenwriters-lecture-series",
        ],
    ),
    (
        "charlie-kaufman",
        "Charlie Kaufman",
        "interioridade, estrutura e metanarrativa",
        ["Spike Jonze", "Michel Gondry", "Duke Johnson", "Robert Frazen"],
        ["Being John Malkovich", "Adaptation", "Synecdoche New York"],
        [
            "https://www.bafta.org/programmes/screenwriters-lecture-series",
            "https://www.wgfoundation.org/screenplay-primers",
        ],
    ),
    (
        "tony-gilroy",
        "Tony Gilroy",
        "thriller, sistemas, política e tensão procedural",
        ["Dan Gilroy", "John Gilroy", "Beau Willimon", "Stephen Schiff", "Diego Luna"],
        ["Michael Clayton", "Bourne series", "Andor"],
        ["https://www.wgfoundation.org/contentlibrary", "https://www.televisionacademy.com/shows/andor"],
    ),
    (
        "jordan-peele",
        "Jordan Peele",
        "metáfora, horror social e setup/payoff",
        ["Monkeypaw Productions", "Ian Cooper", "Hoyte van Hoytema", "Nicholas Monsour", "Michael Abels"],
        ["Get Out", "Us", "Nope"],
        ["https://www.wgfoundation.org/screenplay-primers", "https://www.dga.org/Craft/VisualHistory"],
    ),
    (
        "greta-gerwig",
        "Greta Gerwig",
        "personagem, relações, ponto de vista e adaptação",
        ["Noah Baumbach", "Sam Levy", "Nick Houy", "Sarah Greenwood", "Alexandre Desplat"],
        ["Lady Bird", "Little Women", "Barbie"],
        ["https://www.bafta.org/programmes/screenwriters-lecture-series", "https://www.dga.org/Craft/VisualHistory"],
    ),
    (
        "hayao-miyazaki",
        "Hayao Miyazaki",
        "mundo, ação, silêncio, natureza e ambiguidade moral",
        ["Toshio Suzuki", "Joe Hisaishi", "Studio Ghibli animation departments"],
        ["My Neighbor Totoro", "Princess Mononoke", "Spirited Away"],
        ["https://www.ghibli.jp/", "https://www.oscars.org/collection-highlights/hayao-miyazaki"],
    ),
    (
        "billy-wilder-ia-diamond",
        "Billy Wilder e I. A. L. Diamond",
        "premissa, ironia, construção cômica e reescrita",
        ["Charles Brackett", "I. A. L. Diamond", "Doane Harrison", "Alexandre Trauner"],
        ["Some Like It Hot", "The Apartment", "Sunset Boulevard"],
        [
            "https://www.wgfoundation.org/archive",
            "https://www.oscars.org/film-archive/collections/writers-guild-foundation-collection",
        ],
    ),
    (
        "akira-kurosawa-shinobu-hashimoto",
        "Akira Kurosawa e Shinobu Hashimoto",
        "estrutura multiperspectiva, conflito e escrita colaborativa",
        ["Hideo Oguni", "Ryuzo Kikushima", "Takashi Shimura", "Toshiro Mifune"],
        ["Rashomon", "Seven Samurai", "Ikiru"],
        [
            "https://www.criterion.com/current/posts/5737-mightier-than-the-sword-shinobu-hashimoto-at-100",
            "https://www.dga.org/Craft/VisualHistory",
        ],
    ),
    (
        "nora-ephron",
        "Nora Ephron",
        "voz, observação, romance e construção cômica",
        ["Delia Ephron", "Rob Reiner", "Julie Kavner", "Richard Marks"],
        ["When Harry Met Sally", "Sleepless in Seattle", "Julie & Julia"],
        ["https://www.wgfoundation.org/archive", "https://www.wgfoundation.org/blog/2025/7/30/thelibraryproject"],
    ),
    (
        "paddy-chayefsky",
        "Paddy Chayefsky",
        "argumento dramático, instituições e conflito verbal",
        ["Sidney Lumet", "Howard Gottfried", "Owen Roizman", "Alan Heim"],
        ["Marty", "The Hospital", "Network"],
        ["https://www.wgfoundation.org/archive", "https://www.oscars.org/library"],
    ),
    (
        "william-goldman",
        "William Goldman",
        "clareza, estrutura, adaptação e leitura de audiência",
        ["George Roy Hill", "Richard Lester", "Rob Reiner", "David V. Picker"],
        ["Butch Cassidy and the Sundance Kid", "All the President's Men", "The Princess Bride"],
        ["https://www.wgfoundation.org/contentlibrary", "https://www.oscars.org/library"],
    ),
    (
        "paul-schrader",
        "Paul Schrader",
        "personagem solitário, contradição moral e tensão transcendental",
        ["Martin Scorsese", "Brian De Palma", "Michael Chapman", "Thelma Schoonmaker"],
        ["Taxi Driver", "Raging Bull", "First Reformed"],
        [
            "https://www.bafta.org/media-centre/press-releases/bafta-screenwriters-lecture-series-paul-schrader/",
            "https://www.dga.org/Craft/VisualHistory",
        ],
    ),
    (
        "spike-lee",
        "Spike Lee",
        "ponto de vista, política, energia formal e confronto",
        ["Ernest Dickerson", "Barry Alexander Brown", "Terence Blanchard", "Ruth E. Carter"],
        ["Do the Right Thing", "Malcolm X", "BlacKkKlansman"],
        [
            "https://www.dga.org/craft/dgaq/issues/0801-spring-2008/dga-interview-spike-lee",
            "https://www.dga.org/news/guild-news/2020/december2020/cod_spikelee_pb",
        ],
    ),
    (
        "bong-joon-ho-han-jin-won",
        "Bong Joon-ho e Han Jin-won",
        "geografia, classe, viradas tonais e causalidade espacial",
        ["Han Jin-won", "Hong Kyung-pyo", "Yang Jin-mo", "Lee Ha-jun", "Jung Jae-il"],
        ["Memories of Murder", "Snowpiercer", "Parasite"],
        ["https://www.bafta.org/programmes/screenwriters-lecture-series", "https://www.dga.org/Craft/VisualHistory"],
    ),
    (
        "celine-sciamma",
        "Céline Sciamma",
        "desejo, olhar, gesto e economia dramática",
        ["Claire Mathon", "Julien Lacheray", "Bénédicte Couvreur", "Jean-Baptiste de Laubier"],
        ["Tomboy", "Portrait of a Lady on Fire", "Petite Maman"],
        [
            "https://www.bafta.org/media-centre/press-releases/screenwriters-lecture-series-2019-celine-sciamma/",
            "https://www.dga.org/Craft/VisualHistory",
        ],
    ),
    (
        "park-chan-wook-jeong-seo-kyeong",
        "Park Chan-wook e Jeong Seo-kyeong",
        "ponto de vista, desejo, reviravolta e composição",
        ["Jeong Seo-kyeong", "Chung Chung-hoon", "Kim Sang-bum", "Ryu Seong-hie", "Jo Yeong-wook"],
        ["Lady Vengeance", "The Handmaiden", "Decision to Leave"],
        [
            "https://static.bafta.org/uploads_pre_202411/transcripts/sls_-_park_chan-wook.pdf",
            "https://www.dga.org/Craft/VisualHistory",
        ],
    ),
    (
        "guillermo-del-toro",
        "Guillermo del Toro",
        "monstro, mito, objeto e mundo material",
        ["Guillermo Navarro", "Eugenio Caballero", "Bernat Vilaplana", "Alexandre Desplat"],
        ["Pan's Labyrinth", "The Shape of Water", "Pinocchio"],
        [
            "https://www.dga.org/craft/dgaq/issues/1401-winter-2014/dga-interview-del-toro",
            "https://www.dga.org/craft/dgaq/issues/0701-spring-2007/director-profile-guillermo-del-toro",
        ],
    ),
    (
        "alfonso-cuaron",
        "Alfonso Cuarón",
        "ponto de vista, duração, espaço e colaboração técnica",
        ["Carlos Cuarón", "Emmanuel Lubezki", "Mark Sanger", "Jonás Cuarón", "Andy Nicholson"],
        ["Y Tu Mamá También", "Children of Men", "Gravity", "Roma"],
        [
            "https://www.dga.org/craft/dgaq/issues/1303-summer-2013/alfonso-cuaron",
            "https://static.bafta.org/uploads_pre_202411/transcripts/bafta_screenwriterslecture_alfonsocuaron_1.pdf",
        ],
    ),
    (
        "asghar-farhadi",
        "Asghar Farhadi",
        "informação assimétrica, dilema moral e causalidade cotidiana",
        ["Mahmoud Kalari", "Hayedeh Safiyari", "Keyvan Moghaddam", "ensemble casts"],
        ["About Elly", "A Separation", "The Salesman"],
        ["https://www.dga.org/Craft/VisualHistory", "https://www.bafta.org/programmes/screenwriters-lecture-series"],
    ),
    (
        "alice-birch",
        "Alice Birch",
        "estrutura fragmentada, voz e adaptação",
        ["William Oldroyd", "Lenny Abrahamson", "Sebastian Leio", "writers' rooms"],
        ["Lady Macbeth", "Succession", "Normal People", "Dead Ringers"],
        [
            "https://www.bafta.org/media-centre/press-releases/screenwriters-lecture-series-2024-alice-birch/",
            "https://www.wgfoundation.org/screenplay-primers",
        ],
    ),
    (
        "mike-leigh",
        "Mike Leigh",
        "personagem, improvisação, pesquisa e construção por ensaio",
        ["Dick Pope", "Jon Gregory", "Eve Stewart", "Simon Channing Williams", "ensemble casts"],
        ["Secrets & Lies", "Vera Drake", "Mr. Turner"],
        [
            "https://www.bafta.org/media-centre/press-releases/screenwriters-lecture-series-2024-mike-leigh/",
            "https://www.bafta.org/stories/mike-leigh-screenwriters-lecture/",
        ],
    ),
    (
        "shonda-rhimes",
        "Shonda Rhimes",
        "engine de episódio, ensemble, urgência e showrunning",
        ["Betsy Beers", "Krista Vernoff", "Joan Rater", "Tony Phelan", "writers' rooms"],
        ["Grey's Anatomy", "Scandal", "Private Practice"],
        [
            "https://www.televisionacademy.com/video/series-showrunners-0",
            "https://www.televisionacademy.com/bios/shonda-rhimes",
        ],
    ),
    (
        "david-simon-ed-burns",
        "David Simon e Ed Burns",
        "sistemas, instituições, reportagem e romance televisivo",
        ["George Pelecanos", "Richard Price", "Dennis Lehane", "Nina Noble", "Clark Johnson", "Joe Chappelle"],
        ["The Corner", "The Wire", "Generation Kill"],
        [
            "https://freshairarchive.org/segments/ed-burns-creating-wire",
            "https://www.movingimagesource.us/files/dialogues/3/50252_programs_transcript_pdf_309.pdf",
        ],
    ),
    (
        "john-august-craig-mazin",
        "John August e Craig Mazin",
        "craft explícito, arquitetura de cena e crítica de páginas",
        ["Scriptnotes guests", "Three Page Challenge writers", "production collaborators per work"],
        ["Scriptnotes", "Big Fish", "Chernobyl"],
        ["https://johnaugust.com/2022/scriptnotes-episode-532-mistakes-of-yes", "https://johnaugust.com/threepage"],
    ),
    (
        "michael-arndt",
        "Michael Arndt",
        "começos, clímax e convergência de stakes",
        ["Pixar story teams", "Jonathan Dayton", "Valerie Faris", "Lee Unkrich"],
        ["Little Miss Sunshine", "Toy Story 3", "Endings"],
        ["https://www.pandemoniuminc.com/endings-video", "https://www.wgaeast.org/onwriting/michael-arndt-endings/"],
    ),
    (
        "armando-iannucci-jesse-armstrong",
        "Armando Iannucci e Jesse Armstrong",
        "satira institucional, status, ensemble e escalada verbal",
        ["Simon Blackwell", "Tony Roche", "Georgia Pritchett", "Lucy Prebble", "writers' rooms"],
        ["The Thick of It", "Veep", "Succession"],
        [
            "https://www.bafta.org/stories/armando-iannucci-annual-television-lecture-in-2012/",
            "https://www.bafta.org/media-centre/press-releases/bafta-tv-sessions-2022-screenwriting/",
        ],
    ),
)


def profile(slug: str, name: str, focus: str, collaborators: list[str], works: list[str]) -> str:
    return f"""# {name} — modelo de método criativo

**Status de pesquisa:** `seed_evidence_only`; não aprovado como mente operacional.  
**Lente principal:** {focus}.  
**Regra de identidade:** este artefato não imita voz, personalidade ou opinião privada.

## Escopo profissional

O modelo será derivado de obras, créditos, entrevistas e materiais públicos. A unidade correta de autoria é o ecossistema: roteiro, direção, fotografia, montagem, design, atuação, música, VFX e som serão atribuídos separadamente.

## Obras-âncora iniciais

{chr(10).join(f"- {work}" for work in works)}

## Colaboradores a verificar por obra

{chr(10).join(f"- {person}" for person in collaborators)}

## Hipóteses de trabalho — inferências, não declarações

- A lente de `{focus}` será testada contra dez unidades, incluindo obra contrastante e limitação.
- Uma recorrência só vira heurística depois de aparecer em múltiplas obras e receber fonte ou análise temporal.
- A contribuição de um colaborador não será atribuída ao nome-âncora.

## Limitações atuais

- A filmografia/bibliografia de dez unidades ainda não passou pelo gate R1.
- Fontes listadas são pontos de partida, não corpus concluído.
- Fracassos, contradições e contraindicações exigem pesquisa específica.
- Nenhuma recomendação deste perfil pode liberar geração ou publicação.

## Teste inédito futuro

Aplicar as heurísticas a um brief original, registrar previsões antes do storyboard e comparar a crítica com dois revisores humanos sem revelar qual lente foi usada.
"""


def heuristics(name: str, focus: str) -> str:
    return f"""schema_version: studio.creative-mind-heuristics.v1
mind: {json.dumps(name, ensure_ascii=False)}
research_status: seed_evidence_only
heuristics:
  - id: diagnose-before-style
    when: "a proposta pede uma solução visual ou narrativa"
    ask: "qual mudança de crença, relação ou estado precisa ocorrer?"
    do: "escolher uma operação de {focus} que torne a mudança observável"
    avoid: "imitar marcas superficiais de uma obra conhecida"
    evidence_status: inference_pending_corpus
  - id: collaborator-attribution
    when: "uma decisão envolve câmera, edição, design, música, VFX ou performance"
    ask: "quem recebeu crédito e que fonte liga a decisão a essa pessoa?"
    do: "registrar a aresta no grafo e reduzir confiança se a fonte faltar"
    avoid: "atribuir todo o craft ao nome-âncora"
    evidence_status: methodological_rule
  - id: counterexample
    when: "uma recorrência parece universal"
    ask: "em que obra, gênero, escala ou audiência ela falha?"
    do: "preservar contraindicação e alternativa"
    avoid: "transformar gosto em regra"
    evidence_status: methodological_rule
"""


def rubric(name: str) -> str:
    return f"""schema_version: studio.creative-mind-rubric.v1
mind: {json.dumps(name, ensure_ascii=False)}
research_status: seed_evidence_only
dimensions:
  causal_clarity: {{weight: 0.18, question: "cada beat muda algo verificável?"}}
  character_specificity: {{weight: 0.14, question: "objetivo, obstáculo e comportamento são específicos?"}}
  world_function: {{weight: 0.14, question: "o cenário participa da ação ou do tema?"}}
  progression_payoff: {{weight: 0.18, question: "expectativas abertas recebem desenvolvimento e payoff?"}}
  audiovisual_expression: {{weight: 0.14, question: "imagem e som fazem trabalho além de ilustrar a fala?"}}
  originality_context: {{weight: 0.10, question: "a solução nasce do brief, sem imitação protegida?"}}
  feasibility_rights: {{weight: 0.12, question: "produção, créditos e direitos são defensáveis?"}}
hard_failures:
  - unsupported_attribution
  - unmarked_inference
  - missing_rights_or_consent
  - style_imitation_as_method
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    for slug, name, focus, collaborators, works, urls in MINDS:
        root = args.output_root / slug
        cases = root / "cases"
        cases.mkdir(parents=True, exist_ok=True)
        (root / "profile.md").write_text(profile(slug, name, focus, collaborators, works), encoding="utf-8")
        (root / "sources.json").write_text(
            json.dumps(
                {
                    "schema_version": "studio.creative-mind-sources.v1",
                    "mind": name,
                    "research_status": "seed_evidence_only",
                    "sources": [
                        {"url": url, "tier": "institutional_or_primary_starting_point", "reviewed": False}
                        for url in urls
                    ],
                    "global_methods": [
                        "https://www.wgfoundation.org/screenplay-primers",
                        "https://www.bafta.org/programmes/screenwriters-lecture-series",
                        "https://www.dga.org/Craft/VisualHistory",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / "heuristics.yaml").write_text(heuristics(name, focus), encoding="utf-8")
        (root / "critique-rubric.yaml").write_text(rubric(name), encoding="utf-8")
        (root / "collaborators.json").write_text(
            json.dumps(
                {
                    "schema_version": "studio.collaboration-graph.v1",
                    "anchor": name,
                    "status": "credits_pending_per_work_verification",
                    "nodes": [{"name": person, "role": "verify_per_work"} for person in collaborators],
                    "edges": [],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (cases / "README.md").write_text(
            f"# Casos — {name}\n\nStatus: `blocked_by_r1_human_approval`. Dez análises, falhas e teste inédito serão adicionados somente após a aprovação do piloto.\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
