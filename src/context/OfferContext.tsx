import React from 'react';
import { ArrowRight, Check, CheckCircle2, ChevronLeft, CreditCard, ShieldCheck, Sparkles, Users, X } from 'lucide-react';
import type { OfferConfiguration, OfferEventName, OfferRequest, SaaSPlan } from '../types';
import { isPromotionActive, relevantPlanDifferences, resolveOfferConfiguration } from '../offers/offerConfig';
import { useGovernance } from './GovernanceContext';

type OfferContextValue = {
  openOffer: (request: OfferRequest) => boolean;
  closeOffer: () => void;
  isOfferOpen: boolean;
};

type ActiveOffer = {
  request: OfferRequest;
  config: OfferConfiguration;
  currentPlan: SaaSPlan;
  targetPlan: SaaSPlan;
};

const OfferContext = React.createContext<OfferContextValue | null>(null);

const currency = (value: number | null) => value === null
  ? 'Personalizado'
  : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);

const contextLabel: Record<OfferRequest['context'], string> = {
  first_subscription: 'Primeira assinatura', upgrade: 'Upgrade inteligente',
  seat_increase: 'Capacidade da equipe', premium_feature: 'Recurso premium',
  limit_reached: 'Limite do plano', renewal: 'Renovação', promotion: 'Condição configurada',
};

export function OfferProvider({ children }: { children: React.ReactNode }) {
  const { environmentMode, plans, subscription, changePlan, recordOfferEvent } = useGovernance();
  const [active, setActive] = React.useState<ActiveOffer | null>(null);
  const [stage, setStage] = React.useState<'offer' | 'checkout' | 'success'>('offer');
  const [submitting, setSubmitting] = React.useState(false);

  const track = React.useCallback((event: OfferEventName, item: ActiveOffer) => {
    void recordOfferEvent({
      event, offerId: item.config.id, context: item.request.context, source: item.request.source,
      currentPlanId: item.currentPlan.id, targetPlanId: item.targetPlan.id,
      occurredAt: new Date().toISOString(), experimentKey: item.config.experimentKey, variantId: item.config.variantId,
    });
  }, [recordOfferEvent]);

  const openOffer = React.useCallback((request: OfferRequest) => {
    const currentPlan = plans.find((plan) => plan.id === subscription?.planId);
    if (!currentPlan) return false;
    const config = resolveOfferConfiguration(request, currentPlan.id, environmentMode);
    const targetPlan = config && plans.find((plan) => plan.id === config.targetPlanId);
    if (!config || !targetPlan) return false;
    const frequencyKey = `clicko:offer-seen:${environmentMode}:${config.id}:${request.context}:${request.source}`;
    if (request.automatic && window.sessionStorage.getItem(frequencyKey)) return false;
    window.sessionStorage.setItem(frequencyKey, new Date().toISOString());
    const item = { request, config, currentPlan, targetPlan };
    setActive(item); setStage('offer');
    track('OFFER_VIEWED', item);
    return true;
  }, [environmentMode, plans, subscription?.planId, track]);

  const closeOffer = React.useCallback(() => {
    if (active && stage !== 'success') track('OFFER_DISMISSED', active);
    setActive(null); setStage('offer'); setSubmitting(false);
  }, [active, stage, track]);

  React.useEffect(() => {
    if (!active) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeOffer();
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [active, closeOffer]);

  const startCheckout = () => {
    if (!active) return;
    track('OFFER_CLICKED', active); track('UPGRADE_STARTED', active); track('CHECKOUT_STARTED', active);
    setStage('checkout');
  };

  const completeCheckout = async () => {
    if (!active || active.targetPlan.monthlyPrice === null) return;
    setSubmitting(true);
    const completed = await changePlan(active.targetPlan.id);
    setSubmitting(false);
    if (!completed) return;
    track('CHECKOUT_COMPLETED', active);
    window.sessionStorage.setItem(`clicko:offer-completed:${active.config.id}`, new Date().toISOString());
    setStage('success');
  };

  const value = React.useMemo(() => ({ openOffer, closeOffer, isOfferOpen: Boolean(active) }), [openOffer, closeOffer, active]);
  const promotionActive = active ? isPromotionActive(active.config) : false;
  const price = active && promotionActive ? active.config.promotion!.promotionalMonthlyPrice : active?.targetPlan.monthlyPrice ?? null;
  const differences = active ? relevantPlanDifferences(active.currentPlan, active.targetPlan, active.request) : [];

  return <OfferContext.Provider value={value}>
    {children}
    {active && <div className="clicko-offer-overlay fixed inset-0 z-[110] grid place-items-center overflow-y-auto bg-black/72 p-3 backdrop-blur-sm sm:p-6">
      <button aria-label="Fechar oferta" onClick={closeOffer} className="absolute inset-0 cursor-default" />
      <section role="dialog" aria-modal="true" aria-labelledby="clicko-offer-title" className="clicko-offer-dialog relative my-auto w-full max-w-[760px] overflow-hidden rounded-2xl border border-white/[0.09] bg-[#0d0d0d] shadow-2xl">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[#ff5c5c]/70 to-transparent" />
        <button onClick={closeOffer} aria-label="Fechar" className="absolute right-4 top-4 z-10 grid h-8 w-8 place-items-center rounded-lg border border-white/[0.06] bg-black/30 text-[#777] hover:text-white"><X className="h-4 w-4" /></button>

        {stage === 'offer' && <div className="p-5 sm:p-7">
          <div className="pr-10"><div className="flex flex-wrap items-center gap-2"><span className="rounded-full border border-[#ff7a00]/20 bg-[#ff7a00]/[0.07] px-2.5 py-1 text-[8px] font-semibold uppercase tracking-[0.13em] text-[#ff9a3d]">{contextLabel[active.request.context]}</span>{active.config.badge && <span className="rounded-full bg-[#ff5c5c]/10 px-2.5 py-1 text-[8px] text-[#ff8a8a]">{active.config.badge}</span>}</div><h2 id="clicko-offer-title" className="mt-4 max-w-xl text-[clamp(22px,3vw,34px)] font-semibold leading-tight tracking-[-0.035em] text-white">{active.request.context === 'premium_feature' && active.request.featureLabel ? `Libere ${active.request.featureLabel}.` : active.config.headline}</h2><p className="mt-3 max-w-2xl text-[10px] leading-5 text-[#909090]">{active.request.reason} {active.config.description}</p></div>

          <div className="mt-6 grid gap-4 md:grid-cols-[1fr_250px]">
            <div className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-4"><div className="flex items-center justify-between gap-4"><div><span className="text-[8px] uppercase tracking-[0.14em] text-[#666]">Próximo plano</span><h3 className="mt-1 text-lg font-semibold text-white">{active.targetPlan.name}</h3></div><div className="text-right">{promotionActive && <div className="text-[9px] text-[#666] line-through">{currency(active.config.promotion!.originalMonthlyPrice)}</div>}<strong className="text-xl text-white">{currency(price)}</strong>{price !== null && <span className="block text-[8px] text-[#666]">por mês</span>}</div></div><div className="mt-4 grid gap-2 sm:grid-cols-2">{active.config.benefits.slice(0, 4).map((benefit) => <div key={benefit} className="flex items-center gap-2 text-[9px] text-[#bcbcbc]"><span className="grid h-4 w-4 place-items-center rounded-full bg-[#ff5c5c]/10 text-[#ff7c7c]"><Check className="h-2.5 w-2.5" /></span>{benefit}</div>)}</div>{active.config.bonus && <div className="mt-4 rounded-lg border border-[#ff7a00]/15 bg-[#ff7a00]/[0.055] p-3 text-[8px] text-[#d8985b]">{active.config.bonus}</div>}{promotionActive && <p className="mt-3 text-[8px] leading-relaxed text-[#777]">{active.config.promotion!.terms} · válida até {new Date(active.config.promotion!.endsAt).toLocaleString('pt-BR')}.</p>}</div>
            <div className="rounded-xl border border-white/[0.07] bg-black/35 p-4"><span className="text-[8px] uppercase tracking-[0.14em] text-[#666]">O que muda agora</span><div className="mt-3 space-y-3">{differences.length ? differences.map((item) => <div key={item.label}><div className="text-[8px] text-[#8c8c8c]">{item.label}</div><div className="mt-1 flex items-center gap-2 text-[9px]"><span className="text-[#666]">{item.current}</span><ArrowRight className="h-3 w-3 text-[#ff5c5c]" /><strong className="text-white">{item.target}</strong></div></div>) : <p className="text-[9px] leading-relaxed text-[#888]">Os benefícios configurados do plano passam a ficar disponíveis após a confirmação.</p>}</div></div>
          </div>

          <div className="mt-6 flex flex-col-reverse gap-2 border-t border-white/[0.06] pt-5 sm:flex-row sm:items-center sm:justify-between"><button onClick={closeOffer} className="px-3 py-2 text-[9px] text-[#777] hover:text-white">Agora não</button><button onClick={startCheckout} className="flex h-11 items-center justify-center gap-2 rounded-lg bg-[#ff5c5c] px-5 text-[10px] font-bold text-white">{active.config.ctaLabel}<ArrowRight className="h-4 w-4" /></button></div>
        </div>}

        {stage === 'checkout' && <div className="p-5 sm:p-7"><button onClick={() => setStage('offer')} className="flex items-center gap-2 text-[9px] text-[#777] hover:text-white"><ChevronLeft className="h-4 w-4" />Voltar à oferta</button><div className="mt-6 grid gap-6 md:grid-cols-[1fr_280px]"><div><div className="flex items-center gap-2 text-[9px] uppercase tracking-[0.15em] text-[#ff7a00]"><CreditCard className="h-4 w-4" />Confirmação do plano</div><h2 id="clicko-offer-title" className="mt-3 text-2xl font-semibold text-white">{active.targetPlan.name}</h2><p className="mt-2 text-[10px] leading-5 text-[#888]">Revise plano, periodicidade e valor antes de confirmar. Não há desconto promocional aplicado quando nenhuma promoção está configurada.</p><div className="mt-5 space-y-3">{active.targetPlan.features.map((feature) => <div key={feature} className="flex items-center gap-2 text-[9px] text-[#bbb]"><CheckCircle2 className="h-4 w-4 text-[#ff7a00]" />{feature}</div>)}</div></div><aside className="rounded-xl border border-white/[0.08] bg-black/35 p-5"><span className="text-[8px] uppercase tracking-[0.14em] text-[#666]">Resumo</span><div className="mt-4 flex items-center justify-between text-[10px]"><span className="text-[#888]">Periodicidade</span><strong className="text-white">Mensal</strong></div><div className="mt-3 flex items-center justify-between text-[10px]"><span className="text-[#888]">Plano</span><strong className="text-white">{active.targetPlan.name}</strong></div><div className="my-4 h-px bg-white/[0.07]" /><div className="flex items-end justify-between"><span className="text-[9px] text-[#888]">Total mensal</span><strong className="text-xl text-white">{currency(price)}</strong></div>{price === null ? <div className="mt-5 rounded-lg border border-[#ff7a00]/20 bg-[#ff7a00]/[0.06] p-3 text-[8px] leading-relaxed text-[#d79a62]">Este plano possui condições personalizadas. Nenhuma alteração ou cobrança será realizada nesta etapa.</div> : <><div className="mt-5 flex items-start gap-2 rounded-lg border border-white/[0.06] p-3 text-[8px] leading-relaxed text-[#777]"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#ff7a00]" />Ao confirmar, o plano e seus limites são atualizados imediatamente no ambiente.</div><button onClick={() => void completeCheckout()} disabled={submitting} className="mt-4 flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-[#ff5c5c] text-[10px] font-bold text-white disabled:opacity-50">{submitting ? <Sparkles className="h-4 w-4 animate-pulse" /> : <CreditCard className="h-4 w-4" />}{submitting ? 'Atualizando plano…' : 'Confirmar alteração'}</button></>}</aside></div></div>}

        {stage === 'success' && <div className="grid min-h-[420px] place-items-center p-7 text-center"><div><span className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-[#ff5c5c]/10 text-[#ff7c7c]"><CheckCircle2 className="h-7 w-7" /></span><h2 id="clicko-offer-title" className="mt-5 text-2xl font-semibold text-white">Plano atualizado.</h2><p className="mx-auto mt-2 max-w-sm text-[10px] leading-5 text-[#888]">{active.targetPlan.name} já está ativo. Limites, capacidade e benefícios foram sincronizados com o ambiente.</p><button onClick={closeOffer} className="mt-6 rounded-lg bg-white px-5 py-2.5 text-[10px] font-bold text-black">Continuar no Clicko</button></div></div>}
      </section>
    </div>}
  </OfferContext.Provider>;
}

export function useOffers() {
  const value = React.useContext(OfferContext);
  if (!value) throw new Error('useOffers deve ser usado dentro de OfferProvider.');
  return value;
}
