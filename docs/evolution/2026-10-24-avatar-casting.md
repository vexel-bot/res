# Aparência e narração independentes na geração de avatar

Data: 24 de outubro de 2026.
Estado: vínculo implementado; inferência generativa em andamento.

## O que mudou

O pedido de avatar com imagem e fala final (contrato V2) aceita uma pessoa ou
um personagem como aparência, acompanhados por outra voz autorizada ou uma voz
licenciada. Cada versão mantém sua própria autorização. A autorização da
aparência não substitui a da pessoa que forneceu a voz.

O elenco salvo no documento não pode ser trocado silenciosamente por um job.
As duas referências são congeladas no vínculo de execução e registradas no
arquivo resultante. Antes de retornar um resultado existente ou registrar uma
nova entrega, o servidor confere novamente as versões e as autorizações.

Se a voz for revogada ou o documento mudar durante a execução, o resultado
não é incorporado à biblioteca. A revogação também impede reutilizar um
resultado anterior como se ainda estivesse autorizado.

## Áudio final e voz escolhida

Uma fala sintetizada precisa corresponder ao roteiro, à duração e à versão
da voz selecionada. O tipo de origem distingue voz clonada de voz licenciada.
A amostra de cadastro continua proibida como substituto da fala final.

Para sintetizar com uma voz licenciada cadastrada, sua versão aprovada precisa
registrar o provedor e o timbre em `pronunciationProfile.synthesisBinding`.
Sem esse vínculo, o servidor não atribui a outro timbre o nome dessa voz.
O contrato anterior de avatar permanece compatível com seu vínculo original
de apresentador e voz da mesma pessoa.

## Cobertura e limites

Os testes exercitam as quatro combinações de aparência e voz, autorização
independente, procedência do áudio, reabertura do resultado, divergência de
elenco e alterações durante a execução. O provedor desses testes é simulado:
isso valida o fluxo de dados e permissões, não a qualidade de um modelo.

Esta atualização não instala pesos nem habilita inferência no computador.
LongCat e os candidatos de clonagem de voz continuam dependendo de runners,
recursos e validação de saída. A produção de vídeo com elenco no departamento
criativo ainda não está liberada. O uso do retrato existente em imagem pelo
PhotoCraft segue disponível para versões elegíveis.

## Evidência

- `backend/app/services/studios/casting.py`
- `backend/app/services/studios/jobs.py`
- `backend/app/services/studios/avatar_video.py`
- `backend/app/services/studios/speech.py`
- `backend/tests/test_avatar_independent_cast.py`
