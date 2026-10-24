/** Reserved local-only identities; these are not commercial memberships. */
export const DEV_WORKSPACE_ID = 'ws-dev-clicko';
export const DEV_USER_ID = 'usr-dev-clicko';
export const DEV_CLIENT_ID = 'client-ws-dev-clicko';
export type DevelopmentSession = {
  enabled: true;
  workspaceId: string;
  clientId: string;
  expiresAt: string;
};
