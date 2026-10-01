# Correções após a reprovação de Distribution

## Estado desta implementação — 7 de setembro de 2026

Entrega parcial. O vídeo anterior permanece um diagnóstico negativo: direção escrita no runner,
execução pelo renderizador, sem demonstração de produção autônoma. Não foi substituído por um
vídeo montado externamente nesta alteração.

### Disponível no código

- Produção persistida em eventos, vinculada ao documento, revisão, checksums e chave de idempotência.
- APIs de criar, consultar, retomar e cancelar em `/studios/v1/documents/{id}/production-runs`.
- Etapa de direção pelo adaptador de planejamento existente: dois conceitos, escolha justificada,
  storyboard com estado inicial, ação, consequência, foco e conhecimento adquirido.
- Validação determinística da cobertura integral do roteiro e dos fatos protegidos. Isso impede
  omissões textuais; não prova por si só fidelidade visual ou qualidade narrativa.
- Segunda chamada de composição ligada ao storyboard por IDs, ordem e narração.
- Autoria do provedor/modelo/job registrada separadamente da revisão humana e audiovisual.
- Impedimento por revisão antiga, voz ausente ou provedor indisponível. Uma submissão incerta
  permanece vinculada ao mesmo job e não cria outra submissão na retomada.
- Continuação das etapas de direção/composição pelo worker, com retomada também pela API.
- Botão **Desenvolver direção visual** no painel, exibindo conceito, cenas e pendências.
- Recuperação de técnicas pertinentes mesmo quando seus materiais ainda precisam ser obtidos.
  O pré-flight de execução continua exigindo os recursos reais.
- Catálogo classificado antes do limite de 100 candidatos, com correspondência parcial normalizada
  e descritores de enquadramento, foco, espaço, movimento, função editorial e energia.
- Observação dos pixels do MP4 V2 após o render, com intervalos por cena, cobertura e incerteza.
  Resultados ficam em `audiovisualObservations` no asset e `evaluation.observations` no plano.

### Limites explícitos

O coordenador agora segue direção → voz por cena → composição → animatic interno em qualidade
draft → render → crítica → revisão localizada → nova renderização. O animatic usa o mesmo
motor gráfico e temporal, com verificação técnica antes da exportação padrão; ainda não é um
storyboard simplificado independente de menor custo. Os dois renders têm jobs e recibos próprios.
O detector genérico de quadros pretos ainda pode reprovar fundos gráficos deliberadamente
escuros. Essa reprovação interrompe a exportação padrão e exige tratamento contextual posterior;
a política existente não foi relaxada para fazer o teste passar.

A crítica recebe o MP4 real, seu checksum e o plano. Achados devem indicar cena, intervalo,
evidência, incerteza e correção. Cobertura parcial ou bloqueadores não disparam correções
automáticas. No máximo duas rodadas são realizadas; a confiança declarada pelo modelo não
equivale a revisão humana nem é uma medida calibrada de qualidade. O adaptador compatible
atual aceita imagens, não vídeo completo: nesse caso o rascunho é apresentado com a pendência.

Revisões solicitadas pelo cliente usam `/production-runs/{id}/revise`, com revisão esperada,
IDs das cenas e instrução textual. IDs, ordem, narração, fatos e durações permanecem protegidos.
Cenas não selecionadas devem ser idênticas. Alterar a duração fica bloqueado até existir
remapeamento explícito das dependências temporais. O histórico preserva os vídeos anteriores.

A síntese stock existente não foi promovida, nem suas exigências de qualificação relaxadas.
Os jobs de voz stock existentes são criados por cena, com hash do texto, identidade de provedor
e política de admissão existente. Arquivos sintetizados são medidos com ffprobe e incorporados
com proveniência; o compilador insere a fala integral e rejeita cenas curtas demais. Uma gravação
fornecida pode atender uma única cena; várias cenas exigem alinhamento explícito, ainda pendente.

Permanecem por implementar/qualificar no novo coordenador:

1. Aquisição automática autorizada e inspeção complementar dos candidatos, acervo sonoro curado
   e mapa sonoro com verificação de sincronismo e inteligibilidade.
2. Qualificação real do provedor stock, alinhamento de gravações longas e calibração da crítica.
3. Peça autônoma de 12–15s, audição e revisão humana, antes da peça de 45–60s e transferência
   entre temas/identidades.

A inspeção local desta rodada encontrou Gemini não configurado, registro de voz vazio e
HyperFrames desabilitado na configuração da aplicação. Os testes ativam o renderizador somente
em ambiente isolado e utilizam respostas controladas de planejamento/voz. O teste criativo
com provedor real depende dessas configurações e da admissão da voz; não foi executado aqui.

Nenhum teste simulado de LLM qualifica direção criativa. Nenhuma leitura de frames qualifica
mixagem, música ou compreensão da narração. `autonomousProductionQualified` permanece falso.

### Evidência observada

O observador novo leu o MP4 negativo e produziu
`reviews/distribution-2026-09-07/encoded-observations.json`: 102 amostras a 2 fps,
seis intervalos de pouca mudança visual e razão de 0,72277 entre comparações quase estáticas.
Essa medida usa outro limiar/resolução que o diagnóstico anterior; não é uma comparação
de melhoria entre versões. Pausas podem ser intencionais. Áudio e qualidade editorial continuam
sem aprovação nessa medição.

Os testes de produção usam respostas controladas do adaptador e banco descartável fora do
repositório. Os testes do observador codificam e leem MP4s reais. Não houve chamada paga de LLM,
alteração de credenciais nem aprovação humana inventada.

Verificações desta rodada: 17 testes de backend passaram com HyperFrames habilitado; o teste
de worker foi repetido após acrescentar asserções sobre as observações do MP4 e passou.
Os 5 testes de interface passaram, assim como TypeScript e Ruff nos arquivos alterados.
A bateria anterior desta rodada também passou para importação/catálogo e contratos V2.

Continuação da implementação: 27 testes de backend passaram antes da inclusão do animatic.
Após essa inclusão, os 6 testes de continuação passaram, incluindo os dois MP4s reais
(animatic e exportação padrão), crítica vinculada ao checksum e revisão localizada.
O provedor fake de voz passou pelo fluxo existente de job, armazenamento, proveniência e
medição do WAV; isso é teste de integração, não qualificação de voz. Os 5 testes da interface,
TypeScript e Ruff também passaram. Todos os bancos de pytest foram descartáveis, fora do
repositório; a peça criativa com serviços reais continua reservada ao próximo teste.
