export type ClientOperationState = 'registered' | 'invited' | 'managed' | 'independent';

export type ClientOperationRecord = {
  id: string;
  workspaceId: string;
  name: string;
  updatedAt: string;
  operationState: ClientOperationState;
  invitationEmail?: string;
  invitationKind?: 'portal' | 'independent';
  billingStatus?: 'none' | 'checkout_pending' | 'active' | 'past_due' | 'ended';
  linkedWorkspaceId?: string;
  sharedSummary?: string;
  portalRequests?: Array<{ id: string; title: string; detail: string; status: 'pending' | 'approved'; createdAt: string; decidedAt?: string }>;
  portalComments?: Array<{ id: string; message: string; createdAt: string }>;
  portalDocuments?: Array<{ id: string; name: string; mime: string; uploadedAt: string }>;
  operationSignals?: Array<{ kind: 'costs' | 'reports' | 'automations' | 'integrations' | 'team' | 'settings'; at: string }>;
};

export const clientOperationLabels: Record<ClientOperationState, string> = {
  registered: 'Cliente cadastrado',
  invited: 'Cliente convidado',
  managed: 'Operação gerenciada',
  independent: 'Conta independente',
};

export const CLIENT_OPERATION_REQUIRED = 'Para operar separadamente em nome deste cliente, ative uma operação gerenciada ou convide-o para criar uma conta própria.';

export const hasClientOperation = (record?: ClientOperationRecord | null) =>
  Boolean(record && (record.operationState === 'managed' || record.operationState === 'independent') && record.billingStatus === 'active');
