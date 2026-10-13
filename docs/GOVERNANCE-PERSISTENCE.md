# Persistência local da governança

## Abrangência

O backend salva workspaces, equipe, assinaturas, aprovações, histórico e convites. Conteúdos/arquivos no navegador e tokens OAuth não foram migrados para este armazenamento. Imagem e Vídeo não foram alterados.

O padrão é `.clicko-data/governance.json`, relativo ao diretório de execução do servidor. Execute `npm run dev` ou `npm start` a partir da raiz do projeto. A variável opcional `CLICKO_GOVERNANCE_DATA_FILE` configura outro caminho absoluto privado. Não use `public/`, `dist/`, uma pasta publicada na web, um caminho versionado ou um serviço de sincronização de arquivos.

## Primeiro uso e servidor legado

- Se não houver arquivo, o servidor cria o estado inicial legado da aplicação. Isso não importa dados de processos antigos nem comprova cobrança/assinatura real.
- Um processo antigo ainda pode conter alterações apenas em memória. Preserve esse estado antes de encerrá-lo. Esta implementação não reinicia processos nem afirma migrar informações que não consegue ler.
- Após iniciar a versão atualizada, toda mutação de governança é gravada antes de devolver sucesso. Um reinício normal recupera o arquivo existente.
- O diretório padrão está no `.gitignore`. O Vite bloqueia os arquivos privados e suas cópias; caminhos sob `public/` ou `dist/` são recusados na inicialização.
- Em Windows, restrinja a ACL da pasta ao usuário/serviço que executa a aplicação. Os modos 0700/0600 não substituem ACLs do Windows. Não envie snapshots ou convites para suporte público.

## Falhas e recuperação

- Erro de escrita: API responde 503 e mantém o estado anterior em memória. Verifique espaço, permissão e disponibilidade do volume antes de repetir.
- Arquivo inválido: inicialização falha sem substituir o original. Preserve o arquivo e investigue; não apague o armazenamento para “resolver” a falha.
- `governance.json.previous` contém apenas a revisão imediatamente anterior. Não é histórico completo nem substitui backups independentes e testados.
- Um arquivo `.lock` impede escritores concorrentes. Após queda abrupta ele pode permanecer. Antes de removê-lo manualmente, confirme que nenhum processo está gravando e preserve uma cópia do armazenamento. Não apague locks de processos ativos.
- Restauração deve ser feita com o serviço parado e com cópia preservada do arquivo atual. Verifique a revisão escolhida antes de colocá-la no caminho ativo.
- Limite de snapshot: 50 MiB. Escritas maiores são recusadas, evitando produzir um arquivo que não possa ser reaberto.

## Limites de produção

Destina-se a uma instância de servidor. A escrita é síncrona e não implementa transações distribuídas, replicação, rotação de logs ou armazenamento seguro de tokens sociais. Use volume persistente e backups externos; para escala/múltiplas instâncias, migre para banco transacional mantendo as APIs.

Esta mudança não resolve o login por timer nem transforma headers de identificação em autenticação. Não exponha a aplicação como serviço autenticado de produção enquanto esse bloqueador permanecer.

## Validação

`npm test` usa dados temporários isolados para verificar gravação, reinício em outro processo, rollback em erro, concorrência, arquivo inválido, exclusão de convite e bloqueio HTTP. Não altera os dados do servidor ativo nem executa integrações externas.
