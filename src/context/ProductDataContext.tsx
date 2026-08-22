import React from "react";
import { authToken } from "../api";
import {
  productApi,
  type ApprovalActionInput,
  type BootstrapRecord,
  type CampaignInput,
  type CampaignUpdate,
  type CreativeInput,
  type CreativeRecord,
  type CreativeUpdate,
  type PostInput,
  type PostUpdate,
  type ProductSnapshot,
  type WorkspaceResourceInput,
  type WorkspaceRecord,
} from "../api/productApi";

type ProductDataStatus = "guest" | "loading" | "ready" | "refreshing" | "error";

interface ProductDataValue {
  status: ProductDataStatus;
  bootstrap?: BootstrapRecord;
  snapshot?: ProductSnapshot;
  workspaces: WorkspaceRecord[];
  activeWorkspace?: WorkspaceRecord;
  error?: string;
  pendingAction?: string;
  refresh: () => Promise<void>;
  selectWorkspace: (workspaceId: string) => Promise<void>;
  createCampaign: (
    input: Omit<CampaignInput, "workspaceId">,
  ) => Promise<string>;
  updateCampaign: (campaignId: string, input: CampaignUpdate) => Promise<void>;
  createPost: (input: Omit<PostInput, "workspaceId">) => Promise<string>;
  updatePost: (postId: string, input: PostUpdate) => Promise<void>;
  decidePost: (postId: string, input: ApprovalActionInput) => Promise<void>;
  createCreative: (
    input: Omit<CreativeInput, "workspaceId">,
  ) => Promise<CreativeRecord>;
  updateCreative: (
    documentId: string,
    input: CreativeUpdate,
  ) => Promise<CreativeRecord>;
  saveWorkspaceResource: (
    kind: WorkspaceResourceInput["kind"],
    resourceKey: string,
    payload: Record<string, unknown>,
  ) => Promise<void>;
}

const ACTIVE_WORKSPACE_KEY = "clicko:active-workspace";
const ProductDataContext = React.createContext<ProductDataValue | null>(null);

function messageFrom(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Não foi possível sincronizar o produto.";
}

export function ProductDataProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [status, setStatus] = React.useState<ProductDataStatus>(() =>
    authToken.get() ? "loading" : "guest",
  );
  const [bootstrap, setBootstrap] = React.useState<BootstrapRecord>();
  const [snapshot, setSnapshot] = React.useState<ProductSnapshot>();
  const snapshotRef = React.useRef<ProductSnapshot>();
  const [activeWorkspaceId, setActiveWorkspaceId] = React.useState<string>();
  const [error, setError] = React.useState<string>();
  const [pendingAction, setPendingAction] = React.useState<string>();

  const loadWorkspace = React.useCallback(
    async (workspaceId: string, mode: "loading" | "refreshing" = "loading") => {
      setStatus(mode);
      setError(undefined);
      try {
        const nextSnapshot = await productApi.snapshot(workspaceId);
        setSnapshot(nextSnapshot);
        snapshotRef.current = nextSnapshot;
        setActiveWorkspaceId(workspaceId);
        localStorage.setItem(ACTIVE_WORKSPACE_KEY, workspaceId);
        setStatus("ready");
      } catch (requestError) {
        setError(messageFrom(requestError));
        setStatus("error");
        throw requestError;
      }
    },
    [],
  );

  const refresh = React.useCallback(async () => {
    if (!authToken.get()) {
      setBootstrap(undefined);
      setSnapshot(undefined);
      snapshotRef.current = undefined;
      setActiveWorkspaceId(undefined);
      setError(undefined);
      setStatus("guest");
      return;
    }

    setStatus(snapshotRef.current ? "refreshing" : "loading");
    setError(undefined);
    try {
      const nextBootstrap = await productApi.bootstrap();
      setBootstrap(nextBootstrap);
      const preferredId = localStorage.getItem(ACTIVE_WORKSPACE_KEY);
      const workspaceId = nextBootstrap.workspaces.some(
        (workspace) => workspace.id === preferredId,
      )
        ? preferredId!
        : nextBootstrap.workspaces[0]?.id;
      if (!workspaceId)
        throw new Error("Sua conta ainda não possui um workspace.");
      await loadWorkspace(
        workspaceId,
        snapshotRef.current ? "refreshing" : "loading",
      );
    } catch (requestError) {
      setError(messageFrom(requestError));
      setStatus("error");
    }
  }, [loadWorkspace]);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  React.useEffect(() => {
    const unauthorized = () => {
      setBootstrap(undefined);
      setSnapshot(undefined);
      snapshotRef.current = undefined;
      setActiveWorkspaceId(undefined);
      setStatus("guest");
    };
    window.addEventListener("nexus:unauthorized", unauthorized);
    return () => window.removeEventListener("nexus:unauthorized", unauthorized);
  }, []);

  const refreshWorkspace = React.useCallback(async () => {
    if (!activeWorkspaceId) return;
    await loadWorkspace(activeWorkspaceId, "refreshing");
  }, [activeWorkspaceId, loadWorkspace]);

  const runMutation = React.useCallback(
    async <T,>(label: string, mutation: () => Promise<T>) => {
      setPendingAction(label);
      setError(undefined);
      try {
        const result = await mutation();
        await refreshWorkspace();
        return result;
      } catch (requestError) {
        setError(messageFrom(requestError));
        throw requestError;
      } finally {
        setPendingAction(undefined);
      }
    },
    [refreshWorkspace],
  );

  const requireWorkspaceId = React.useCallback(() => {
    if (!activeWorkspaceId)
      throw new Error("Selecione um workspace antes de continuar.");
    return activeWorkspaceId;
  }, [activeWorkspaceId]);

  const value = React.useMemo<ProductDataValue>(
    () => ({
      status,
      bootstrap,
      snapshot,
      workspaces: bootstrap?.workspaces ?? [],
      activeWorkspace: bootstrap?.workspaces.find(
        (workspace) => workspace.id === activeWorkspaceId,
      ),
      error,
      pendingAction,
      refresh,
      selectWorkspace: async (workspaceId) => loadWorkspace(workspaceId),
      createCampaign: async (input) => {
        const record = await runMutation("create-campaign", () =>
          productApi.createCampaign({
            ...input,
            workspaceId: requireWorkspaceId(),
          }),
        );
        return record.id;
      },
      updateCampaign: async (campaignId, input) => {
        await runMutation("update-campaign", () =>
          productApi.updateCampaign(campaignId, input),
        );
      },
      createPost: async (input) => {
        const record = await runMutation("create-post", () =>
          productApi.createPost({
            ...input,
            workspaceId: requireWorkspaceId(),
          }),
        );
        return record.id;
      },
      updatePost: async (postId, input) => {
        await runMutation("update-post", () =>
          productApi.updatePost(postId, input),
        );
      },
      decidePost: async (postId, input) => {
        await runMutation("approval-action", () =>
          productApi.approvalAction(postId, input),
        );
      },
      createCreative: async (input) =>
        runMutation("create-creative", () =>
          productApi.createCreative({
            ...input,
            workspaceId: requireWorkspaceId(),
          }),
        ),
      updateCreative: async (documentId, input) =>
        runMutation("autosave-creative", () =>
          productApi.updateCreative(documentId, input),
        ),
      saveWorkspaceResource: async (kind, resourceKey, payload) => {
        const workspaceId = requireWorkspaceId();
        const current = snapshotRef.current;
        const resources =
          kind === "connected_account"
            ? current?.connectedAccounts
            : kind === "presenter_session"
              ? current?.presenterSessions
              : [];
        const existing = resources?.find(
          (item) => item.resourceKey === resourceKey,
        );
        await runMutation(`save-${kind}`, () =>
          existing
            ? productApi.updateWorkspaceResource(existing.id, workspaceId, {
                payload,
              })
            : productApi.createWorkspaceResource({
                workspaceId,
                kind,
                resourceKey,
                payload,
              }),
        );
      },
    }),
    [
      activeWorkspaceId,
      bootstrap,
      error,
      loadWorkspace,
      pendingAction,
      refresh,
      requireWorkspaceId,
      runMutation,
      snapshot,
      status,
    ],
  );

  return (
    <ProductDataContext.Provider value={value}>
      {children}
    </ProductDataContext.Provider>
  );
}

export function useProductData() {
  const value = React.useContext(ProductDataContext);
  if (!value)
    throw new Error(
      "useProductData deve ser usado dentro de ProductDataProvider.",
    );
  return value;
}
