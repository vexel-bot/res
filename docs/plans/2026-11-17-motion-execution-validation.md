# Motion: execução verificável e direção por referências

## Implementação local

Novas sessões nativas EffectCraft v2 recebem `motionQualityProfile=reference-led-v1`. Sessões antigas mantêm o perfil original. O perfil requer referência externa efetivamente inspecionada antes de registrar um plano; `referenceObservations`, `productionChecks` e `aestheticCriteria` explicitam interpretação e observação. A escolha criativa continua com o diretor.

`probe_motion_script` executa operações numa cópia descartável e não altera o rascunho, seus lotes ou evidências. `verify_motion_execution` lê propriedades por layer ID/UID exatos, incluindo metadados de chaves quando disponíveis. Aceita tolerância explícita, nunca busca aproximada. Configuração ausente é inconclusiva; divergência conhecida falha. Scripts bem-sucedidos continuam inconclusivos quanto à aplicação de cada instrução até verificação.

Recibos de `edit_project` incluem `executionReceipt`. Configurações `prop.set` são comparadas com a inspeção persistida. Scripts recebem alerta de exceções vazias; a análise estática é indicativa, não interpreta JavaScript nem prova falhas. Operações em excesso ao limite de leitura são declaradas não verificadas. Resultados e verificações ficam no histórico do job e são recuperáveis por `inspect_direction payload.kind=execution`; a compactação conserva identificadores.

Avaliações adicionam dimensão `craft`, separada de `technical`, `intent` e `audiovisual`. O novo perfil exige intenção e acabamento demonstrados na prova curta antes de ampliar a produção. A entrega informa acabamento por cena. Falta de escuta permanece inconclusiva. Um rascunho não equivale a promoção formal.

`inspect_production_capabilities` expõe o protocolo para curvas, movimento, composição, profundidade, luz/material, sombras, tipografia e som. O protocolo não é qualificação de execução. Cada operação ainda exige prova identificada; motor novo só será integrado após lacuna demonstrada. Nada restringe a criação a 2D ou promete suporte 3D não observado.

`inspect_direction payload.kind=costs` separa utilização do diretor, do avaliador e exposição incerta, com respostas e thinking por etapa. Histórico antigo pode ter etapa incorreta; contagem de ferramentas não representa alocação causal de custo.

## Validação reproduzível sem chamadas pagas

- `clicko-motion-offline-audit.py --evidence JOB-EVIDENCE.json --output AUDIT.json`: lê logs existentes e localiza riscos, consumo e ausência de referências. Não altera recibos históricos nem inventa aplicação de propriedades.
- `clicko-motion-native-proof.py --source NATIVE.ecproj --output DIRECTORY`: copia o projeto, substitui a composição da cópia por fixture técnico de um segundo, aplica curvas/traços e interpolação linear/Bézier e renderiza cinco quadros. Não escreve no banco ou no original, não chama modelos e não produz anúncio.
- Os quadros gerados são inicialmente `rendered_unobserved`. Observação posterior deve registrar arquivo/hash, quadros e limites separadamente. Cinco quadros não são cobertura temporal integral.
- Testes cobrem comparação real de parâmetros, falha/ausência, tolerância, isolamento da prova descartável, referências obrigatórias, contratos antigos, compactação e orçamento.

## Limites e avanço

A execução desta entrega é local. As gerações pagas continuam suspensas. Autorizar implementação não autoriza nova produção, retomada automática de Claude ou gasto ilimitado.

A prova local inicial qualifica apenas o exemplo observado de curva/traço e posições amostradas de interpolação. Máscaras, luzes, materiais, sombras, áudio perceptual e 3D ainda precisam de provas específicas. Não são declarados aprovados pelo protocolo. Integração de outro motor depende do resultado dessas provas; nenhum provedor adicional foi acionado.

Após qualificar as capacidades necessárias, uma nova autorização financeira permitirá a prova criativa curta dirigida pelo Claude. Somente seu resultado justificará uma produção completa e uma comparação estética com as referências. Esta implementação não demonstra, por si, qualidade profissional dos próximos vídeos.
