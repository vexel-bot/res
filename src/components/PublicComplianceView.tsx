import React from 'react';
import { ArrowLeft, ExternalLink, ShieldCheck } from 'lucide-react';
import { ClickoLogo } from './ClickoLogo';

export type PublicCompliancePage = 'about' | 'privacy' | 'terms' | 'data-deletion' | 'support' | 'integrations';

const pagePaths: Record<PublicCompliancePage, string> = {
  about: '/about',
  privacy: '/privacy',
  terms: '/terms',
  'data-deletion': '/data-deletion',
  support: '/support',
  integrations: '/integrations',
};

export const publicCompliancePage = (pathname: string): PublicCompliancePage | undefined => {
  const normalized = pathname.replace(/\/+$/, '') || '/';
  return (Object.entries(pagePaths).find(([, path]) => path === normalized)?.[0] as PublicCompliancePage | undefined);
};

const updatedAt = '20 de setembro de 2026';

function Privacy() {
  return <>
    <Lead title="Política de Privacidade" text="Como a Clicko trata os dados necessários para autenticação, operação do produto e integrações sociais." />
    <Section title="Dados tratados"><p>Tratamos dados de cadastro e sessão, contexto do perfil pessoal ou workspace, identificadores das contas sociais autorizadas, permissões concedidas, metadados de páginas, canais, organizações ou boards e métricas solicitadas pelo usuário.</p><p>Access tokens e refresh tokens são mantidos exclusivamente no backend, cifrados em repouso e nunca são entregues ao navegador.</p></Section>
    <Section title="Finalidades"><p>Os dados são usados para autenticar o usuário, manter o isolamento entre contas e workspaces, listar recursos autorizados, sincronizar métricas, publicar conteúdo quando essa capability estiver disponível e atender solicitações de suporte, segurança e auditoria.</p></Section>
    <Section title="Compartilhamento e provedores"><p>A Clicko envia dados às APIs oficiais somente para executar a ação solicitada. Cada integração também está sujeita aos termos e políticas do respectivo provedor. Prestadores de infraestrutura podem processar dados estritamente para hospedagem, banco, observabilidade e segurança.</p></Section>
    <Section title="Retenção e segurança"><p>Conexões permanecem enquanto estiverem autorizadas. Ao desconectar, tokens e o vínculo operacional são removidos; registros mínimos de auditoria podem ser preservados para segurança, investigação e obrigações aplicáveis. A Clicko utiliza isolamento por owner, criptografia autenticada, controles de acesso e logs sanitizados.</p></Section>
    <Section title="Controle do usuário"><p>O usuário pode revogar uma integração em Contas Conectadas ou no próprio provedor. Solicitações de acesso, correção ou exclusão são tratadas pelo fluxo descrito em <a href="/data-deletion">Exclusão de Dados</a>.</p></Section>
  </>;
}

function Terms() {
  return <>
    <Lead title="Termos de Uso" text="Condições essenciais para utilização responsável da Clicko e de suas integrações." />
    <Section title="Uso da plataforma"><p>O usuário deve fornecer informações corretas, proteger suas credenciais e utilizar somente contas, páginas e recursos para os quais possua autorização. É proibido usar a Clicko para violar direitos, políticas de plataformas, leis aplicáveis ou distribuir conteúdo abusivo, fraudulento ou ilícito.</p></Section>
    <Section title="Integrações externas"><p>As redes sociais são serviços independentes. Disponibilidade, permissões, quotas, revisão de aplicativos e formatos aceitos podem mudar por decisão de cada provedor. A Clicko apresenta somente capabilities efetivamente disponíveis para a autorização concedida.</p></Section>
    <Section title="Conteúdo e decisões"><p>O usuário continua responsável pelo conteúdo criado, aprovado e publicado, inclusive pela legitimidade de mídias, marcas, dados e direitos de terceiros. Recursos assistidos por inteligência artificial devem ser revisados antes do uso.</p></Section>
    <Section title="Segurança e continuidade"><p>A Clicko pode suspender sessões, integrações ou ações que apresentem risco, abuso, violação de permissão ou falha de segurança. Alterações materiais destes termos devem ser comunicadas pelos canais oficiais antes de entrarem em vigor.</p></Section>
  </>;
}

function DataDeletion() {
  return <>
    <Lead title="Exclusão de Dados" text="Como revogar uma rede social e solicitar a remoção de dados associados." />
    <Section title="Desconectar uma rede"><ol><li>Entre na Clicko e abra <strong>Contas Conectadas</strong>.</li><li>Selecione a conta social desejada e escolha <strong>Desconectar</strong>.</li><li>A Clicko tenta revogar a autorização no provedor quando a API permite e remove o vínculo e os tokens armazenados daquele owner.</li></ol><p>Também é possível revogar o acesso diretamente nas configurações de aplicativos conectados da rede social.</p></Section>
    <Section title="Solicitar exclusão adicional"><p>Com a sessão autenticada, abra <strong>Configurações → Ajuda e Suporte</strong> e identifique a conta ou workspace. A equipe confirma a identidade e o escopo antes de excluir dados adicionais. Registros mínimos de segurança e auditoria podem ser retidos quando necessários para prevenção de fraude, investigação ou obrigação aplicável.</p></Section>
    <Section title="O que não é apagado pela Clicko"><p>Conteúdo já publicado em uma rede social precisa ser gerenciado também no próprio provedor. A Clicko não controla cópias, retenções ou políticas mantidas por serviços externos.</p></Section>
  </>;
}

function Support() {
  return <>
    <Lead title="Contato e Suporte" text="Canais para dúvidas operacionais, privacidade e segurança." />
    <Section title="Usuários da Clicko"><p>Entre na plataforma e acesse <strong>Configurações → Ajuda e Suporte</strong>. O contexto autenticado permite identificar com segurança a conta pessoal ou workspace relacionado ao atendimento.</p></Section>
    <Section title="Problemas com integração"><p>Informe o provedor, horário aproximado, ação executada e o requestId exibido. Nunca envie senha, access token, refresh token, client secret ou chave de API.</p></Section>
    <Section title="Canal público"><p>O endereço público de atendimento empresarial deve ser confirmado pela Clicko antes do lançamento comercial. Esta página não inventa um e-mail ou uma entidade jurídica ainda não confirmados.</p></Section>
  </>;
}

const providers = [
  ['Instagram', 'Conta profissional e recursos associados à Página autorizada.'],
  ['Facebook', 'Páginas administradas pelo usuário.'],
  ['Threads', 'Perfil autorizado para conteúdo e insights aprovados.'],
  ['TikTok', 'Perfil e publicação somente conforme auditoria e permissões do provedor.'],
  ['YouTube', 'Canal e estatísticas autorizadas; upload não é anunciado nesta versão.'],
  ['LinkedIn', 'Perfil ou organização quando os produtos e scopes estiverem aprovados.'],
  ['Pinterest', 'Conta e boards autorizados.'],
  ['X', 'Perfil, leitura e publicação conforme o plano e os limites da API.'],
];

function Integrations() {
  return <>
    <Lead title="Integrações Sociais" text="Conexões próprias de cada assinante por OAuth oficial, sem compartilhar credenciais técnicas da Clicko." />
    <Section title="Como funciona"><p>Ao clicar em Conectar, o usuário é redirecionado ao provedor, autentica-se diretamente nele, escolhe as permissões e retorna à Clicko. Quando existem vários recursos compatíveis, a seleção acontece no contexto autenticado do mesmo owner.</p></Section>
    <div className="grid gap-3 sm:grid-cols-2">{providers.map(([name, description]) => <article key={name} className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4"><strong className="text-sm text-white">{name}</strong><p className="mt-2 text-xs leading-5 text-[#9a9a9a]">{description}</p></article>)}</div>
    <Section title="Revogação e escopo"><p>A Clicko solicita apenas os scopes necessários às funções apresentadas. O usuário pode desconectar a qualquer momento. Recursos que dependem de revisão, tier comercial ou permissão adicional permanecem identificados como indisponíveis, sem dados simulados.</p></Section>
  </>;
}

function About() {
  return <>
    <Lead title="Clicko" text="Uma central de operação de conteúdo para organizar criação, planejamento, distribuição e análise." />
    <Section title="Produto"><p>A Clicko reúne fluxos pessoais e corporativos em contextos isolados, com controle de acesso e integrações sociais autorizadas pelo próprio usuário. A plataforma preserva a separação entre dados de cada pessoa e workspace.</p></Section>
    <Section title="Princípios"><p>Clareza, autorização explícita, segurança por padrão e capabilities honestas. Nenhum assinante precisa conhecer client IDs, secrets, consoles de desenvolvedor ou configurações internas para conectar a própria conta.</p></Section>
  </>;
}

function Lead({ title, text }: { title: string; text: string }) {
  return <header className="border-b border-white/[0.08] pb-8"><span className="text-[10px] font-semibold uppercase tracking-[0.28em] text-[#FF7F50]">Transparência Clicko</span><h1 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-white sm:text-4xl">{title}</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-[#999]">{text}</p><p className="mt-3 text-[10px] text-[#666]">Atualizado em {updatedAt}</p></header>;
}

function Section({ title, children }: React.PropsWithChildren<{ title: string }>) {
  return <section className="border-b border-white/[0.07] py-6 last:border-0"><h2 className="text-sm font-semibold text-white">{title}</h2><div className="mt-3 space-y-3 text-xs leading-6 text-[#a0a0a0] [&_a]:text-[#FF7F50] [&_ol]:list-decimal [&_ol]:space-y-2 [&_ol]:pl-5 [&_strong]:font-medium [&_strong]:text-white">{children}</div></section>;
}

const content: Record<PublicCompliancePage, React.FC> = { about: About, privacy: Privacy, terms: Terms, 'data-deletion': DataDeletion, support: Support, integrations: Integrations };

export function PublicComplianceView({ page }: { page: PublicCompliancePage }) {
  const Content = content[page];
  return <main className="min-h-screen bg-black px-5 py-8 text-white sm:px-8">
    <div className="mx-auto max-w-4xl">
      <nav className="flex items-center justify-between gap-4 border-b border-white/[0.08] pb-6">
        <a href="/login" className="block" aria-label="Ir para a autenticação"><ClickoLogo authentication appearance="seamless" className="h-12 w-28" /></a>
        <a href="/login" className="flex items-center gap-2 rounded-lg border border-white/[0.09] px-3 py-2 text-[10px] text-[#aaa] transition hover:border-white/[0.16] hover:text-white"><ArrowLeft className="h-3.5 w-3.5" />Entrar na Clicko</a>
      </nav>
      <div className="py-10"><Content /></div>
      <footer className="flex flex-col gap-5 border-t border-white/[0.08] py-7 sm:flex-row sm:items-center sm:justify-between"><div className="flex items-center gap-2 text-[10px] text-[#777]"><ShieldCheck className="h-4 w-4 text-[#FF7F50]" />Segurança e transparência por padrão</div><div className="flex flex-wrap gap-x-4 gap-y-2 text-[10px] text-[#888]">{Object.entries(pagePaths).map(([id, href]) => <a key={id} href={href} className="transition hover:text-white">{{ about: 'Sobre', privacy: 'Privacidade', terms: 'Termos', 'data-deletion': 'Exclusão', support: 'Suporte', integrations: 'Integrações' }[id as PublicCompliancePage]}<ExternalLink className="ml-1 inline h-2.5 w-2.5" /></a>)}</div></footer>
    </div>
  </main>;
}
