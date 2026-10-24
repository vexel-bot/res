import React from 'react';
import { ArrowUpRight, CalendarDays, Check, Clock3, Copy, ExternalLink, FileText, Film, MoreHorizontal, RotateCcw, X } from 'lucide-react';
import type { ClientIntelligenceProfile, ConnectedAccount, LibraryAsset, Post, PostFormat, SocialPlatform } from '../types';
import type { KlicPageDetails } from '../klic/pageContext';
import { ClickoSelectMenu } from './ClickoSelectMenu';
import './PublishedHistory.css';

export type ConfirmedPublication = {
  id: string;
  ownerId: string;
  contentId: string;
  connectionId: string;
  clientId?: string;
  provider?: SocialPlatform;
  title?: string;
  status: string;
  scheduledAt: string;
  createdAt: string;
  updatedAt: string;
  providerPostId?: string;
  permalink?: string;
  request: { kind: string; text?: string; mediaUrls?: string[] };
};

type HistoryProps = {
  jobs: ConfirmedPublication[];
  posts: Post[];
  accounts: ConnectedAccount[];
  clients: ClientIntelligenceProfile[];
  assets: LibraryAsset[];
  loading: boolean;
  error: boolean;
  canRead: boolean;
  onDuplicate: (job: ConfirmedPublication, post?: Post) => void;
  onReuse: (job: ConfirmedPublication, post?: Post) => void;
  onPerformance: (job: ConfirmedPublication) => void;
  onContextChange?: (details: KlicPageDetails) => void;
};

const platformNames: Record<SocialPlatform, string> = {
  instagram: 'Instagram', facebook: 'Facebook', tiktok: 'TikTok', youtube: 'YouTube',
  linkedin: 'LinkedIn', x: 'X', pinterest: 'Pinterest', threads: 'Threads',
};

const formatNames: Partial<Record<PostFormat, string>> = {
  post: 'Post', carousel: 'Carrossel', reels: 'Reel', story: 'Story', tiktok: 'Vídeo',
  'youtube-short': 'Short', 'youtube-long': 'Vídeo', 'linkedin-article': 'Artigo',
  pin: 'Pin', thread: 'Thread',
};

function publicationFormat(job: ConfirmedPublication, post?: Post): string {
  if (post) return formatNames[post.format] || post.format;
  return ({ carousel: 'Carrossel', short_video: 'Vídeo curto', story: 'Story', video: 'Vídeo', document: 'Documento', image: 'Imagem', text: 'Post' } as Record<string, string>)[job.request.kind] || 'Conteúdo';
}

function localDay(value: string): string {
  const date = new Date(value);
  return Number.isFinite(date.getTime()) ? `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}` : '';
}

function groupLabel(value: string, now = new Date()): string {
  const day = localDay(value);
  if (day === localDay(now.toISOString())) return 'Hoje';
  const yesterday = new Date(now); yesterday.setDate(now.getDate() - 1);
  if (day === localDay(yesterday.toISOString())) return 'Ontem';
  const start = new Date(now); start.setHours(0, 0, 0, 0); start.setDate(start.getDate() - ((start.getDay() + 6) % 7));
  if (new Date(value) >= start) return 'Esta semana';
  return new Date(value).toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
}

function HistorySelect({ label, value, options, onChange }: { label: string; value: string; options: Array<[string, string]>; onChange: (value: string) => void }) {
  return <ClickoSelectMenu label={label} value={value} options={options} onChange={onChange} className="published-filter" menuClassName="published-filter-options" />;
}

export function PublishedHistory({ jobs, posts, accounts, clients, assets, loading, error, canRead, onDuplicate, onReuse, onPerformance, onContextChange }: HistoryProps) {
  const [period, setPeriod] = React.useState('all');
  const [start, setStart] = React.useState('');
  const [end, setEnd] = React.useState('');
  const [platform, setPlatform] = React.useState('all');
  const [accountId, setAccountId] = React.useState('all');
  const [clientId, setClientId] = React.useState('all');
  const [format, setFormat] = React.useState('all');
  const [detailId, setDetailId] = React.useState<string | null>(null);
  React.useEffect(() => {
    onContextChange?.({ view: 'Publicados', period: period === 'custom' ? `${start || 'início'} a ${end || 'hoje'}` : period,
      filters: { rede: platform, conta: accountId, cliente: clientId, formato: format },
      selected: detailId ? { kind: 'publicacao', id: detailId } : undefined });
  }, [period, start, end, platform, accountId, clientId, format, detailId, onContextChange]);
  const postById = React.useMemo(() => new Map(posts.map(post => [post.id, post])), [posts]);
  const published = React.useMemo(() => jobs.filter(job => job.status === 'published' && Number.isFinite(Date.parse(job.updatedAt))), [jobs]);
  const accountById = React.useMemo(() => new Map(accounts.map(account => [account.id, account])), [accounts]);
  const clientById = React.useMemo(() => new Map(clients.map(client => [client.id, client])), [clients]);
  const now = new Date();
  const earliest = period !== 'all' && period !== 'custom' ? new Date(now.getFullYear(), now.getMonth(), now.getDate() - Number(period) + 1).getTime() : null;
  const filtered = published.filter(job => {
    const timestamp = Date.parse(job.updatedAt);
    const linked = postById.get(job.contentId);
    const network = job.provider || accountById.get(job.connectionId)?.platform || linked?.platform;
    if (earliest !== null && timestamp < earliest) return false;
    if (period === 'custom' && ((start && localDay(job.updatedAt) < start) || (end && localDay(job.updatedAt) > end))) return false;
    if (platform !== 'all' && network !== platform) return false;
    if (accountId !== 'all' && job.connectionId !== accountId) return false;
    if (clientId !== 'all' && (job.clientId || linked?.clientId) !== clientId) return false;
    if (format !== 'all' && publicationFormat(job, linked) !== format) return false;
    return true;
  }).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  const groups = new Map<string, ConfirmedPublication[]>();
  filtered.forEach(job => { const group = groupLabel(job.updatedAt, now); groups.set(group, [...(groups.get(group) || []), job]); });
  const detail = detailId ? published.find(job => job.id === detailId) : undefined;
  const detailPost = detail ? postById.get(detail.contentId) : undefined;
  const detailNetwork = detail?.provider || accountById.get(detail?.connectionId || '')?.platform || detailPost?.platform;
  const accountsInHistory = [...new Set(published.map(job => job.connectionId))];
  const clientsInHistory = [...new Set(published.map(job => job.clientId || postById.get(job.contentId)?.clientId).filter((id): id is string => Boolean(id)))];
  const formatsInHistory = [...new Set(published.map(job => publicationFormat(job, postById.get(job.contentId))))];
  const networksInHistory = [...new Set(published.map(job => job.provider || accountById.get(job.connectionId)?.platform || postById.get(job.contentId)?.platform).filter((id): id is SocialPlatform => Boolean(id)))];

  return <section className="published-history" aria-label="Histórico de publicações">
    <div className="published-heading"><div><span>PUBLICAÇÕES CONFIRMADAS</span><h2>Histórico de Publicações</h2><p>Conteúdos publicados pelas contas conectadas, em ordem cronológica.</p></div><strong>{published.length} {published.length === 1 ? 'publicação' : 'publicações'}</strong></div>
    <div className="published-filters">
      <HistorySelect label="Período" value={period} onChange={setPeriod} options={[["all", "Todo o histórico"], ["7", "Últimos 7 dias"], ["30", "Últimos 30 dias"], ["90", "Últimos 90 dias"], ["custom", "Personalizado"]]} />
      <HistorySelect label="Rede social" value={platform} onChange={setPlatform} options={[["all", "Todas"], ...networksInHistory.map(id => [id, platformNames[id]] as [string, string])]} />
      <HistorySelect label="Perfil / conta" value={accountId} onChange={setAccountId} options={[["all", "Todos"], ...accountsInHistory.map(id => [id, accountById.get(id)?.name || accountById.get(id)?.handle || 'Conta não conectada'] as [string, string])]} />
      <HistorySelect label="Cliente" value={clientId} onChange={setClientId} options={[["all", "Todos"], ...clientsInHistory.map(id => [id, clientById.get(id)?.name || 'Cliente removido'] as [string, string])]} />
      <HistorySelect label="Formato" value={format} onChange={setFormat} options={[["all", "Todos"], ...formatsInHistory.map(name => [name, name] as [string, string])]} />
      {period === 'custom' && <div className="published-date-fields"><label>De<input type="date" value={start} max={end || undefined} onChange={event => setStart(event.target.value)} /></label><label>Até<input type="date" value={end} min={start || undefined} onChange={event => setEnd(event.target.value)} /></label></div>}
    </div>
    {!canRead ? <div className="published-empty"><FileText /><h3>Histórico indisponível</h3><p>Seu perfil não tem permissão para consultar publicações das contas conectadas.</p></div>
      : loading && !published.length ? <div className="published-empty"><Clock3 /><h3>Consultando publicações</h3><p>Buscando as confirmações das redes sociais.</p></div>
      : error && !published.length ? <div className="published-empty"><FileText /><h3>Não foi possível carregar o histórico</h3><p>Verifique a conexão e tente abrir o Calendário novamente.</p></div>
      : !filtered.length ? <div className="published-empty"><CalendarDays /><h3>{published.length ? 'Nenhuma publicação neste filtro' : 'Nenhuma publicação confirmada ainda'}</h3><p>{published.length ? 'Ajuste o período ou os outros filtros.' : 'Quando a rede confirmar uma publicação, ela aparecerá aqui automaticamente.'}</p></div>
      : <div className="published-groups">{[...groups.entries()].map(([name, rows]) => <section key={name} className="published-group" aria-label={name}><header><h3>{name}</h3><span>{rows.length} {rows.length === 1 ? 'conteúdo' : 'conteúdos'}</span></header><div className="published-cards">{rows.map(job => {
        const post = postById.get(job.contentId);
        const network = job.provider || accountById.get(job.connectionId)?.platform || post?.platform;
        const account = accountById.get(job.connectionId);
        const client = clientById.get(job.clientId || post?.clientId || '');
        const media = post?.imageUrl || post?.assetIds?.map(id => assets.find(asset => asset.id === id && asset.mimeType?.startsWith('image/'))?.url).find(Boolean) || (['image', 'carousel'].includes(job.request.kind) ? job.request.mediaUrls?.[0] : undefined);
        const title = post?.title || job.title || job.request.text?.slice(0, 90) || 'Publicação sem título';
        const publishedAt = new Date(job.updatedAt).toLocaleString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
        const url = job.permalink?.startsWith('https://') ? job.permalink : undefined;
        return <article className="published-card" key={job.id}>
          <div className="published-thumb">{media ? <img src={media} alt="" loading="lazy" /> : ['video', 'short_video'].includes(job.request.kind) || ['reels', 'tiktok', 'youtube-short', 'youtube-long'].includes(post?.format || '') ? <Film /> : <FileText />}</div>
          <div className="published-card-content"><div className="published-card-top"><span className="published-network">{network ? platformNames[network] : 'Rede social'}</span><span className="published-status"><Check />Publicado</span></div><h4>{title}</h4>{(post?.copy || job.request.text) && <p className="published-caption">{post?.copy || job.request.text}</p>}<div className="published-meta"><span>{account?.name || account?.handle || 'Conta não conectada'}</span>{client && <span>{client.name}</span>}<span>{publicationFormat(job, post)}</span><span>{publishedAt}</span></div></div>
          <div className="published-card-actions"><button type="button" onClick={() => setDetailId(job.id)}>Ver detalhes</button><details><summary aria-label={`Mais ações para ${title}`}><MoreHorizontal /></summary><div>{url ? <a href={url} target="_blank" rel="noopener noreferrer"><ExternalLink />Visualizar publicação</a> : <span className="is-disabled">Link da publicação indisponível</span>}<button type="button" onClick={() => onDuplicate(job, post)}><Copy />Duplicar</button><button type="button" onClick={() => onReuse(job, post)}><RotateCcw />Reutilizar conteúdo</button><button type="button" onClick={() => onPerformance(job)}><ArrowUpRight />Ver desempenho</button></div></details></div>
        </article>;
      })}</div></section>)}</div>}
    {detail && <div className="published-detail-backdrop" role="presentation" onClick={() => setDetailId(null)}><section role="dialog" aria-modal="true" aria-labelledby="published-detail-title" onClick={event => event.stopPropagation()}><header><div><span>PUBLICAÇÃO CONFIRMADA</span><h2 id="published-detail-title">{detailPost?.title || detail.title || 'Detalhes da publicação'}</h2></div><button type="button" aria-label="Fechar detalhes" onClick={() => setDetailId(null)}><X /></button></header><div className="published-detail-body"><div><span>Status</span><strong>Publicado pela integração</strong></div><div><span>Rede</span><strong>{detailNetwork ? platformNames[detailNetwork] : 'Rede não disponível'}</strong></div><div><span>Conta</span><strong>{accountById.get(detail.connectionId)?.name || accountById.get(detail.connectionId)?.handle || 'Conta não conectada'}</strong></div><div><span>Cliente</span><strong>{clientById.get(detail.clientId || detailPost?.clientId || '')?.name || 'Sem cliente vinculado'}</strong></div><div><span>Formato</span><strong>{publicationFormat(detail, detailPost)}</strong></div><div><span>Publicado em</span><strong>{new Date(detail.updatedAt).toLocaleString('pt-BR')}</strong></div></div>{(detailPost?.copy || detail.request.text) && <p className="published-detail-copy">{detailPost?.copy || detail.request.text}</p>}<p className="published-detail-note">Este registro documenta o envio confirmado pela rede social. Removê-lo da Clicko não excluiria a publicação da rede.</p></section></div>}
  </section>;
}
