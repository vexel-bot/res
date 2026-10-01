# res — plano revisado para qualificar o difusor local

Data: 10 de setembro de 2026. Estado: planejamento após inspeção de código, hardware e fontes primárias; nenhuma inferência executada nesta análise.

## 1. Decisão de produto

O difusor é uma entrega necessária do res. Um impedimento de hardware mantém essa entrega pendente; não a transforma em funcionalidade opcional concluída.

O objetivo inicial é o sistema gerar, avaliar e incorporar um trecho visual útil de aproximadamente 1–2 segundos por inferência local. Um endpoint, um teste simulado ou uma sequência de frames sem utilidade editorial não atendem ao objetivo. A qualificação será específica por modelo, operação, resolução e classe de cena.

Preservar direção agnóstica de LLM, HyperFrames, FFmpeg, FastAPI e Celery/Redis. O difusor produz materiais; a composição controla textos, logos obtidos, timing e montagem. O diretor escolhe quando gerar e o que preservar. Não haverá treinamento de modelo, aluguel de GPU, dependência de Oracle para inferência ou fallback pago automático. O teto de US$1 continua aplicável ao conjunto das eventuais chamadas do piloto, incluindo planejamento e crítica.

## 2. O diagnóstico anterior não demonstra impossibilidade

Inspeção em `workers/media-generation-local/`:

| Evidência no código atual | Consequência | Correção planejada |
|---|---|---|
| Manifesto exige 8.192 MiB de VRAM e 12.288 MiB de RAM | Reprova a máquina antes do experimento de offloading | Admissão por perfil e estimativas explícitas de pico, depois medições; não apenas reduzir constantes |
| Seleção Wan contabiliza 28.935.465.418 bytes de download | A combinação atual exige cerca de 39,64 GiB livres com margem e reserva | Selecionar somente componentes, precisão e variantes necessários; incluir instalação e temporários separadamente |
| Preflight mede `.model-cache`, mas `snapshot_download` usa cache padrão | A verificação pode não corresponder ao disco utilizado | Um único diretório configurado para download, carregamento e offload; medir todos os volumes envolvidos |
| `requirements.lock` contém somente comentários | Worker ainda não possui instalação reprodutível | Resolver dependências no ambiente isolado e gerar lock instalável com hashes |
| Contrato aceita somente o perfil Wan e retorna sempre 33 frames | Modelo não é substituível; duração pedida não determina a saída | Registro de perfis e contrato V2, preservando o contrato V1 |
| `api.py` usa `os.kill(pid, 0)` como consulta de existência | No Windows essa chamada pode terminar o processo | Substituir por consulta não destrutiva e identidade de processo; testar antes de inferir |
| Lease pode ser removido enquanto `process.json` ainda não existe | Há janela para iniciar duas tarefas pesadas | Estado de inicialização atômico, posse e heartbeat |
| Cancelamento registra sucesso mesmo sem confirmar término | Pode liberar GPU ainda ocupada ou atingir PID reutilizado | Verificar identidade, término e posse antes de liberar recursos |

A documentação do Wan informa 8,19 GB para o caminho divulgado; isso não estabelece o mínimo físico de toda configuração otimizada. Também não prova que 4 GB bastem. [Wan 2.1](https://github.com/Wan-Video/Wan2.1)

A semântica de `os.kill` difere no Windows: sinais diferentes dos eventos de console documentados usam terminação de processo. Essa é uma correção anterior aos testes de GPU. [Python](https://docs.python.org/3/library/os.html#os.kill)

## 3. Recursos observados e regra de admissão

Leitura desta análise: i5-12450H, RTX 2050 com 4.096 MiB de VRAM total e 3.962 MiB livres; RAM física total de aproximadamente 7,73 GiB e apenas 253 MiB disponíveis; disco C: com aproximadamente 23,31 GiB livres. Disponibilidade é uma fotografia da sessão, não característica permanente. A memória comprometida/paginação será medida separadamente; memória virtual não equivale a RAM rápida disponível.

Não iniciar inferência com essa pressão atual de RAM. Primeiro inventariar processos do próprio res e serializar render, inspeção pesada e geração, descarregando somente componentes controlados pelo sistema. Não encerrar aplicativos do usuário, apagar arquivos pessoais ou alterar paginação. Se ainda faltar memória, expor a necessidade concreta e manter a execução aguardando recursos.

Dois preflights independentes:

1. **Instalação:** somar arquivos exatos dos modelos, dependências instaladas, wheels temporários, cache, eventuais cópias no Windows e arquivos de offload. Preservar pelo menos 10 GiB livres. Um manifesto incompleto não autoriza download.
2. **Execução:** medir RAM disponível, memória comprometida, VRAM livre, disco temporário, driver, runtime CUDA e compatibilidade de dtype. Separar picos de carregamento, codificação de texto, denoising, VAE e verificação.

O primeiro perfil ainda não terá pico medido: utilizar estimativa conservadora documentada e um processo monitorado de calibração. Proposta inicial de reserva operacional: 1,5 GiB de RAM física e 512 MiB de VRAM fora do orçamento do worker, ajustável somente com evidência. O monitor deve poder terminar a árvore do worker ao aproximar-se das reservas; isso reduz risco, mas não garante ausência de OOM por alocação súbita.

Depois da calibração, a admissão usa o maior pico observado, margem declarada e recursos disponíveis. Registrar `blocked_current_load`, `blocked_storage`, `unsupported_runtime`, `out_of_memory` e `deadline_exceeded` distintamente. Uma carga momentânea ou instalação incompleta não implica `hardware_incapable`.

## 4. Seleção dos candidatos

### Primeiro candidato: AnimateDiff-Lightning com base SD 1.5

Hipótese: uma base menor e encoder de texto menor oferecem um experimento mais plausível que carregar o conjunto Wan atual. É uma hipótese de viabilidade, não promessa de qualidade profissional nem de suporte a qualquer cena.

O autor disponibiliza adaptadores destilados de 2, 4 e 8 passos; usar primeiro o de 4 passos com seu scheduler e parâmetros correspondentes. Não trocar scheduler ou reduzir passos arbitrariamente. [ByteDance](https://huggingface.co/ByteDance/AnimateDiff-Lightning)

Inventário de metadados consultado, sem baixar pesos:

| Componente candidato | Bytes de pesos selecionados |
|---|---:|
| Adaptador Lightning 4 passos | 907.702.248 |
| SD 1.5 UNet fp16 | 1.719.125.304 |
| Encoder de texto fp16 | 246.144.864 |
| VAE fp16 | 167.335.342 |
| Verificador de conteúdo fp16, quando integrado ao fluxo | 608.018.440 |
| Total desses pesos | 3.648.326.198 |

O total não inclui tokenizer, configurações, dependências, temporários, ativações ou cópias de carregamento. Portanto não é estimativa de RAM/VRAM. O inventário completo deve manter as verificações de conteúdo do pipeline e evitar carregá-las simultaneamente quando puderem operar em etapa separada.

Revisões consultadas: `ByteDance/AnimateDiff-Lightning@027c893eec01df7330f5d4b733bc9485ee02e8b2`; `stable-diffusion-v1-5/stable-diffusion-v1-5@451f4fe16113bff5a5d2269ed5ad43b0592e9a14`. A segunda origem declara ser um espelho sem afiliação com Runway; registrar essa proveniência e verificar licença e integridade, sem apresentá-la como publicação oficial atual da Runway. O modelo base tem limitações conhecidas em texto, faces e composição. [Model card do espelho](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5)

A: teste técnico de 256×256, 8 frames, 4 passos, batch 1. Serve para comprovar carregamento e execução, não qualidade.

B: após A, 384×256, 16 frames, 8 fps, 4 passos, batch 1. É candidato de utilidade editorial, ainda sujeito a reprovação. A resolução reduzida pode prejudicar modelos treinados em imagens maiores; registrá-la como desvio de teste. Se necessário e os picos permitirem, testar 512×512 como perfil separado, nunca ampliar automaticamente durante a mesma tentativa.

Usar fp16 suportado, descarregamento sequencial para CPU e decodificação VAE em pequenos lotes. Não mover todo o pipeline para CUDA antes de ativar o descarregamento. A arquitetura AnimateDiff e os mecanismos de economia disponíveis estão descritos pelo mantenedor do Diffusers. [Diffusers/AnimateDiff](https://huggingface.co/docs/diffusers/api/pipelines/animatediff)

### Segundo candidato: Wan 2.1 1.3B otimizado

Manter como candidato para comparação, evitando assumir superioridade nos cenários do res antes de testar. Replanejar todos os pesos, inclusive UMT5, que pode dominar RAM e disco. Separar codificação de prompt, descarregar encoder e só então denoising e VAE. Cache de embeddings será privado por cliente e vinculado a prompt, tokenizer, modelo e revisão.

Quantização do encoder e descarregamento por blocos/disco entram como perfis experimentais próprios quando a combinação Windows/CUDA/biblioteca for suportada. Não basta baixar um arquivo pequeno se a conversão exige carregar o modelo integral em memória. Não alterar compressão, precisão ou scheduler silenciosamente.

Diffusers documenta offloading para disco e armazenamento de pesos em precisão menor com conversão para computação. Isso pode reduzir memória e aumentar muito o tempo; não é garantia de adequação à RTX 2050. Testar os mecanismos isoladamente antes de combiná-los. [Memória no Diffusers](https://huggingface.co/docs/diffusers/optimization/memory)

### Candidato alternativo: LTX-Video 2B destilado

Avaliar somente se o primeiro perfil produzir qualidade insuficiente ou se I2V for a próxima necessidade essencial. O perfil precisa incluir o encoder e o VAE. A configuração oficial 0.9.8 consultada é multiescala e referencia upscaler e modelos adicionais de melhoria de prompt; não cabe tratá-la como um download único de “2B”. Um caminho simplificado precisa de validação própria. [Configuração oficial](https://raw.githubusercontent.com/Lightricks/LTX-Video/main/configs/ltxv-2b-0.9.8-distilled.yaml)

Os kernels FP8 opcionais do projeto indicam Ada ou posterior. Não os planejar como aceleração disponível nesta máquina; armazenamento quantizado com conversão para fp16 é outra questão de compatibilidade. [LTX-Video](https://github.com/Lightricks/LTX-Video)

Não instalar todos os candidatos simultaneamente. A próxima escolha depende do motivo de reprovação anterior: falta de memória, tempo ou qualidade pedem mudanças diferentes.

## 5. Arquitetura executável

```text
Diretor → necessidade visual e critérios
        → seletor de perfil qualificado
        → job persistido / preflight no computador executor
        → preparação → texto → denoising → VAE → verificação
        → candidato em quarentena → admissão no catálogo
        → composição HyperFrames/FFmpeg → auditoria → revisão
```

Manter um worker isolado; adicionar `profiles/`, `adapters/`, `model_store.py`, `resource_monitor.py` e `execution_store.py` à pasta atual. O backend não instala PyTorch. O arquivo de lock deve especificar Python/plataforma, versões compatíveis, índice de wheels CUDA e hashes transitivos; gerar somente após resolução real. Não preencher versões fictícias neste plano.

`SceneGenerationRequestV2` reutilizará cliente autenticado, revisão do documento, cena, necessidade, seed e intenção de câmera. Acrescentará perfil registrado, digest da requisição e referências de entrada por ID/checksum. Tamanho, frames e passos vêm do perfil; o diretor escolhe dentre capacidades oferecidas. V1 preserva o significado do perfil Wan antigo. I2V continua indisponível até implementação e qualificação próprias.

Duração: o perfil informa quantização temporal e duração produzível. O planejador pode solicitar 2 s; se o perfil não puder atendê-los, a diferença deve ser resolvida antes do job. Não esticar, repetir frames ou alterar fps para esconder incompatibilidade.

Intenção de câmera generativa precisa ser traduzida em prompt e registrada como orientação aproximada. Câmera precisa continua no compositor. O sistema não anunciará rastreamento, troca de figurino ou preservação exata de identidade com base em uma amostra genérica.

Para esta entrega, backend executor e worker ficam no PC. Hoje o adaptador exige loopback e arquivo local: colocar o backend na Oracle não fará esses caminhos funcionarem automaticamente. Integração posterior exige agente local que retira jobs autenticados e devolve artefatos verificados, sem publicar a API GPU na internet. Oracle não integra o requisito de inferência.

## 6. Jobs, cancelamento e admissão

Antes de baixar ou inferir, corrigir:

1. Persistir estado e digest antes de iniciar processo; mesmo ID com payload diferente retorna conflito. Consulta a execução conhecida acontece antes do preflight de nova execução.
2. Usar transações no armazenamento de execução, lease com posse e heartbeat; não remover lease apenas porque o PID ainda não foi gravado. Uma única tarefa pesada do res por vez, incluindo render e recorte.
3. Consultar processo sem sinais no Windows. Identificar execução, PID e instante de criação; cancelamento só afeta a árvore comprovadamente pertencente ao worker. Confirmar término antes de marcar `cancelled` e liberar exclusão.
4. Watchdog independente da conexão HTTP e dos limites do Celery. Prazo máximo de 30 minutos de inferência por amostra; duas amostras por rodada. Download possui progresso e política própria de retomada, sem consumir o prazo de inferência.
5. Separar logs de recibo estruturado; gravar recibos atomicamente. Normalizar erros de rede, conflito e recursos. Timeout incerto não autoriza nova submissão.
6. Vincular artefato à execução exata, checksum, modelo, configuração e revisão. Recibo inclui passos, scheduler, precisão, frames, duração, tempos por estágio, RAM/VRAM de pico, falhas e avaliação.
7. Incorporar candidato somente após avaliação e revalidar revisão na mesma transação de incorporação. Chave única impede duplicação. Resultado atrasado continua acessível como candidato, sem sobrescrever documento atual.

## 7. Sequência e entregas verificáveis

| Etapa | Trabalho | Evidência de saída |
|---|---|---|
| 0 | Corrigir lifecycle Windows, exclusão, retomada e contrato de perfis | Testes reais com subprocessos inofensivos, incluindo consultas que não terminam o processo e cancelamento com identidade |
| 1 | Inventário completo e lock; preflight de instalação e execução | Manifesto, estimativa por volume e motivo de admissão/espera; nenhum download implícito |
| 2 | Instalar apenas o candidato A se houver espaço e memória | Ambiente isolado verificável, hashes, teste CUDA pequeno |
| 3 | Inferência A → B, com monitor e prazos | MP4 realmente gerado, recibos e picos; repetir em segunda rodada somente com motivo registrado |
| 4 | Qualificação em necessidades do res | Dois temas e seeds distintos, pertinência, estabilidade e utilidade no tamanho final |
| 5 | Integração autônoma | Diretor produz a necessidade e o prompt; sistema gera, inspeciona e incorpora; Codex não escreve cenas finais nem fornece arquivos |
| 6 | Comparação com produção determinística | Mesmo briefing e identidade, vídeos completos, custos observados e revisão humana separada |

A rodada de distribuição deve precisar de movimento de conteúdo, objeto ou ambiente; um simples zoom em uma imagem gerada não prova difusão de vídeo útil. O diretor decide a cena com base no briefing e repertório. Casos controlados de engenharia podem usar prompts fixos, mas serão identificados como benchmarks, sem representar autonomia de direção.

Avaliar o clipe antes e depois da composição: aderência à necessidade, movimento observável, estabilidade do objeto, ausência de deformação impeditiva e adequação da resolução ao tamanho em que será usado. Verificar decodificação, duração, frames ausentes/duplicados e variações patológicas; diferença de pixels sozinha não prova qualidade. Interpolação e upscale permanecem fora da primeira qualificação.

Critério técnico: duas execuções reais de um perfil dentro dos limites, sem OOM, perda de responsividade impeditiva, duplicação de job ou corrupção. Critério editorial: pelo menos dois casos distintos com 4/5 em pertinência, continuidade e adequação; revisão humana registrada. A aprovação vale somente para os usos e parâmetros demonstrados. Uma nota produzida pela LLM não preenche revisão humana.

## 8. Resultado de cada caminho

- **Executa e serve à cena:** promover aquele perfil e registrar alcance limitado; seguir integração autônoma.
- **Executa, mas resultado fraco:** difusão comprovada, produto ainda reprovado; comparar modelo/base ou condicionamento, sem adicionar efeitos para esconder defeitos.
- **Não executa por pressão momentânea:** aguardar recursos e repetir medição, sem concluir inviabilidade do hardware.
- **Falha com configuração admitida:** registrar estágio, pico e erro; revisar estratégia de memória uma variável por vez.
- **Todos os candidatos plausíveis excedem recursos ou tempo:** entregar evidência e estimativa do recurso adicional necessário. O requisito do difusor permanece aberto. Acordar eventual mudança de hardware ou infraestrutura em decisão separada; não contratar GPU nem ativar API paga automaticamente.

Nenhuma inferência foi comprovada até esta revisão. A conclusão atual é que o perfil implementado é inadequado como único experimento e o worker precisa de correções antes de ser utilizado. O próximo marco é uma geração local real e auditável; a qualidade profissional continua sendo uma exigência posterior de qualificação, não consequência automática de instalar um modelo.
