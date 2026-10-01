# res — implementação do repertório e execução de motion

Data: 9 de setembro de 2026

## Escopo implementado

- O plano contextual V2 registra estados visuais, intervalos de observação, spans tipográficos,
  região de interesse, intenção de crop, semântica de material e versões de execução.
- O compilador fixa compilador, biblioteca de componentes, runtime e política de auditoria.
  Uma versão desconhecida interrompe a compilação. Planos anteriores continuam legíveis.
- Keywords dentro de uma frase viram spans vinculados ao texto de origem; não criam uma camada
  duplicada quando há uma associação única e temporalmente válida.
- O cálculo de geometria compõe matrizes de pais e filhos, origem, escala, rotação, câmera,
  instâncias e opacidade herdada. A auditoria usa esses limites efetivos.
- O runtime exporta amostras de geometria do DOM e mede a região essencial de imagens e vídeos
  após `contain`/`cover`. Crop que remove a ROI vira uma correção localizada.
- Overshoot é observado no início, pico e estabilização. A amostragem é distribuída pelo vídeo
  e pelos intervalos declarados, em vez de consumir o limite apenas nas primeiras cenas.
- O catálogo de repertório inclui as dez observações do Pinterest como conhecimento datado e
  separado das capacidades executáveis. A recuperação filtra capacidade, ranqueia antes de
  limitar e preserva diversidade relevante entre montagem, composição e som.
- Requisitos de material agora descrevem entidade, ação e aparência. Esses campos participam
  da consulta e do ranking, sem transformar metadados do provedor em aprovação visual.
- Filmagem obrigatória continua bloqueada quando o provedor não está disponível; componente
  procedural não a substitui. Aquisição, inspeção, aceitação e incorporação permanecem estados
  distintos e idempotentes.
- A biblioteca executável ganhou pilha ordenada de filtros e modos de mistura tipados. Grupos,
  conectores, máscaras fornecidas, câmera, transições, spans e perfis de motion continuam no
  mesmo runtime compartilhado.
- Reparos são classificados entre normalização limitada e mudança semântica. Mudanças de
  intenção exigem alternativa explícita. Correções automáticas continuam limitadas a duas por
  etapa e vinculadas à revisão de origem.
- O painel mostra achados por cena/elemento, enquadramento da ROI e as versões fixadas do plano.

## Defeito corrigido durante a validação

Uma trilha estática definia opacidade `1` para toda camada sem animação. Isso anulava a
opacidade de profundidade declarada e fazia elementos de fundo competirem com o foco. A trilha
agora preserva a opacidade editorial e a auditoria também calcula sua herança nos grupos.

## Validação executada

- Testes de contratos e compilação V2, geometria, auditoria visual, aquisição, repertório,
  persistência, idempotência, produção, revisão e compatibilidade passaram.
- O adaptador HyperFrames 0.8.31 produziu um MP4 real de qualificação com câmera, overshoot,
  profundidade, tipografia e a pilha de efeitos pelo fluxo compilado.
- `ruff`, `node --check`, TypeScript e o build de produção passaram.
- Nenhuma API paga foi chamada e nenhum material foi escolhido manualmente para produzir uma
  peça de validação editorial.

## Capacidades ainda não qualificadas

Matte animado por outra camada, blur temporal, geometria 3D articulada, tracking, rotoscopia,
estabilização e deformações complexas continuam indisponíveis. O sistema deve bloqueá-las ou
apresentar uma alternativa; não deve anunciar equivalência ao After Effects.

A etapa autônoma com briefing novo, aquisição pelo próprio res, vídeo completo e revisão humana
é o próximo experimento. Ela não foi simulada com cenas ou assets montados pelo Codex nesta
implementação.
