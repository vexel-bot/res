import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const REQUIRED_TASKS = ["FC-1", "FC-2", "FC-3", "FC-4", "FC-5"] as const;
type RequiredTask = (typeof REQUIRED_TASKS)[number];

interface Participant {
  participantId: string;
  segment: "creator" | "reviewer" | "publisher";
  viewport: "desktop" | "mobile";
}

interface TaskResult {
  participantId: string;
  taskId: RequiredTask;
  firstClick: string;
  firstClickSuccess: boolean;
  taskResult: "success" | "assisted" | "failed" | "invalid_run";
  timeToFirstClickMs: number;
  taskTimeMs: number;
  seq: number;
}

interface AccessibilityRun {
  participantId: string;
  method: "keyboard" | "screen-reader";
  criticalJourneyCompleted: boolean;
  severity3Issues: number;
}

interface StudyIssue {
  issueId: string;
  severity: 0 | 1 | 2 | 3;
  participantIds: string[];
  screenId?: string;
  actionId?: string;
  route?: string;
}

interface ValidationStudy {
  schemaVersion: "1.0.0";
  studyId: string;
  surface: {
    type: "figma" | "build";
    version: string;
    url: string;
  };
  participants: Participant[];
  results: TaskResult[];
  accessibilityRuns: AccessibilityRun[];
  issues: StudyIssue[];
}

function unique(values: string[]) {
  return [...new Set(values)];
}

const inputPath = process.argv[2];
if (!inputPath) {
  console.error(
    "Uso: npm run audit:cx-user-validation -- <caminho-do-results.json>",
  );
  process.exit(2);
}

let study: ValidationStudy;
try {
  study = JSON.parse(readFileSync(resolve(inputPath), "utf8")) as ValidationStudy;
} catch (error) {
  console.error(`Não foi possível ler o estudo: ${String(error)}`);
  process.exit(2);
}

const participantIds = unique(
  (study.participants ?? []).map((participant) => participant.participantId),
);
const knownParticipants = new Set(participantIds);
const structuralIssues: string[] = [];

if (participantIds.length !== 10 || participantIds.length !== study.participants.length) {
  structuralIssues.push("O estudo deve conter exatamente 10 participantes com IDs únicos.");
}

const taskSummaries = REQUIRED_TASKS.map((taskId) => {
  const rows = (study.results ?? []).filter(
    (result) =>
      result.taskId === taskId &&
      result.taskResult !== "invalid_run" &&
      knownParticipants.has(result.participantId),
  );
  const uniqueParticipants = unique(rows.map((row) => row.participantId));
  const duplicateCount = rows.length - uniqueParticipants.length;
  if (uniqueParticipants.length !== 10) {
    structuralIssues.push(
      `${taskId} precisa de 10 execuções válidas; recebeu ${uniqueParticipants.length}.`,
    );
  }
  if (duplicateCount > 0) {
    structuralIssues.push(`${taskId} contém ${duplicateCount} resultado(s) duplicado(s).`);
  }
  const successes = rows.filter((row) => row.firstClickSuccess).length;
  return {
    taskId,
    validParticipants: uniqueParticipants.length,
    successes,
    rate: uniqueParticipants.length === 0 ? 0 : successes / uniqueParticipants.length,
    passed: uniqueParticipants.length === 10 && successes >= 8,
  };
});

const accessibilityRuns = study.accessibilityRuns ?? [];
const keyboardRuns = accessibilityRuns.filter((run) => run.method === "keyboard");
const screenReaderRuns = accessibilityRuns.filter(
  (run) => run.method === "screen-reader",
);
const keyboardPassed = keyboardRuns.some(
  (run) => run.criticalJourneyCompleted && run.severity3Issues === 0,
);
const screenReaderPassed = screenReaderRuns.some(
  (run) => run.criticalJourneyCompleted && run.severity3Issues === 0,
);

if (keyboardRuns.length === 0) {
  structuralIssues.push("Falta uma rodada integral somente por teclado.");
}
if (screenReaderRuns.length === 0) {
  structuralIssues.push("Falta uma rodada integral com leitor de tela.");
}

const issues = study.issues ?? [];
const severity3Issues = issues.filter((issue) => issue.severity === 3);
const repeatedSeverity2Issues = issues.filter(
  (issue) => issue.severity === 2 && unique(issue.participantIds).length >= 3,
);

const quantitativeGatePassed = taskSummaries.every((task) => task.passed);
const assistiveGatePassed = keyboardPassed && screenReaderPassed;
const complete = structuralIssues.length === 0;
const decision = !complete
  ? "incomplete"
  : !quantitativeGatePassed || severity3Issues.length > 0 || !assistiveGatePassed
    ? "fail"
    : repeatedSeverity2Issues.length > 0
      ? "conditional"
      : "pass";

const report = {
  studyId: study.studyId,
  surface: study.surface,
  decision,
  criteria: {
    participantCount: participantIds.length,
    requiredParticipantCount: 10,
    quantitativeGatePassed,
    keyboardPassed,
    screenReaderPassed,
    severity3IssueCount: severity3Issues.length,
    repeatedSeverity2IssueCount: repeatedSeverity2Issues.length,
  },
  tasks: taskSummaries,
  structuralIssues,
};

console.log(JSON.stringify(report, null, 2));
if (decision === "fail") process.exitCode = 1;
if (decision === "incomplete") process.exitCode = 2;
