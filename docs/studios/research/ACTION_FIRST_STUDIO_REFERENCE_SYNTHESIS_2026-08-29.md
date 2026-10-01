# Clicko Studios — pesquisa comparativa e decisão `action-first`

**Data:** 2026-08-29  
**Status:** decisão de produto aprovada para prototipação; validação humana pendente  
**Escopo:** experiência de criação, vídeo, avatar, edição assistida e integração com o stack open source  

---

## 1. Pergunta de pesquisa

Como fazer os Studios parecerem um laboratório de produção ativo, com menos informação passiva e
menos passos cognitivos, sem transformar geração de conteúdo em uma caixa-preta ou esconder
consentimento, custos, jobs, versões e revisão humana?

## 2. Método e limites

Foram inspecionadas superfícies públicas e documentação primária de Spiel, HeyGen, Runway e
Descript, além dos repositórios oficiais do OpenCut e HyperFrames. A análise separa:

- **observação:** comportamento visível ou documentado pela fonte;
- **inferência:** aplicação proposta para a Clicko;
- **limite:** capacidade anunciada, incompleta ou que não deve ser tratada como fato de produto.

Não foi feito benchmark de qualidade de geração nesta etapa. A pesquisa avalia arquitetura de
interação, não qualidade de modelo, latência ou custo real.

## 3. Evidência por referência

### 3.1 Spiel

Fonte: [Spiel — Avatars](https://www.spiel.video/avatars) e
[Spiel — página inicial](https://www.spiel.video/).

**Observado**

- a área de resultado domina a tela;
- um dock inferior concentra identidade/rosto, adição de material, prompt e ação de geração;
- o usuário começa por uma intenção e vê poucas decisões simultâneas;
- voz e imagem são apresentadas como capacidades próximas do resultado, não como configurações
  administrativas separadas.

**Limite**

- o AI Studio é apresentado como futuro; suas promessas de edição não provam um fluxo entregue;
- a simplicidade aparente não revela governança, direitos, versionamento ou recuperação.

**Inferência para a Clicko**

Usar a hierarquia visual “resultado primeiro + dock de próxima ação”, mas tornar contexto, estado,
consentimento e jobs honestos por meio de disclosure progressivo.

### 3.2 HeyGen

Fontes:

- [Quick Avatar Video](https://help.heygen.com/en/articles/12903996-quick-avatar-video)
- [AI Studio overview](https://help.heygen.com/en/articles/11049655-overview-our-new-ai-studio)
- [Video Agent](https://help.heygen.com/en/articles/12402907-how-to-get-started-with-video-agent)

**Observado**

- o caminho rápido segue avatar → roteiro → voz/movimento → gerar;
- o resultado rápido pode ser enviado a um Studio para refinamento;
- cenas e roteiro são a unidade de edição antes da timeline detalhada;
- ajustes que exigem nova geração são diferenciados de acabamento manual.

**Inferência para a Clicko**

Separar explicitamente “Gerar rascunho” de “Abrir controle dirigido”. O primeiro reduz tempo até o
resultado; o segundo preserva controle por cena e evita regenerar a peça inteira.

### 3.3 Runway

Fontes:

- [Creating with Runway Agent](https://help.runwayml.com/hc/en-us/articles/51601639579667-Creating-with-Runway-Agent)
- [Trimming and assembling clips](https://help.runwayml.com/hc/en-us/articles/52685547867667-Trimming-and-Assembling-Clips-in-Studio)
- [Creating with Edit Studio](https://help.runwayml.com/hc/en-us/articles/51683104370451-Creating-with-Edit-Studio)

**Observado**

- o agente planeja e executa, mas o resultado permanece editável;
- uma timeline permite cortar, reordenar, inserir material e desfazer/refazer;
- edições por prompt podem ser limitadas a uma região temporal selecionada;
- o usuário alterna entre intenção em linguagem natural e controle espacial/temporal.

**Inferência para a Clicko**

O comando do agente deve sempre declarar o alvo: peça, cena, camada, trecho ou seleção. A ação
default modifica o menor escopo seguro e cria comparação reversível.

### 3.4 Descript

Fontes:

- [Working with scenes and layouts](https://help.descript.com/hc/en-us/articles/10119710379917-Working-with-scenes-and-layouts)
- [Search Actions](https://help.descript.com/hc/en-us/articles/10164095817997-Search-Actions)

**Observado**

- roteiro/transcrição funciona como superfície de edição não destrutiva;
- cenas fazem a ponte entre narrativa e composição visual;
- propriedades aparecem conforme a seleção;
- busca de ações reduz a necessidade de memorizar onde cada ferramenta está.

**Inferência para a Clicko**

Roteiro, transcrição e cards de cena devem ser superfícies de edição de primeira classe. Uma Action
Palette acessível por teclado deve localizar tanto comandos quanto destinos sem duplicar navegação.

### 3.5 OpenCut

Fonte: [OpenCut](https://github.com/opencut-app/opencut).

**Observado**

- o projeto se posiciona como editor de vídeo open source;
- a reescrita anuncia núcleo Rust, API do editor, plugins, MCP, scripting e execução headless;
- o repositório separa a visão da reescrita do produto clássico.

**Limite**

- itens anunciados no roadmap não são dependências confiáveis do MVP;
- não será feito fork integral nem acoplamento do domínio Clicko ao estado interno do editor.

**Uso estratégico**

- referência e extração seletiva de padrões de timeline, snapping, seleção, atalhos, waveform,
  histórico de comandos e undo/redo;
- qualquer código incorporado exige revisão de licença, dependências e fronteira de adapter;
- o CreativeDocument e o MotionGraph continuam sendo a autoridade do produto.

### 3.6 HyperFrames

Fonte: [HyperFrames](https://github.com/heygen-com/hyperframes).

**Observado**

- projeto Apache-2.0 orientado a vídeo construído por agentes;
- representa cenas em projeto editável e busca render determinístico;
- combina HTML/CSS/media com animações navegáveis e renderização programática.

**Uso estratégico**

- adapter opt-in para preview e render de cenas programáticas;
- ponte entre decisão do agente, projeto editável e artefato reproduzível;
- não substitui o Studio Kernel, o pipeline FFmpeg nem os contratos de job/review.

## 4. Decisão de produto

O padrão canônico passa a ser o **Action-first Studio Surface**:

```text
Pedir → Ver rascunho → Refinar o menor escopo → Comparar → Fixar versão → Revisar
```

A tela começa pelo trabalho que pode ser feito agora. Explicações, proveniência, custo, provider,
jobs e políticas continuam disponíveis, mas aparecem no momento e no nível de detalhe adequados.

### 4.1 Hierarquia da superfície

1. **Context bar compacta** — projeto, documento, versão, save e job.
2. **Production Rail** — etapa atual, dependência e próximo gate humano.
3. **Stage dominante** — canvas, player, resultado, roteiro ou conjunto que está sendo produzido.
4. **Action Dock persistente** — pedido, alvo, contexto essencial e CTA primária.
5. **Inspector contextual** — apenas propriedades da seleção atual.
6. **Details drawer** — direitos, lineage, provider, custo estimado, logs e dados avançados.

O Stage e a próxima ação devem ocupar a maior parte da atenção. O Details drawer nunca abre por
padrão em um caminho rápido.

### 4.2 Três níveis de controle

| Nível | Quando usar | Superfície | Saída |
|---|---|---|---|
| **Rápido** | usuário quer chegar ao primeiro resultado | intenção, formato, identidade/voz opcional e materiais | storyboard ou preview privado |
| **Dirigido** | usuário quer orientar sem editar quadro a quadro | roteiro, cenas, cards, seleção e sugestões | versão editável por cena |
| **Pro** | acabamento preciso | timeline, tracks, waveform, keyframes e propriedades | versão pronta para Review |

“Mais controle” expande o mesmo documento; não cria outro produto, não perde contexto e não altera
provider por acidente.

### 4.3 Contrato do Action Dock

O dock possui no máximo:

- alvo atual: peça, cena, camada, trecho ou seleção;
- campo de intenção em linguagem natural;
- até quatro context chips essenciais: formato, identidade/rosto, voz e cenário/material;
- uma CTA primária, como `Gerar rascunho`, `Aplicar à cena` ou `Renderizar preview`;
- uma entrada `Mais controle`;
- estado compacto de custo estimado e job quando a ação for assíncrona.

Cada elemento interativo precisa de `actionId`. Sugestões sem contrato são texto, não botões.

### 4.4 Loop de refinamento

- o sistema apresenta o que entendeu antes de iniciar job caro ou irreversível;
- por padrão, uma mudança afeta apenas o menor alvo explicitamente selecionado;
- antes/depois e undo ficam disponíveis para mutações locais;
- regeneração total exige escolha explícita e informa custo/impacto;
- resultado gerado é rascunho privado até ser fixado em versão;
- Review sempre recebe uma versão imutável, nunca o estado vivo do editor.

### 4.5 Estados honestos sem poluir a tela

- `ready`: stage + próxima ação;
- `dirty/saving/saved`: status na Context bar;
- `queued/running`: mini job strip expansível;
- `recoverable-error`: mensagem junto da ação que falhou, preservando o pedido;
- `conflict`: comparação e escolha explícita;
- `forbidden/consent-required`: gate no ponto de uso, com motivo e saída segura;
- `offline/stale`: trabalho local identificado e publicação bloqueada quando necessário.

## 5. Composição com o stack open source

```text
Action Dock / cenas / timeline
            ↓
      Studio Kernel
            ↓
provider-neutral plans, CreativeDocument, MotionGraph, jobs e versões
     ↙           ↓             ↘
HyperFrames    FFmpeg       adapters de IA
programático   mídia/QC     voz/visão/avatar
     ↑                           ↑
OpenCut: padrões UX       Supervision: evidência visual
(sem fork do domínio)     (não é modelo generativo)
```

- **OpenCut:** repertório de interação de edição avançada.
- **HyperFrames:** render programático determinístico e projeto inspecionável.
- **FFmpeg:** ingestão, proxy, composição, encode, normalização e QC.
- **Supervision:** overlays e evidência de detecção no reality lane.
- **voz/avatar:** sempre atrás de contracts, consentimento, amostra privada e revisão.
- **modelos de planejamento/visão:** produzem planos e sugestões; não escrevem diretamente no
  documento nem escolhem provider na UI.

## 6. Aplicação por família de Studio

| Família | Stage inicial | CTA rápida | Controle dirigido | Pro |
|---|---|---|---|---|
| Editorial | roteiro/copy | gerar rascunho | blocos, claims e variações | estrutura e histórico |
| Visual | composição | propor layout | layers e alternativas | inspector e motion |
| Carrossel | conjunto | criar sequência | cards de slide/função | ordem, layers e conjunto |
| Vídeo | player/storyboard | montar primeiro corte | cenas, transcrição e B-roll | timeline/waveform/tracks |
| Presenter | amostra privada | gerar teste | performance, voz e cena | abrir no Video Studio |
| Reuse | origem + resultado | gerar derivações | receitas/canais | lote e regras |
| Factory | rodada | iniciar rodada | células, gates e exceções | fila/telemetria operacional |

## 7. Riscos e contramedidas

| Risco | Contramedida obrigatória |
|---|---|
| rapidez vira caixa-preta | resumo do plano, alvo e custo antes do job |
| dock fica congestionado | quatro chips no máximo; restante no inspector/drawer |
| usuário perde controle | níveis Rápido/Dirigido/Pro sobre o mesmo documento |
| IA regenera demais | menor escopo por padrão; regeneração total explícita |
| simplificação esconde direitos | gate contextual de consentimento e escopo |
| roadmap open source vira dependência | adapters e capability readiness; fallback FFmpeg |
| timeline domina usuários iniciantes | Pro fechado por padrão, mas alcançável em um clique |
| aparência de ação com botão vazio | Action Contract obrigatório em todo controle |

## 8. Hipóteses de validação

1. 80% dos participantes inicia uma peça de vídeo ou avatar no primeiro clique.
2. O primeiro preview é solicitado sem ajuda do moderador.
3. O participante consegue alterar apenas uma cena sem regenerar o vídeo inteiro.
4. O participante encontra timeline/controle Pro quando precisa de precisão.
5. Consentimento, custo e estado do job são compreendidos no ponto de decisão.
6. Nenhum participante confunde “preview privado” com conteúdo aprovado/publicado.

Essas hipóteses devem entrar nos protótipos de `10 — Prototype Tests` e no protocolo moderado. O
padrão só passa de protótipo para decisão validada após evidência de usuários reais.
