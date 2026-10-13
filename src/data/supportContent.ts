export type SupportDocumentSection = {
  title: string;
  paragraphs?: string[];
  items?: string[];
};

export type SupportDocument = {
  id: string;
  title: string;
  summary: string;
  version: string;
  updatedAt: string;
  acceptance?: 'required-on-material-change' | 'informational';
  sections: SupportDocumentSection[];
};

export type SupportFaq = {
  id: string;
  question: string;
  answer: string;
  category: string;
};

export const SUPPORT_CONTACT_URL = 'https://vexelbr.com/#/contato';
export const LEGAL_VERSION = '1.0.0';
export const LEGAL_UPDATED_AT = '27 de setembro de 2026';

export const supportDocuments: SupportDocument[] = [
  {
    id: 'terms-of-use',
    title: 'Termos de Uso',
    summary: 'Regras gerais para acesso, cadastro e utilização responsável da Clicko.',
    version: LEGAL_VERSION,
    updatedAt: LEGAL_UPDATED_AT,
    acceptance: 'required-on-material-change',
    sections: [
      { title: 'Aceite e escopo', paragraphs: ['Ao criar uma conta ou utilizar a Clicko, o usuário declara que leu e concorda com estes Termos. A plataforma reúne recursos de planejamento, criação, inteligência artificial, publicação, integrações, colaboração e análise de conteúdo.'] },
      { title: 'Conta e acesso', items: ['O usuário deve fornecer informações verdadeiras e manter seus dados atualizados.', 'Credenciais são pessoais e devem ser protegidas contra uso não autorizado.', 'O responsável pelo workspace administra membros, permissões e conteúdos do ambiente corporativo.'] },
      { title: 'Uso da plataforma', paragraphs: ['A Clicko deve ser utilizada de forma lícita, ética e compatível com estes Termos, com a Política de Uso Aceitável e com as regras dos serviços conectados. Funcionalidades podem variar conforme perfil, plano, disponibilidade técnica e integrações habilitadas.'] },
      { title: 'Conteúdo e decisões do usuário', paragraphs: ['O usuário permanece responsável por revisar, aprovar, publicar e manter os conteúdos criados ou processados na plataforma, inclusive resultados produzidos com inteligência artificial. A Clicko não substitui avaliação profissional, jurídica, contábil ou editorial.'] },
      { title: 'Disponibilidade e alterações', paragraphs: ['A Clicko busca manter o serviço disponível e seguro, mas poderá realizar manutenções, corrigir falhas, ajustar funcionalidades ou descontinuar recursos. Alterações materiais destes Termos serão comunicadas por meios adequados e poderão exigir novo aceite.'] },
      { title: 'Suspensão e encerramento', paragraphs: ['Contas podem ser limitadas ou suspensas em caso de fraude, risco de segurança, violação legal, inadimplência ou descumprimento destes documentos. O usuário pode solicitar encerramento e tratamento dos dados conforme a Política de Privacidade e as obrigações legais aplicáveis.'] },
    ],
  },
  {
    id: 'privacy',
    title: 'Política de Privacidade',
    summary: 'Como dados pessoais são coletados, utilizados, protegidos e compartilhados.',
    version: LEGAL_VERSION,
    updatedAt: LEGAL_UPDATED_AT,
    acceptance: 'required-on-material-change',
    sections: [
      { title: 'Dados tratados', items: ['Dados de cadastro, contato, perfil e autenticação.', 'Dados de uso, registros de segurança, preferências e interações com a plataforma.', 'Conteúdos, arquivos e comandos enviados pelo usuário para processamento.', 'Dados autorizados pelo usuário ao conectar redes sociais e serviços de terceiros.'] },
      { title: 'Finalidades e bases legais', paragraphs: ['Os dados são tratados para executar o serviço contratado, autenticar usuários, manter segurança, personalizar a experiência, prestar suporte, cumprir obrigações legais, prevenir fraudes e, quando aplicável, atender consentimentos ou interesses legítimos avaliados conforme a Lei Geral de Proteção de Dados Pessoais (LGPD).'] },
      { title: 'Compartilhamento e operadores', paragraphs: ['Dados podem ser processados por provedores de infraestrutura, inteligência artificial, armazenamento, comunicação, pagamento e integrações estritamente necessários à operação. Cada compartilhamento deve observar finalidade, segurança, minimização e obrigações contratuais.'] },
      { title: 'Retenção e segurança', paragraphs: ['Os dados são mantidos pelo tempo necessário à prestação dos serviços, ao cumprimento de obrigações legais, à defesa de direitos e à prevenção de fraude. São adotadas medidas técnicas e organizacionais proporcionais ao risco, embora nenhum sistema seja totalmente imune a incidentes.'] },
      { title: 'Direitos do titular', items: ['Confirmação e acesso aos dados pessoais.', 'Correção de dados incompletos, inexatos ou desatualizados.', 'Informação sobre compartilhamentos e consequências do consentimento.', 'Revogação do consentimento, oposição, portabilidade, anonimização, bloqueio ou eliminação quando aplicáveis.', 'Revisão de decisões automatizadas nos casos previstos em lei.'] },
      { title: 'Contato e solicitações', paragraphs: ['Solicitações relacionadas a privacidade e proteção de dados podem ser encaminhadas pelo canal oficial de suporte. A identidade do solicitante poderá ser validada antes do atendimento para proteger a conta e os dados pessoais.'] },
    ],
  },
  {
    id: 'cookies',
    title: 'Política de Cookies',
    summary: 'Uso de cookies e tecnologias locais necessárias à experiência da plataforma.',
    version: LEGAL_VERSION,
    updatedAt: LEGAL_UPDATED_AT,
    acceptance: 'informational',
    sections: [
      { title: 'Tecnologias utilizadas', paragraphs: ['A Clicko pode utilizar cookies, armazenamento local e tecnologias equivalentes para manter sessões, preferências de tema, segurança, navegação e desempenho.'] },
      { title: 'Categorias', items: ['Essenciais: autenticação, segurança, estabilidade e preferências indispensáveis.', 'Funcionais: personalização da experiência e recuperação de contexto.', 'Medição: diagnóstico agregado de uso e desempenho, quando habilitado.', 'Terceiros: recursos solicitados pelo usuário, como integrações e serviços externos.'] },
      { title: 'Controle do usuário', paragraphs: ['Cookies não essenciais, quando utilizados, devem respeitar as escolhas apresentadas ao usuário. O navegador também permite remover ou bloquear tecnologias locais, o que pode limitar funcionalidades essenciais da Clicko.'] },
    ],
  },
  {
    id: 'subscription-billing',
    title: 'Termos de Assinatura e Cobrança',
    summary: 'Planos, renovação, limites, tributos e condições de pagamento.',
    version: LEGAL_VERSION,
    updatedAt: LEGAL_UPDATED_AT,
    acceptance: 'required-on-material-change',
    sections: [
      { title: 'Planos e contratação', paragraphs: ['Recursos, limites, assentos, armazenamento e integrações variam conforme o plano apresentado no momento da contratação. Condições comerciais específicas prevalecem quando formalizadas em proposta ou contrato.'] },
      { title: 'Cobrança e renovação', paragraphs: ['Assinaturas recorrentes podem ser renovadas automaticamente no período escolhido até o cancelamento. Valores, periodicidade, tributos e data de cobrança devem ser informados antes da confirmação.'] },
      { title: 'Falhas de pagamento', paragraphs: ['Pagamentos recusados ou vencidos podem gerar novas tentativas, aviso ao titular e limitação temporária de recursos, preservados os direitos legais e as condições contratadas.'] },
      { title: 'Mudanças de plano', paragraphs: ['Upgrades, downgrades e alterações de quantidade podem produzir ajuste proporcional ou valer a partir do ciclo seguinte, conforme informado na interface de contratação.'] },
    ],
  },
  {
    id: 'cancellation-refund',
    title: 'Cancelamento e Reembolso',
    summary: 'Como encerrar a assinatura e quando um reembolso pode ser aplicável.',
    version: LEGAL_VERSION,
    updatedAt: LEGAL_UPDATED_AT,
    acceptance: 'required-on-material-change',
    sections: [
      { title: 'Cancelamento', paragraphs: ['O titular pode solicitar o cancelamento pelos canais disponibilizados. Salvo disposição legal ou comercial diferente, o acesso permanece até o fim do período já pago e a renovação seguinte deixa de ocorrer.'] },
      { title: 'Direito de arrependimento', paragraphs: ['Contratações sujeitas à legislação brasileira de consumo observarão o direito de arrependimento e demais direitos obrigatórios quando aplicáveis ao caso concreto.'] },
      { title: 'Reembolsos', paragraphs: ['Pedidos são avaliados de acordo com a legislação, a data da solicitação, o período contratado, o uso do serviço e as condições comerciais informadas. Cobranças indevidas confirmadas serão corrigidas pelos meios adequados.'] },
      { title: 'Dados após o cancelamento', paragraphs: ['Após o encerramento, dados poderão permanecer por período limitado para exportação, cumprimento legal, segurança e defesa de direitos. A exclusão seguirá a Política de Privacidade e os prazos técnicos comunicados ao usuário.'] },
    ],
  },
  {
    id: 'acceptable-use',
    title: 'Política de Uso Aceitável',
    summary: 'Condutas permitidas e proibidas para proteger usuários, terceiros e a Clicko.',
    version: LEGAL_VERSION,
    updatedAt: LEGAL_UPDATED_AT,
    acceptance: 'required-on-material-change',
    sections: [
      { title: 'Usos proibidos', items: ['Praticar atividade ilícita, fraudulenta, enganosa, abusiva ou discriminatória.', 'Violar direitos autorais, marcas, privacidade, imagem ou outros direitos de terceiros.', 'Distribuir malware, tentar acessar contas ou sistemas sem autorização ou contornar medidas de segurança.', 'Enviar spam, manipular métricas, automatizar abuso ou publicar conteúdo proibido pelas plataformas conectadas.', 'Gerar ou divulgar conteúdo que exponha pessoas a risco, fraude, assédio ou exploração.'] },
      { title: 'Fiscalização e medidas', paragraphs: ['A Clicko pode investigar sinais de abuso e aplicar medidas proporcionais, incluindo aviso, limitação, remoção de conteúdo, suspensão ou encerramento, respeitados os direitos do usuário e as obrigações legais.'] },
    ],
  },
  {
    id: 'ai-content',
    title: 'Política de Conteúdo Gerado por IA',
    summary: 'Regras para uso responsável da KLIC e de recursos generativos.',
    version: LEGAL_VERSION,
    updatedAt: LEGAL_UPDATED_AT,
    acceptance: 'required-on-material-change',
    sections: [
      { title: 'Natureza das respostas', paragraphs: ['Resultados de inteligência artificial são sugestões probabilísticas e podem conter imprecisões, omissões ou conteúdo inadequado ao contexto. O usuário deve revisar fatos, linguagem, direitos e conformidade antes de utilizar ou publicar qualquer resultado.'] },
      { title: 'Dados enviados à IA', paragraphs: ['Não devem ser enviados dados sigilosos, pessoais sensíveis ou materiais sem autorização. O processamento poderá envolver provedores externos identificados na documentação de privacidade e nas configurações aplicáveis.'] },
      { title: 'Responsabilidade e transparência', items: ['O usuário decide se, como e onde utilizará o conteúdo gerado.', 'Quando exigido por lei, contrato ou plataforma, o uso de IA deve ser informado.', 'A IA não deve ser usada para personificação enganosa, violação de direitos ou decisões de alto impacto sem supervisão humana adequada.'] },
      { title: 'Direitos e originalidade', paragraphs: ['A disponibilidade de um resultado não garante exclusividade, originalidade ou ausência de direitos de terceiros. Cabe ao usuário realizar as verificações necessárias antes do uso comercial.'] },
    ],
  },
  {
    id: 'content-intellectual-property',
    title: 'Conteúdo e Propriedade Intelectual',
    summary: 'Titularidade, licenças técnicas e responsabilidades sobre materiais.',
    version: LEGAL_VERSION,
    updatedAt: LEGAL_UPDATED_AT,
    acceptance: 'required-on-material-change',
    sections: [
      { title: 'Conteúdo do usuário', paragraphs: ['O usuário mantém os direitos que possui sobre textos, imagens, vídeos, marcas, arquivos e demais materiais enviados. Ao utilizar a Clicko, concede apenas as autorizações técnicas necessárias para armazenar, processar, adaptar formatos e entregar as funcionalidades solicitadas.'] },
      { title: 'Responsabilidade pela publicação', paragraphs: ['O usuário declara possuir direitos e autorizações suficientes sobre o conteúdo utilizado e publicado, incluindo imagem, voz, música, marca e dados pessoais de terceiros.'] },
      { title: 'Propriedade da plataforma', paragraphs: ['Software, identidade visual, documentação, fluxos, componentes e marcas da Clicko e da VEXEL permanecem protegidos por direitos de propriedade intelectual. O acesso ao serviço não transfere esses direitos ao usuário.'] },
      { title: 'Denúncias', paragraphs: ['Comunicações sobre possível infração podem ser encaminhadas ao suporte com identificação do material, fundamento da solicitação e comprovação de legitimidade.'] },
    ],
  },
  {
    id: 'data-account-deletion',
    title: 'Proteção de Dados e Exclusão de Conta',
    summary: 'Solicitações sobre dados, exportação, retenção e encerramento da conta.',
    version: LEGAL_VERSION,
    updatedAt: LEGAL_UPDATED_AT,
    acceptance: 'required-on-material-change',
    sections: [
      { title: 'Solicitações do titular', paragraphs: ['O usuário pode solicitar acesso, correção, informação, oposição, portabilidade ou eliminação de dados conforme a legislação aplicável. Algumas solicitações dependem de validação de identidade e podem sofrer limitações legais ou técnicas justificadas.'] },
      { title: 'Exclusão da conta', items: ['A exclusão desativa o acesso e inicia o procedimento de remoção dos dados associados.', 'Dados compartilhados em workspace podem permanecer sob controle da organização responsável.', 'Registros mínimos podem ser retidos para cumprimento legal, prevenção de fraude, auditoria e defesa de direitos.', 'Backups são eliminados conforme ciclos seguros de retenção.'] },
      { title: 'Segurança', paragraphs: ['O usuário deve comunicar imediatamente suspeitas de acesso indevido. Incidentes confirmados serão tratados segundo o plano de resposta da plataforma e as comunicações legalmente exigidas.'] },
    ],
  },
  {
    id: 'integrations-third-parties',
    title: 'Integrações e Serviços de Terceiros',
    summary: 'Conexões sociais, APIs externas, disponibilidade e responsabilidades.',
    version: LEGAL_VERSION,
    updatedAt: LEGAL_UPDATED_AT,
    acceptance: 'required-on-material-change',
    sections: [
      { title: 'Autorização das conexões', paragraphs: ['Ao conectar uma conta externa, o usuário autoriza a Clicko a acessar e executar somente as operações abrangidas pelas permissões concedidas. Tokens e vínculos devem ser protegidos e podem ser revogados pelo usuário ou pelo provedor.'] },
      { title: 'Regras dos provedores', paragraphs: ['Instagram, Facebook, TikTok, YouTube, LinkedIn, Threads, Pinterest, X e outros serviços possuem termos, limites e políticas próprios. O usuário também deve cumprir essas regras.'] },
      { title: 'APIs e disponibilidade', paragraphs: ['Integrações dependem de APIs, permissões, revisões, cotas e disponibilidade de terceiros. Mudanças externas podem limitar, atrasar ou interromper funcionalidades sem controle direto da Clicko.'] },
      { title: 'Processamento de conteúdo', paragraphs: ['Textos, imagens, vídeos, áudios, métricas e metadados podem ser enviados aos serviços estritamente necessários à ação solicitada. O tratamento observa a Política de Privacidade e as escolhas do usuário.'] },
      { title: 'Limitação de responsabilidade', paragraphs: ['A Clicko não controla indisponibilidades, bloqueios, alterações de API, decisões de moderação ou perdas causadas exclusivamente por serviços externos, sem prejuízo das responsabilidades que não possam ser afastadas por lei.'] },
    ],
  },
];

export const supportFaqs: SupportFaq[] = [
  { id: 'profiles-workspaces', category: 'Contas e workspaces', question: 'Qual é a diferença entre perfil pessoal e workspace corporativo?', answer: 'O perfil pessoal organiza a operação individual. O workspace corporativo reúne equipe, clientes, permissões, aprovações e recursos compartilhados. Os dados permanecem separados conforme o contexto ativo.' },
  { id: 'invite-members', category: 'Contas e workspaces', question: 'Como adicionar pessoas ao workspace?', answer: 'No ambiente corporativo, acesse Equipe e utilize a opção de convite disponível para o seu nível de permissão. Os limites de assentos dependem do plano ativo.' },
  { id: 'social-connections', category: 'Conexões', question: 'Como conectar uma rede social?', answer: 'Acesse Conexões, escolha “Conectar conta” e selecione a plataforma. A autorização acontece no ambiente oficial do provedor. Algumas redes exigem conta profissional, página, canal ou permissões adicionais.' },
  { id: 'connection-expired', category: 'Conexões', question: 'O que fazer quando uma conexão expira?', answer: 'Abra Conexões e use a ação de reconectar. A Clicko solicitará novamente apenas as permissões necessárias. Publicações e métricas podem ficar indisponíveis até a renovação do vínculo.' },
  { id: 'schedule-content', category: 'Publicação', question: 'Como publicar ou agendar conteúdo?', answer: 'Crie ou selecione um conteúdo, escolha uma conta conectada e defina data e horário no Calendário. Antes da publicação, revise texto, mídia, permissões e regras específicas da rede.' },
  { id: 'image-video-generation', category: 'Criação', question: 'Como funcionam os recursos de imagem e vídeo?', answer: 'As áreas de Imagem e Vídeo processam instruções e arquivos enviados pelo usuário conforme as opções disponíveis. Revise o resultado, os direitos de uso e os requisitos da plataforma de destino antes de publicar.' },
  { id: 'klic', category: 'KLIC', question: 'O que a KLIC pode fazer?', answer: 'A KLIC auxilia em análise, planejamento e criação dentro do contexto disponível. As respostas podem conter imprecisões; decisões e publicações sempre devem passar por revisão humana.' },
  { id: 'analytics', category: 'Analytics', question: 'Por que alguns dados não aparecem no Analytics?', answer: 'Os dados dependem da conexão, das permissões e da disponibilidade das APIs de cada rede. Verifique o período, o contexto ativo e o status das contas conectadas.' },
  { id: 'account-security', category: 'Segurança', question: 'Como proteger minha conta?', answer: 'Use senha exclusiva, mantenha seus dispositivos protegidos, não compartilhe credenciais e encerre acessos suspeitos. Em caso de atividade não reconhecida, procure o suporte imediatamente.' },
  { id: 'plans-limits', category: 'Assinatura', question: 'Onde consultar plano e limites?', answer: 'Abra Configurações e acesse Plano e Assinatura. A área mostra o plano reconhecido pela plataforma e os limites disponíveis quando fornecidos pelo serviço de cobrança.' },
  { id: 'support', category: 'Suporte', question: 'Como falar com o suporte?', answer: 'O atendimento técnico, operacional e institucional da Clicko é realizado pela equipe da VEXEL. Use o botão “Falar com o suporte” nesta página para abrir o canal oficial.' },
];
