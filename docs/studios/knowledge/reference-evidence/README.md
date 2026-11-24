# Evidências visuais consultáveis

As quatro folhas foram copiadas sem alteração dos artefatos locais observados em 12/11/2026. O catálogo versionado `backend/app/services/studios/craft_reference_evidence.v1.json` registra os hashes, autoria, URL e cobertura de cada uma.

- `paulo-contact-play.jpg`: amostras visuais válidas de @paulo.ia. A antiga folha `paulo-contact.jpg` não faz parte deste pacote.
- `creators-contact.jpg`: amostras de @creators, com crédito a @martsromero.
- `moonsol-contact.jpg`: amostras da colagem e do tutorial de @moonsol.design; não tratar a duração do tutorial como cadência de um anúncio.
- `orbita-independente-quadros.jpg`: resultado interno considerado progresso pelo proprietário. Não é aprovação final; o vídeo original é silencioso, tem pico luminoso próximo de 8 s e exigiu recuperação manual de exportação.

As folhas externas são **evidências de análise**, sem autorização de uso como cenas de produção. Os tempos solicitados são marcos aproximados; quadros esparsos não comprovam movimento fino, cortes exatos ou áudio.

A ferramenta `inspect_reference` resolve apenas IDs do catálogo controlado. Ela registra cada evidência como ativo de análise no workspace autorizado, verifica os hashes e retorna o texto de cobertura e a imagem real. A operação não anexa os ativos ao projeto, não os insere no manifesto de mídia de produção e não invoca API paga.
