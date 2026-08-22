(() => {
  const normalize = (value) => value.replace(/\s+/g, ' ').trim().toLocaleLowerCase('pt-BR');
  const exactRoutes = new Map([
    ['hoje', '/today'],
    ['descobrir', '/discover'],
    ['planejar', '/campaigns/active'],
    ['criar', '/content/new'],
    ['aprovar', '/approvals/post-1'],
    ['publicar', '/publish/active'],
    ['aprender', '/analytics/learning'],
    ['radar', '/radar'],
    ['calendário', '/calendar'],
    ['templates', '/templates'],
    ['automações', '/automations/active'],
    ['configurações', '/settings/ai-governance'],
    ['biblioteca', '/library/assets'],
  ]);
  const containsRoutes = [
    ['transformar em campanha', '/campaigns/new?source=radar'],
    ['nova campanha', '/campaigns/new'],
    ['criar campanha', '/campaigns/new'],
    ['campaign room', '/campaigns/active'],
    ['approval room', '/approvals/post-1'],
    ['content command', '/content/dashboard'],
    ['novo conteúdo', '/content/new'],
    ['novo post', '/content/new?type=post'],
    ['brand memory', '/brand-memory'],
    ['memória da marca', '/brand-memory'],
    ['ver calendário', '/calendar'],
    ['ver aprovações', '/approvals/post-1'],
    ['ver todas', '/content/dashboard'],
    ['descobrir', '/discover'],
    ['planejar', '/campaigns/active'],
    ['criar', '/content/new'],
    ['aprovar', '/approvals/post-1'],
    ['publicar', '/publish/active'],
    ['aprender', '/analytics/learning'],
    ['+ novo', '/content/new'],
  ];

  document.addEventListener('click', (event) => {
    const target = event.target instanceof Element ? event.target.closest('a,button,[role="button"]') : null;
    if (!target) return;
    const label = normalize(target.getAttribute('aria-label') || target.textContent || '');
    const route = exactRoutes.get(label) || containsRoutes.find(([text]) => label.includes(text))?.[1];
    if (!route) return;
    event.preventDefault();
    window.parent.postMessage({ type: 'clicko:stitch-navigate', route }, window.location.origin);
  }, true);
})();
