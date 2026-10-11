# Implementação experimental do Alight Motion — 01/10/2026

**Foi implementada a base comum e a infraestrutura experimental. O Alight não foi promovido a motor principal.** A execução no aplicativo, o compilador de projeto e a avaliação estética continuam pendentes de um Android físico e da prova mínima de importação/exportação.

## Entregas desta implementação

- Nove fichas no repertório existente, com fonte, classificação da evidência, função perceptiva, materiais, parâmetros, contraindicações, correções e qualificação por motor/versão. Todas as fichas novas permanecem conhecimento; nenhuma foi marcada como tutorial assistido ou render verificado.
- Receitas tipadas, vinculadas à cena e aos elementos, persistidas no CreativeDocument antes dos hashes. Snapshot do job, pacote e recibo preservam os vínculos. Defaults vazios mantêm a forma de serialização dos contratos antigos.
- Provider `alight-motion.contextual-v1` condicionado à flag, Android físico, perfil, versão e calibração. O compilador/importador real não foi inventado. O pacote interno não é XML do Alight.
- Worker local com bloqueio exclusivo, timeout, uma repetição de erro transitório identificado, confirmação de etapa, journal, observações duráveis, logs, cancelamento, quarentena e validação de retomada. Sem driver validado, permanece indisponível.
- Recuperação visual silenciosa vinculada a job/checksum, probe e finalização FFmpeg. O áudio do aplicativo é recusado. Tempos e geometria planejados não são apresentados como medição.
- Endpoints experimentais owner/admin de capacidades, campanhas, casos, trials, comparações e promoção, no prefixo existente. Dados ficam em eventos imutáveis do Studio; não foi criada outra base de conhecimento ou banco de campanhas.
- Painel do Studio com motor vinculado, pendências, custo compartilhado e indicadores separados de técnico, visual e autonomia. Sessões de comparação usam versões congeladas, rótulos cegos e revisão humana existente. Não há notas preenchidas automaticamente.
- Registro dos trials antes da execução, na mesma transação do job. Falhas não podem ser escondidas inscrevendo apenas sucessos; um caso fica congelado depois de iniciar sua coorte. Revogação da revisão humana, mudança de revisão, material ou checksum invalidam evidência.
- Briefs dos três estudos e roteiro de qualificação em `workers/alight-motion`. São documentos de planejamento, sem projetos comerciais ou resultados artificiais preenchidos como sucesso.

## Situação por etapa do plano

| Etapa | Situação | Evidência faltante |
|---|---|---|
| Biblioteca, receitas, API e painel | Implementados em software experimental | Estudos e execução das técnicas no app |
| Descoberta oficial | Pesquisa documental registrada | Interface oficial utilizável não identificada; nenhuma execução oficial comprovada |
| Projeto mínimo e perfil | Procedimento e admissão preparados | Android físico, projetos editáveis reais e calibração |
| Worker e compilador | Orquestração e tratamento de falhas implementados | Driver UI e compilador baseados em estrutura real homologada |
| Três peças, controles e comparações | Briefs e fluxo preparados | Materiais, exports reais e avaliações humanas |
| Trinta jobs e promoção | Critérios implementados | 30 jobs reais, 29 automáticos, p95, recuperação e integridade |

Sem esses itens não existe prova de melhora visual, fidelidade de importação ou autonomia do aplicativo. Um vídeo manual futuro poderá ser referência de aparência; não contará como job automático.

## Consulta real do ambiente

`python workers/alight-motion/worker.py probe` retornou `available: false`, capacidades vazias e pendências `adb_unavailable`, `physical_device_missing`, `device_profile_missing`, `validated_import_missing`, `validated_compiler_missing`. Isso significa que nenhum Android está disponível **ao worker**; sem ADB ele não inventa observações do aparelho.

O [recibo desta implementação](research/ALIGHT_MOTION_IMPLEMENTATION_RECEIPT_2026-10-01.json) registra gasto incremental de APIs de US$ 0, nenhuma compra e zero jobs reais do Alight. O saldo da fase é consultado no ledger compartilhado do Studio; não foi presumido um saldo a partir da ausência de chamadas nesta etapa.

## Regras de comparação e promoção

A comparação de fidelidade aceita duas variantes, Alight e Remotion, do mesmo briefing e materiais, com direção/receita idêntica limitada a capacidades compartilhadas. A comparação editorial aceita três variantes: Alight dirigido, Remotion atual e controle FFmpeg simples. O ganho da segunda não é atribuído exclusivamente ao motor.

As referências congelam documento, revisão, asset e checksum. O backend reconfere origem, fontes autorizadas, snapshot, QC, saída 15 s / 1080×1920 / 30 fps e áudio. Uma sessão obsoleta não aprova a campanha. Na revisão, os motores ficam sem identificação; chegar ao fim por seek não comprova reprodução completa. O revisor confirma leitura em celular, comparação cega, controle e intervenções registradas.

Cada linguagem exige revisão visual humana de pelo menos 4/5 em clareza, ritmo, continuidade e acabamento, mais preferência cega pelo Alight e fidelidade confirmada. Ação e produto exige oito segundos de ação dentro da imagem. QC técnico não preenche nota nem preferência.

A coorte exige dez jobs por linguagem, pelo menos 29 sucessos automáticos entre os 30, p95 de até 600.000 ms incluindo render/finalização, recuperação transitória real e integridade entre jobs. Todos os recibos precisam pertencer ao perfil atual e ao vídeo final correspondente. Mocks não contam. Promoção é evento explícito, restrito aos perfis e a novos documentos; projetos antigos conservam o vínculo. Dispositivo ocupado não dispara outro motor.

## Validação de software

Os resultados finais de testes estão registrados no recibo. A cobertura inclui contratos antigos, receita/hash, caracteres/fontes nos fluxos existentes, trim com fps distintos, masks/overlap, ausência de assets, checksums, acesso, fonte/revisão obsoleta, inscrição da coorte, leitura visual independente de QC, dispositivo ocupado, falha desconhecida, cancelamento, timeout, exportação antiga e evidências persistidas. Drivers simulados testam estas fronteiras; seus outputs não foram usados em uma campanha real.

Validação final: 46 testes focados de backend aprovados e um teste adicional de capacidade aprovado; dez testes de navegador aprovados; TypeScript, build e lint das novas unidades aprovados. A regressão ampliada registrou 143 aprovações e uma falha de fixture, corrigida e aprovada na repetição focada. Esses números são execuções de teste, não jobs de qualificação do Alight.

Falhas de teste foram auditadas antes de alteração: fixture sem especificação obrigatória de saída; harness isolado tentando carregar o preâmbulo do Vite; uso de locator que não correspondia ao nome acessível; referência a vídeo local inexistente. As fixtures foram corrigidas e a reprodução de teste passou a usar um pequeno MP4 gerado localmente, declarado exclusivamente como fixture.

Durante revisão de código também foram corrigidos: estado `completed` incompatível com os jobs reais (`succeeded`), hash de receitas ausente no consumidor de render, inscrição após commit que permitiria corrida de coorte, permissão por caminhos internos/generic jobs, repetição genérica de erros desconhecidos e persistência de aprovação depois da revogação das notas humanas.

Os testes adicionais também identificaram uma recusa do novo provider no contrato genérico de jobs e um import ausente na checagem de permissão interna. Ambos foram corrigidos e os testes afetados passaram. Componentes nativos e efeitos precisam de suas capacidades exatas no perfil; não basta o dispositivo estar conectado.

## Próxima execução necessária

O primeiro trabalho dependente do ambiente é a prova mínima em Android físico, descrita no [README do worker](../../workers/alight-motion/README.md). Ela produzirá o formato editável, referências, perfil e observações para implementar o compilador e os seletores. Em seguida, aplicar os [três briefs](../../workers/alight-motion/qualification-cases.json), produzir variantes/controles e executar as revisões e a coorte.

Para a direção, consultar a [biblioteca de técnicas](ALIGHT_MOTION_TECHNIQUES.md). Para as fontes e os limites de interface oficial, consultar a [pesquisa](research/ALIGHT_MOTION_ASSESSMENT_2026-10-01.md). Nenhum serviço externo foi instalado, nenhum emulador foi incluído e nenhuma compra foi feita.
