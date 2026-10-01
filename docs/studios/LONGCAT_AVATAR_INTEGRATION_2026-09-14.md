# LongCat Avatar 1.5 — estado da integração

## Estado atual

O res registra `longcat-avatar-1.5-ai2v-480p-int8-experimental-v1` como um
candidato de `avatar_video` para a operação `image_audio_to_avatar`. A integração
está preparada, mas o perfil permanece `unavailable`. Nenhum peso foi baixado,
nenhuma inferência foi executada e nenhuma infraestrutura foi contratada.

O pedido V2 exige uma imagem cadastrada na versão de identidade autorizada e um
asset separado contendo a fala final. Amostras usadas para cadastrar ou clonar a
voz são rejeitadas como áudio de condução. O pedido fixa checksums, revisão do
documento, cena, necessidade editorial, perfil, seed e parâmetros. A seleção
híbrida e o registro aprovado do provedor são fixados no job e revalidados antes
da execução.

## Limites do perfil

- Uma pessoa, plano médio, AI2V, 480p, 25 fps, INT8 e oito passos.
- Áudio final limpo; o separador vocal do demo oficial não integra este perfil.
- Um segmento contém 93 frames. Continuações acrescentam 80 frames porque 13
  frames são reutilizados. O res calcula duração produzida e corte final.
- Texto, logos, legendas, identidade visual e montagem continuam no compositor
  determinístico.
- Troca de fala invalida o avatar dependente. Mudanças apenas de tipografia,
  cor ou sobreposição recompõem sem inferência.

## Bloqueios atuais

O worker requer Linux/CUDA e o caminho oficial usa duas GPUs. A máquina atual não
tem RAM/VRAM compatíveis. Também faltam a imagem do worker com digest, o lock
Linux com hashes, a revisão de toda a cadeia de dependências, o runner de áudio
limpo e a qualificação visual em português.

O manifesto de modelo fixa as revisões oficiais e os checksums dos principais
arquivos binários. O preflight é somente leitura e verifica os arquivos antes de
importar PyTorch. O endpoint interno é autenticado e, no estado atual, responde
com `blocked_resources` antes de submissão ou download.

## Caminho de qualificação

A política em
`benchmarks/studios/identity/longcat-avatar-1.5-screening-policy.v1.json` começa
por um segmento nativo, avança para dez segundos, depois continuações de 30 e 60
segundos e só então avalia 720p. Corpo inteiro e duas pessoas são capacidades
separadas. Promoção comercial exige dez pessoas, trinta casos, revisão humana e
evidências de identidade, sincronismo em português, continuidade, falhas,
recursos e custo por minuto aceito.
