# Segmentação temporal e transformações locais automáticas — 08/11/2026

## Resultado

A Clicko executou, sem API de inferência, três operações reais sobre um vídeo de pessoa em movimento: segmentação temporal, geração de cenário e alteração de região. Cada job preparou os materiais, compôs o efeito, exportou o MP4 e salvou uma cópia editável com referências aos arquivos originais e derivados. O projeto de origem foi preservado.

O material de teste é um trecho previamente gerado com atriz fictícia, não um vídeo geométrico que simula uma pessoa. A geração desta etapa foi local; não foi uma nova chamada ao serviço que produziu a cena original.

**Custo adicional de API: US$ 0.** Nenhuma chave Anthropic foi cadastrada ou usada. Não houve fallback para OpenRouter, Anthropic ou outro provedor pago. Foi instalado um único peso RVM de aproximadamente 15 MB a partir da distribuição oficial; os pesos de difusão já estavam no computador.

## Como usar

1. Abrir um projeto canônico de vídeo.
2. Em **Produto, estratégia e copy do anúncio → Materiais do produto ou serviço e direção de edição**, adicionar o vídeo com papel **Apresentador** ou **Demonstração**, salvar e vincular a versão.
3. Abrir **Preparação automática e efeitos locais**.
4. Escolher vídeo, efeito e trecho. Para geração, escolher o ambiente.
5. Acionar **Preparar e executar localmente**. A Clicko acompanha o job, permite cancelamento e recupera o pedido após recarregar a página.
6. Visualizar o MP4 e abrir a cópia editável. O novo conjunto contém vídeo normalizado, máscara temporal, recorte PNG, candidato a cenário limpo e, para geração, o cenário ou região gerada.

A receita de texto atrás da pessoa passa a usar a máscara temporal quando disponível, em vez de aplicar a imagem recortada do primeiro quadro sobre todo o movimento.

## Mecanismos comprovados

| Operação | Preparação e execução | Evidência real | Limite de interpretação |
| --- | --- | --- | --- |
| Pessoa em movimento | RVM MobileNetV3 ONNX, quadros sequenciais, estados recorrentes reutilizados, matte FFV1 sem perdas | 144 quadros, 6 segundos; recorte renderizado pelo compilador canônico | Não comprova cabelo perfeito, seleção de uma pessoa entre várias ou segmentação de produtos segurados. |
| Novo cenário | Remove a pessoa do quadro de referência, prepara candidato de placa limpa, executa SD 1.5 img2img, revela o cenário atrás do vídeo original recortado | Job real, MP4, camadas editáveis, pesos verificados e relatório de difusão | O cenário gerado é uma imagem. Não é síntese temporal de vídeo nem reconstrução 3D. |
| Alteração localizada | Executa difusão e restringe o resultado a um retângulo normalizado com bordas suaves, preservando a pessoa sobre a região | 144 quadros; comparação dos pixels externos à região | Não faz tracking de câmera nem garante interação física plausível do novo conteúdo. |

O primeiro resultado generativo modificava também a bancada e enfraquecia o contato das mãos com os objetos. A versão final infere uma faixa inferior fixa com transição suave e preserva essa área da origem. É uma proteção de composição, não reconhecimento semântico de todos os objetos. Bordas da alteração localizada também foram suavizadas sem permitir vazamento para fora do retângulo.

## Critérios de revisão

- **Temporalidade:** máscara acompanha os movimentos, duração e contagem de quadros coincidem, cortes de cena reiniciam a memória quando detectados.
- **Identidade:** pessoa vem da origem; difusão não deve reconstruir seu rosto. Comparar olhos, cabelo, mãos e contorno em vários instantes.
- **Integridade:** logo, produto, objeto segurado e informação essencial não podem desaparecer com o recorte. O RVM é um modelo de pessoa; um produto pode exigir proteção adicional.
- **Contato:** mãos, bancada, chão e objetos mantêm relações compreensíveis. A proteção inferior reduz um defeito observado, sem aprovar automaticamente sombras/contato.
- **Região:** alteração fica dentro da área solicitada, sem caixa dura ou vazamento; a pessoa permanece no primeiro plano.
- **Cenário:** iluminação, escala e perspectiva são coerentes com a origem; rejeitar uma imagem bonita que prejudique a ação.
- **Reutilização:** materiais e máscaras ficam vinculados por escopo e origem, e a cópia abre no editor com suas camadas.
- **Custo:** inferência local, sem credenciais encaminhadas ao worker, sockets de saída bloqueados e sem fallback pago.

Resultados continuam como rascunhos com `reviewRequired: true`. Os testes técnicos não aprovam um anúncio nem comprovam fidelidade estética integral às referências do Instagram.

## Testes realizados

- Jobs pela própria aplicação: `segment_person`, `replace_background`, `localized_edit`; MP4s persistidos e baixados pelos endpoints autenticados.
- Galeria de 18 segundos exportada pelo fluxo de timeline/render-jobs da Clicko.
- Comparação de **todos os 432 quadros** dos três resultados finais com as respectivas fontes normalizadas e máscaras. A área opaca da pessoa foi comparada dentro da tolerância H.264, excluindo a faixa inferior protegida da medição de pessoa. A alteração regional também foi verificada fora de seu retângulo.
- A diferença RGB média da área opaca foi aproximadamente 1,2 em escala 0–255; tolerância funcional definida em 8. Isso comprova preservação técnica, não perfeição das bordas ou entendimento do anúncio.
- Navegador real: disparo de geração, acompanhamento do job, carregamento do MP4 e abertura da cópia editável passaram. O último passo foi repetido a partir da recuperação do job concluído. Apenas descoberta opcional de provedores/modelos foi isolada no teste; efeitos, downloads, persistência e navegação usaram a aplicação real.
- Testes de contrato, escopo, replay, erro de versão, máscara temporal, perfis CPU/GPU e ausência de credenciais no ambiente do worker passaram, além das regressões do renderer e do typecheck TypeScript.
- Um travamento inicial no subprocesso Python do Windows foi encontrado no caminho do servidor. A preparação passou a inicializar o runtime selecionado explicitamente, com entrada fechada e ambiente limitado; cancelamento/timeout encerra a árvore de processos pertencente ao job. O teste foi repetido com sucesso pela aplicação.

Os modelos foram executados em uma RTX 2050 de 4 GB, com 8 GB de RAM do sistema. A execução isolada de difusão mediu cerca de 3,1 GB de pico de alocação CUDA. Os relatórios distinguem tempo de segmentação/difusão de todo o tempo do job, que também inclui inicialização, verificações, composição e armazenamento. O perfil limita os trechos a 2–12 segundos e a maior dimensão a 640 pixels para este teste local.

## Evidências

Diretório: `C:/Users/edugu/OneDrive/Documentos/res/output/efeitos-automaticos-2026-11-08/`

- `clicko-efeitos-automaticos.mp4`: galeria final, 18 segundos.
- `segment_person.mp4`, `replace_background.mp4`, `localized_edit.mp4`: estudos finais separados.
- `evidence.json`: jobs, documentos, arquivos e relatórios locais.
- `pixel-verification.json`: comparação completa de quadros.
- `gallery-report.json`: documento/job da galeria.
- `contato-final.jpg`: amostras visuais a 0,2 s, 3 s e 5,7 s por efeito; essa revisão por amostras não equivale a playback humano integral.

Estado e teste de interface: `.codex-runtime/automatic-effects-20261108/api-state.json`, `ui-report.json` e `automatic-effects-ui.png`.

## Implantação e próximos limites

O código do backend, a interface e os workers estão integrados. Servidores sem pesos/dependências indicam indisponibilidade; não tentam baixar modelos durante a inferência. A instalação explícita é descrita em `workers/material-effects/README.md`.

A próxima qualificação deve usar mais pessoas, cabelos, roupas, iluminação e movimentos, incluindo contraexemplos com objetos segurados, oclusões e câmera móvel. A execução deste caso não permite generalizar a qualidade para todo vídeo. Transformação de figurino/corpo, objetos novos interagindo fisicamente e câmera 3D continuam fora do mecanismo comprovado aqui.

Fontes técnicas primárias: [contrato de inferência do RVM](https://github.com/PeterL1n/RobustVideoMatting/blob/master/documentation/inference.md) e [pipeline img2img do Diffusers](https://huggingface.co/docs/diffusers/api/pipelines/stable_diffusion/img2img). Modelo, revisão, checksum e licenças estão registrados em `workers/material-effects/models.lock.json` e no perfil SD 1.5 reutilizado.
