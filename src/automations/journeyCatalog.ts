import { newFlow, uid, type Flow, type FlowStep } from './automationModel';

export type JourneyGoal = {
  id: string;
  category: string;
  title: string;
  objective: string;
  signal: string;
  condition: string;
  action: string;
  responsible: string;
  deadline: string;
  expectedResult: string;
  indicator: string;
  requiresClient: boolean;
  requiresOperation: boolean;
};

export const journeyGoals: JourneyGoal[] = [
  { id: 'client-onboarding', category: 'Entrada', title: 'Organizar a entrada de um cliente', objective: 'Iniciar o relacionamento com etapas claras.', signal: 'Cliente cadastrado na carteira.', condition: 'Contato principal e responsável definidos.', action: 'Preparar checklist de boas-vindas e notificar o responsável.', responsible: 'Responsável pela conta', deadline: 'Até 1 dia útil', expectedResult: 'Entrada organizada sem informações perdidas.', indicator: 'Tempo até o primeiro contato', requiresClient: true, requiresOperation: false },
  { id: 'request-documents', category: 'Documentos', title: 'Solicitar e cobrar documentos', objective: 'Manter pendências documentais visíveis.', signal: 'Documento solicitado ou prazo próximo.', condition: 'Documento ainda não recebido.', action: 'Lembrar o responsável e preparar nova solicitação ao cliente.', responsible: 'Responsável pela conta', deadline: '2 dias antes do prazo', expectedResult: 'Documentos recebidos no período previsto.', indicator: 'Pendências documentais em aberto', requiresClient: true, requiresOperation: false },
  { id: 'cost-approval', category: 'Custos', title: 'Aprovar custos acima do limite', objective: 'Proteger gastos da operação do cliente.', signal: 'Novo custo acima do limite acordado.', condition: 'Valor ultrapassa o teto e não existe aprovação.', action: 'Encaminhar a solicitação ao aprovador e aguardar decisão.', responsible: 'Aprovador da operação', deadline: 'Antes do compromisso financeiro', expectedResult: 'Nenhum custo fora do limite sem aprovação.', indicator: 'Custos excepcionais aprovados', requiresClient: true, requiresOperation: true },
  { id: 'budget-limit', category: 'Custos', title: 'Alertar orçamento próximo do limite', objective: 'Evitar ultrapassar o orçamento.', signal: 'Consumo se aproxima do teto do período.', condition: 'Uso atinge 80% do orçamento ativo.', action: 'Alertar gestor e apresentar saldo restante.', responsible: 'Gestor da operação', deadline: 'Assim que atingir o sinal', expectedResult: 'Decisão antecipada sobre o orçamento.', indicator: 'Percentual do orçamento consumido', requiresClient: true, requiresOperation: true },
  { id: 'unanswered-items', category: 'Relacionamento', title: 'Acompanhar pendências sem resposta', objective: 'Reduzir atrasos de retorno.', signal: 'Solicitação enviada sem resposta.', condition: 'Prazo de resposta combinado foi ultrapassado.', action: 'Lembrar o responsável pela pendência.', responsible: 'Responsável pela conta', deadline: 'Após 2 dias úteis', expectedResult: 'Pendências resolvidas ou escaladas.', indicator: 'Tempo médio de resposta', requiresClient: true, requiresOperation: false },
  { id: 'inactive-clients', category: 'Relacionamento', title: 'Recuperar clientes sem movimentação', objective: 'Identificar contas que precisam de atenção.', signal: 'Ausência de atividade recente.', condition: 'Sem movimentação no período definido.', action: 'Sugerir contato de retomada ao responsável.', responsible: 'Responsável pela carteira', deadline: 'Após 30 dias', expectedResult: 'Retomada ou decisão explícita de pausa.', indicator: 'Clientes sem atividade', requiresClient: true, requiresOperation: false },
  { id: 'period-close', category: 'Gestão', title: 'Fechar um período', objective: 'Conferir resultados e pendências do período.', signal: 'Chegada da data de fechamento.', condition: 'Dados da operação disponíveis para revisão.', action: 'Preparar conferência, relatório e aprovação do fechamento.', responsible: 'Gestor da operação', deadline: 'Último dia do período', expectedResult: 'Período fechado com registro e responsável.', indicator: 'Fechamentos concluídos no prazo', requiresClient: true, requiresOperation: true },
  { id: 'due-dates', category: 'Gestão', title: 'Acompanhar vencimentos', objective: 'Evitar compromissos vencidos.', signal: 'Prazo cadastrado se aproxima.', condition: 'Compromisso ainda está pendente.', action: 'Avisar responsável e registrar necessidade de decisão.', responsible: 'Gestor da operação', deadline: '3 dias antes do vencimento', expectedResult: 'Vencimentos tratados antecipadamente.', indicator: 'Vencimentos em atraso', requiresClient: true, requiresOperation: true },
  { id: 'contract-renewal', category: 'Gestão', title: 'Preparar renovações', objective: 'Antecipar a renovação de contratos.', signal: 'Contrato próximo do vencimento.', condition: 'Renovação não iniciada.', action: 'Abrir checklist de negociação e alertar o responsável.', responsible: 'Gestor da operação', deadline: '30 dias antes do término', expectedResult: 'Renovação decidida antes do vencimento.', indicator: 'Renovações dentro do prazo', requiresClient: true, requiresOperation: true },
  { id: 'unactivated-invites', category: 'Assinaturas', title: 'Acompanhar convites sem ativação', objective: 'Evitar convites de assinatura esquecidos.', signal: 'Convite de conta independente preparado.', condition: 'Cliente ainda não ativou assinatura própria.', action: 'Lembrar o responsável para fazer o acompanhamento.', responsible: 'Responsável pela carteira', deadline: 'Após 7 dias', expectedResult: 'Convite acompanhado sem conceder acesso operacional.', indicator: 'Convites pendentes de ativação', requiresClient: true, requiresOperation: false },
  { id: 'operation-signal', category: 'Assinaturas', title: 'Identificar necessidade de operação própria', objective: 'Detectar quando o cadastro já demanda uma operação separada.', signal: 'Demandas recorrentes de custos, relatórios, equipe ou integrações.', condition: 'Cliente continua apenas cadastrado ou convidado.', action: 'Sugerir ativação gerenciada ou convite para assinatura própria; não liberar recursos antes do pagamento.', responsible: 'Gestor da carteira', deadline: 'Na próxima revisão da conta', expectedResult: 'Modelo de acesso e cobrança adequado à operação.', indicator: 'Clientes com demanda operacional sem licença', requiresClient: true, requiresOperation: false },
];

export function fromJourney(goal: JourneyGoal): Flow {
  const nodes: FlowStep[] = [
    { id: uid(), type: 'trigger', label: 'Sinal identificado', details: goal.signal },
    { id: uid(), type: 'condition', label: 'Condição de decisão', details: goal.condition },
    { id: uid(), type: 'notify', label: 'Próxima ação', details: goal.action },
  ];
  return { ...newFlow(), title: goal.title, trigger: goal.signal, nodes, journeyId: goal.id, responsible: goal.responsible, deadline: goal.deadline, expectedResult: goal.expectedResult, indicator: goal.indicator, requiresOperation: goal.requiresOperation };
}
