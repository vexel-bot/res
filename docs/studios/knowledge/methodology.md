# Metodologia da inteligência criativa audiovisual

## Objetivo

Transformar obras públicas e autorizadas em conhecimento de decisão auditável. O sistema não imita personalidade nem atribui um resultado inteiro à pessoa mais famosa: ele registra observações, fontes, inferências, colaboradores, limites e testes transferíveis.

## Unidade de análise

Uma unidade é um vídeo completo, sequência, episódio, roteiro ou estudo de craft com limites temporais e fonte definidos. Toda unidade recebe `analysis.md` e `shots.json`. O mapa temporal pode conter três classes de fronteira, que nunca devem ser confundidas:

1. **corte editorial confirmado:** conferido quadro a quadro por uma pessoa;
2. **candidato de mudança visual:** resultado de diferença de pixels, sujeito a flashes, câmera e motion;
3. **unidade editorial alinhada à fala:** intervalo semântico útil, mas não necessariamente um plano.

## Protocolo R1

1. registrar URL, autoria declarada, acesso, duração, checksum e direitos;
2. extrair metadados e transcrição de máquina em ambiente temporário;
3. observar contact sheets e vídeo completo;
4. mapear mensagem, beats, personagem, cenário, imagem, montagem, motion/CGI/VFX e som;
5. separar observação, declaração documentada e inferência;
6. destilar princípio, contraexemplo e teste de aceitação;
7. submeter análise e mapa temporal à revisão humana;
8. corrigir a taxonomia antes de abrir R2.

## Escala e qualidade

- O corpus planejado contém 900 unidades; uma linha no manifesto não equivale a uma anotação concluída.
- O contador `annotated` só sobe quando os dois artefatos existem, têm cobertura temporal e passam validação.
- Dez por cento das unidades críticas exigem segunda revisão humana.
- Divergência temporal, funcional ou epistêmica é preservada e adjudicada; não é apagada por média.
- Métrica de plataforma ajuda a selecionar, mas não prova causalidade, qualidade ou retenção.

## Escala de confiança

| Faixa | Uso permitido |
|---|---|
| 0,90–1,00 | medida técnica reproduzível ou declaração primária inequívoca |
| 0,75–0,89 | observação direta com fonte/locator completo |
| 0,55–0,74 | interpretação plausível que exige revisão |
| 0,30–0,54 | hipótese de trabalho; não automatizar decisão |
| 0,00–0,29 | lacuna ou especulação; registrar, não usar |

## Regra de não fabricação

Ausência de fonte, obra inacessível, crédito incerto ou hardware indisponível vira `blocked`/`gap`. Nunca será preenchida com memória provável, citação inventada ou contagem simulada.

