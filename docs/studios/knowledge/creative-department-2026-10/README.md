# Departamento criativo — pesquisa de conteúdo e anúncios

Rodada iniciada em 14/10/2026. Conteúdo é a prioridade; anúncios constituem a segunda frente. Este diretório contém conhecimento e requisitos de experiência, não a implementação do departamento em produção.

## Decisões do usuário

- Studios possuem direção e produção próprias, operadas por agentes especializados.
- O cliente define o objetivo, escolhe a direção editorial e revisa a entrega.
- Pesquisa, roteiro, produção, edição e qualidade acontecem nos bastidores.
- KLIC encaminha contexto; os Studios são responsáveis pela criação.
- Higgsfield permanece a referência principal de experiência. Runway e Adobe GenStudio complementam a pesquisa.
- Fontes integrais PhotoCraft, FilmCraft e EffectCraft permanecem preservadas.

Esta direção substitui a exposição de edição e controle técnico ao cliente proposta em `../../STUDIOS_CREATIVE_LAB_DIRECTION_2026-10-14.md`. O caráter laboratorial representa a disciplina interna do departamento, não a obrigação de o cliente operar uma bancada técnica.

## Entregas da rodada

1. `candidates.json`: inventário de descoberta, com pelo menos 30 candidatos por autor principal. Descoberta não significa análise concluída.
2. `cases.json` e `cases/`: 36 fichas selecionadas; 6 YouTube + 6 Instagram por autor principal e 2 fontes por referência complementar.
3. `frameworks.json` e `FRAMEWORKS.md`: princípios, fontes, versões, requisitos e contraexemplos.
4. `SYNTHESIS.md`: convergências, divergências, limites e diferenças entre conteúdo, anúncio, educação e autoridade.
5. `AGENT_APPLICATION.md`: responsabilidades dos agentes e aplicação dos conhecimentos ao processo interno.
6. `EXPERIENCE_REQUIREMENTS.md`: pedido, direção e revisão da entrega, sem expor edição ou controle de qualidade.
7. `EXERCISES.md`: nove aplicações a contextos fictícios explicitamente definidos.
8. `SOFTWARE_REFERENCES.md`: comparação de entrada, possibilidades, continuidade e avaliação.
9. `coverage.json`: contagens reais e lacunas, geradas pelo validador.

## Estado verificado da entrega

92 candidatos descobertos, 36 fichas selecionadas, 16 fichas de frameworks/princípios e nove exercícios fictícios. O conjunto tem 12 análises documentais complementares e 24 fichas de YouTube/Instagram com cobertura de texto e de amostras visuais declarada. Essas 24 fichas não são análises audiovisuais integrais concluídas.

O validador passou a integridade documental. Permanecem 20 unidades que exigem revisão audiovisual integral e três carrosséis com cobertura visual incompleta. A imagem estática AS-IG-01 foi observada. Revisão humana e teste de compreensão com clientes não foram atestados. A rodada não libera automaticamente o protótipo.

- [Síntese comparativa](SYNTHESIS.md)
- [Frameworks e versões](FRAMEWORKS.md)
- [Nove exercícios](EXERCISES.md)
- [Requisitos de experiência](EXPERIENCE_REQUIREMENTS.md)
- [Aplicação pelos agentes](AGENT_APPLICATION.md)
- [Referências de software](SOFTWARE_REFERENCES.md)
- [Cobertura, afirmações críticas e lacunas](REVIEW_AND_GAPS.md)
- [Relatório de integridade](coverage.json)
- [Índice das 36 fichas](CASE_INDEX.md)

## Como interpretar a evidência

`teaching`: ensino documentado do autor; `observation`: observação direta da obra; `interpretation`: análise do pesquisador; `clicko_hypothesis`: proposta transferível que ainda precisa ser testada.

Cada ficha declara cobertura textual, visual e sonora separadamente. Ler legendas não equivale a ouvir áudio; amostrar quadros não equivale a assistir integralmente. Datas de acesso e publicação permanecem distintas. Métricas públicas descrevem a captura, não comprovam causalidade.

Não persistir mídias de terceiros, capturas extensas ou transcrições integrais neste acervo. As transcrições temporárias usadas na pesquisa não integram o produto. Arquivos temporários preexistentes do usuário são preservados.

## Verificação

Executar `python scripts/studios/validate_creative_research.py`. O relatório distingue integridade documental, cobertura das modalidades e liberação para prototipação. A integridade dos registros não comprova desempenho comercial nem qualifica automaticamente a análise audiovisual completa.
