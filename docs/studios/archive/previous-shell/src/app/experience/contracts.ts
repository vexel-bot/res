export const SCREEN_STATES = [
  "loading",
  "empty",
  "ready",
  "dirty",
  "saving",
  "saved",
  "recoverable-error",
  "terminal-error",
  "conflict",
  "readonly",
  "forbidden",
  "offline",
  "stale",
  "job-queued",
  "job-running",
  "job-cancelling",
  "job-cancelled",
] as const;

export type ScreenState = (typeof SCREEN_STATES)[number];

export const ACTION_TYPES = [
  "NAV",
  "SELECT",
  "MUTATE",
  "UPLOAD",
  "JOB",
  "REVIEW",
  "EXTERNAL",
  "DESTRUCTIVE",
] as const;

export type ActionType = (typeof ACTION_TYPES)[number];

export type PersistenceMode =
  | "none"
  | "local"
  | "autosave"
  | "mutation"
  | "version"
  | "job";

export interface ActionFeedbackContract {
  loading: string;
  success: string;
  recoverableError: string;
}

export interface ActionContract {
  actionId: string;
  label: string;
  type: ActionType;
  object: string;
  preconditions: readonly string[];
  permissions: readonly string[];
  sideEffect: string;
  feedback: ActionFeedbackContract;
  persistence: PersistenceMode;
  nextRoute?: string;
  analyticsEvent: string;
  accessibleName: string;
  testId: string;
}

export interface ScreenContract {
  screenId: string;
  routeTemplate: string;
  owner: string;
  shell: string;
  userJob: string;
  requiredContext: readonly string[];
  focalObject: string;
  primaryActionId: string;
  secondaryActionIds: readonly string[];
  output: string;
  nextBestAction: string;
  supportedStates: readonly ScreenState[];
  permissions: readonly string[];
  persistence: PersistenceMode;
  analyticsViewEvent: string;
  acceptanceTests: readonly string[];
}

export interface ContractIssue {
  field: string;
  message: string;
}

const EVENT_NAME = /^[a-z][a-z0-9]*(?:\.[a-z0-9_-]+)+$/;
const STABLE_ID = /^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$/;

function required(value: string, field: string, issues: ContractIssue[]) {
  if (!value.trim()) issues.push({ field, message: `${field} is required` });
}

export function validateActionContract(
  contract: ActionContract,
): ContractIssue[] {
  const issues: ContractIssue[] = [];
  required(contract.actionId, "actionId", issues);
  required(contract.label, "label", issues);
  required(contract.object, "object", issues);
  required(contract.sideEffect, "sideEffect", issues);
  required(contract.feedback.loading, "feedback.loading", issues);
  required(contract.feedback.success, "feedback.success", issues);
  required(
    contract.feedback.recoverableError,
    "feedback.recoverableError",
    issues,
  );
  required(contract.accessibleName, "accessibleName", issues);
  required(contract.testId, "testId", issues);

  if (!STABLE_ID.test(contract.actionId)) {
    issues.push({
      field: "actionId",
      message: "actionId must be a stable upper-case hyphenated ID",
    });
  }
  if (!EVENT_NAME.test(contract.analyticsEvent)) {
    issues.push({
      field: "analyticsEvent",
      message: "analyticsEvent must be a namespaced lower-case event",
    });
  }
  if (contract.type === "JOB" && contract.persistence !== "job") {
    issues.push({
      field: "persistence",
      message: "JOB actions must persist as observable jobs",
    });
  }
  if (contract.type === "DESTRUCTIVE" && contract.preconditions.length === 0) {
    issues.push({
      field: "preconditions",
      message: "DESTRUCTIVE actions must declare a protection precondition",
    });
  }
  if (contract.type === "NAV" && !contract.nextRoute) {
    issues.push({
      field: "nextRoute",
      message: "NAV actions must declare their destination",
    });
  }
  return issues;
}

export function validateScreenContract(
  contract: ScreenContract,
  actions: ReadonlyMap<string, ActionContract>,
): ContractIssue[] {
  const issues: ContractIssue[] = [];
  required(contract.screenId, "screenId", issues);
  required(contract.routeTemplate, "routeTemplate", issues);
  required(contract.owner, "owner", issues);
  required(contract.shell, "shell", issues);
  required(contract.userJob, "userJob", issues);
  required(contract.focalObject, "focalObject", issues);
  required(contract.output, "output", issues);
  required(contract.nextBestAction, "nextBestAction", issues);

  if (!STABLE_ID.test(contract.screenId)) {
    issues.push({
      field: "screenId",
      message: "screenId must be a stable upper-case hyphenated ID",
    });
  }
  if (!contract.routeTemplate.startsWith("/")) {
    issues.push({ field: "routeTemplate", message: "route must be absolute" });
  }
  if (!actions.has(contract.primaryActionId)) {
    issues.push({
      field: "primaryActionId",
      message: `missing action contract ${contract.primaryActionId}`,
    });
  }
  for (const actionId of contract.secondaryActionIds) {
    if (!actions.has(actionId)) {
      issues.push({
        field: "secondaryActionIds",
        message: `missing action contract ${actionId}`,
      });
    }
  }
  if (!contract.supportedStates.includes("loading")) {
    issues.push({ field: "supportedStates", message: "loading is required" });
  }
  if (!contract.supportedStates.includes("recoverable-error")) {
    issues.push({
      field: "supportedStates",
      message: "recoverable-error is required",
    });
  }
  if (!EVENT_NAME.test(contract.analyticsViewEvent)) {
    issues.push({
      field: "analyticsViewEvent",
      message: "analyticsViewEvent must be a namespaced lower-case event",
    });
  }
  if (contract.acceptanceTests.length === 0) {
    issues.push({
      field: "acceptanceTests",
      message: "at least one acceptance test is required",
    });
  }
  return issues;
}
