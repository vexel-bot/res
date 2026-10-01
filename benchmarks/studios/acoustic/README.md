# Qualificação acústica do Studio

Esta pasta contém a política de produto e os contratos de evidência para detectar presença de fala e música no MP4 final. Ela não contém áudio e não qualifica nenhum detector hoje.

O fluxo promocional é fail-closed:

1. a política precisa estar `approved` e vinculada por digest;
2. o corpus privado precisa cobrir `natural_only`, `speech`, `music`, `speech_music` e `silence`, com direitos verificados e bytes conferidos sob um `asset-root` explícito;
3. a execução precisa estar vinculada ao provider, modelo, worker manifest, revisão de licença, conversão e avaliador por SHA-256;
4. o verificador recalcula matrizes de confusão, taxas de falso positivo/negativo e inconclusivos por caso;
5. somente uma avaliação `passed` pode receber um recibo HMAC; o segredo permanece fora do repositório;
6. o backend exige o recibo íntegro e sua identidade exata no provider e no modelo antes de expor a capacidade.

Comando de avaliação (não altera o registry):

```powershell
$env:STUDIO_ACOUSTIC_PROMOTION_HMAC_SECRET = '<segredo-de-release-com-32-ou-mais-caracteres>'
python backend/scripts/evaluate_acoustic_qualification.py `
  --backend backend `
  --policy benchmarks/studios/acoustic/acoustic-presence-ptbr-policy.v1.json `
  --corpus C:\private-benchmark\corpus.v1.json `
  --run C:\private-benchmark\candidate-run.v1.json `
  --asset-root C:\private-benchmark\assets `
  --signer-key-id acoustic-release-key-2026-08 `
  --receipt-output C:\private-benchmark\promotion-receipt.v1.json
```

O arquivo de política está deliberadamente em `draft`. Ainda faltam corpus autorizado e representativo, revisão formal dos limites, execução candidata, licença, worker real e assinatura de release. Portanto, o registry de produção continua vazio e o botão de análise permanece indisponível.
