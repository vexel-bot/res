export const demoMedia = {
  hero: "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=1600&q=88",
  cup: "https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=1200&q=88",
  beans: "https://images.unsplash.com/photo-1442512595331-e89e73853f31?auto=format&fit=crop&w=1200&q=88",
  pour: "https://images.unsplash.com/photo-1511081692775-05d0f180a065?auto=format&fit=crop&w=1200&q=88",
  table: "https://images.unsplash.com/photo-1445116572660-236099ec97a0?auto=format&fit=crop&w=1200&q=88",
  people: "https://images.unsplash.com/photo-1521017432531-fbd92d768814?auto=format&fit=crop&w=1200&q=88",
};

export const demoCampaign = {
  id: "campaign-aurora",
  name: "Ritual Café Aurora",
  objective: "Transformar o primeiro café do dia em um ritual de presença.",
  audience: "Pessoas criativas, 24–40, que valorizam origem e pequenos rituais.",
  bigIdea: "Todo dia merece um começo que fica.",
  offer: "Café especial de origem + assinatura mensal",
  channels: ["Instagram", "TikTok", "Newsletter"],
};

export const demoPosts = [
  { id: "post-ritual", title: "O primeiro gole", status: "in_review", platform: "Instagram", format: "Carrossel", imageUrl: demoMedia.hero },
  { id: "post-origem", title: "Da origem à xícara", status: "approved", platform: "Instagram", format: "Reel", imageUrl: demoMedia.beans },
  { id: "post-manha", title: "Manhã sem pressa", status: "draft", platform: "TikTok", format: "Vídeo", imageUrl: demoMedia.cup },
];

export const demoOpportunity = {
  id: "op-festival",
  title: "Festival do Café Independente",
  source: "Radar cultural · São Paulo",
  window: "18–24 set",
  fit: 94,
  summary: "Conversas sobre origem, métodos artesanais e consumo consciente cresceram 38% nas últimas duas semanas.",
};

export const statusLabel: Record<string, string> = {
  draft: "Rascunho",
  in_review: "Em revisão",
  pending_approval: "Aguardando aprovação",
  approved: "Aprovado",
  changes_requested: "Ajustes solicitados",
  rejected: "Rejeitado",
  scheduled: "Agendado",
  published: "Publicado",
  active: "Ativa",
  planned: "Planejada",
  completed: "Concluída",
};
