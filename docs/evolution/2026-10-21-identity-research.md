# Personagens, rosto e voz — pesquisa e direção de implementação

## Objetivo recebido

Clonar rosto e voz autorizados, oferecer personagens com aparência e voz pré-selecionadas e permitir seu uso na imagem ou no vídeo escolhido pelo cliente. A documentação da evolução deve aparecer no sistema antes desta integração.

## Auditoria inicial em 21/10/2026

- Existem perfis e versões de identidade, voz, consentimento, avaliação e revogação.
- Há seis posições de catálogo de personagens; elas são candidatos, não seis personagens já produzidos e qualificados.
- O transporte LongCat 1.5 já existe, com hashes e um worker separado. O manifesto indica pesos não instalados e perfil indisponível.
- A sala atual ainda não conecta uma escolha reutilizável de aparência e voz à peça.
- O ambiente inspecionado contém uma RTX 2050 com aproximadamente 4 GB de VRAM. Isso não comprova capacidade para executar os perfis generativos pesquisados.

## LongCat: versão e responsabilidade

Em 21/10/2026, o repositório oficial consultado ainda apresenta Avatar 1.5 como sua atualização de avatar. A revisão HEAD observada foi 6b3f4b8582a8bc3f20f795735f5383716c4ba794, igual à registrada no adaptador existente. Não foi confirmada uma versão Avatar posterior nas fontes oficiais consultadas. Ausência nessa consulta não prova ausência em todos os canais.

LongCat recebe imagem e áudio para produzir uma performance em vídeo. Ele não substitui um sintetizador que aprende ou reproduz a voz de uma amostra e não é o motor para inserir uma pessoa em uma imagem estática. O fluxo documentado inclui modo destilado, INT8 e exemplos distribuídos em duas GPUs. A receita vLLM-Omni mostra uma alternativa de GPU única, com medições próprias; isso não é evidência de desempenho Clicko.

## Comparação de candidatos

### LongCat-Video-Avatar 1.5

Função: avatar dirigido por áudio, continuação e possibilidades de personagens estilizados. Código MIT no upstream consultado. Candidato para performance em vídeo, reaproveitando o adaptador existente; permanece sem inferência validada neste ambiente.

Fonte: https://github.com/meituan-longcat/LongCat-Video

Modelo: https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5

Receita alternativa: https://github.com/vllm-project/vllm-omni/blob/main/recipes/meituan-longcat/LongCat-Video-Avatar-1.5.md

### Qwen3-TTS

Função: modelos Base para clonagem, CustomVoice para timbres prontos e VoiceDesign para desenho de voz. O projeto declara português entre dez idiomas e versões 0.6B/1.7B; código Apache-2.0. Candidato para voz reutilizável. A presença de português não prova sotaque brasileiro, pronúncia de marcas ou fidelidade de identidade no nosso caso.

Revisão consultada: 022e286b98fbec7e1e916cb940cdf532cd9f488e.

Fonte: https://github.com/QwenLM/Qwen3-TTS

### Chatterbox Multilingual V3 e pacote PT-BR

Função: clonagem por referência e síntese multilíngue. O upstream declara pacote específico para português brasileiro, modelo de 0.5B e código MIT. Já existe trabalho de integração desse candidato no repositório Clicko. Deve ser comparado ao Qwen3-TTS com o mesmo roteiro, referência e avaliação, preservando watermark e condições dos pesos.

Revisão consultada: 5de7a54aa4e5e2baadb0182dde554908b48b85c2.

Fonte: https://github.com/resemble-ai/chatterbox

### CosyVoice

Função: síntese e clonagem multilíngues com controles de inferência. O projeto oficial consultado redireciona de FunAudioLLM para QwenAudio; código Apache-2.0. Alternativa de comparação, sem assumir equivalência de português e PT-BR nem ativação automática.

Revisão consultada: 074ca6dc9e80a2f424f1f74b48bdd7d3fea531cc.

Fonte: https://github.com/QwenAudio/CosyVoice

### SoulX-FlashHead

Função: retratos falantes com variantes de execução e proposta de streaming; projeto de 1.3B, código Apache-2.0. Alternativa especializada para planos de retrato, não substituto comprovado de cenas com corpo, objetos e múltiplos personagens. Comparar identidade e oclusões; velocidade anunciada pelo autor não foi reproduzida aqui.

Revisão consultada: 9bc03de06bb0de82cd6bc477804512ae06144bf2.

Fonte: https://github.com/Soul-AILab/SoulX-FlashHead

### Wan2.2 S2V

Função: geração de vídeo dirigida por fala. Código do repositório Apache-2.0. Alternativa para comparar movimento, obediência à direção e preservação de aparência. Não faz clonagem de voz por si só. O tamanho e o custo precisam ser medidos por perfil; não será escolhido apenas por popularidade.

Revisão consultada: 1ea34ff48f87168174e12956e200b1d908b1c5ff.

Fonte: https://github.com/Wan-Video/Wan2.2

### Qwen-Image / Image-Edit

Função: geração e edição condicionadas por imagens, incluindo preservação de características do personagem. O repositório anuncia Qwen-Image-2.0 e aponta Image-Edit-2511 com melhorias de consistência; código Apache-2.0. Anúncio de família e disponibilidade de pesos são coisas distintas: fixar o modelo efetivamente acessível e sua licença antes de instalação. É o candidato a estudar para inserir a identidade visual na peça estática, em vez de tentar usar LongCat para imagens.

Revisão consultada: 6b5e1f5cec987d404be5ac6657db3b9aacb56a89.

Fonte: https://github.com/QwenLM/Qwen-Image

Modelo de edição: https://huggingface.co/Qwen/Qwen-Image-Edit-2511

### Fish Speech / Drama 3 / S2-Pro

Função: vozes expressivas e múltiplos falantes. O projeto consultado já apresenta Drama 3 e distingue sua licença Community da Research para S2-Pro. Não assumir que os pesos estão sob uma licença permissiva equivalente a MIT/Apache; não promover automaticamente para o SaaS comercial. Manter como comparativo documental até a cadeia de uso estar resolvida.

Revisão consultada: 541566932abbaebcb0a40e562a1f846738383f38.

Fonte: https://github.com/fishaudio/fish-speech

## Decisão técnica provisória

Não há vencedor comprovado sem uma avaliação no nosso público e idioma. Reaproveitar os contratos existentes: identidade visual autorizada, voz independente, geração de uma performance e inserção na peça. LongCat continua candidato de vídeo; Chatterbox PT-BR e Qwen3-TTS são os candidatos prioritários de voz; Qwen Image-Edit é candidato de imagem. Os Crafts continuam responsáveis por montagem e composição da entrega.

## Experiência requerida

- Biblioteca única com Minhas identidades, Personagens e Vozes.
- Rosto e voz cadastrados de forma independente; ter apenas um deles não deve exigir criar o outro.
- Escolha de aparência no pedido de imagem, carrossel ou vídeo.
- Escolha de voz para narração, diálogo ou apresentação em vídeo; uma imagem estática não produz fala.
- Escolha do material e da cena onde o personagem aparecerá, com posição e intenção, preservadas no projeto.
- Visualização e audição das amostras reais, sem preencher um catálogo fictício como se fosse operacional.
- O cadastro preserva amostras; gerar uma réplica é uma operação posterior, com versão e artefato próprios.

## Critérios de comprovação

- Criar uma identidade autorizada e uma voz, salvar, fechar e reabrir.
- Escolher personagem e material alvo e demonstrar a inserção na imagem e no vídeo.
- Gerar fala nova em PT-BR a partir de referência e conferir completude, pronúncia e semelhança.
- Avaliar sincronismo, continuidade de rosto, dentes, olhos, mãos e interação com objetos.
- Registrar revisão exata do modelo, dependências, pesos, checksum, duração, consumo e falhas.
- Revogar autorização e comprovar que novos usos e trabalhos dependentes são bloqueados.

## Pendências mantidas abertas

Conectar as escolhas aos projetos e operações de geração; finalizar os runners; instalar e qualificar pesos; disponibilizar personagens reais com ativos e direitos próprios; demonstrar os fluxos finais com hardware compatível. Nenhum peso foi baixado ou GPU externa contratada por esta pesquisa. A documentação de fornecedor é evidência de interface e alegação do fornecedor, não um benchmark próprio.


## Continuidade em 24/10/2026

A biblioteca e a seleção de versões foram implementadas nesta branch depois da auditoria inicial. A composição com retrato em imagem e a associação de voz não substituem a geração de novas cenas ou a clonagem sintetizada. O registro de 24/10/2026 discrimina o comportamento implementado e a integração generativa que ainda precisa ser concluída.
