# Dez anúncios UGC — plano, crítica e validação

Data: 30/08/2026. Status: experimento local; não aprovado para publicação.

## Perfil vigente — vídeo UGC com sons naturais e legendas, sem voz

Direção explícita do usuário em 30/08, posterior aos lotes descritos abaixo. Esta é a prioridade da
próxima entrega. Nenhuma chamada de TTS, clonagem, voz stock ou lip-sync deve ser feita nesta rodada.

- Visual: pessoa/avatar demonstrando produto ou ação de forma natural, sem performance de fala.
- Áudio: ambiente e foley autorizado, sincronizado ao que acontece; sem narração, falas de fundo ou música.
- Legendas: copy editorial em blocos temporizados; não apresentar como transcrição. Entregar texto
  legível no próprio MP4 e arquivo de legendas editável quando o fluxo de exportação estiver integrado.
- Continuidade: conferir mãos/objetos, contato, gravidade, sombras e correspondência som/ação.
- Qualidade inicial de legenda (hipótese de produto a validar): até duas linhas, leitura confortável,
  quebra por unidade de sentido, sem cobrir produto/rosto/CTA e sem disputar atenção com outros textos.
- Direitos: fonte/licença dos takes e sons; consentimento de imagem quando houver pessoa real.
- Voz e lip-sync: não aplicáveis, sem “bloqueado por falta de voz” neste perfil.
- Silêncio, cards estáticos ou legenda desacompanhada de vídeo real não bastam para aprovar a entrega.

| Caso | Direção de som natural |
|---|---|
| Café | Grãos, despejo de água e caneca tocando a mesa |
| SaaS | Teclas e cliques discretos em demonstração real |
| Protetor solar | Tampa e manuseio da embalagem, sem fala |
| Perfumaria | Tampa, borrifada e tecido |
| Clínica | Ambiente calmo sem conversas captadas |
| Orçamento | Teclas, papel e ambiente de mesa |
| Refeições | Abertura de embalagem, prato e talheres |
| Cadeira | Rodízios e ajustes compatíveis com o mecanismo mostrado |
| Curso | Páginas e teclado, sem voz de aula |
| Moda | Cabides, tecido e passos |

São direções de produção, não sons já obtidos ou validados. O corpus histórico de fala permanece
inalterado; o próximo corpus deve ter novo identificador/digest e checagens de leitura de legenda,
presença de ambiente/foley e ausência de voz, em vez de reciclar `spoken_pacing` como aprovação.
O formato não dispensa revisão humana ou permite liberar imagem de pessoa sem direitos válidos.

### Contrato e corpus sem voz executados

O corpus novo foi congelado em
`benchmarks/studios/ugc/ugc-no-voice-natural-caption-casebook.v1.json`, com suite
`clicko.ugc-no-voice-natural-caption.pt-br.v1` e digest canônico
`624a1cffa264175170746a42defcad356fc601c36b9f25e3599d0ec10a908008`.
Ele não altera nem reclassifica o corpus falado v1.

Os dez casos cobrem os seis slots de casting e dez nichos. Cada caso contém cenário, ação,
continuidade, fatos permitidos, alegações proibidas, cinco legendas editoriais cronometradas e dois
cues de som natural ligados ao que aparece na tela. O contrato fixa:

- `natural-foley-only` como único modo de áudio;
- voz, conversa captada e música como `prohibited`;
- até duas linhas e 42 caracteres por linha, com hipótese inicial de até 18 caracteres/segundo;
- hook inicial, demonstração visual e CTA final, sem sobreposição de legendas;
- licença, checksum, relatório de detecção e escuta humana para cada arquivo de som;
- MP4 1080×1920/H.264 com áudio real, legenda queimada, direitos do take e relatório do mix final;
- recibo humano ligado ao digest exato do caso antes de declarar o vídeo pronto;
- publicação externa sempre bloqueada neste benchmark.

A auditoria reproduzível em `artifacts/validation/ugc-no-voice/audit-20260830-v3/` aprovou
o contrato mecânico dos 10/10 planos e marcou 0/10 como prontos para produção. Isso é o resultado
correto: não foram fornecidos takes/avatar, sons licenciados, relatórios de ausência de voz/música
ou revisão humana. Nenhuma voz, música, geração de mídia ou publicação foi executada.

Complementa o plano mestre de CX sem substituir CX-0 a CX-6. Os dez casos são testes de conteúdo dos
fluxos Editorial → Visual/Carrossel/Vídeo → Review; não autorizam pular consentimento, ativar modelos
biométricos ou chamar uma tela de concluída apenas porque um arquivo foi produzido.

## O que foi executado e o que falta

| Capacidade | Evidência disponível | Limite da evidência |
|---|---|---|
| Copy/roteiro | Dois lotes locais Qwen3-4B e diagnósticos | Contrato e palavras-chave não provam boa copy |
| Peça visual | 10 PNGs por lote, 1080×1350 | Composição Pillow; sem inferência de imagem ou fundo |
| Carrossel | 10 ZIPs por lote, cinco PNGs ordenados | Não comprova narrativa persuasiva nem edição persistida |
| Vídeo | 10 animatics por lote, 1080×1920, H.264 | Cards estáticos e faixa silenciosa; sem avatar/voz/motion avançado |
| Avatar | Seis slots de catálogo distribuídos na matriz | Nenhum rosto gerado, IdentityVersion ativado ou lip-sync medido |
| Voz | Contratos e gates preexistentes | Nenhuma voz clonada nesta bateria |
| Integração de produto | Compositor canônico reutilizado | Harness offline não percorre autenticação, jobs, save ou review via UI |
| Plano UGC sem voz | 10/10 casos passam no contrato novo | 0/10 em produção; faltam takes, sons e revisão com evidência |

Corpus histórico falado: `benchmarks/studios/ugc/ugc-ad-creative-acceptance-casebook.v1.json`.
Corpus vigente sem voz: `benchmarks/studios/ugc/ugc-no-voice-natural-caption-casebook.v1.json`.
Os nomes Lia, Maya, Nina, Caio, Theo e Bento são slots de casting, não pessoas autorizadas ou avatares já produzidos.

## Matriz de direção

| Caso | Nicho | Casting | Fundo e performance | Vídeo |
|---|---|---|---|---|
| 01 | Assinatura de café | Lia | Cozinha matinal, janela lateral, caneca; gesto acolhedor | 15 s |
| 02 | SaaS de conteúdo | Bento | Mesa de estúdio, monitor abstrato; demonstração didática | 20 s |
| 03 | Protetor solar | Nina | Banheiro claro, pele natural, embalagem; sem antes/depois | 15 s |
| 04 | Perfumaria | Theo | Madeira escura, frasco e luz lateral; performance discreta | 15 s |
| 05 | Orientação preventiva | Maya | Sala clara, sem jaleco/credencial fictícia; postura responsável | 30 s |
| 06 | Organização financeira | Caio | Home office, gráficos fictícios rotulados; sem prometer economia | 30 s |
| 07 | Refeições prontas | Lia | Cozinha residencial, prato e embalagem; sem depoimento fabricado | 15 s |
| 08 | Cadeira de escritório | Bento | Posto de trabalho e detalhes dos mecanismos; demo fiel à ficha | 20 s |
| 09 | Curso de conversação | Nina | Canto de estudo, notebook e fone; incentivo sem prazo de fluência | 15 s |
| 10 | Coleção cápsula | Maya | Arara minimalista e paleta coerente; sem selo ambiental inventado | 30 s |

Cada caso contém cenário, fundo, iluminação, enquadramento, roupa, props e três restrições de continuidade.
Sombras, contato das mãos, reflexos, permanência de objetos e coerência de gestos precisam ser
inspecionados no vídeo com inferência real. Repetir o nome do cenário no texto não comprova física.

## Processo editorial a implementar e validar

1. Fixar brief, oferta e fatos aprovados; separar informação conhecida, hipótese e evidência ausente.
2. Definir estágio de consciência, ângulo, casting, cenário, duração e CTA do mesmo documento.
3. Gerar cinco beats: hook → problema → demonstração → oferta → CTA. A legenda editorial ordenada
   é a única fonte de texto do vídeo; não gerar roteiro falado.
4. Avaliar restrições, oferta, duração, leitura e sincronismo; mostrar a causa da reprovação por campo/cena.
5. Revisar somente os trechos reprovados, mantendo fatos e campos bloqueados. Registrar a tentativa anterior.
6. Projetar visual/carrossel/animatic a partir da mesma versão; inserir revisão de texto e legibilidade.
7. Quando houver providers e ativos aprovados, gerar take/avatar e cenário, adquirir foley autorizado,
   validar ausência de fala/música e encaminhar ao Video Studio.
8. Revisão explícita da versão e do artefato. Nenhum score automático autoriza publicação.

O benchmark implementa 2–4 e a composição offline de 6, parcialmente. Em 5, já constrói feedback
com os critérios reprovados e o roteiro anterior, preservando os campos bloqueados e o recibo da
tentativa. Isso não comprova revisão de qualidade pelo modelo nem implementa o ciclo assistido
na interface, a geração biométrica ou os handoffs de produto de 5, 7 e 8.

## Critérios de decisão do perfil vigente

- Todas as checagens do plano precisam passar; produção permanece bloqueada sem bytes verificáveis.
- Legendas: até duas linhas, 42 caracteres por linha e hipótese inicial de 18 caracteres/segundo;
  hook, demonstração e CTA são obrigatórios e não podem se sobrepor.
- Cada cue sonoro exige arquivo dentro da raiz da execução, SHA-256, licença, origem, relatório de
  detector e escuta humana. Declaração em JSON sem bytes correspondentes não abre o gate.
- O mix final precisa conter áudio, mas nenhum sinal de fala ou música; detector sozinho não basta.
- O take/avatar exige direitos verificados e revisão visual. Slot de catálogo não é ativo produzido.
- Copy, legibilidade, sincronismo e segurança exigem recibo humano ligado ao digest exato do caso.
- O benchmark não publica, mesmo quando todos os gates de produção estiverem satisfeitos.

## Critérios históricos dos lotes falados

- Todas as checagens obrigatórias precisam passar; a média é apenas descritiva.
- Alegação proibida, oferta inventada, arquivo ausente/corrompido ou roteiro divergente reprova o pré-check.
- Hook de 3–14 palavras. Fala total: 24–44 palavras/15 s, 32–58/20 s, 48–84/30 s. São faixas iniciais de produto;
  a medição real de fala e pausas prevalece quando houver áudio.
- Frases completas; sem vazamento de instruções internas; sem caracteres de outro sistema de escrita não previstos neste corpus PT-BR.
- `review_routing` comprova encaminhamento para revisão, não segurança ou veracidade das alegações.
- Integridade: bytes, SHA-256, tamanho, PNGs decodificáveis, ordem/contagem do ZIP, geometria, duração, FPS,
  codec e decodificação integral do MP4. Metadados declarados não bastam.
- Revisão editorial: naturalidade, tese, precisão da oferta, fatos, especificidade, CTA e coerência entre formatos.
- Revisão audiovisual futura: identidade, articulação, pronúncia, sincronização, mãos, reflexos e continuidade física.
- Avaliação humana real continua necessária; crítica pelo assistente não substitui MOS com avaliadores ou CX-0.

## Revisão editorial dos dez resultados v2

Revisor: assistente; leitura direta do JSON gerado. Sem participantes humanos, teste de conversão ou MOS.
As sugestões abaixo são referências autorais de revisão, **não saídas do Qwen nem publicidade aprovada**.
Todos os atributos e ofertas continuam sujeitos à confirmação de quem fornece o produto.

| Caso | Julgamento da copy gerada | Correção necessária |
|---|---|---|
| 01 | Reprovar: converte frete incluído em envio gratuito; roteiro termina no meio da frase | Preservar preço não informado e resumir a fala |
| 02 | Ajustar: confunde vídeo de 20 s com promessa de executar o trabalho em 20 s | Remover promessa de velocidade e demonstrar uma ação verificável |
| 03 | Reprovar: inventa proteção completa, duração diária, FPS alto e formulação leve | Usar apenas informação da ficha; nenhuma eficácia inventada |
| 04 | Reprovar: inventa cedro e sementes; menciona frasco genérico e extrapola duração | Remover notas não fornecidas e instruções de produção da fala |
| 05 | Reprovar para uso: atribui detecção antecipada de problemas sem evidência | Limitar o anúncio a orientação/agendamento e revisar com responsável |
| 06 | Ajustar: narração incorpora gráficos abstratos e contas fictícias do cenário | Separar direção visual da proposta do aplicativo |
| 07 | Ajustar: “melhor opção” e “sem sacrifícios” são generalizações | Tornar o benefício concreto e evitar superlativos |
| 08 | Reprovar: caracteres chineses no CTA, fala truncada e orientação corporal não validada | Conferir PT-BR e limitar demonstração aos ajustes documentados |
| 09 | Ajustar: abertura genérica e fala longa para o formato | Tornar a barreira de conversação específica e encurtar |
| 10 | Reprovar: inventa materiais sustentáveis e preços acessíveis | Remover atributos não confirmados, sem greenwashing |

### Referências de copy para a próxima revisão

01 — “Escolher o café da semana virou tentativa e erro? Conheça uma assinatura com seleção rotativa.
Veja as opções do mês e confira as condições do primeiro envio antes de pedir.”

02 — “Seu conteúdo começa numa ferramenta e se perde em outra? Veja um fluxo que reúne planejamento,
copy, edição e revisão. Acompanhe a peça do briefing até a revisão e conheça o teste guiado.”

03 — “Quer incluir um protetor solar na sua rotina? Conheça a linha facial e confira as informações
do produto. Veja a composição e as orientações de uso antes de escolher.”

04 — “Gosta de fragrâncias amadeiradas e de um estilo discreto? Conheça esta proposta e descubra
se combina com você. Confira a descrição do produto e as opções disponíveis.”

05 — “Você quer organizar seus cuidados, mas ainda tem dúvidas sobre por onde começar? Conheça a
consulta inicial de orientação preventiva. Veja quais atendimentos estão disponíveis e prepare suas
perguntas. Confira o responsável pelo atendimento, os horários e as condições antes de agendar sua conversa inicial.”

06 — “Você sabe onde estão concentrados os gastos da sua rotina? Conheça um aplicativo para
categorizar e acompanhar o orçamento. Veja como organizar seus registros e consultar as categorias
em um só lugar. Confira as funções, as integrações e as condições disponíveis antes de experimentar.”

07 — “A semana está corrida e o almoço ficou para depois? Conheça as refeições prontas porcionadas.
Confira o cardápio, os ingredientes e a entrega para montar um kit que faça sentido na sua rotina.”

08 — “Sua cadeira tem ajustes que você ainda não explorou? Veja as opções de altura, braços e inclinação
deste produto. Confira os mecanismos e as medidas na ficha antes de escolher a configuração para seu espaço.”

09 — “Você estuda as regras, mas trava na hora de conversar? Conheça uma proposta de prática guiada.
Confira o nível e os horários da aula de apresentação e veja como funciona.”

10 — “Você olha para o guarda-roupa e sente falta de combinações? Conheça uma coleção cápsula com
curadoria de peças. Veja as sugestões de composição, compare com o que você já usa e escolha com
calma. Confira os materiais, as medidas e a disponibilidade antes de conhecer a coleção completa.”

Essas referências devem ser adaptadas ao brief validado e divididas em beats antes do próximo ensaio.
Não foram executadas como substituição silenciosa de uma resposta do modelo.

## Evidência histórica e revisão das conclusões

- Lote v1: média antiga 4,554; dez resultados rotulados `pass` após um retry. Esse rótulo veio de
  média compensatória e não deve ser apresentado como aprovação de dez anúncios.
- Lote v2: média antiga 4,800; nove `pass`, um `fail`. A leitura editorial revelou alegações indevidas
  mesmo entre os nove. Não é uma melhoria de qualidade comprovada por usuários.
- Auditoria estrita dos dois lotes: arquivos íntegros nos vinte kits; roteiro/falas divergentes e outros
  checks pendentes impedem aprovação. As fontes históricas são preservadas; nova avaliação tem digest próprio.
- Auditoria reproduzível: `audit-20260830-verified/audit.json`, com snapshot do avaliador e hashes das
  fontes; 20/20 kits íntegros e 0/20 aprovados no pré-check atual. Não é uma nova execução de inferência.
- Diagnóstico v3, café e SaaS: a fonte única corrigiu a divergência roteiro/beats, mas os dois casos
  ainda falharam em duração/completude. Inspeção visual do PNG de café confirmou marcador de catálogo
  e texto interno de revisão no lugar do CTA. O arquivo não é um anúncio final.
- Retry controlado do café: o Qwen devolveu CTA e direções acima dos limites do contrato; a tentativa
  falhou fechada antes do render. O relatório v2 permaneceu byte a byte inalterado. A execução derivada
  reavaliou os outros nove casos e copiou somente seus artefatos íntegros; 0/10 passaram no critério atual.
- Artefatos ficam em `artifacts/validation/ugc-ad-acceptance/`, fora dos fontes de produção. Contêm
  material experimental sintético, sem dados biométricos reais; não há política de acesso de produção comprovada pelo harness.
- Nenhuma execução nesta etapa comprova geração de imagem por IA, rosto, voz ou lip-sync.

## Implementação, rollback e próxima sequência

- Contratos: `backend/app/domain/studios/ugc_acceptance.py` e contexto aditivo em `intelligence.py`.
- Provider: saída compacta restrita ao UGC; formato genérico preserva limites do contrato original.
- Decodificação: evita corte gramatical no meio das palavras, mantendo validação de comprimento no
  contrato; rejeita `finish_reason=length`. Isso evita aceitação silenciosa, não garante boa geração.
- Roteiro derivado dos beats, revisão obrigatória e bloqueio de termos de oferta inventados.
- Runner: recibos parciais por caso; retry cria execução derivada e preserva o resultado anterior.
  Os nove casos herdados são reavaliados; somente arquivos verificados são copiados, sem reutilizar
  rótulos antigos de aprovação. Copiar evidências históricas não significa nova inferência nesses casos.
- Auditor: `backend/scripts/audit_ugc_ad_acceptance.py`; nenhuma chamada de modelo ou edição dos lotes antigos.
- Compositor: fallback de fonte do Windows corrigido; sem alteração de shell, tokens ou rotas.
- Rollback: não chamar o harness/adapter experimental; não há migration, publicação ou provider promovido.

Próximos cortes: reduzir a verbosidade da revisão sem afrouxar o contrato e validá-la novamente,
sem alterar fatos bloqueados; medir o fluxo
autenticado Editorial → documento → revisão com este corpus e executar
o protocolo CX-0. Inferência visual e Presenter continuam dependentes dos gates de licença,
hardware, consentimento, qualidade e revisão já definidos. Voz fica adiada e não bloqueia o novo
perfil sem narração. Figma só será alterado por MCP.

## Candidato adiado por orientação do usuário

Voicebox: informado em 30/08 como projeto aberto no navegador local, com alegação de clonagem em 23
idiomas e comparação a ElevenLabs/WhisperFlow. URL exata, identidade do projeto, licença e capacidades
ainda não verificadas. Não foi clonado, instalado ou conectado nesta etapa. Avaliar somente depois
do plano/meta atual: cadeia de código/pesos, PT-BR, clonagem versus ditado, hardware, retenção,
consentimento e encaixe nos providers existentes. A reconexão do Figma não altera essa prioridade.
