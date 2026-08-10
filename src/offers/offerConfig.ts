import type { OfferConfiguration, OfferRequest, SaaSPlan } from '../types';

export const OFFER_CONFIGURATIONS: OfferConfiguration[] = [
  {
    id: 'company-solo-to-team', enabled: true,
    contexts: ['upgrade', 'seat_increase', 'premium_feature', 'limit_reached'],
    environment: 'company', eligibleCurrentPlans: ['solo'], targetPlanId: 'team',
    headline: 'Colaboração com governança, sem perder o ritmo.',
    description: 'O plano Equipe libera a estrutura necessária para trabalhar com colaboradores e aprovações.',
    ctaLabel: 'Fazer upgrade',
    benefits: ['Até 6 usuários', 'Fluxo de aprovação', 'Automações'],
  },
  {
    id: 'company-solo-to-business', enabled: true,
    contexts: ['upgrade', 'seat_increase', 'premium_feature', 'limit_reached'],
    environment: 'company', eligibleCurrentPlans: ['solo'], targetPlanId: 'business',
    headline: 'Mais capacidade e controle para estruturar sua operação.',
    description: 'O plano Negócios reúne colaboração, análises avançadas e auditoria completa.',
    ctaLabel: 'Fazer upgrade',
    benefits: ['Até 16 usuários', 'Análises avançadas', 'Auditoria completa'],
  },
  {
    id: 'company-solo-to-enterprise', enabled: true,
    contexts: ['upgrade', 'seat_increase', 'premium_feature', 'limit_reached'],
    environment: 'company', eligibleCurrentPlans: ['solo'], targetPlanId: 'enterprise',
    headline: 'Governança personalizada para uma operação maior.',
    description: 'O plano Corporativo possui condições personalizadas e exige definição comercial antes da ativação.',
    ctaLabel: 'Ver condições',
    benefits: ['Usuários personalizados', 'SLA dedicado', 'Governança avançada'],
  },
  {
    id: 'company-team-to-business', enabled: true,
    contexts: ['upgrade', 'seat_increase', 'premium_feature', 'limit_reached'],
    environment: 'company', eligibleCurrentPlans: ['team'], targetPlanId: 'business',
    headline: 'Mais capacidade para uma operação que está crescendo.',
    description: 'O plano Negócios amplia assentos e adiciona recursos de análise e auditoria.',
    ctaLabel: 'Fazer upgrade',
    benefits: ['Até 16 usuários', 'Análises avançadas', 'Auditoria completa'],
    badge: 'Recomendado para escala',
  },
  {
    id: 'company-team-to-enterprise', enabled: true,
    contexts: ['upgrade', 'seat_increase', 'premium_feature', 'limit_reached'],
    environment: 'company', eligibleCurrentPlans: ['team'], targetPlanId: 'enterprise',
    headline: 'Governança personalizada para uma operação maior.',
    description: 'O plano Corporativo possui condições personalizadas e exige definição comercial antes da ativação.',
    ctaLabel: 'Ver condições',
    benefits: ['Usuários personalizados', 'SLA dedicado', 'Governança avançada'],
  },
  {
    id: 'company-business-to-enterprise', enabled: true,
    contexts: ['upgrade', 'seat_increase', 'premium_feature', 'limit_reached'],
    environment: 'company', eligibleCurrentPlans: ['business'], targetPlanId: 'enterprise',
    headline: 'Capacidade e governança definidas para sua operação.',
    description: 'O plano Corporativo possui condições personalizadas e exige contato comercial.',
    ctaLabel: 'Solicitar condições',
    benefits: ['Usuários personalizados', 'SLA dedicado', 'Governança avançada'],
  },
  {
    id: 'personal-first-subscription', enabled: true,
    contexts: ['first_subscription', 'renewal'],
    environment: 'personal', eligibleCurrentPlans: ['solo'], targetPlanId: 'solo',
    headline: 'Sua produção pessoal organizada em um único fluxo.',
    description: 'O plano Solo reúne criação com IA e calendário editorial para uso individual.',
    ctaLabel: 'Continuar com o plano Solo',
    benefits: ['Uso individual', 'Criação com IA', 'Calendário editorial'],
  },
];

export function isPromotionActive(offer: OfferConfiguration, at = new Date()) {
  if (!offer.promotion) return false;
  const current = at.getTime();
  return current >= new Date(offer.promotion.startsAt).getTime() && current <= new Date(offer.promotion.endsAt).getTime();
}

export function resolveOfferConfiguration(
  request: OfferRequest,
  currentPlanId: SaaSPlan['id'],
  environment: 'personal' | 'company',
) {
  return OFFER_CONFIGURATIONS.find((offer) =>
    offer.enabled
    && offer.contexts.includes(request.context)
    && (offer.environment === 'both' || offer.environment === environment)
    && offer.eligibleCurrentPlans.includes(currentPlanId)
    && (!request.targetPlanId || offer.targetPlanId === request.targetPlanId),
  );
}

export function relevantPlanDifferences(currentPlan: SaaSPlan, targetPlan: SaaSPlan, request: OfferRequest) {
  const differences: Array<{ label: string; current: string; target: string }> = [];
  if (request.context === 'seat_increase' || request.context === 'limit_reached') {
    differences.push({
      label: 'Assentos',
      current: currentPlan.maxUsers === null ? 'Personalizado' : `Até ${currentPlan.maxUsers}`,
      target: targetPlan.maxUsers === null ? 'Personalizado' : `Até ${targetPlan.maxUsers}`,
    });
  }
  const newFeatures = targetPlan.features.filter((feature) => !currentPlan.features.includes(feature));
  newFeatures.slice(0, request.context === 'seat_increase' ? 1 : 2).forEach((feature) => {
    differences.push({ label: feature, current: 'Não incluído', target: 'Incluído' });
  });
  return differences.slice(0, 3);
}
