# Edição contextual V2 — implementação e qualificação

Atualizado em 7 de setembro de 2026. Escopo: edição e motion do res.

**A entrega narrada ainda não está concluída.** O motor produziu vídeos reais, mas não há uma voz utilizável registrada nem credenciais Gemini configuradas neste ambiente. A direção por LLM foi exercitada no limite da API com respostas controladas; isso não qualifica a qualidade editorial de um modelo. A audição integral e a revisão humana permanecem pendentes.

## O que foi conectado

- `ContextualPlanRequestV2` → cenas tipadas → `CreativeDocumentV1` + timeline + `MotionGraphV1` → HyperFrames → FFmpeg → recibo e avaliação. A timeline pode começar sem filmagens.
- Múltiplos elementos e áudios por cena, IDs estáveis, relações de grupo, repetição escalonada, alinhamento entre irmãos, ordem de camadas e dependências temporais. Transformações de grupos usam a hierarquia DOM/CSS, incluindo origem, rotação e escala.
- Tipografia com arquivos reais e verificação de caracteres, revelações por palavra, caminhos vetoriais internos, cartões, máscaras estáticas, cortes, dissolve, wipe e correspondência de transformação de elementos simples. A correspondência transfere o elemento durante a sobreposição sem duplicar a cópia anterior; exige origem central e proporções uniformes quando há rotação. Correspondências complexas entre grupos e transformações já animadas geram impedimento.
- Eventos sonoros alimentam a timeline de áudio efetivamente mixada. Música, ambiente e efeitos podem coexistir. O processamento reutiliza fades, ducking e normalização do FFmpeg existente.
- Catálogo do cliente, seleção de candidatos, fontes cadastradas, incorporação de arquivos verificados e endpoint de escolha de material. Materiais gerados continuam sujeitos à verificação existente. Uma busca sem arquivo não torna o recurso renderizável.
- As 25 fichas pesquisadas e sete fichas de componentes estão disponíveis para recuperação. Relevância precede o limite do contexto; capacidades e requisitos de material são filtrados. O plano fixa o conteúdo recuperado por digest. Observações, princípios e sinais de tendência continuam distintos.
- Inspeção por mudanças de cena, amostras junto aos cortes e intervalos solicitados, com lacunas explícitas. Há limites de 120 segundos de detecção por trecho e 12 amostras por trecho; isso não é análise integral.
- Revisões locais reaproveitam a direção estruturada: “mais calmo”, “menos texto” e “mostrar melhor o produto”. Textos factuais e cenas não selecionadas são preservados. Impedimentos anteriores não desaparecem com um pedido de ajuste.
- Rascunho automático separado de aprovação humana. Planos e grafos continuam sugeridos/não revisados; publicação mantém suas exigências. A avaliação técnica fica ligada ao job, arquivo e checksum.

O canvas legado não comporta vídeo e grupos temporais. Para documentos V2 ele recebe um cartão de navegação explícito; a composição completa permanece no documento canônico. O endpoint legado impede sobrescrever essa composição com um canvas incompatível. Documentos V1 continuam com o caminho anterior.

## Evidência produzida

Diretório: `artifacts/validation/editorial-v2-20260906/qualification/`.

| Arquivo | Evidência e limite |
|---|---|
| `distribution-motion-diagnostic.mp4` | Peça própria de 51 segundos, seis cenas, identidade neutra, texto seletivo, cartões, grupos, caminhos, máscara e desenho sonoro procedural. Exibe “narração pendente”. |
| `distribution-motion-revised-diagnostic.mp4` | Revisão mais calma e com menos texto; a conclusão permanece idêntica na direção. |
| `reused-footage-diagnostic.mp4` | Quatro segundos extraídos pelo renderizador a partir de 1,2 segundo do vídeo produzido, com novo cartão e preservação do áudio. |
| `match-transform-diagnostic.mp4` | Exemplo curto de correspondência de posição, tamanho e rotação entre elementos. Não certifica morphing ou composição arbitrária. |
| `*.plan.json`, `*.document.json`, `*.graph.json`, `*.manifest.json`, `*.operations.json`, `*.receipt.json` | Entradas, decisões, grafo, intervalos e cobertura declarada pelo executor. |
| `requested-plan-with-narration.json`, `narration-pending.json` | Roteiro completo solicitado e necessidades de voz que impedem sua aceitação. |
| `audio-preservation-check.json` | Comparação numérica do trecho de áudio: correlação de aproximadamente 0,9998 sem deslocamento. Não substitui audição. |

A linguagem de conexão, repetição e continuidade toma “Distribution”, do @mep.io_, como referência. Roteiro, imagens procedurais, sons e composição do diagnóstico são próprios. O plano desse diagnóstico foi escrito para qualificar o executor; não deve ser apresentado como saída editorial autônoma do Gemini.

## Verificações e custos

- Regressão de backend: **99 aprovados, um smoke opcional não executado**, sem falhas. O teste V2 de API/worker executou render real. A suíte focal do compilador também passou; seus casos se sobrepõem à regressão e não devem ser somados como cobertura distinta.
- Interface: **quatro testes aprovados**, com API controlada. TypeScript (`tsc --noEmit`) passou. Resultados e hashes dos arquivos estão em `validation-summary.json`.
- Após corrigir a duplicação na correspondência entre cenas, a suíte focal teve **19 aprovados e um smoke opcional não executado**; o teste adicional de limites também passou. O render curto validou passagem sem duplicação e retorno na prévia. Essa execução posterior cobre a última alteração; não houve repetição desnecessária da regressão completa.
- Testes de API/worker com MP4 real verificam aplicação, repetição idempotente, cobertura e permanência da revisão humana pendente.
- Testes de interface cobrem início sem filmagem, envio de `planVersion: 2`, materiais pendentes e fluxo de revisão.
- A inspeção antes da captura verifica carregamento de fontes/imagens e transbordamento de texto nos intervalos e keyframes. Uma falha impede o render.
- Cortes em filmagens existentes exigem preservação dos trechos ou transcrição revisada; dependências temporais que não podem ser preservadas geram impedimento. Isso não é uma prova automática de equivalência semântica.
- XMLs de testes ficam em `artifacts/validation/editorial-v2-20260906/`. Os testes de banco usam diretórios descartáveis em `%TEMP%`; não executar pytest no diretório do banco local.
- Os recibos registram duração, frames e tempo de render. Não houve chamadas pagas neste pacote. Custo monetário de CPU/armazenamento não foi calculado sem tarifa de infraestrutura. Não foi criado limite financeiro de produção.
- As versões de 51 segundos levaram aproximadamente **198 e 205 segundos** para renderizar neste computador. São tempos decorridos observados, não custos faturados ou promessa de capacidade em produção.

## Como executar o diagnóstico

No repositório real `C:\Users\edugu\Downloads\res`, com Python/FFmpeg e o runtime fixado em `workers/media-cpu/package-lock.json`:

```powershell
$env:PYTHONPATH = 'C:/Users/edugu/Downloads/res/backend'
python backend/scripts/qualify_editorial_v2.py `
  --output artifacts/validation/editorial-v2-20260906/qualification `
  --cli C:/Users/edugu/Downloads/res/workers/media-cpu/node_modules/hyperframes/bin/hyperframes.mjs `
  --font C:/Windows/Fonts/arial.ttf
```

Adicionar `--reuse-only` executa apenas o reaproveitamento do trecho já renderizado. O script usa uma fonte instalada para o teste local; projetos devem fixar seus próprios arquivos de fonte no catálogo.

O painel disponibiliza V2 quando o renderizador está configurado (`HYPERFRAMES_ENABLED` e `HYPERFRAMES_CLI_PATH`), com `STUDIO_ISOLATED_QUEUES_ENABLED=true`, e usa o planejador escolhido por capacidade. Gemini continua principal; o adaptador compatível recebe o mesmo contrato estruturado. Esta implementação não alterou credenciais nem ativou serviços pagos.

## O que impede declarar a entrega completa

1. Incorporar narração PT-BR utilizável e conferida para o roteiro. O registro de síntese está vazio neste ambiente; não foi criado outro sistema de voz nem reutilizada uma voz de um roteiro diferente.
2. Exercitar a direção com Gemini real e comparar objetivos/identidades usando os mesmos materiais. Não há chave configurada aqui; testes controlados de contrato não substituem esse ensaio.
3. Fazer audição integral e revisão humana de clareza, continuidade, ritmo e adequação da peça narrada. Inspeção de frames e testes numéricos não equivalem a essa revisão.
4. Qualificar o conjunto de combinações além dos exemplos produzidos. Tracking, rotoscopia, estabilização, troca de figurino, máscaras temporais e transformação generativa de filmagens continuam fora desta entrega.

O estado correto é **motor V2 implementado e em qualificação, com diagnósticos reais disponíveis**. Não é certificação de edição universal nem conclusão da peça narrada prevista no plano.
