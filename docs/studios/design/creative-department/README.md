# Clicko Studios — departamento criativo

O frontend do cliente passa a apresentar **pedido → direção → entrega**. Conteúdo é a frente principal; anúncios são uma segunda intenção de trabalho. Imagem, carrossel e vídeo são formatos do projeto. O cliente não precisa operar timeline, camadas ou schemas dos motores.

`prototype.html` preserva o protótipo exploratório com suas duas variantes e dados fictícios. A implementação React utiliza a direção visual escura da sala, com coral, composição editorial e propriedades de revisão. O protótipo não é carregado no aplicativo e suas marcas e mídias de exemplo não são usadas em projetos reais.

## Implementação

- `/studios`, criação de conteúdo, criação em campanhas/projetos, edição de posts e edição de materiais da biblioteca convergem para `src/studios/department/DepartmentStudio.tsx`. Os aliases de navegação antigos também convergem para a sala.
- Os pedidos são registros autenticados por workspace em `/api/v1/studios/v1/projects`. Criação usa chave idempotente; escolha e produção conferem revisão esperada. Recursos internos não são alteráveis pela API genérica de workspace resources.
- As duas propostas iniciais são **esboços derivados do briefing por regras editoriais**, identificados como tal. Não representam pesquisa automática nem resultados de um LLM.
- Produção cria documento recuperável e utiliza os adaptadores Craft existentes. PhotoCraft produz imagens e carrosséis; FilmCraft recebe o vídeo real selecionado da biblioteca para a primeira montagem. EffectCraft permanece disponível nos serviços internos de composição e nos fontes integrais; esta tela não adiciona geração automática de composições.
- No primeiro fluxo de vídeo, o roteiro organiza a intenção, mas não substitui o vídeo selecionado nem produz cenas ou locução automaticamente. Essas operações dependem da produção adicional e dos provedores já previstos na integração.
- Prévia e download vêm dos serviços autenticados. Uma falha não gera mídia ilustrativa como substituta. Carrosséis exportam o conjunto de páginas em ZIP.
- Pedidos de ajuste são registrados na revisão; o envio do pedido não afirma que o ajuste já foi executado. Aprovação preserva o snapshot. Vídeos continuam no fluxo existente de revisão humana de áudio antes da aprovação.
- Credenciais, renders, cache de builds e bases locais permanecem fora do Git. Nenhum arquivo local é apagado por essa exclusão.

## Validação desta entrega

- TypeScript, build de produção e Ruff dos arquivos Python modificados.
- 23 testes de backend de departamento/Craft/lifecycle.
- 13 testes de interface: fluxo de pedido, persistência, conflitos, retomada após falha, intenção de anúncio, requisito de mídia para vídeo, paginação, histórico, responsividade e contratos do editor técnico interno.
- 7 testes unitários Craft e 6 contratos de navegação/experiência.
- Manifesto de procedência validado: fontes completos de PhotoCraft (1.569 arquivos), FilmCraft (1.236), EffectCraft (1.016), bibliotecas, fontes e revisão compatível do FilmCraft preservados.

Os testes de interface utilizam respostas de API controladas; os testes de backend isolam a fronteira de execução nativa. Eles não atestam fidelidade audiovisual. O runtime Docker não respondeu nesta sessão, portanto a exportação nativa completa não foi requalificada nesta mudança de interface. As qualificações anteriores permanecem documentadas nos relatórios Craft existentes.

A validação paga de provedores de IA continua adiada por instrução do usuário. A curadoria em `docs/studios/knowledge/creative-department-2026-10` preserva separadamente suas lacunas de observação audiovisual e revisão humana; a aplicação deste visual não transforma essas lacunas em evidência concluída.
