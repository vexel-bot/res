# Playbook — seis modelos visuais com HeyGem

## Decisão técnica

HeyGem será usado somente como mecanismo visual face-to-face e como referência de captura/fila. O fluxo Clicko não chamará o treinamento de voz do cliente HeyGem e não usará Fish Speech. O áudio de performance será entregue por um provider local separado.

No código auditado, o botão “Create Avatar” recebe um vídeo-base, copia esse vídeo para o diretório do modelo, extrai seu áudio e chama treinamento de voz. Na síntese, o serviço envia `video_url` e `audio_url` para `/easy/submit`. Isso significa que o “modelo visual” operacional é um vídeo-base versionado, não um conjunto independente de pesos faciais treinados pelo cliente.

## Casting fixo

- homens: Caio Vale, Davi Rocha e Kenzo Moura;
- mulheres: Lívia Reis, Aline Torres e Helena Sato;
- todos são personagens ficcionais originais;
- nenhum possui rosto materializado ainda;
- os seis estão em `pending_source_video`.

O roster tipado está em `ledgers/fixed-avatar-cast-2026-09-02.json`.

## Captura ou aquisição do vídeo-base

Cada slot exige um único vídeo:

- 12–20 segundos recomendados; mínimo técnico HeyGem de 8 segundos;
- exatamente uma pessoa adulta;
- 720p ou superior, MP4/MOV;
- rosto frontal, inteiro e desobstruído;
- cabeça sem inclinação extrema;
- mãos abaixo de boca, rosto e pescoço;
- luz suave e estável;
- fundo simples, mas com separação de pele e cabelo;
- postura sentada ou em pé definida pelo character bible;
- respiração e microexpressão naturais;
- sem cortes, zoom digital, filtros de beleza ou música;
- direitos e proveniência verificáveis.

Para o piloto R0, a regra é ainda mais estreita: **um vídeo-base total para um
único avatar**. O slot selecionado é `avatar-caio-vale`; não serão geradas
variações, imagens intermediárias ou vídeos adicionais antes do benchmark desse
arquivo. A decisão e o prompt ficam versionados em
`ledgers/single-avatar-pilot-caio-vale-2026-09-02.json`.

O vídeo pode vir de um performer contratado e consentido ou de geração sintética original com direitos compatíveis. Uma identidade de pessoa real nunca poderá ser transformada em personagem ficcional para contornar consentimento.

## Fluxo visual-only

```text
CharacterBibleV1
→ aprovação do casting
→ vídeo-base autorizado/sintético
→ ingest + checksum + inspeção facial
→ AvatarVisualSourceV1
→ benchmark privado HeyGem
→ áudio local aprovado
→ /easy/submit (video_url + audio_url)
→ QC facial/labial/temporal
→ revisão humana
→ versão de identidade ativa
```

## Conselho cinematográfico aplicado

- Duffer Brothers, `I1`: cada membro do ensemble tem competência, pressão e função distintas; o avatar é escolhido antes de travar comportamento.
- Denis Villeneuve, `I1`: escala, enquadramento, luz e ambiente recebem função; não há colagem aleatória de referências.
- David Fincher, `I1`: performance é calibrada por objetivo, eyeline, pausa e microcomportamento, não por adjetivos genéricos.
- Steven Spielberg, `I1`: reação, clareza emocional e caminho do olhar dão acesso humano ao assunto.

Essas são traduções operacionais baseadas em evidência pública, não imitações de personalidade ou estilo protegido.

## Bloqueios atuais

- nenhum dos seis vídeos-base existe;
- Docker Desktop não respondeu como daemon durante o preflight;
- a máquina possui RTX 2050 com 4 GB de VRAM, abaixo do hardware recomendado pelo projeto e abaixo das receitas comunitárias de 8 GB citadas no próprio README;
- o container `guiji2025/heygem.ai` contém o backend/modelo principal fora do repositório auditado;
- a licença comunitária exige autorização separada acima de 1.000 usuários mensais;
- a cadeia de container/pesos ainda não tem SBOM nem licença completa;
- nenhum provider será ativado ou vídeo sintetizado enquanto esses gates estiverem abertos.
- o Google AI Studio marca Gemini Omni 1.1 Flash e Veo 3.1 como `Paid`, e a
  conta inspecionada não possui projeto Cloud disponível; portanto, a chamada
  externa permanece bloqueada pelo teto de gasto de USD 0.

## Teste de aceitação de cada avatar

- identidade estável em 24 casos privados;
- boca sem deformação, jitter ou teeth artifacts;
- piscadas, olhos e cabeça temporalmente estáveis;
- pele e cabelo sem mudanças de textura;
- gesto e eyeline coerentes com o performance plan;
- sincronização labial PT-BR;
- nenhuma voz extraída ou treinada pelo HeyGem;
- checksum e lineage do vídeo-base e do áudio local;
- disclosure de conteúdo sintético;
- exclusão e revogação testadas antes da promoção.
