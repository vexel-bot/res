# Curvas e limites de movimento — recibo de implementação

O res deixou de aprovar limites de velocidade por médias entre keyframes. O deslocamento original de 100 px em 1 s com ease-in agora mede pico 200 px/s e aceleração 200 px/s²; limiar 150 reprova. Antes, o checker retornava 100 px/s e aceleração indefinida. A contraprova inicial foi preservada em `contract-study.initial.json`; `contract-study.json` executa a implementação atual.

`motion_derivatives.py` calcula os limites quadráticos analíticos e os extremos das derivadas cúbicas em tempo, usando dy/dx e a segunda derivada. Busca raízes polinomiais por partições da derivada e bisseção; não depende de amostrar apenas frames inteiros. A constraint respeita seu intervalo half-open; repouso fora das chaves e descontinuidade de velocidade entram quando a junção fica no interior do intervalo. Uma track não verificável impede aprovação agregada. Holds com salto, mudanças instantâneas de velocidade e Béziers não identidade com tempo singular retornam diagnóstico `incomplete`, conservadoramente, sem infinito no JSON. Mesmo uma singularidade removível ainda pode exigir análise adicional.

O renderer conserva sua interpolação atual. Os limites descrevem a curva contínua pretendida; não são as derivadas infinitesimais dos degraus numéricos da inversão de 18 iterações do runtime. As 31 verificações existentes, com 6.010 amostras da função real do renderer, continuam passando. Nenhuma nova aprovação estética foi inferida desse resultado.

Grafos e schemas V1 continuam legíveis e com os mesmos campos. Uma avaliação salva com as razões antigas de velocidade/aceleração não autoriza projeção reviewed de uma constraint bloqueante. O fluxo de review existente recalcula constraints e exige revisão esperada; pode rejeitar um limite anteriormente aprovado. [Compatibilidade registrada antes da alteração](MOTION_DERIVATIVE_COMPATIBILITY.md).

Evidências finais:

- `motion-derivative-regression-tests.xml`: **66 aprovados**, zero falhas/skips, duas fixtures `real_mp4` explicitamente não selecionadas. Abrange curvas/grafo/API, editorial motion V2, receitas nativas e comandos. A suíte de receitas também conserva seu teste técnico de pixels; não é uma nova rodada dos MP4s de comandos.
- `motion-derivative-final-tests.xml`: **22 aprovados**, subconjunto acima. Inclui oráculos de Bernstein independentes em 20.001 pontos por curva, pico cúbico estreito, recorte, fps racional, hold, joins, singularidades, track mista e proteção contra recibo legado. API real rejeita o antigo falso passe e conserva a sugestão sem persistência parcial.
- A primeira rodada conjunta teve uma fixture de aprovação ainda carregada com limiar antigo, antes do ajuste da expectativa para o pico correto; `motion-derivative-tests.xml` conserva **65 aprovados/1 falha**. A rodada final repetiu toda a seleção com os arquivos atuais e passou.
- `motion-derivative-receipt.json`: hashes dos arquivos/recibos, método, tolerâncias e medição local reproduzível de 1.000 segmentos × duas ordens. Uma execução não mede p95, memória, realtime ou render de vídeo.
- Ruff e verificação do diff passaram. Nenhum código externo, dependência nova ou troca de motor foi incorporado.

Reproduzir o recibo após os testes: `python scripts/validation/editor-motion-derivative-receipt.py`. O script recusa XML final com falha, erro ou skip. Contagens dos dois XMLs se sobrepõem e não devem ser somadas.

Pendências: fonte final/medição e grafemas, safe area e overshoot com geometria completa, split que preserve curvas, máscaras arbitrárias, trim/speed de vídeo real e qualificação visual/humana. Os renders anteriores de comandos permanecem evidências históricas. Os clones temporários de pesquisa continuam presentes: a revisão automática rejeitou sua remoção com `blocked by policy`; não houve liberação de espaço confirmada.
