# Integração dos Studios nas abas atuais da Clicko

Fonte: `origin/main` em `8c089fb`, PR #1 (`codex/craft-studios-active`).
Autor das atualizações: DuduSilvaai.

Commits principais:

- `cfa5f2b5cb4eda1dbd6edfed91221eb12cdddaa9`: departamento criativo e pesquisa editorial.
- `b44f18c15812ab91a6af2e034b537b00573a064c`: instalação limpa e isolamento da validação nativa.
- `4af887309bbb1f28e34fd77e4f5165df91a03d81`: FFmpeg nas verificações reais de ingestão.

O snapshot de Studios, backend, adaptadores, fontes Craft e pesquisa relacionada
foi importado de forma seletiva. Não foi feito merge integral da interface remota:
ela usa outro Dashboard, navegação, autenticação e estado de produto. Os demais
módulos atuais da Clicko continuam na implementação local.

## Ligação com a Clicko atual

`/image` abre o departamento com Imagem selecionada. `/video` abre o mesmo
departamento com Vídeo selecionado. O fluxo é Pedido → Direção → Entrega.
O material pode ser enviado diretamente na etapa Pedido. Os handoffs da KLIC
preenchem título e objetivo. A edição avançada abre os motores PhotoCraft,
FilmCraft ou EffectCraft conforme o formato e mantém o retorno à aba de origem.

`server/studios/proxy.ts` autentica cada chamada pela sessão HTTP-only existente,
valida plano, módulo, permissão e cliente no backend atual e encaminha somente
Studios e arquivos. Identificadores e tokens enviados pelo navegador não são
usados como autoridade. Um JWT de serviço, válido por 60 segundos, nunca é
entregue ao navegador.

`backend/app/studio_app.py` recebe essa identidade e usa IDs determinísticos por
workspace, cliente e usuário. Os projetos são isolados inclusive quando um mesmo
usuário alterna entre clientes. Selecionar outro formato não concede outro módulo.
Não há migração destrutiva dos registros atuais da Clicko. A base e os uploads do
Studio ficam em `.clicko-data/studios`, fora do Git e do servidor de arquivos.

O adaptador `ProductDataContext` funciona somente dentro das duas abas e reaproveita
os providers atuais. A assinatura visual do novo Studio é isolada; a adaptação ao
tema claro não troca os estilos globais da aplicação.

## Execução local

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
npm ci
npm run dev
```

O servidor Node inicia a API em `127.0.0.1:8000`, quando a instalação local existe,
e a encerra junto com o próprio processo. Um serviço configurado por
`CLICKO_STUDIOS_ORIGIN` é administrado separadamente. Em produção, executar
`uvicorn app.studio_app:app --app-dir backend` e configurar em ambos os serviços
o mesmo `CLICKO_STUDIOS_BRIDGE_SECRET`, além de banco/storage adequados.

## Limite do ambiente verificado

As abas anteriores deste checkout eram placeholders “em construção”. O novo
departamento as substitui diretamente. Os projetos, direções e envio de materiais
funcionam com a API importada. Renderização, prévias nativas e exportação dependem
dos binários oficiais de Craft e das ferramentas de mídia. Docker, WSL, Rust e
FFmpeg não estavam instalados neste computador durante a integração. Não foram
fabricados arquivos, prévias nem sucessos de renderização. Uma falha de runtime
preserva o pedido e retorna indisponibilidade.

Para instalar o runtime em ambiente compatível, seguir `CRAFT_INTEGRATION_STATUS.md`
e `workers/craft/README.md`. A verificação de fonte completa confirma os seis
snapshots por identidade Git e inventário. Os testes de serviço que simulam a
fronteira nativa validam persistência e contratos, não fidelidade de pixels.
