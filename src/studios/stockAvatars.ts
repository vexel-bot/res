export interface StockAvatarCandidate {
  id: string;
  subjectKey: string;
  displayName: string;
  presentation: "woman" | "man";
  voiceLabel: string;
  direction: string;
  accent: string;
  rightsProfile: "clicko-stock-candidate-v1";
}

/**
 * Product catalog slots, not generated identities. A slot becomes usable only
 * when the workspace resolves it to an active synthetic IdentityVersion and
 * the governed presenter provider reports readiness.
 */
export const STOCK_AVATAR_CANDIDATES: readonly StockAvatarCandidate[] = [
  {
    id: "lia",
    subjectKey: "stock/clicko/lia",
    displayName: "Lia",
    presentation: "woman",
    voiceLabel: "PT-BR · acolhedora",
    direction: "UGC natural e próximo",
    accent: "#ff8f70",
    rightsProfile: "clicko-stock-candidate-v1",
  },
  {
    id: "maya",
    subjectKey: "stock/clicko/maya",
    displayName: "Maya",
    presentation: "woman",
    voiceLabel: "PT-BR · precisa",
    direction: "Especialista clara",
    accent: "#b9a3ff",
    rightsProfile: "clicko-stock-candidate-v1",
  },
  {
    id: "nina",
    subjectKey: "stock/clicko/nina",
    displayName: "Nina",
    presentation: "woman",
    voiceLabel: "PT-BR · energética",
    direction: "Creator de descoberta",
    accent: "#ff6f91",
    rightsProfile: "clicko-stock-candidate-v1",
  },
  {
    id: "caio",
    subjectKey: "stock/clicko/caio",
    displayName: "Caio",
    presentation: "man",
    voiceLabel: "PT-BR · conversacional",
    direction: "Founder-led direto",
    accent: "#63c7ff",
    rightsProfile: "clicko-stock-candidate-v1",
  },
  {
    id: "theo",
    subjectKey: "stock/clicko/theo",
    displayName: "Theo",
    presentation: "man",
    voiceLabel: "PT-BR · sereno",
    direction: "Premium discreto",
    accent: "#5dd6a5",
    rightsProfile: "clicko-stock-candidate-v1",
  },
  {
    id: "bento",
    subjectKey: "stock/clicko/bento",
    displayName: "Bento",
    presentation: "man",
    voiceLabel: "PT-BR · didático",
    direction: "Demonstração de produto",
    accent: "#f3c75f",
    rightsProfile: "clicko-stock-candidate-v1",
  },
] as const;
