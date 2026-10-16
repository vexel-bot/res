# Projeto disponível antes dos catálogos e auditorias

05/10/2026. O `refresh` de `useVideoStudio` esperava documento, ingestões e seis recursos de apoio no mesmo `Promise.all`. Uma consulta lenta atrasava o documento; uma rejeição impedia o carregamento completo. Isso tornava o editor dependente de consultas que não executam a composição.

O caminho principal agora carrega documento/ingestões, job associado e prévias reais antes de iniciar repertório, propostas assistidas, programa de produção, replanejamento e auditorias de capacidades/autonomia. Cada recurso de apoio publica sua resposta independentemente; erro deixa esse recurso indisponível e aparece com nome e diagnóstico. O projeto não recebe dados inventados ou autorização alternativa. Falhas do caminho principal continuam críticas.

Um contador de carregamento invalida respostas de uma atualização anterior ou de um projeto desmontado. A mesma verificação protege a publicação de metadados e a criação de URLs das prévias durante o carregamento. Não aborta nem promete cancelar solicitações já enviadas; impede que seus resultados substituam a tela atual. O caminho de render, os contratos canônicos, o backend e o renderer não foram modificados.

## Testes e interface real

[Oito testes](tests.txt), sem falhas ou skips: quatro novos casos de carregamento e quatro regressões de encaminhamento do render. Os novos casos comprovam disponibilidade antes de consultas lentas/falhas, propagação de erro crítico, ausência de publicação tardia de dados/avisos e ausência de consultas de apoio para um carregamento já invalidado. [Typecheck](typecheck.txt) passou. Fixtures unitárias exercitam falhas e concorrência; não demonstram qualidade audiovisual.

Observação real no laboratório existente, documento `0ae12fe1-c3aa-4f42-a764-33d076ade8cd`, revisão 2/versão 1. O documento e o asset vieram das APIs autenticadas normais. Apenas duas consultas de apoio foram abortadas localmente no navegador para testar a falha; não houve falha real atribuída ao servidor, nova geração, compra de API ou alteração editorial.

| Rodada | Resultado observado |
|---|---|
| [Falhas provocadas](fault-verified-collect.json) | Capacidades e autonomia indisponíveis, avisos específicos; documento, 12 linhas de camadas e controle de prévia disponíveis enquanto outros recursos ainda carregavam; primeiro frame decodificado observado depois |
| [Recuperação](recovered-verified-collect.json) | Interceptações removidas, clique em Atualizar mídias; seis recursos com HTTP 200, avisos removidos e prévia preservada |

Nos dois registros, as seis consultas começaram depois do término da transferência do MP4. Na rodada com falha: MP4 terminou em aproximadamente 1.675 ms desde o início da observação, recursos começaram em 1.723 ms e o indicador do projeto saiu de carregamento em 1.978 ms. Na recuperação: aproximadamente 538/571/641 ms. A observação iniciou antes do clique; esses números incluem o intervalo até o gesto, têm amostragem de 100 ms e condições de cache diferentes. Não são comparação antes/depois, p95 ou promessa de tempo de abertura. O carregamento geral da aplicação e consultas exigidas pelos outros painéis ainda podem atrasar a navegação. Na rodada com falha, o primeiro frame decodificado após a atualização só foi amostrado em 2.420 ms, depois de os apoios terminarem; na recuperação, em 781 ms. Portanto, os registros provam ordem de transferência e independência do projeto, mas não que o vídeo já estava decodificado antes de todas as respostas. O indicador “MP4 pronto para revisão” reflete o asset carregado e não mede o primeiro frame.

O MP4 observado conserva SHA `1b856b62acb23b07d488c1c6f9582af75fa5cf074f49c465cdab0a40d6943925`, 2.635.718 bytes, 1080 × 1920 e 15 s. Reutiliza a prova high anterior; não demonstra um novo render depois deste ajuste. A reprodução/exportação dessa prova foi registrada no [checkpoint anterior](../output-render-routing/README.md). Capturas: [falha](fault-ui.png) e [recuperação](recovered-ui.png). Observador passivo: [script](../../../../../scripts/validation/editor-project-loading-observe.ps1).

## Diagnósticos preservados

A primeira tentativa de injeção com `**/api/...` não aplicou as falhas: ambas as consultas retornaram HTTP 200. O registro [negativo](fault-tool-negative.json) foi retido e não conta como passe. A leitura do código da versão instalada, agent-browser 0.27.0, revelou que o matcher Rust só trata um asterisco como prefixo/sufixo; múltiplos asteriscos seguem comparação literal. [Fonte examinada](interception-actions-source.json), no [commit fixado](https://github.com/vercel-labs/agent-browser/blob/c830d1b67dc18b754e305859f0ae587f858a1447/cli/src/native/actions.rs#L6929). Com `*/api/...`, a injeção foi observada: status de rede 0 e `Failed to fetch` nos dois recursos, com os demais HTTP 200. Os quatro padrões de interceptação foram removidos. Nenhuma implementação da ferramenta foi portada para o produto.

Durante o desenvolvimento, Fast Refresh tentou conservar uma instância com a ordem antiga dos hooks após a inclusão de estados. A console apontou incompatibilidade de hooks; a verificação prosseguiu após navegação completa para a mesma URL, sem reiniciar servidores. Os registros qualificados vêm da instância montada com a fonte atual, com zero overlays de erro nas observações. O diagnóstico de desenvolvimento não foi usado como prova de falha de backend ou de render.

## Preservação e limite do aceite

[76 hashes atuais](sources.json); apenas `VideoStudio.tsx` e `useVideoStudio.ts` mudaram entre os 73 arquivos do checkpoint anterior. Seus backups exatos estão neste diretório; os outros 71 permaneceram iguais, incluindo backend/renderer. [Auditoria de estado](api-after.json): nove composições/assets/revisões e MP4s históricos preservados, documento ativo exatamente igual na API e três sessões cegas ainda `not_assessed`.

A correção comprova disponibilidade e diagnóstico desse caminho de carregamento. Não amplia capacidades de geração nem certifica estética, áudio, autonomia ou todos os fluxos de edição. Revisão humana dos estudos, duas outras linguagens na timeline real, três novos briefs após o aceite dirigido, integração/avaliação de geradores externos e limpeza recusada continuam pendentes. Não houve repetição da exclusão bloqueada pela revisão automática.
