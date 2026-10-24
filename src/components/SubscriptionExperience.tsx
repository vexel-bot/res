import React from 'react';
import { ArrowRight, Check, ChevronDown, CreditCard, ShieldCheck, Users } from 'lucide-react';
import { ClickoLogo } from './ClickoLogo';
import { ClickoLoader } from './ClickoLoader';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import type { GovernanceWorkspace, PlanCapability, SaaSPlan, SubscriptionStatus, UsageResource, WorkspaceSubscription } from '../types';
import './SubscriptionExperience.css';

type BillingStatus = { subscription: WorkspaceSubscription; workspace: GovernanceWorkspace; accessAllowed: boolean };
const money = (value: number | null) => value === null ? 'Sob consulta' : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(value);
const statusCopy: Partial<Record<SubscriptionStatus, string>> = {
  no_plan: 'Escolha o plano para iniciar sua operação.', pending_checkout: 'Seu checkout foi iniciado. Conclua o pagamento no ambiente seguro.',
  pending_payment: 'Aguardando confirmação do pagamento. O acesso será liberado automaticamente.', past_due: 'Há uma cobrança em atraso. Regularize a assinatura para continuar.',
  payment_failed: 'O pagamento não foi confirmado. Você pode tentar novamente.', canceled: 'Esta assinatura foi cancelada. Escolha um plano para retornar.',
  suspended: 'Esta assinatura está suspensa. Escolha um plano para continuar.', ended: 'Esta assinatura terminou. Escolha um plano para retornar.',
};
type ComparisonRow = { group: string; label: string; resource?: UsageResource; capability?: PlanCapability; suffix?: string; licenses?: boolean };
export const comparisonRows: ComparisonRow[] = [
  { group: 'Criação', label: 'Geração de imagens', resource: 'image_generations' }, { group: 'Criação', label: 'Minutos de vídeo', resource: 'video_minutes', suffix: ' min' },
  { group: 'Criação', label: 'Edição de imagens', capability: 'image_editing' }, { group: 'Criação', label: 'Edição de vídeo', capability: 'video_editing' }, { group: 'Criação', label: 'Criação de textos', capability: 'copy_creation' },
  { group: 'Inteligência artificial', label: 'Créditos KLIC', resource: 'klic_credits' }, { group: 'Inteligência artificial', label: 'KLIC AI', capability: 'klic' },
  { group: 'Publicação e gestão', label: 'Contas sociais', resource: 'social_accounts' }, { group: 'Publicação e gestão', label: 'Calendário editorial', capability: 'calendar' }, { group: 'Publicação e gestão', label: 'Biblioteca', capability: 'library' },
  { group: 'Gestão', label: 'Clientes cadastrados', resource: 'clients' }, { group: 'Gestão', label: 'Armazenamento', resource: 'storage_bytes' },
  { group: 'Análise', label: 'Analytics', capability: 'analytics' }, { group: 'Análise', label: 'Radar', capability: 'radar' },
  { group: 'Automação', label: 'Automações', resource: 'automations' },
  { group: 'Colaboração', label: 'Aprovações', capability: 'approvals' }, { group: 'Colaboração', label: 'Equipe', capability: 'team' }, { group: 'Colaboração', label: 'Licenças incluídas', licenses: true },
];
export const questions = [
  ['Quando meu acesso é liberado?', 'Após a confirmação do pagamento pelo provedor, os recursos do plano são liberados automaticamente para o seu ambiente.'],
  ['Posso mudar de plano depois?', 'Sim. A gestão da assinatura e dos planos disponíveis fica na área de Planos e Assinatura da Clicko.'],
  ['Como funcionam os limites de criação?', 'Imagens, minutos de vídeo e créditos KLIC seguem os limites apresentados no comparativo de cada plano.'],
  ['Como funcionam as licenças de equipe?', 'Os planos corporativos incluem a quantidade de licenças indicada no catálogo. O acesso principal administra o ambiente e os demais usuários ocupam licenças disponíveis.'],
  ['Preciso de uma capacidade personalizada?', 'O plano Corporativo é definido por proposta comercial. Entre em contato com a equipe de suporte para avaliar sua necessidade.'],
];
async function billingRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/governance/billing${path}`, { ...init, credentials: 'same-origin', headers: { 'Content-Type': 'application/json', ...init?.headers } });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || 'Não foi possível concluir a solicitação.');
  return body as T;
}
export function allowance(plan: SaaSPlan, key: UsageResource, suffix = '') {
  if (!plan.entitlements || !(key in plan.entitlements)) return '—';
  const value = plan.entitlements[key];
  if (value === null) return 'Ilimitado';
  if (key === 'storage_bytes') return `${new Intl.NumberFormat('pt-BR').format((value ?? 0) / 1_000_000_000)} GB`;
  return `${new Intl.NumberFormat('pt-BR').format(value ?? 0)}${suffix}`;
}
export function PlanScene() {
  return <div className="clicko-plan-scene" aria-hidden="true"><div className="clicko-plan-scene__orbit" /><div className="clicko-plan-scene__stage">
    <div className="clicko-plan-scene__tile clicko-plan-scene__tile--media"><span className="clicko-plan-scene__tile-label">CRIAÇÃO</span><span className="clicko-plan-scene__media" /><span className="clicko-plan-scene__media-line" /><span className="clicko-plan-scene__media-line short" /></div>
    <div className="clicko-plan-scene__tile clicko-plan-scene__tile--flow"><span className="clicko-plan-scene__tile-label">FLUXO</span><span className="clicko-plan-scene__flow"><i /><b /><i /><b /><i /></span></div>
    <div className="clicko-plan-scene__tile clicko-plan-scene__tile--data"><span className="clicko-plan-scene__tile-label">EVOLUÇÃO</span><span className="clicko-plan-scene__bars"><i /><i /><i /><i /><i /></span><span className="clicko-plan-scene__data-line" /></div>
  </div><span className="clicko-plan-scene__caption">CRIAÇÃO <b>·</b> INTELIGÊNCIA <b>·</b> GESTÃO</span></div>;
}
export function PlanComparison({ plans }: { plans: SaaSPlan[] }) {
  if (!plans.length) return null;
  return <section className="clicko-plan-comparison" aria-labelledby="clicko-plan-comparison-title"><div className="clicko-plan-section-heading"><div><span className="clicko-plan-eyebrow">TRANSPARÊNCIA EM CADA DETALHE</span><h2 id="clicko-plan-comparison-title">Compare com clareza.</h2><p>Limites e acessos do catálogo atual da Clicko.</p></div></div><div className="clicko-plan-comparison__scroll"><table><thead><tr><th scope="col">Recurso</th>{plans.map(plan => <th scope="col" key={plan.id}>{plan.name}</th>)}</tr></thead><tbody>
    {comparisonRows.map((row, index) => <React.Fragment key={row.label}>{(index === 0 || comparisonRows[index - 1].group !== row.group) && <tr className="clicko-plan-comparison__group"><th colSpan={plans.length + 1} scope="colgroup">{row.group}</th></tr>}<tr><th scope="row">{row.label}</th>{plans.map(plan => <td key={plan.id}>{row.resource ? allowance(plan, row.resource, row.suffix) : row.capability ? (plan.capabilities?.[row.capability] ? <Check size={16} aria-label="Incluído" /> : <span aria-label="Não incluído">—</span>) : row.licenses ? (plan.maxUsers === null ? 'Personalizadas' : plan.includedLicenses ?? plan.maxUsers) : '—'}</td>)}</tr></React.Fragment>)}
  </tbody></table></div></section>;
}
export function PlanAfterAndFaq() {
  return <><section className="clicko-plan-after" aria-labelledby="clicko-plan-after-title"><div><span className="clicko-plan-eyebrow">SIMPLES DO INÍCIO AO USO</span><h2 id="clicko-plan-after-title">Da escolha à criação.</h2></div><ol><li><span>01</span>Escolha seu plano</li><li><span>02</span>Conclua o pagamento seguro</li><li><span>03</span>Aguarde a confirmação</li><li><span>04</span>Crie com os recursos liberados</li></ol></section><section className="clicko-plan-faq" aria-labelledby="clicko-plan-faq-title"><div className="clicko-plan-section-heading"><div><span className="clicko-plan-eyebrow">ANTES DE COMEÇAR</span><h2 id="clicko-plan-faq-title">Dúvidas frequentes.</h2></div></div><div>{questions.map(([question, answer]) => <details key={question}><summary>{question}<ChevronDown size={16} /></summary><p>{answer}</p></details>)}</div></section></>;
}
export function SubscriptionExperience() {
  const { refresh, logout } = useAuth();
  const { theme } = useTheme();
  const [plans, setPlans] = React.useState<SaaSPlan[]>([]);
  const [status, setStatus] = React.useState<BillingStatus>();
  const [selected, setSelected] = React.useState<SaaSPlan['id']>();
  const [busy, setBusy] = React.useState(false);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState('');
  const load = React.useCallback(async () => {
    try {
      const [catalog, nextStatus] = await Promise.all([billingRequest<{ plans: SaaSPlan[] }>('/catalog'), billingRequest<BillingStatus>('/status')]);
      if (!Array.isArray(catalog.plans) || !nextStatus?.subscription) throw new Error('O servidor de assinatura ainda não está disponível. Reinicie o backend da Clicko.');
      setPlans(catalog.plans); setStatus(nextStatus); setError('');
      if (nextStatus.accessAllowed) await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível carregar os planos.'); }
    finally { setLoading(false); }
  }, [refresh]);
  React.useEffect(() => { void load(); }, [load]);
  React.useEffect(() => {
    if (!['pending_checkout', 'pending_payment'].includes(status?.subscription?.status || '')) return;
    const timer = window.setInterval(() => { void load(); }, 5000);
    return () => window.clearInterval(timer);
  }, [load, status?.subscription?.status]);
  const activePlan = plans.find(plan => plan.id === selected);
  const compatible = (plan: SaaSPlan) => !status?.workspace?.kind || plan.audience === 'both' || plan.audience === (status.workspace.kind === 'personal' ? 'personal' : 'organization');
  const checkout = async () => {
    if (!activePlan || activePlan.monthlyPrice === null || !compatible(activePlan)) return;
    setBusy(true); setError('');
    try {
      const result = await billingRequest<{ checkoutUrl: string }>('/checkout', { method: 'POST', body: JSON.stringify({ planId: activePlan.id, seats: activePlan.includedLicenses || 1 }) });
      window.location.assign(result.checkoutUrl);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível iniciar o checkout.'); setBusy(false); }
  };
  return <main data-theme={theme} className="clicko-app-shell clicko-subscription-gate"><div className="clicko-subscription-gate__inner">
    <header className="clicko-subscription-gate__top"><ClickoLogo appearance="seamless" className="h-12 w-32" /><button type="button" onClick={() => void logout()}>Sair</button></header>
    <section className="clicko-plan-hero" aria-labelledby="clicko-plan-title"><div className="clicko-plan-hero__copy"><span className="clicko-plan-eyebrow"><span /> PLANOS E ASSINATURA</span><h1 id="clicko-plan-title">Sua próxima etapa começa aqui.</h1><p>Crie, organize e evolua sua operação em um só lugar. Escolha a capacidade que acompanha seu momento — e cresça com a Clicko.</p><div className="clicko-plan-hero__meta"><span><Check size={14} /> Conteúdo e inteligência</span><span><Check size={14} /> Gestão conectada</span></div></div><PlanScene /></section>
    {status?.subscription && !['no_plan', 'active', 'trialing'].includes(status.subscription.status) && <div className="clicko-plan-notice" role="status"><ShieldCheck size={17} /><span>{statusCopy[status.subscription.status] || 'Acompanhe o estado da sua assinatura.'}</span></div>}
    {error && <div className="clicko-plan-error" role="alert">{error}<button type="button" onClick={() => void load()}>Tentar novamente</button></div>}
    <section className="clicko-plan-catalog" aria-labelledby="clicko-plan-catalog-title"><div className="clicko-plan-section-heading"><div><span className="clicko-plan-eyebrow">ESCOLHA SEU ESPAÇO</span><h2 id="clicko-plan-catalog-title">Planos para cada forma de criar.</h2><p>Valores mensais e recursos definidos pelo catálogo atual da Clicko.</p></div><span className="clicko-plan-period">Cobrança mensal</span></div>
    {loading ? <div className="clicko-plan-loading"><ClickoLoader context="section" label="Carregando planos" message="Carregando planos…" /></div> : <div className="clicko-plan-grid">{plans.map(plan => {
      const isSelected = selected === plan.id;
      const isCurrent = status?.accessAllowed && status.subscription.planId === plan.id;
      const available = compatible(plan);
      return <article key={plan.id} className={`clicko-plan-card ${plan.id === 'business' ? 'is-featured' : ''} ${isSelected ? 'is-selected' : ''} ${!available ? 'is-incompatible' : ''}`}>
        <div className="clicko-plan-card__top"><span className="clicko-plan-card__audience">{plan.audience === 'personal' ? 'PESSOAL' : 'CORPORATIVO'}</span>{isCurrent ? <span className="clicko-plan-card__badge">Seu plano atual</span> : plan.id === 'business' ? <span className="clicko-plan-card__badge">Para crescer</span> : null}</div>
        <h3>{plan.name}</h3><p className="clicko-plan-card__description">{plan.description}</p><div className="clicko-plan-card__price">{money(plan.monthlyPrice)}{plan.monthlyPrice !== null && <small>/ mês</small>}</div>
        <div className="clicko-plan-card__rule" /><div className="clicko-plan-card__metrics"><span><strong>{allowance(plan, 'image_generations')}</strong><small>imagens</small></span><span><strong>{allowance(plan, 'video_minutes')}</strong><small>min de vídeo</small></span></div>
        <ul>{plan.features.map(feature => <li key={feature}><Check size={13} />{feature}</li>)}</ul>
        <div className="clicko-plan-card__foot"><span><Users size={14} /> {plan.maxUsers === null ? 'Licenças personalizadas' : `${plan.includedLicenses ?? plan.maxUsers} licença${(plan.includedLicenses ?? plan.maxUsers) === 1 ? '' : 's'} incluídas`}</span>{!available && <small>Disponível para {plan.audience === 'personal' ? 'Perfil Pessoal' : 'Workspace Corporativo'}</small>}</div>
        {plan.monthlyPrice === null ? <a className="clicko-plan-card__action" href="https://vexelbr.com/#/contato" target="_blank" rel="noopener noreferrer">Falar com atendimento <ArrowRight size={15} /></a> : <button type="button" className="clicko-plan-card__action" disabled={!available || isCurrent} aria-pressed={isSelected} onClick={() => setSelected(plan.id)}>{isCurrent ? 'Plano atual' : !available ? 'Perfil não compatível' : isSelected ? 'Plano selecionado' : 'Escolher plano'}{available && !isCurrent && <ArrowRight size={15} />}</button>}
      </article>;
    })}</div>}</section>
    {activePlan && <section className="clicko-plan-summary" aria-label="Resumo da assinatura"><div><span className="clicko-plan-eyebrow">SUA ESCOLHA</span><h2>{activePlan.name} <span>· {money(activePlan.monthlyPrice)} / mês</span></h2><p>{activePlan.includedLicenses ?? 1} licença{(activePlan.includedLicenses ?? 1) === 1 ? '' : 's'} incluída{(activePlan.includedLicenses ?? 1) === 1 ? '' : 's'} · {allowance(activePlan, 'image_generations')} imagens · {allowance(activePlan, 'video_minutes', ' min')} de vídeo</p><small><ShieldCheck size={14} /> O acesso é liberado após a confirmação do pagamento.</small></div><button type="button" disabled={busy} onClick={() => void checkout()}>{busy ? <><ClickoLoader size="small" tone="light" label="Processando pagamento" /> Processando pagamento…</> : <><CreditCard size={16} /> Continuar para pagamento <ArrowRight size={16} /></>}</button></section>}
    <PlanComparison plans={plans} /><PlanAfterAndFaq />
    <footer className="clicko-plan-footer"><span>Clicko — Desenvolvido pela VEXEL</span><nav aria-label="Informações legais"><a href="/terms">Termos de Uso</a><a href="/privacy">Privacidade</a><a href="/support">Ajuda e suporte</a></nav></footer>
  </div></main>;
}
