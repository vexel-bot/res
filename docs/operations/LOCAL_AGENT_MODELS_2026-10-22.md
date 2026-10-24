# Modelos e operação local dos agentes

## Hardware medido em 22/10/2026

Evidência reproduzível: `scripts/agents/audit-environment.ps1`, saída em
`.codex-runtime/stage2-hardware.json`.

| Item | Observação |
| --- | --- |
| Sistema | Windows 11 Home Single Language 64 bits, build 26300 |
| CPU | Intel Core i7-12650H; CIM reportou 8 núcleos/14 processadores lógicos |
| RAM visível | 8.279.613.440 bytes, aproximadamente 7,71 GiB |
| RAM livre durante medições | Aproximadamente 0,8–1,3 GiB; varia com os processos abertos |
| GPU | Intel UHD Graphics integrada; `AdapterRAM` reportou 1 GiB, não comprova VRAM dedicada |
| Disco C: | Aproximadamente 199 GiB livres no levantamento |
| Runtime | Node 24.15.0, Python 3.12.14 no `.venv`; Pillow 12.3.0 e NumPy 2.4.4 |
| FFmpeg | Binário privado LGPL já disponível no mecanismo central; fora do PATH |
| Ausências | Rust/Cargo, Docker, distribuição WSL, Ollama, llama-server, Torch, ONNX/DirectML, Diffusers e Transformers |
| Pesos conhecidos | Diretórios padrão de Ollama e Hugging Face ausentes; não é uma busca exaustiva em todos os discos |

Não há GPU NVIDIA identificada; não foi demonstrado CUDA. DirectML/Vulkan não
foram instalados nem homologados neste adaptador Intel. Não foi instalado runtime,
driver ou peso novo. Os renderizadores locais funcionam com o ambiente existente.

## Seleção condicionada, não instalação automática

| Opção | Avaliação para este computador |
| --- | --- |
| Regras locais + Pillow/FFmpeg | Operacional e testado; primeira escolha enquanto a RAM está ocupada |
| Qwen3 0.6B quantizado em CPU/Ollama | Candidato leve para um ensaio posterior de comandos curtos; exige liberar RAM, instalar runtime/pesos autorizados e medir JSON/latência. Não foi executado |
| LLM 3B/7B+ | Não selecionado com a pouca RAM livre; contexto e cache elevam o consumo além do tamanho do arquivo |
| Geração de imagem local por difusão | Não operacional; faltam runtime, pesos e demonstração de memória/desempenho. Edição local não depende dela |
| Gemini Free Tier | A conta precisa comprovar tier/modelo/cota gratuitos antes de qualquer chamada. Chave existente não basta |
| Claude/Runway/Gemini pago | Integrações existentes preservadas para fase futura, com orçamento e admissão; não utilizadas |

A licença Apache-2.0 do Qwen3 0.6B foi conferida no
[model card oficial](https://huggingface.co/Qwen/Qwen3-0.6B). A escolha de uma
quantização exigirá verificar origem, licença, checksum e consumo real. O número
de parâmetros não garante boa interpretação nem JSON correto; 0.6B é candidato
a benchmark pequeno, não promessa de direção audiovisual autônoma.

[Ollama para Windows](https://docs.ollama.com/windows) documenta execução nativa e
o endpoint local; o suporte gráfico documentado não comprova aceleração neste
Intel. [Structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
permite schema no campo `format`. O backend valida novamente a saída antes de
aplicar, mesmo que o runtime gere JSON sintaticamente correto.

A documentação de [billing Gemini](https://ai.google.dev/gemini-api/docs/billing)
distingue Free Tier e projetos com cobrança. Nenhuma consulta à conta, ativação de
faturamento ou chamada de geração foi feita. Não há fallback automático para essa
chave quando Ollama está indisponível.

## Inicialização e uso

1. Na raiz do repositório, `npm run dev:local`; confirmar `npm run dev:status`.
2. Desde 23/10/2026, `dev:local` usa sessão temporária emitida pelo servidor,
   Clicko Developer / Cliente DEV e `.codex-runtime/clicko-dev`. Não copia
   credenciais comerciais nem elimina autenticação. A governança e a ponte
   reconhecem o cliente reservado. Para testar autenticação comercial, pare o DEV
   antes de iniciar com `CLICKO_DEV_MODE=false` e uma conta legítima no perfil
   separado. Consulte o README para operação e limpeza recuperável.
3. Abrir `/studios/video/motion`, `/studios/image/edit` ou
   `/studios/tools/composition`, escolher **Edição local**.
4. Criar projeto e informar briefing. Conferir origem e plano antes de aplicar.
5. Editar camadas/propriedades, salvar e exportar. Para cortes/áudio, salvar a
   composição e abrir o editor canônico. Versões anteriores continuam no histórico.
6. Na KLIC, usar **Produção local** ou um pedido explícito, como “Crie um motion
   design de 12 segundos sobre inteligência artificial”. O retorno vincula projeto
   e tarefa; o plano é aplicado no Studio. O botão KLIC do editor abre a mesma
   conversa contextual, não outro chat.

Sem modelo, exemplos de regras suportadas: criar motion/cartão, alterar primeiro
título entre aspas, cor hexadecimal dos títulos/fundo e duração de motion sem
clipes. Pedidos livres não suportados retornam limitação, sem alteração fictícia.
Na Etapa 3, “Desfaça a última alteração” prepara a composição salva imediatamente
anterior para revisão/aplicação, sem apagar snapshots/exports. É restauração
versionada, não uma pilha conversacional multinível. Com seleção, pede desmarcar.

Quando houver runtime e modelo **já instalados** e aprovados pelo operador,
administrador pode registrar a conexão em **Modelos dos agentes**, com o ID exato,
e selecionar o modelo separadamente para Audiovisual e Imagem. A interface não
baixa pesos; o servidor recusa modelo cloud, conexão paga ou endpoint remoto.
A configuração da KLIC/Gemini continua no mecanismo original, sem mudar segredos.

## Repetir a aceitação real

```powershell
npm run dev:local
.venv\Scripts\python.exe scripts/agents/acceptance.py create
npm run dev:stop
npm run dev:local
# Em outro terminal, depois de dev:status informar ready:
.venv\Scripts\python.exe scripts/agents/acceptance.py verify
```

O script usa a ponte de serviço do perfil de QA, materiais sintéticos próprios e
uma partição própria. Não homologa o login/licença comercial do browser. Produz
MP4s e PNG reais, JSONs editáveis, planos, histórico e checksums, sem LLM simulado
ser anunciado como inferência. Não rode com a pasta de dados de clientes.

## Motores e próximos requisitos

PhotoCraft/FilmCraft/EffectCraft continuam bloqueados pela ausência de binários e
WASM; esta etapa não baixa nem altera fontes upstream. Usar as instruções e
checagens de integridade da [Etapa 1](STAGE1_LOCAL_INFRASTRUCTURE.md) quando o
operador disponibilizar Docker/WSL/Rust. Redis/Celery distribuídos seguem não
homologados. O primeiro ciclo de inferência deverá medir memória, latência,
JSON válido, comando suportado, escopo e qualidade com um modelo local real.
