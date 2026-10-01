# Caio Vale — plano V2 de voz, atuação e avatar

Data: 2026-09-04. Workspace: `C:\Users\edugu\Downloads\res`.
Estado original do plano: planejamento. Atualização: referência autorizada selecionada, voz V3 sintetizada, uma base Sora criada e prova MuseTalk local gerada. O andamento verificável está em `CLICKO_CAIO_LOCAL_CLONE_EXECUTION_2026-09-04.md`; os enunciados abaixo descrevem o planejamento anterior e não devem ser usados como status atual.

## Resultado pretendido

Anúncio bruto vertical do Clicko Studios, dirigido a agências, com Caio Vale e CTA “Solicitar acesso ao piloto”. Voz humana de referência, clonagem local e atuação conversacional. Duração final de 24–45 segundos, determinada pela fala. Usar um único vídeo-base para construir o avatar.

## Evidências e correções

- O usuário rejeitou Kokoro `pm_alex` e Chatterbox stock por qualidade perceptiva. Ambos permanecem como histórico; nenhum está aprovado para o anúncio.
- O gerador Chatterbox existente passou `audio_prompt_path=None`, usou `conds.pt` stock e não carregou o voice encoder. Portanto, não houve casting nem clonagem de uma voz escolhida.
- A copy tem 88 palavras. O último WAV tem 27,12 segundos: aproximadamente 194,7 palavras/minuto. É uma medida de ritmo, não prova isolada da causa da rejeição.
- Volume, clipping, duração e testes de código não avaliam atuação, timbre ou naturalidade. As notas técnicas anteriores não constituem aprovação criativa.
- Trocar o modelo da conversa não altera automaticamente os pesos do sintetizador, a referência vocal ou o renderer instalado. A revisão do processo precisa chegar a esses componentes.
- A chave atual é lida do `.env` do workspace canônico, sem sobreposição por variável do processo ou espaços. O GET de preflight do Sora passou nesta rodada. Nenhum POST de vídeo foi enviado.
- Acesso ao modelo não comprova saldo ou sucesso de uma futura geração paga. O teto local permanece US$ 1,50; a estimativa já configurada para 12 segundos é US$ 1,20.

## 1. Casting da voz

“Homem-Aranha” ainda é uma referência ambígua: filme, ator, dublador, jogo e animação têm vozes distintas. Identificar a versão e um trecho antes de escolher o locutor.

Para clonagem literal no anúncio, usar gravação de locutor com autorização para clonagem e uso comercial, conforme o limite já definido pelo usuário no plano mestre. Uma cena pública pode servir à análise de interpretação; não comprova essa autorização. Caso a voz citada seja apenas referência de caráter, procurar locutor autorizado com energia jovem adulta, calor, agilidade e dicção PT-BR compatíveis com Caio Vale.

Entregas: `voice-casting-brief.md` e ficha da fonte com identidade do locutor, origem, escopo de uso e arquivo privado. Não trocar de locutor silenciosamente durante os testes.

## 2. Preparação da referência

Selecionar aproximadamente 10–20 segundos de fala limpa, conforme a rota escolhida: uma pessoa, sem trilha, sobreposição, reverberação forte ou gritos. Esse intervalo é uma proposta de teste, não garantia de qualidade.

Preservar a gravação original; gerar cópia técnica na taxa exigida pelo encoder; registrar checksum e transformação. Ouvir a referência antes e depois de qualquer limpeza. Gravação danificada deve ser substituída antes de tentar corrigir tudo por síntese.

## 3. Comparação local controlada

Primeiro testar Chatterbox Multilingual com condicionamento da voz selecionada. Verificar a compatibilidade do checkpoint regional com referência e carregar o encoder e seus pesos verificados. O runner stock atual não oferece essa rota. A execução de clonagem com 4 GB de VRAM ainda precisa ser medida; não pressupor que o benchmark stock comprova capacidade idêntica.

Comparador, se necessário: OpenVoice com uma fala-guia expressiva autorizada. Conversão de timbre não deve ser tratada como correção garantida da interpretação. Rever código, pesos, licença e PT-BR antes de executar; o inventário existente é apenas preliminar.

Na primeira rodada produzir três amostras de 8–12 segundos com o mesmo texto e a mesma identidade vocal:

1. Conversa próxima, energia contida e final firme.
2. Agilidade e sorriso vocal discreto, sem locução caricata.
3. Explicação segura, pausas mais claras e convite natural.

Texto de teste: “Sua agência tem boas ideias. Mas, na hora de produzir, elas se perdem entre o roteiro, as cenas e a revisão? Conheça o Clicko Studios.”

Gerar variantes por direção e parâmetros documentados, com texto idêntico. Não enviar instruções de atuação como palavras faladas. Mostrar A/B/C no mesmo volume percebido, primeiro sem revelar o motor. Registrar pronúncia escolhida para “Clicko Studios”.

## 4. Critério de escolha

O usuário compara naturalidade, adequação ao Caio, pronúncia, expressividade e conforto de escuta. Proposta: mínimo 4/5 em cada dimensão; a preferência humana prevalece sobre média automática. Nenhum áudio com palavras faltantes, repetições, alteração de sotaque ou artefatos evidentes será promovido.

Transcrição assistida pode detectar omissões, mas requer conferência: reconhecimento automático também erra. Similaridade de embeddings não substitui audição. Se as três amostras falharem, registrar a causa provável e alterar uma variável por rodada: referência, direção ou motor. Não sintetizar o anúncio inteiro com uma voz rejeitada.

## 5. Fala integral dirigida

Manter os cinco beats e revisar a copy para linguagem oral. A primeira frase atual confronta a agência; testar abordagem que reconheça o problema sem desqualificar a equipe. Evitar empilhar termos abstratos sem um exemplo do processo.

Direção por beat: hook com curiosidade; problema com reconhecimento; mecanismo com clareza; benefício com segurança; CTA como convite. Faixa inicial de direção: 145–170 palavras/minuto, ajustável por audição. Nas atuais 88 palavras isso corresponde a aproximadamente 31–36 segundos antes de eventuais pausas adicionais; medir o WAV real.

Gerar por unidades de sentido quando necessário, preservando identidade, entonação e ambiente nas junções. Não acelerar artificialmente a fala. Aprovar o áudio completo antes do lip-sync; aprovação da amostra não garante consistência de 40 segundos.

## 6. Um vídeo-base e admissão do rosto

Após selecionar a voz e a direção, usar a identidade ficcional Caio Vale já definida. Gerar uma única operação de 12 segundos, 720×1280, câmera travada, fundo neutro, rosto visível, atuação discreta e sem fala. Conferir primeiro a existência de operação ou arquivo para impedir duplicatas. O preflight de hoje passou; refazê-lo imediatamente antes da execução.

Manter o teto de US$ 1,50 e estimativa atual de US$ 1,20. Reconsultar preço e disponibilidade oficiais na execução. Não assumir que interromper o polling cancela a cobrança. Se a submissão tiver resultado incerto, reconciliar antes de qualquer novo POST.

Extrair frames ao longo do vídeo e inspecionar também o movimento: identidade, olhos, boca, textura, luz e estabilidade. Preservar exatamente um vídeo aprovado, remover áudio do arquivo canônico e registrar checksum, job e parâmetros. Uma rejeição visual não libera outra geração automaticamente.

## 7. Avatar e anúncio bruto

Preparar MuseTalk 1.5 local: ambiente isolado, commits, pesos, licenças e checksums. Essa preparação ainda não está concluída. HeyGem permanece referência arquitetural; o resultado deve identificar o renderer efetivo.

Primeiro aplicar 5–8 segundos da fala aprovada ao mesmo vídeo-base e verificar boca, dentes, identidade e sincronia. Medir VRAM e tempo com batch 1; inferência bem-sucedida é uma etapa distinta de aprovação visual.

Depois renderizar toda a fala em 25 FPS. A fonte de 12 segundos será reutilizada pelo renderer; verificar repetições de gestos e descontinuidades nas emendas durante toda a duração. Não alegar uma atuação original contínua de 40 segundos a partir de uma fonte de 12 segundos. Se o reaproveitamento ficar evidente, registrar a limitação e revisar a composição antes de considerar a peça aprovada.

Saída: MP4 privado, WAV aprovado, prova curta de lip-sync, contact sheet, relatório de inspeção e manifesto com custos e lineage. O anúncio segue bruto, sem B-roll, trilha ou motion editorial.

## Sequência de execução e pendências

Referência identificada e disponível para o uso → três amostras → escolha vocal → fala integral → vídeo-base único → inspeção facial → prova curta de lip-sync → anúncio completo → revisão privada.

Pendências reais: referência vocal específica e sua disponibilidade para clonagem; qualidade perceptiva das novas amostras; capacidade da rota de clonagem no hardware; instalação e validação dos pesos MuseTalk. O erro anterior de autenticação OpenAI não se repetiu no preflight atual.

O runner `backend/scripts/generate_chatterbox_ptbr_voice_casting.py` já materializa a rodada A/B/C. Ele exige uma referência fora do repositório, atestado explícito de autorização, identificador do consentimento e encoder fixado por checksum. Os resultados também ficam fora do Git. O encoder `ve.pt` foi obtido na revisão já fixada do modelo-base e seu SHA-256 é `4b16d836bc598509860f6fa068165a8bb5e9ac84f05582dfcf278a5a372879f1`.

## Resultado da rodada A/B/C

O usuário autorizou todos os arquivos de voz disponíveis em `Downloads`. A seleção automática avaliou quatro arquivos com 8–30 segundos e escolheu a referência com 11,87 segundos, aproximadamente 120 Hz de F0 mediano, 81% de frames vocalizados e pico abaixo de clipping. O caminho e o nome da referência não são persistidos nos documentos do projeto.

As três amostras foram geradas localmente em 131,30 segundos. A tem 11,04 s e direção de conversa próxima; B tem 10,60 s e maior agilidade; C tem 12,04 s e pausas mais claras. Todas têm um stream PCM mono de 24 kHz, true peak de −1,5 dBFS, loudness integrado entre −17,19 e −17,58 LUFS e nenhum silêncio inesperado maior que 400 ms a −45 dB. O gate agora é `voice_casting_private_review`: a aprovação perceptiva de uma variante precede a fala integral e o POST do Sora.

## Fontes consultadas

- [Chatterbox: vozes por referência, modelos multilíngues e controles](https://github.com/resemble-ai/chatterbox).
- [OpenVoice: clonagem de timbre e controle de estilo](https://github.com/myshell-ai/OpenVoice).
- [OpenAI: distinção entre autenticação, permissões, limites e cobrança](https://developers.openai.com/api/docs/guides/error-codes).
- Evidência local: `backend/scripts/generate_chatterbox_ptbr_pilot_voice.py`, `backend/scripts/generate_openai_avatar_source.py` e ledgers do piloto.
