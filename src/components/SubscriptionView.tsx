import React from 'react';
import {
  ArrowRight, BarChart3, CalendarDays, Check, ChevronDown,
  CircleHelp, Clock3, CreditCard, Image, Layers3,
  ShieldCheck, Users, Workflow, X,
} from 'lucide-react';
import { useGovernance } from '../context/GovernanceContext';
import { useOffers } from '../context/OfferContext';
import type { SaaSPlan, SubscriptionStatus, WorkspaceSubscription } from '../types';
import { allowance, comparisonRows, questions } from './SubscriptionExperience';
import { ClickoLoader } from './ClickoLoader';
import { KlicSymbol } from './KlicSymbol';
import './SubscriptionView.css';

const number = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 });
const money = (value: number | null | undefined) => value === undefined ? '—' : value === null ? 'Personalizado' : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(value);
const date = (value?: string) => value && Number.isFinite(Date.parse(value)) ? new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' }).format(new Date(value)) : 'Não informada';
const statuses: Record<SubscriptionStatus, string> = {
  no_plan: 'Sem plano', pending_checkout: 'Checkout iniciado', pending_payment: 'Pagamento em processamento',
  active: 'Ativa', trialing: 'Período de teste', past_due: 'Cobrança em atraso', payment_failed: 'Pagamento não confirmado',
  canceled: 'Cancelada', suspended: 'Suspensa', ended: 'Encerrada',
};
const historyLabels: Record<string, string> = {
  created: 'Assinatura criada', checkout_started: 'Checkout iniciado', cancel_scheduled: 'Cancelamento agendado',
  ended: 'Assinatura encerrada', activated: 'Assinatura ativada', renewed: 'Assinatura renovada',
  payment_failed: 'Pagamento não confirmado', canceled: 'Assinatura cancelada', upgrade: 'Upgrade de plano', downgrade: 'Alteração de plano',
};
const categories = [...new Set(comparisonRows.map(row => row.group))];
const supportUrl = 'https://vexelbr.com/#/contato';
type BillingCycle = NonNullable<WorkspaceSubscription['billingCycle']>;
const billingPrice = (plan: SaaSPlan | undefined, cycle: BillingCycle) => plan?.monthlyPrice == null ? plan?.monthlyPrice : plan.monthlyPrice * (cycle === 'annual' ? 12 : 1);
const cycleLabel = (cycle: BillingCycle) => cycle === 'annual' ? 'anual' : 'mensal';
const cycleSuffix = (cycle: BillingCycle) => cycle === 'annual' ? '/ ano' : '/ mês';

function Progress({ value, limit, label }: { value: number; limit: number | null | undefined; label: string }) {
  const percent = typeof limit === 'number' && limit > 0 ? Math.min(100, Math.max(0, value / limit * 100)) : null;
  return <div className="cb-progress" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent ?? undefined} aria-valuetext={percent === null ? (limit === null ? 'Sem limite definido' : limit === 0 ? 'Sem capacidade incluída' : 'Consumo indisponível') : `${number.format(percent)}% utilizado`}><span style={{ width: `${percent ?? 0}%` }} /></div>;
}

function PlanGlyph({ plan }: { plan: SaaSPlan['id'] }) {
  const cubes = plan === 'enterprise' ? [[12, 27], [34, 39], [56, 27], [34, 15]] : plan === 'business' ? [[12, 40], [34, 28], [56, 16]] : [[12, 28], [34, 40], [56, 28]];
  return <svg className={`cb-plan-glyph cb-plan-glyph--${plan}`} viewBox="0 0 95 82" fill="none" aria-hidden="true">{cubes.map(([x, y], index) => <g key={index} transform={`translate(${x} ${y})`}><path d="M0 0 18-10 36 0 18 10Z" className="cb-cube-top" /><path d="M0 0 18 10V29L0 19Z" className="cb-cube-left" /><path d="M18 10 36 0V19L18 29Z" className="cb-cube-right" /></g>)}</svg>;
}

function SubscriptionScene() {
  return <div className="cb-scene" aria-hidden="true"><div className="cb-scene-track" /><div className="cb-scene-stage">
    <div className="cb-scene-panel cb-scene-flow"><span><Workflow size={12} /> FLUXO CRIATIVO</span><div className="cb-scene-nodes"><i /><b /><i /><b /><i /></div><div className="cb-scene-lines"><i /><i /><i /></div><div className="cb-scene-calendar">{Array.from({ length: 12 }, (_, i) => <i key={i} />)}</div></div>
    <div className="cb-scene-panel cb-scene-media"><span><Image size={12} /> CRIAÇÃO</span><div className="cb-scene-image"><i /><i /></div><div className="cb-scene-lines"><i /><i /></div></div>
    <div className="cb-scene-panel cb-scene-growth"><span><BarChart3 size={12} /> EVOLUÇÃO</span><div className="cb-scene-bars"><i /><i /><i /><i /><i /></div></div>
  </div><div className="cb-scene-caption">CRIAÇÃO <b>·</b> INTELIGÊNCIA <b>·</b> GESTÃO</div></div>;
}

function ComparisonValue({ plan, row }: { plan: SaaSPlan; row: typeof comparisonRows[number] }) {
  if (row.resource) return <>{allowance(plan, row.resource, row.suffix)}</>;
  if (row.capability) {
    const value = plan.capabilities?.[row.capability];
    return value === true ? <><Check className="cb-check" size={16} aria-hidden="true" /><span className="cb-sr-only">Incluído</span></> : <span className="cb-unavailable">{value === false ? 'Não incluído' : 'Não informado'}</span>;
  }
  return <>{plan.maxUsers === null ? 'Personalizadas' : plan.includedLicenses ?? plan.maxUsers}</>;
}

function Comparison({ plans, currentPlanId, billingCycle, currentBillingCycle }: { plans: SaaSPlan[]; currentPlanId?: SaaSPlan['id']; billingCycle: BillingCycle; currentBillingCycle: BillingCycle }) {
  if (!plans.length) return null;
  return <section className="cb-section cb-comparison" aria-labelledby="cb-comparison-title"><div className="cb-section-heading"><div><span className="cb-eyebrow">TRANSPARÊNCIA EM CADA DETALHE</span><h2 id="cb-comparison-title">Compare com clareza.</h2><p>Cada recurso, cada limite. Encontre a capacidade certa para sua operação.</p></div></div>
    <div className="cb-comparison-table" tabIndex={0} role="region" aria-label="Comparativo completo dos planos"><table><thead><tr><th scope="col">Planos Workspace</th>{plans.map(plan => <th scope="col" key={plan.id}><span>{plan.name}</span><small>{plan.id === currentPlanId && billingCycle === currentBillingCycle ? 'Seu plano atual' : plan.monthlyPrice === null ? 'Sob consulta' : `${money(billingPrice(plan, billingCycle))} ${cycleSuffix(billingCycle)}`}</small></th>)}</tr></thead><tbody>{categories.map(category => <React.Fragment key={category}><tr className="cb-category-row"><th scope="colgroup" colSpan={plans.length + 1}>{category}</th></tr>{comparisonRows.filter(row => row.group === category).map(row => <tr key={row.label}><th scope="row">{row.label}</th>{plans.map(plan => <td key={plan.id}><ComparisonValue plan={plan} row={row} /></td>)}</tr>)}</React.Fragment>)}</tbody></table></div>
    <div className="cb-comparison-mobile">{categories.map((category, index) => <details key={category} open={index === 0}><summary>{category}<ChevronDown size={17} /></summary>{comparisonRows.filter(row => row.group === category).map(row => <div className="cb-mobile-resource" key={row.label}><h3>{row.label}</h3><dl>{plans.map(plan => <div key={plan.id}><dt>{plan.name}</dt><dd><ComparisonValue plan={plan} row={row} /></dd></div>)}</dl></div>)}</details>)}</div>
  </section>;
}

export const SubscriptionView: React.FC = () => {
  const { plans, subscription, workspace, licenses, usage: usagePool, changePlan, loading, environmentMode } = useGovernance();
  const { openOffer } = useOffers();
  const [selectedPlan, setSelectedPlan] = React.useState<SaaSPlan['id']>();
  const [billingCycle, setBillingCycle] = React.useState<BillingCycle>('monthly');
  const [submitting, setSubmitting] = React.useState(false);
  const submittingRef = React.useRef(false);
  const summaryRef = React.useRef<HTMLDivElement>(null);
  const currentPlan = plans.find(plan => plan.id === subscription?.planId);
  const currentBillingCycle: BillingCycle = subscription?.billingCycle || 'monthly';
  const selected = plans.find(plan => plan.id === selectedPlan);
  const occupiedSeats = licenses.filter(item => item.status === 'in_use' || item.status === 'reserved').length || (environmentMode === 'personal' ? 1 : 0);
  const visiblePlans = plans.filter(plan => plan.audience === 'both' || plan.audience === (environmentMode === 'personal' ? 'personal' : 'organization'));
  const klic = usagePool?.resources.klic_credits;
  const history = [...(subscription?.history ?? [])].reverse();

  React.useEffect(() => { setSelectedPlan(undefined); setBillingCycle(subscription?.billingCycle || 'monthly'); }, [subscription?.planId, subscription?.billingCycle, workspace?.id]);

  const confirmPlan = async () => {
    if (!selected || (selected.id === subscription?.planId && billingCycle === currentBillingCycle) || submittingRef.current) return;
    if (selected.monthlyPrice === null) { window.open(supportUrl, '_blank', 'noopener,noreferrer'); return; }
    const currentIndex = plans.findIndex(plan => plan.id === subscription?.planId);
    const targetIndex = plans.findIndex(plan => plan.id === selected.id);
    if (billingCycle === 'monthly' && targetIndex > currentIndex && openOffer({ context: 'upgrade', targetPlanId: selected.id, source: 'subscription.plan-selector', reason: `Você escolheu o plano ${selected.name}. Veja apenas as diferenças relevantes antes de continuar.` })) return;
    submittingRef.current = true;
    setSubmitting(true);
    try { if (await changePlan(selected.id, billingCycle)) setSelectedPlan(undefined); }
    finally { submittingRef.current = false; setSubmitting(false); }
  };

  const selectPlan = (plan: SaaSPlan) => {
    setSelectedPlan(plan.id);
    requestAnimationFrame(() => summaryRef.current?.scrollIntoView({ block: 'nearest', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' }));
  };

  if (loading && !subscription) return <div id="clicko-subscription-page" className="clicko-billing-page"><div className="cb-loading"><ClickoLoader context="section" label="Carregando sua assinatura" message="Carregando sua assinatura…" /></div></div>;

  return <div id="clicko-subscription-page" className="clicko-billing-page">
    <header className="cb-hero"><div className="cb-hero-copy"><span className="cb-eyebrow"><span className="cb-dot" /> PLANOS E ASSINATURA</span><h1>Sua operação,<br />no seu ritmo.</h1><p>Gerencie sua assinatura e acompanhe a capacidade que sustenta cada etapa de criação, inteligência e crescimento da Clicko.</p></div><SubscriptionScene /></header>

    <section className="cb-overview" aria-label="Sua assinatura atual">
      <article className="cb-current"><div className="cb-current-top"><span className="cb-badge"><span className="cb-dot" /> Plano atual</span><span className="cb-subtle">{environmentMode === 'personal' ? 'Perfil Pessoal' : 'Workspace Corporativo'}</span></div><div className="cb-current-main"><div><h2>{currentPlan?.name || 'Plano não informado'}</h2><p>{currentPlan?.description}</p></div><div className="cb-current-price"><strong>{money(billingPrice(currentPlan, currentBillingCycle))}</strong>{typeof currentPlan?.monthlyPrice === 'number' && <span>por {currentBillingCycle === 'annual' ? 'ano' : 'mês'}</span>}</div></div>
        <div className="cb-current-dates"><div><span>Assinatura ativa desde</span><strong>{date(subscription?.startedAt)}</strong></div><div><span>{subscription?.cancelAtPeriodEnd ? 'Acesso até' : 'Renovação em'}</span><strong>{date(subscription?.cancelAtPeriodEnd ? subscription.endsAt || subscription.renewsAt : subscription?.renewsAt)}</strong></div><div><span>Status</span><strong className="cb-status">{subscription?.cancelAtPeriodEnd ? 'Cancelamento agendado' : subscription ? statuses[subscription.status] : 'Não informado'}</strong></div></div>
        <div className="cb-payment"><span className="cb-icon-box"><CreditCard size={18} /></span><div><strong>{subscription?.paymentMethod || 'Forma de pagamento não informada'}</strong><p>{subscription?.billingEmail ? <>Cobrança para <span>{subscription.billingEmail}</span></> : 'E-mail de cobrança não informado'}</p></div><ShieldCheck size={17} className="cb-payment-shield" /></div>
        {subscription?.pendingPlanId && <p className="cb-pending" role="status"><Clock3 size={14} />Alteração para {plans.find(plan => plan.id === subscription.pendingPlanId)?.name || subscription.pendingPlanId}, com cobrança {cycleLabel(subscription.pendingBillingCycle || 'monthly')}, aguardando confirmação.</p>}
      </article>
      <article className="cb-capacity-card"><div className="cb-card-title"><h2>Uso de assentos</h2><Users size={18} /></div><div className="cb-capacity-value">{number.format(occupiedSeats)}<span>/ {workspace?.maxUsers === null ? 'Ilimitado' : workspace?.maxUsers ?? '—'}</span></div><Progress value={occupiedSeats} limit={workspace?.maxUsers} label="Uso de assentos" /><p>Convites pendentes reservam uma vaga do plano.</p><span className="cb-card-bottom">{workspace?.maxUsers === null ? 'Capacidade personalizada' : typeof workspace?.maxUsers === 'number' ? `${Math.max(0, workspace.maxUsers - occupiedSeats)} ${workspace.maxUsers - occupiedSeats === 1 ? 'vaga disponível' : 'vagas disponíveis'}` : 'Capacidade não informada'}</span></article>
      <article className="cb-capacity-card cb-klic"><div className="cb-card-title"><h2>Consumo da KLIC</h2><KlicSymbol /></div><div className="cb-capacity-value">{klic ? number.format(klic.used) : '—'}<span>/ {klic?.limit === null ? 'Ilimitado' : klic ? number.format(klic.limit) : '—'}</span></div><Progress value={klic?.used ?? 0} limit={klic?.limit} label="Consumo dos créditos KLIC" /><p>{environmentMode === 'company' ? 'Saldo compartilhado pela organização; licenças não ampliam este limite.' : 'Saldo individual da sua Conta Pessoal.'}</p><span className="cb-card-bottom"><span className="cb-klic-dot" /> Créditos de inteligência</span></article>
    </section>

    <section className="cb-section cb-catalog" aria-labelledby="cb-plans-title"><div className="cb-section-heading"><div><span className="cb-eyebrow">EVOLUA QUANDO PRECISAR</span><h2 id="cb-plans-title">Espaço para sua próxima etapa.</h2><p>Compare as capacidades do seu perfil e selecione uma nova etapa.</p></div><div className="cb-billing-control"><span><CalendarDays size={15} /> Periodicidade</span><div className="cb-billing-toggle" role="radiogroup" aria-label="Periodicidade da cobrança"><button type="button" role="radio" aria-checked={billingCycle === 'monthly'} className={billingCycle === 'monthly' ? 'is-active' : ''} onClick={() => { setBillingCycle('monthly'); setSelectedPlan(undefined); }}>Mensal</button><button type="button" role="radio" aria-checked={billingCycle === 'annual'} className={billingCycle === 'annual' ? 'is-active' : ''} onClick={() => { setBillingCycle('annual'); setSelectedPlan(undefined); }}>Anual</button></div></div></div><h3 className="cb-sr-only">Planos disponíveis</h3>
      <div className="cb-plans">{visiblePlans.map(plan => { const samePlan = plan.id === subscription?.planId; const current = samePlan && billingCycle === currentBillingCycle; const isSelected = plan.id === selectedPlan; return <article key={plan.id} className={`cb-plan ${current ? 'is-current' : ''} ${plan.id === 'business' ? 'is-featured' : ''} ${plan.id === 'enterprise' ? 'is-custom' : ''} ${isSelected ? 'is-selected' : ''}`}><div className="cb-plan-top"><span className="cb-subtle">{plan.audience === 'personal' ? 'INDIVIDUAL' : 'CORPORATIVO'}</span><PlanGlyph plan={plan.id} /></div><h3>{plan.name}</h3><p className="cb-plan-description">{plan.description}</p><div className="cb-plan-price">{money(billingPrice(plan, billingCycle))}{plan.monthlyPrice !== null && <small>{cycleSuffix(billingCycle)}</small>}</div>{billingCycle === 'annual' && plan.monthlyPrice !== null && <p className="cb-plan-equivalent">Equivale a {money(plan.monthlyPrice)} por mês</p>}<div className="cb-plan-features"><ul>{plan.features.map(feature => <li key={feature}><Check size={15} />{feature}</li>)}</ul></div><div className="cb-plan-seats"><Users size={16} />{plan.maxUsers === null ? 'Licenças personalizadas' : `${plan.includedLicenses ?? plan.maxUsers} ${(plan.includedLicenses ?? plan.maxUsers) === 1 ? 'licença incluída' : 'licenças incluídas'}`}</div>
        {current ? <div className="cb-current-label"><Check size={16} /> Seu plano atual</div> : plan.monthlyPrice === null ? <a className="cb-button" href={supportUrl} target="_blank" rel="noopener noreferrer">Falar com atendimento <ArrowRight size={16} /></a> : <button type="button" className={`cb-button ${plan.id === 'business' ? 'cb-button-primary' : ''}`} aria-pressed={isSelected} onClick={() => selectPlan(plan)}>{isSelected ? 'Opção selecionada' : samePlan ? `Alterar para ${billingCycle === 'annual' ? 'anual' : 'mensal'}` : 'Selecionar plano'}{isSelected ? <Check size={16} /> : <ArrowRight size={16} />}</button>}
      </article>; })}</div>
      {!visiblePlans.length && <div className="cb-empty"><Layers3 size={20} /><p>Nenhum plano disponível para este perfil no momento.</p></div>}
      {selected && (selected.id !== subscription?.planId || billingCycle !== currentBillingCycle) && <div className="cb-selection" ref={summaryRef} aria-label="Resumo da alteração de plano"><div><span className="cb-eyebrow">SUA PRÓXIMA ETAPA</span><h3>{selected.name} <span>{money(billingPrice(selected, billingCycle))}{selected.monthlyPrice !== null && ` ${cycleSuffix(billingCycle)}`}</span></h3><p>{selected.maxUsers === null ? 'Capacidade personalizada.' : `${selected.includedLicenses ?? selected.maxUsers} licenças incluídas.`} Cobrança {cycleLabel(billingCycle)}; a mudança entra em vigor após confirmação do provedor.</p></div><div className="cb-selection-actions"><button type="button" className="cb-button cb-button-primary" disabled={submitting} onClick={() => void confirmPlan()}>{submitting ? <><ClickoLoader size="tiny" tone="light" label="Processando alteração de plano" /> Processando…</> : <>Continuar <ArrowRight size={16} /></>}</button><button type="button" className="cb-selection-close" aria-label="Limpar seleção de plano" disabled={submitting} onClick={() => setSelectedPlan(undefined)}><X size={17} /></button></div></div>}
    </section>

    <Comparison plans={visiblePlans} currentPlanId={subscription?.planId} billingCycle={billingCycle} currentBillingCycle={currentBillingCycle} />

    <section className="cb-section cb-notes" aria-labelledby="cb-notes-title"><header className="cb-notes-heading"><div><span className="cb-eyebrow">TRANSPARÊNCIA DA ASSINATURA</span><h2 id="cb-notes-title">Informações da assinatura</h2><p>Regras de capacidade, cobrança e movimentações do seu plano.</p></div></header><div className="cb-notes-list"><article className="cb-note-card cb-rules"><div className="cb-note-title"><span><ShieldCheck size={18} /></span><div><small>Capacidade e cobrança</small><h3>Política de capacidade</h3></div></div><ul><li><span className="cb-note-index">01</span><div><strong>Continuidade dos conteúdos</strong><p>Ao atingir o limite, novas operações são bloqueadas. Seus conteúdos existentes são preservados.</p></div></li><li><span className="cb-note-index">02</span><div><strong>Gestão de assentos</strong><p>Usuários desativados liberam assentos; convites pendentes reservam uma vaga.</p></div></li><li><span className="cb-note-index">03</span><div><strong>Alterações de plano</strong><p>Mudanças de plano passam pelo checkout e dependem da confirmação do provedor.</p></div></li></ul></article><article className="cb-note-card cb-history"><div className="cb-note-title"><span><Clock3 size={18} /></span><div><small>Cobrança e mudanças</small><h3>Histórico da assinatura</h3></div></div>{history.length ? <details><summary><span>{history.length} {history.length === 1 ? 'evento registrado' : 'eventos registrados'}</span><ChevronDown size={16} /></summary><ol>{history.map(item => <li key={item.id}><span className="cb-timeline-dot" /><div><strong>{historyLabels[item.event] || item.event.replaceAll('_', ' ')}</strong><time dateTime={item.occurredAt}>{date(item.occurredAt)}</time></div><span>{statuses[item.toStatus]}</span></li>)}</ol></details> : <div className="cb-history-empty"><span className="cb-timeline-dot" /><div><strong>Nenhuma movimentação registrada</strong><p>Nenhum evento de cobrança foi confirmado para esta assinatura.</p></div></div>}</article></div></section>

    <section className="cb-section cb-faq" aria-labelledby="cb-faq-title"><div><span className="cb-eyebrow">ANTES DE COMEÇAR</span><h2 id="cb-faq-title">Dúvidas frequentes.</h2><p>Respostas rápidas para escolher e seguir com segurança.</p><a href={supportUrl} target="_blank" rel="noopener noreferrer"><CircleHelp size={15} /> Falar com atendimento <ArrowRight size={14} /></a></div><div className="cb-questions">{questions.map(([question, answer]) => <details key={question}><summary>{question}<ChevronDown size={16} /></summary><p>{answer}</p></details>)}</div></section>
  </div>;
};
