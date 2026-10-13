import React from 'react';
import { useOperations } from '../context/OperationsContext';
import { klicPageScope, useKlicPageDetails } from '../klic/pageContext';
import {
  Bell, Building2, Check, CircleAlert, Clock3, Copy,
  FileKey, Gauge, LifeBuoy, LockKeyhole,
  Mail, MonitorSmartphone, Save, ScrollText,
  Settings, ShieldCheck, Smartphone, UserRound, X,
} from 'lucide-react';
import { useGovernance } from '../context/GovernanceContext';
import { useTheme, type ThemeMode } from '../context/ThemeContext';
import type { UserAccount } from '../types';
import { AuditLogsView } from './AuditLogsView';
import { useAuth } from '../context/AuthContext';
import { ProfilePhotoField } from './ProfilePhotoField';
import { SupportCenterView } from './SupportCenterView';
import { ConsumptionSettingsView } from './ConsumptionSettingsView';
import { ClickoLoader } from './ClickoLoader';
import { ClickoSelectMenu } from './ClickoSelectMenu';
import { hasPermission } from '../security/accessControl';

type SectionId = 'account' | 'company' | 'security' | 'audit' | 'billing' | 'support';
type Availability = 'available' | 'not-configured' | 'development' | 'unavailable';
type Channel = 'internal' | 'email' | 'push';
type AISettings = {
  model: string; creativity: number; depth: 'objective' | 'balanced' | 'detailed'; language: string;
  writingStyle: 'direct' | 'natural' | 'technical' | 'executive' | 'creative';
  formality: 'casual' | 'professional' | 'formal'; autoCta: boolean; improvements: boolean;
  proofreading: boolean; titles: boolean; hashtags: boolean; variations: boolean;
};
type SettingsState = {
  account: { avatar: string; firstName: string; lastName: string; name: string; role: string; company: string; email: string; phone: string; language: string; timezone: string; dateFormat: string; timeFormat: string; signature: string };
  organization: { legalName: string; tradeName: string; taxId: string; industry: string; website: string; phone: string; email: string; logo: string; displayName: string; country: string; language: string; timezone: string; dateFormat: string; internalId: string };
  appearance: { theme: ThemeMode; layout: 'comfortable' | 'compact'; animations: boolean; transitions: boolean; reduceMotion: boolean };
  preferences: { homePage: string; autoWorkspace: string; defaultView: string; calendarView: string; contentSort: string; persistentFilters: boolean; aiLanguage: string; openLastPage: boolean; restoreContext: boolean };
  personalAI: AISettings;
};
type Auxiliary = { notificationChannels: Record<Channel, boolean>; notifications: Record<string, Record<Channel, boolean>> };
type Capabilities = { geminiConfigured: boolean; webhooksConfigured: boolean; analyticsConfigured: boolean; socialPublishingConfigured: boolean; storageMode: string; transactionalEmailConfigured: boolean };

const STORAGE_KEY = 'clicko-studio:user-settings';
const sections: Array<{ id: SectionId; label: string; description: string; icon: React.ComponentType<{ className?: string }> }> = [
  { id: 'account', label: 'Minha Conta', description: 'Perfil e informações pessoais', icon: UserRound },
  { id: 'company', label: 'Empresa', description: 'Identidade e dados corporativos', icon: Building2 },
  { id: 'security', label: 'Segurança', description: 'Acesso e proteção da conta', icon: ShieldCheck },
  { id: 'audit', label: 'Logs e Histórico', description: 'Atividades e auditoria', icon: ScrollText },
  { id: 'billing', label: 'Consumo', description: 'Utilização dos recursos do plano', icon: Gauge },
  { id: 'support', label: 'Ajuda e Suporte', description: 'Orientação e atendimento', icon: LifeBuoy },
];
const initialSettingsSection = (): SectionId => {
  const requested = new URLSearchParams(window.location.search).get('section') as SectionId | null;
  return requested && sections.some((section) => section.id === requested) ? requested : 'account';
};

const SettingsTopNavigation: React.FC<{
  items: typeof sections;
  active: SectionId;
  onSelect: (section: SectionId) => void;
}> = ({ items, active, onSelect }) => {
  const navigation = React.useRef<HTMLElement>(null);
  React.useEffect(() => {
    navigation.current?.querySelector<HTMLElement>('[aria-current="page"]')?.scrollIntoView({ block: 'nearest', inline: 'center' });
  }, [active]);
  const onKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const nextIndex = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1
      : event.key === 'ArrowRight' ? (index + 1) % items.length : (index - 1 + items.length) % items.length;
    const next = items[nextIndex];
    if (!next) return;
    onSelect(next.id);
    navigation.current?.querySelectorAll<HTMLButtonElement>('.clicko-settings-top-tab')[nextIndex]?.focus();
  };
  return <nav ref={navigation} className="clicko-settings-top-nav" aria-label="Navegação das Configurações">
    <div className="clicko-settings-top-nav__track">
      {items.map((section, index) => {
        const Icon = section.icon;
        const selected = section.id === active;
        return <button key={section.id} type="button" className={`clicko-settings-top-tab ${selected ? 'is-active' : ''}`} aria-current={selected ? 'page' : undefined} title={section.description} onClick={() => onSelect(section.id)} onKeyDown={(event) => onKeyDown(event, index)}>
          <Icon aria-hidden="true" />
          <span>{section.label}</span>
        </button>;
      })}
    </div>
  </nav>;
};
const notificationEvents = [
  ['approvals', 'Aprovações', 'Conteúdos que precisam de decisão'], ['comments', 'Comentários e menções', 'Respostas e marcações com @'],
  ['publications', 'Publicações', 'Agendamentos, sucessos e falhas'], ['tasks', 'Tarefas', 'Prazos e mudanças de status'],
  ['ai', 'KLIC e automações', 'Sugestões, conclusões e alertas'], ['invites', 'Convites', 'Novos membros e colaborações'],
  ['system', 'Sistema', 'Segurança e manutenção'], ['digest', 'Resumo diário', 'Consolidado diário da operação'],
] as const;

const DEFAULT_BRAZIL_TIMEZONE = 'America/Sao_Paulo';
const brazilTimezones = [
  [DEFAULT_BRAZIL_TIMEZONE, 'Brasília · GMT-3 (padrão)'],
  ['America/Noronha', 'Fernando de Noronha · GMT-2'],
  ['America/Manaus', 'Manaus · GMT-4'],
  ['America/Rio_Branco', 'Rio Branco · GMT-5'],
] as const;
const normalizeBrazilTimezone = (timezone?: string) => brazilTimezones.some(([id]) => id === timezone) ? timezone! : DEFAULT_BRAZIL_TIMEZONE;

function defaults(account: UserAccount): SettingsState {
  const parts = account.type === 'personal' ? account.name.trim().split(/\s+/).filter(Boolean) : [];
  return {
    account: { avatar: account.avatar || '', firstName: parts[0] || '', lastName: parts.slice(1).join(' '), name: account.type === 'personal' ? account.name : '', role: account.role || '', company: account.type === 'company' ? account.name : '', email: account.email || '', phone: '', language: 'pt-BR', timezone: 'America/Sao_Paulo', dateFormat: 'DD/MM/AAAA', timeFormat: '24h', signature: '' },
    organization: { legalName: '', tradeName: '', taxId: '', industry: '', website: '', phone: '', email: account.type === 'company' ? account.email || '' : '', logo: '', displayName: account.type === 'company' ? account.name : '', country: 'BR', language: 'pt-BR', timezone: 'America/Sao_Paulo', dateFormat: 'DD/MM/AAAA', internalId: account.workspaceId },
    appearance: { theme: 'dark', layout: 'comfortable', animations: true, transitions: true, reduceMotion: false },
    preferences: { homePage: 'dashboard', autoWorkspace: 'last', defaultView: 'cards', calendarView: 'week', contentSort: 'recent', persistentFilters: true, aiLanguage: 'pt-BR', openLastPage: true, restoreContext: true },
    personalAI: { model: 'server-managed', creativity: 64, depth: 'balanced', language: 'pt-BR', writingStyle: 'direct', formality: 'professional', autoCta: true, improvements: true, proofreading: true, titles: true, hashtags: true, variations: false },
  };
}
const auxiliaryDefaults = (): Auxiliary => ({ notificationChannels: { internal: true, email: false, push: false }, notifications: Object.fromEntries(notificationEvents.map(([id]) => [id, { internal: true, email: false, push: false }])) });

function loadSettings(account: UserAccount): SettingsState {
  const base = defaults(account);
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY}:${account.id}`);
    if (!raw) return base;
    const parsed = JSON.parse(raw) as Omit<Partial<SettingsState>, 'account' | 'personalAI'> & {
      account?: Partial<SettingsState['account']>;
      personalAI?: Partial<Omit<AISettings, 'depth' | 'formality'>> & { depth?: string; formality?: string | number };
    };
    const oldName = parsed.account?.name || base.account.name;
    const nameParts = oldName.trim().split(/\s+/).filter(Boolean);
    const depth = parsed.personalAI?.depth === 'concise' ? 'objective' : parsed.personalAI?.depth;
    const formality = typeof parsed.personalAI?.formality === 'number' ? parsed.personalAI.formality < 35 ? 'casual' : parsed.personalAI.formality > 72 ? 'formal' : 'professional' : parsed.personalAI?.formality;
    return {
      ...base, ...parsed,
      account: { ...base.account, ...parsed.account, avatar: account.avatar || '', firstName: parsed.account?.firstName || nameParts[0] || '', lastName: parsed.account?.lastName || nameParts.slice(1).join(' '), timezone: normalizeBrazilTimezone(parsed.account?.timezone) },
      organization: { ...base.organization, ...parsed.organization, timezone: normalizeBrazilTimezone(parsed.organization?.timezone) }, appearance: { ...base.appearance, ...parsed.appearance, theme: parsed.appearance?.theme === 'light' ? 'light' : 'dark' }, preferences: { ...base.preferences, ...parsed.preferences },
      personalAI: { ...base.personalAI, ...parsed.personalAI, depth: (['objective', 'balanced', 'detailed'].includes(String(depth)) ? depth : 'balanced') as AISettings['depth'], formality: (['casual', 'professional', 'formal'].includes(String(formality)) ? formality : 'professional') as AISettings['formality'] },
    };
  } catch { return base; }
}
function loadAuxiliary(accountId: string): Auxiliary {
  const base = auxiliaryDefaults();
  try { const saved = JSON.parse(localStorage.getItem(`${STORAGE_KEY}:${accountId}`) || '{}'); const value = saved.auxiliary || JSON.parse(localStorage.getItem(`${STORAGE_KEY}:${accountId}:auxiliary`) || '{}') as Partial<Auxiliary>; return { notificationChannels: { ...base.notificationChannels, ...value.notificationChannels }, notifications: { ...base.notifications, ...value.notifications } }; } catch { return base; }
}

const Field: React.FC<React.InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string }> = ({ label, hint, className = '', ...props }) => <label className="block min-w-0"><span className="mb-1.5 block text-[10px] font-medium text-[rgba(255,255,255,0.72)]">{label}</span><input {...props} className={`h-10 w-full rounded-lg border border-white/[0.07] bg-[rgba(128,128,128,0.14)] px-3 text-[11px] text-white outline-none transition duration-200 placeholder:text-[#808080] focus:border-[#FF7F50]/55 focus:ring-2 focus:ring-[#FF7F50]/10 disabled:cursor-not-allowed disabled:opacity-40 ${className}`} />{hint && <span className="mt-1.5 block text-[8px] leading-4 text-[#808080]">{hint}</span>}</label>;
type SettingsSelectChange = { target: { value: string } };
type SettingsSelectOptionProps = { value?: string | number; children?: React.ReactNode };
const SelectField: React.FC<{ label: string; hint?: string; value?: string | number; onChange?: (event: SettingsSelectChange) => void; options?: readonly (readonly [string, string])[]; children?: React.ReactNode }> = ({ label, hint, value = '', onChange, options: providedOptions, children }) => {
  const childOptions = React.Children.toArray(children).flatMap((child) => {
    if (!React.isValidElement<SettingsSelectOptionProps>(child)) return [];
    const name = React.Children.toArray(child.props.children).join('');
    const id = String(child.props.value ?? name);
    return [[id, name] as const];
  });
  const options = providedOptions ?? childOptions;
  return <div className="settings-select-field">
    <ClickoSelectMenu label={label} value={String(value)} options={options} onChange={(next) => onChange?.({ target: { value: next } })} className="settings-select-menu" />
    {hint && <span className="settings-select-field__hint">{hint}</span>}
  </div>;
};
const Toggle: React.FC<{ checked: boolean; onChange: (value: boolean) => void; label: string; disabled?: boolean }> = ({ checked, onChange, label, disabled }) => <button type="button" role="switch" aria-checked={checked} aria-label={label} disabled={disabled} onClick={() => onChange(!checked)} className={`relative h-[22px] w-10 shrink-0 rounded-full border transition duration-200 disabled:cursor-not-allowed disabled:opacity-35 ${checked ? 'border-[#FF7F50]/60 bg-[#FF7F50]' : 'border-white/10 bg-[rgba(128,128,128,0.34)]'}`}><span className={`absolute top-[2px] h-4 w-4 rounded-full bg-white transition-transform duration-200 ${checked ? 'translate-x-[20px]' : 'translate-x-[2px]'}`} /></button>;
const ToggleRow: React.FC<{ title: string; description: string; checked: boolean; onChange: (value: boolean) => void; disabled?: boolean; status?: string }> = ({ title, description, checked, onChange, disabled, status }) => <div className="flex items-center justify-between gap-5 border-b border-white/[0.045] py-3.5 last:border-0"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><span className="text-[11px] font-medium text-[rgba(255,255,255,0.88)]">{title}</span>{status && <span className="rounded-full bg-white/[0.045] px-2 py-0.5 text-[7px] text-[#808080]">{status}</span>}</div><p className="mt-0.5 text-[9px] leading-4 text-[#808080]">{description}</p></div><Toggle label={title} checked={checked} onChange={onChange} disabled={disabled} /></div>;
const Section: React.FC<{ title?: string; description?: string; children: React.ReactNode }> = ({ title, description, children }) => <section className="border-b border-white/[0.06] py-6 first:pt-0 last:border-0">{(title || description) && <header className="mb-5"><h3 className="text-[13px] font-semibold text-white">{title}</h3>{description && <p className="mt-1 max-w-2xl text-[9px] leading-5 text-[#808080]">{description}</p>}</header>}{children}</section>;
const Status: React.FC<{ state: Availability; label?: string }> = ({ state, label }) => {
  const meta = { available: [label || 'Disponível', 'bg-[#FF7F50]', 'border-[#FF7F50]/20 bg-[#FF7F50]/[0.07] text-[#FF7F50]'], 'not-configured': [label || 'Não configurado', 'bg-[#F28500]', 'border-[#F28500]/20 bg-[#F28500]/[0.06] text-[#F28500]'], development: [label || 'Em desenvolvimento', 'bg-[#808080]', 'border-white/[0.07] bg-white/[0.035] text-[#808080]'], unavailable: [label || 'Indisponível', 'bg-[#808080]', 'border-white/[0.06] bg-white/[0.025] text-[#808080]'] }[state];
  return <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-1 text-[8px] ${meta[2]}`}><span className={`h-1.5 w-1.5 rounded-full ${meta[1]}`} />{meta[0]}</span>;
};

const acceptedProfileImageTypes = new Set(['image/jpeg', 'image/png', 'image/webp']);
const maxProfileImageBytes = 5 * 1024 * 1024;

function blobAsDataUrl(blob: Blob) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => typeof reader.result === 'string' ? resolve(reader.result) : reject(new Error('Não foi possível processar a imagem.'));
    reader.onerror = () => reject(new Error('Não foi possível ler a imagem selecionada.'));
    reader.readAsDataURL(blob);
  });
}

async function decodeProfileImage(file: File): Promise<{ source: CanvasImageSource; width: number; height: number; close: () => void }> {
  if (typeof createImageBitmap === 'function') {
    const bitmap = await createImageBitmap(file);
    return { source: bitmap, width: bitmap.width, height: bitmap.height, close: () => bitmap.close() };
  }
  const sourceUrl = URL.createObjectURL(file);
  try {
    const image = await new Promise<HTMLImageElement>((resolve, reject) => {
      const element = new Image();
      element.onload = () => resolve(element);
      element.onerror = () => reject(new Error('A imagem selecionada não pôde ser aberta.'));
      element.src = sourceUrl;
    });
    return { source: image, width: image.naturalWidth, height: image.naturalHeight, close: () => {} };
  } finally {
    URL.revokeObjectURL(sourceUrl);
  }
}

async function optimizeProfileImage(file: File, target: 'avatar' | 'logo') {
  if (!acceptedProfileImageTypes.has(file.type)) throw new Error('Selecione uma imagem JPG, PNG ou WebP.');
  if (file.size > maxProfileImageBytes) throw new Error('A imagem deve possuir no máximo 5 MB.');

  let decoded: Awaited<ReturnType<typeof decodeProfileImage>>;
  try {
    decoded = await decodeProfileImage(file);
  } catch {
    throw new Error('A imagem selecionada não pôde ser aberta.');
  }
  try {
    if (!decoded.width || !decoded.height) throw new Error('A imagem selecionada não é válida.');
    const maxSide = target === 'avatar' ? 512 : 1024;
    const scale = Math.min(1, maxSide / Math.max(decoded.width, decoded.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(decoded.width * scale));
    canvas.height = Math.max(1, Math.round(decoded.height * scale));
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Não foi possível processar a imagem neste navegador.');
    context.imageSmoothingEnabled = true;
    context.imageSmoothingQuality = 'high';
    context.drawImage(decoded.source, 0, 0, canvas.width, canvas.height);
    const optimized = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/webp', 0.86));
    if (!optimized) throw new Error('Não foi possível otimizar a imagem selecionada.');
    return blobAsDataUrl(optimized);
  } finally {
    decoded.close();
  }
}

export const SettingsView: React.FC = () => {
  const { environmentMode, activeAccount, currentUser } = useGovernance();
  const { activeWorkspace, activeClient } = useOperations();
  const { theme, setTheme } = useTheme();
  const { uploadAvatar } = useAuth();
  const [avatarFile, setAvatarFile] = React.useState<File>();
  const [avatarPreview, setAvatarPreview] = React.useState('');
  const [saving, setSaving] = React.useState(false);
  const imageRequest = React.useRef(0);
  const saveController = React.useRef<AbortController | null>(null);
  React.useEffect(() => () => { imageRequest.current += 1; saveController.current?.abort(); }, [activeAccount.id]);
  React.useEffect(() => () => { if (avatarPreview) URL.revokeObjectURL(avatarPreview); }, [avatarPreview]);
  const isPersonal = environmentMode === 'personal';
  const [activeSection, setActiveSection] = React.useState<SectionId>(initialSettingsSection);
  const [value, setValue] = React.useState(() => loadSettings(activeAccount));
  const [auxiliary, setAuxiliary] = React.useState(() => loadAuxiliary(activeAccount.id));
  const [savedValue, setSavedValue] = React.useState(value);
  const [savedAuxiliary, setSavedAuxiliary] = React.useState(auxiliary);
  const [dirty, setDirty] = React.useState(false);
  const [feedback, setFeedback] = React.useState<'saved' | 'error' | null>(null);
  const [pendingSection, setPendingSection] = React.useState<SectionId | null>(null);
  const [imageError, setImageError] = React.useState('');
  const [copied, setCopied] = React.useState(false);
  useKlicPageDetails('settings', klicPageScope(activeWorkspace.id, activeClient?.id), { view: activeSection });
  const [capabilities, setCapabilities] = React.useState<Capabilities | null>(null);
  const canReadSubscription = isPersonal || hasPermission(currentUser, 'subscription.read');
  const canReadOwnUsage = isPersonal || hasPermission(currentUser, 'usage.read.own');
  const visibleSections = React.useMemo(() => sections.filter((section) => {
    if (section.id === 'company') return !isPersonal;
    if (section.id === 'audit') return hasPermission(currentUser, 'audit.read');
    if (section.id === 'billing') return canReadSubscription || canReadOwnUsage;
    return true;
  }), [canReadOwnUsage, canReadSubscription, currentUser, isPersonal]);
  const currentSection = visibleSections.find((section) => section.id === activeSection) || visibleSections[0];

  React.useEffect(() => { const next = loadSettings(activeAccount); const nextAux = loadAuxiliary(activeAccount.id); setValue(next); setSavedValue(next); setAuxiliary(nextAux); setSavedAuxiliary(nextAux); setDirty(false); setFeedback(null); setActiveSection(initialSettingsSection()); setAvatarFile(undefined); setAvatarPreview(''); setImageError(''); }, [activeAccount.id]);
  React.useEffect(() => {
    if (!currentUser || dirty || value.account.firstName) return;
    const parts = currentUser.name.trim().split(/\s+/).filter(Boolean);
    const account = { ...value.account, firstName: parts[0] || '', lastName: parts.slice(1).join(' '), name: currentUser.name, email: value.account.email || currentUser.email || '', role: value.account.role || currentUser.role };
    const next = { ...value, account };
    setValue(next);
    setSavedValue(next);
  }, [currentUser, dirty, value]);
  React.useEffect(() => { if (isPersonal && activeSection === 'company') setActiveSection('account'); }, [activeSection, isPersonal]);
  React.useEffect(() => { if (!visibleSections.some((section) => section.id === activeSection)) setActiveSection('account'); }, [activeSection, visibleSections]);
  React.useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get('section');
    if (requested && !visibleSections.some((section) => section.id === requested)) {
      window.history.replaceState({}, '', '/settings?section=account');
      setActiveSection('account');
    }
  }, [visibleSections]);
  React.useEffect(() => {
    const syncSection = () => {
      const requested = initialSettingsSection();
      if (visibleSections.some((section) => section.id === requested)) setActiveSection(requested);
    };
    window.addEventListener('popstate', syncSection);
    window.addEventListener('clicko:settings-section', syncSection);
    return () => { window.removeEventListener('popstate', syncSection); window.removeEventListener('clicko:settings-section', syncSection); };
  }, [visibleSections]);
  React.useEffect(() => { if (!feedback) return; const timeout = window.setTimeout(() => setFeedback(null), 2600); return () => window.clearTimeout(timeout); }, [feedback]);
  const refreshCapabilities = React.useCallback(async () => {
    try {
      const response = await fetch('/api/capabilities');
      if (!response.ok) throw new Error('Não foi possível consultar as capacidades da plataforma.');
      setCapabilities(await response.json() as Capabilities);
    } catch {
      // Unavailable channels stay disabled when the server cannot verify them.
      setCapabilities(null);
    }
  }, []);
  React.useEffect(() => { void refreshCapabilities(); }, [refreshCapabilities]);

  const patch = <K extends keyof SettingsState>(group: K, next: Partial<SettingsState[K]>) => { setValue((current) => ({ ...current, [group]: { ...current[group], ...next } })); setDirty(true); setFeedback(null); };
  const chooseTheme = (next: ThemeMode) => {
    setTheme(next);
    setValue((current) => ({ ...current, appearance: { ...current.appearance, theme: next } }));
    setSavedValue((current) => ({ ...current, appearance: { ...current.appearance, theme: next } }));
    setFeedback(null);
  };
  React.useLayoutEffect(() => {
    const host = document.createElement('div');
    host.className = 'clicko-settings-theme-switcher';
    host.setAttribute('role', 'radiogroup');
    host.setAttribute('aria-label', 'Tema da interface');
    const render = () => {
      host.innerHTML = `<button type="button" data-theme-option="light" role="radio" aria-checked="${theme === 'light'}">Claro</button><button type="button" data-theme-option="dark" role="radio" aria-checked="${theme === 'dark'}">Escuro</button>`;
      host.querySelectorAll<HTMLButtonElement>('button').forEach((button) => {
        button.className = button.dataset.themeOption === theme ? 'is-selected' : '';
        button.addEventListener('click', () => chooseTheme(button.dataset.themeOption as ThemeMode));
      });
    };
    render();
    const saveButton = Array.from(document.querySelectorAll<HTMLButtonElement>('.clicko-main-stage header button'))
      .find((button) => button.textContent?.includes('Salvar alterações'));
    const mount = saveButton?.parentElement;
    if (!mount || !saveButton) return;
    mount.insertBefore(host, saveButton);
    return () => host.remove();
  }, [theme]);
  const patchAux = (next: Auxiliary) => { setAuxiliary(next); setDirty(true); setFeedback(null); };
  const save = async () => {
    if (saving) return;
    const controller = new AbortController();
    saveController.current = controller;
    setSaving(true);
    setImageError('');
    try {
      const avatar = avatarFile ? await uploadAvatar(avatarFile, activeAccount.workspaceId, controller.signal) : (activeAccount.avatar || '');
      if (controller.signal.aborted) return;
      const account = { ...value.account, avatar, name: `${value.account.firstName} ${value.account.lastName}`.trim() };
      const next = { ...value, account };
      localStorage.setItem(`${STORAGE_KEY}:${activeAccount.id}`, JSON.stringify({ ...next, auxiliary }));
      setValue(next); setSavedValue(next); setSavedAuxiliary(auxiliary);
      setAvatarFile(undefined); setAvatarPreview(''); setDirty(false); setFeedback('saved');
    } catch (error) {
      if (controller.signal.aborted) return;
      setImageError(error instanceof Error ? error.message : 'Não foi possível salvar a foto.');
      setFeedback('error');
    } finally {
      if (!controller.signal.aborted) setSaving(false);
    }
  };
  const discard = () => { imageRequest.current += 1; setAvatarFile(undefined); setAvatarPreview(''); setImageError(''); setValue(savedValue); setAuxiliary(savedAuxiliary); setDirty(false); setFeedback(null); };
  const commitSection = (section: SectionId) => { setActiveSection(section); window.history.pushState({}, '', `/settings?section=${section}`); };
  const navigate = (section: SectionId) => { if (section === activeSection) return; if (dirty) setPendingSection(section); else commitSection(section); };
  const discardAndNavigate = () => { discard(); if (pendingSection) commitSection(pendingSection); setPendingSection(null); };
  const handleImage = async (target: 'avatar' | 'logo', file?: File) => {
    if (!file || saving) return;
    const request = ++imageRequest.current;
    setImageError('');
    try {
      if (!acceptedProfileImageTypes.has(file.type)) throw new Error('Selecione uma imagem JPG, PNG ou WebP.');
      if (!file.size || file.size > maxProfileImageBytes) throw new Error('Selecione uma imagem de até 5 MB.');
      if (target === 'avatar') {
        // The selected file remains the upload payload. Preview never waits for
        // compression, and the server validates/normalizes the actual bytes.
        const decoded = await decodeProfileImage(file);
        decoded.close();
        if (request !== imageRequest.current) return;
        setAvatarPreview(URL.createObjectURL(file));
        setAvatarFile(file);
        setDirty(true); setFeedback(null);
      } else {
        const image = await optimizeProfileImage(file, target);
        if (request === imageRequest.current) patch('organization', { logo: image });
      }
    } catch (error) {
      if (request === imageRequest.current) setImageError(error instanceof Error ? error.message : 'Não foi possível abrir a imagem.');
    }
  };
  const copyId = async () => { try { await navigator.clipboard.writeText(value.organization.internalId); setCopied(true); window.setTimeout(() => setCopied(false), 1800); } catch { setCopied(false); } };

  const renderAccount = () => {
    const initials = `${value.account.firstName[0] || ''}${value.account.lastName[0] || ''}`.toUpperCase() || 'C';
    return <div><Section><div className="flex flex-col gap-5 sm:flex-row sm:items-center"><ProfilePhotoField src={avatarPreview || activeAccount.avatar || ''} initials={initials} disabled={saving} onSelect={(file) => void handleImage('avatar', file)} /><div className="min-w-0 flex-1"><h3 className="truncate text-[15px] font-semibold text-white">{`${value.account.firstName} ${value.account.lastName}`.trim() || activeAccount.name}</h3><p className="mt-1 text-[10px] text-[#808080]">{value.account.role || 'Cargo não informado'}{value.account.company ? ` · ${value.account.company}` : ''}</p>{imageError && <p role="alert" className="mt-2 text-[8px] text-[#FF7F50]">{imageError}</p>}</div></div></Section><Section title="Informações pessoais"><div className="grid gap-4 sm:grid-cols-2"><Field label="Nome" value={value.account.firstName} onChange={(event) => patch('account', { firstName: event.target.value })} /><Field label="Sobrenome" value={value.account.lastName} onChange={(event) => patch('account', { lastName: event.target.value })} /><Field label="Cargo" value={value.account.role} onChange={(event) => patch('account', { role: event.target.value })} /><Field label="Empresa" value={value.account.company} onChange={(event) => patch('account', { company: event.target.value })} /><Field label="E-mail" type="email" value={value.account.email} onChange={(event) => patch('account', { email: event.target.value })} /><Field label="Telefone" value={value.account.phone} placeholder="Não informado" onChange={(event) => patch('account', { phone: event.target.value })} /></div></Section><Section title="Localização e formatos"><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><SelectField label="Idioma" value={value.account.language} onChange={(event) => patch('account', { language: event.target.value })}><option value="pt-BR">Português (Brasil)</option><option value="en-US">English (US)</option><option value="es">Español</option></SelectField><SelectField label="Fuso horário" value={value.account.timezone} onChange={(event) => patch('account', { timezone: event.target.value })} options={brazilTimezones} /><SelectField label="Formato de data" value={value.account.dateFormat} onChange={(event) => patch('account', { dateFormat: event.target.value })}><option>DD/MM/AAAA</option><option>MM/DD/AAAA</option><option>AAAA-MM-DD</option></SelectField><SelectField label="Formato de hora" value={value.account.timeFormat} onChange={(event) => patch('account', { timeFormat: event.target.value })}><option value="24h">24 horas</option><option value="12h">12 horas</option></SelectField></div></Section></div>;
  };

  const renderCompany = () => <div><Section title="Identidade da organização" description="Somente informações fornecidas pela equipe são mantidas nesta área."><div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-center"><div className="grid h-16 w-16 shrink-0 place-items-center overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.035]">{value.organization.logo ? <img src={value.organization.logo} alt="Logo da organização" className="h-full w-full object-contain" /> : <Building2 className="h-5 w-5 text-[#808080]" />}</div><div className="flex-1"><h3 className="text-[13px] font-medium text-white">{value.organization.displayName || activeAccount.name}</h3><p className="mt-1 text-[9px] text-[#808080]">Logo e nome exibidos no contexto corporativo.</p></div><label className="w-fit cursor-pointer rounded-lg border border-white/[0.08] px-3 py-2 text-[9px] text-[rgba(255,255,255,0.72)] hover:border-[#FF7F50]/30 hover:text-[#FF7F50]">Alterar logo<input type="file" accept="image/*" className="hidden" onChange={(event) => handleImage('logo', event.target.files?.[0])} /></label></div><div className="grid gap-4 sm:grid-cols-2"><Field label="Nome da empresa" value={value.organization.legalName} placeholder="Não informado" onChange={(event) => patch('organization', { legalName: event.target.value })} /><Field label="Nome fantasia" value={value.organization.tradeName} placeholder="Não informado" onChange={(event) => patch('organization', { tradeName: event.target.value })} /><Field label="Nome exibido" value={value.organization.displayName} onChange={(event) => patch('organization', { displayName: event.target.value })} /><Field label="CNPJ" value={value.organization.taxId} placeholder="Não informado" onChange={(event) => patch('organization', { taxId: event.target.value })} /><Field label="Segmento" value={value.organization.industry} placeholder="Não informado" onChange={(event) => patch('organization', { industry: event.target.value })} /><Field label="Site" value={value.organization.website} placeholder="Não informado" onChange={(event) => patch('organization', { website: event.target.value })} /><Field label="Telefone" value={value.organization.phone} placeholder="Não informado" onChange={(event) => patch('organization', { phone: event.target.value })} /><Field label="E-mail corporativo" type="email" value={value.organization.email} placeholder="Não informado" onChange={(event) => patch('organization', { email: event.target.value })} /></div></Section><Section title="Configurações organizacionais"><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><SelectField label="País" value={value.organization.country} onChange={(event) => patch('organization', { country: event.target.value })}><option value="BR">Brasil</option><option value="PT">Portugal</option><option value="US">Estados Unidos</option></SelectField><SelectField label="Idioma" value={value.organization.language} onChange={(event) => patch('organization', { language: event.target.value })}><option value="pt-BR">Português (Brasil)</option><option value="en-US">English (US)</option><option value="es">Español</option></SelectField><SelectField label="Fuso horário" value={value.organization.timezone} onChange={(event) => patch('organization', { timezone: event.target.value })} options={brazilTimezones} /><SelectField label="Formato de data" value={value.organization.dateFormat} onChange={(event) => patch('organization', { dateFormat: event.target.value })}><option>DD/MM/AAAA</option><option>MM/DD/AAAA</option><option>AAAA-MM-DD</option></SelectField></div></Section><Section title="Identificador interno" description="Identificador técnico real deste ambiente. Não é editável."><div className="flex max-w-xl items-center gap-2 rounded-lg border border-white/[0.06] bg-[rgba(128,128,128,0.14)] p-3"><code className="min-w-0 flex-1 truncate text-[10px] text-[rgba(255,255,255,0.72)]">{value.organization.internalId}</code><button type="button" onClick={() => void copyId()} className="flex h-8 items-center gap-1.5 rounded-md px-2.5 text-[8px] text-[#808080] hover:bg-white/[0.04] hover:text-white">{copied ? <Check className="h-3.5 w-3.5 text-[#FF7F50]" /> : <Copy className="h-3.5 w-3.5" />}{copied ? 'Copiado' : 'Copiar'}</button></div></Section></div>;


  const renderSecurity = () => {
    const lastAccess = currentUser?.lastAccess ? new Date(currentUser.lastAccess).toLocaleString('pt-BR') : 'Não informado pelo servidor';
    const summary: Array<[string, string, React.ComponentType<{ className?: string }>, Availability]> = [['Senha', 'Integração pendente', LockKeyhole, 'development'], ['Autenticação em dois fatores', 'Integração pendente', FileKey, 'development'], ['Sessões abertas', 'Dados indisponíveis', MonitorSmartphone, 'unavailable'], ['Último acesso', lastAccess, Clock3, currentUser?.lastAccess ? 'available' : 'unavailable']];
    return <div><Section title="Resumo de segurança" description="Visão baseada exclusivamente nos dados atualmente disponíveis."><div className="grid gap-px overflow-hidden rounded-xl border border-white/[0.06] bg-white/[0.06] sm:grid-cols-2 xl:grid-cols-4">{summary.map(([title, text, Icon, state]) => <div key={title} className="bg-[rgba(128,128,128,0.14)] p-4"><Icon className="h-4 w-4 text-[#FF7F50]" /><span className="mt-4 block text-[8px] uppercase tracking-[0.12em] text-[#808080]">{title}</span><strong className="mt-1 block text-[10px] font-medium text-white">{text}</strong><div className="mt-3"><Status state={state} /></div></div>)}</div></Section><Section title="Alteração de senha" description="O serviço de identidade ainda não expõe uma operação segura de troca de senha."><div className="max-w-xl rounded-xl border border-white/[0.06] bg-white/[0.015] p-4"><div className="mb-4 flex items-center justify-between gap-3"><span className="text-[10px] font-medium text-white">Credenciais da conta</span><Status state="development" label="Integração pendente" /></div><div className="grid gap-3 sm:grid-cols-2"><Field label="Nova senha" type="password" placeholder="Indisponível" disabled /><Field label="Confirmar senha" type="password" placeholder="Indisponível" disabled /></div><button disabled className="mt-4 rounded-lg bg-[#FF7F50] px-4 py-2.5 text-[9px] font-semibold text-black opacity-35">Atualizar senha</button></div></Section><Section title="Autenticação em dois fatores" description="A ativação será disponibilizada quando o serviço de autenticação estiver conectado."><div className="max-w-xl"><ToggleRow title="Autenticação 2FA" description="Adiciona uma segunda etapa ao login" checked={false} onChange={() => undefined} disabled status="Em desenvolvimento" /></div></Section><Section title="Sessões ativas" description="Dispositivos e localizações serão exibidos quando o backend de sessões estiver disponível."><Empty icon={MonitorSmartphone} title="Nenhum dado de sessão disponível" text="A Clicko não gera sessões fictícias para preencher esta área." /></Section><Section title="Histórico de acesso"><Empty icon={Clock3} title="Histórico ainda indisponível" text="O serviço de autenticação ainda não fornece registros detalhados." /></Section></div>;
  };

  const renderPreferences = () => {
    const channels: Record<Channel, boolean> = { internal: true, email: Boolean(capabilities?.transactionalEmailConfigured), push: false };
    return <div><Section title="Inicialização"><div className="grid gap-4 lg:grid-cols-2"><SelectField label="Página inicial" value={value.preferences.homePage} onChange={(event) => patch('preferences', { homePage: event.target.value })}><option value="dashboard">Dashboard</option><option value="calendar">Calendário</option><option value="library">Biblioteca</option><option value="analytics">Analytics</option></SelectField><SelectField label="Ambiente automático" value={value.preferences.autoWorkspace} onChange={(event) => patch('preferences', { autoWorkspace: event.target.value })}><option value="last">Último acessado</option><option value="none">Sempre perguntar</option></SelectField></div><div className="mt-3 grid gap-x-8 lg:grid-cols-2"><ToggleRow title="Reabrir última página" description="Retoma a última área utilizada" checked={value.preferences.openLastPage} onChange={(next) => patch('preferences', { openLastPage: next })} /><ToggleRow title="Restaurar contexto" description="Preserva o contexto da última sessão" checked={value.preferences.restoreContext} onChange={(next) => patch('preferences', { restoreContext: next })} /></div></Section><Section title="Visualização"><div className="grid gap-4 md:grid-cols-3"><SelectField label="Conteúdos" value={value.preferences.defaultView} onChange={(event) => patch('preferences', { defaultView: event.target.value })}><option value="list">Lista</option><option value="cards">Cartões</option><option value="kanban">Kanban</option></SelectField><SelectField label="Calendário" value={value.preferences.calendarView} onChange={(event) => patch('preferences', { calendarView: event.target.value })}><option value="week">Semana</option><option value="month">Mês</option></SelectField><SelectField label="Ordenação" value={value.preferences.contentSort} onChange={(event) => patch('preferences', { contentSort: event.target.value })}><option value="recent">Mais recentes</option><option value="oldest">Mais antigos</option><option value="status">Por status</option><option value="performance">Por desempenho</option></SelectField></div></Section><Section title="Comportamento e KLIC"><div className="grid gap-x-8 lg:grid-cols-2"><ToggleRow title="Filtros persistentes" description="Mantém filtros entre sessões e páginas" checked={value.preferences.persistentFilters} onChange={(next) => patch('preferences', { persistentFilters: next })} /><SelectField label="Idioma padrão da KLIC" value={value.preferences.aiLanguage} onChange={(event) => patch('preferences', { aiLanguage: event.target.value })}><option value="pt-BR">Português (Brasil)</option><option value="en-US">English (US)</option><option value="es">Español</option></SelectField></div></Section><Section title="Notificações" description="Canais não conectados permanecem identificados e indisponíveis."><div className="grid gap-2 sm:grid-cols-3">{([['internal', 'Na Clicko', Bell, 'Canal interno da plataforma'], ['email', 'Por e-mail', Mail, 'Requer e-mail transacional'], ['push', 'No celular', Smartphone, 'Integração ainda não disponível']] as const).map(([id, label, Icon, description]) => <div key={id} className="rounded-xl border border-white/[0.06] p-4"><div className="flex items-center justify-between"><Icon className="h-4 w-4 text-[#FF7F50]" /><Toggle label={label} checked={auxiliary.notificationChannels[id]} disabled={!channels[id]} onChange={(next) => patchAux({ ...auxiliary, notificationChannels: { ...auxiliary.notificationChannels, [id]: next } })} /></div><strong className="mt-4 block text-[10px] font-medium text-white">{label}</strong><p className="mt-1 text-[8px] leading-4 text-[#808080]">{description}</p><div className="mt-3"><Status state={channels[id] ? 'available' : id === 'email' ? 'not-configured' : 'development'} /></div></div>)}</div><div className="mt-5 divide-y divide-white/[0.05] rounded-xl border border-white/[0.06] px-4">{notificationEvents.map(([id, title, description]) => <div key={id} className="py-4"><div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><strong className="text-[10px] font-medium text-white">{title}</strong><p className="mt-1 text-[8px] text-[#808080]">{description}</p></div><div className="grid grid-cols-3 gap-1">{(['internal', 'email', 'push'] as const).map((channel) => <button key={channel} type="button" disabled={!channels[channel]} onClick={() => patchAux({ ...auxiliary, notifications: { ...auxiliary.notifications, [id]: { ...auxiliary.notifications[id], [channel]: !auxiliary.notifications[id][channel] } } })} className={`rounded-md border px-2.5 py-1.5 text-[7px] disabled:cursor-not-allowed disabled:opacity-30 ${auxiliary.notifications[id][channel] && channels[channel] ? 'border-[#FF7F50]/25 bg-[#FF7F50]/[0.07] text-[#FF7F50]' : 'border-white/[0.06] text-[#808080]'}`}>{channel === 'internal' ? 'Clicko' : channel === 'email' ? 'E-mail' : 'Celular'}</button>)}</div></div></div>)}</div></Section></div>;
  };


  const renderBilling = () => <ConsumptionSettingsView />;

  const renderSupport = () => <SupportCenterView />;

  const renderCurrent = () => ({ account: renderAccount, company: renderCompany, security: renderSecurity, preferences: renderPreferences, audit: () => <AuditLogsView embedded />, billing: renderBilling, support: renderSupport }[activeSection] || renderAccount)();

  return <div className="mx-auto w-full max-w-[1480px] px-4 pb-24 pt-5 sm:px-6 lg:px-8 lg:pt-7"><header className="mb-5 border-b border-white/[0.06] pb-5"><div className="flex flex-wrap items-end justify-between gap-4"><div><div className="flex items-center gap-2.5"><span className="grid h-8 w-8 place-items-center rounded-lg bg-[#FF7F50]/[0.08] text-[#FF7F50]"><Settings className="h-4 w-4" /></span><h1 className="text-[20px] font-semibold tracking-[-0.025em] text-white">Configurações</h1></div></div><button onClick={save} disabled={!dirty || saving} className="flex h-9 items-center gap-2 rounded-lg bg-[#FF7F50] px-4 text-[9px] font-semibold text-black hover:bg-[#FF7F50] disabled:cursor-not-allowed disabled:opacity-30">{saving ? <ClickoLoader size="tiny" tone="light" label="Salvando configurações" /> : <Save className="h-3.5 w-3.5" />}Salvar alterações</button></div></header><SettingsTopNavigation items={visibleSections} active={activeSection} onSelect={navigate} /><div className="clicko-settings-layout"><main className="min-w-0"><header className="mb-6 flex flex-wrap items-start justify-between gap-3 border-b border-white/[0.06] pb-5"><div><h2 className="text-[17px] font-semibold tracking-[-0.02em] text-white">{currentSection.label}</h2><p className="mt-1 text-[9px] text-[#808080]">{currentSection.description}</p></div></header>{renderCurrent()}</main></div>{(dirty || feedback) && <div className="fixed bottom-4 left-1/2 z-[70] w-[calc(100%-2rem)] max-w-2xl -translate-x-1/2 rounded-xl border border-white/[0.09] bg-[rgba(128,128,128,0.14)]/95 p-3 shadow-2xl shadow-black/60 backdrop-blur-xl"><div className="flex flex-col gap-3 sm:flex-row sm:items-center"><div className="flex flex-1 items-center gap-3">{feedback === 'saved' ? <Check className="h-4 w-4 text-[#FF7F50]" /> : <CircleAlert className="h-4 w-4 text-[#F28500]" />}<div><strong className="block text-[9px] font-medium text-white">{feedback === 'saved' ? 'Alterações salvas' : feedback === 'error' ? 'Não foi possível salvar' : 'Alterações não salvas'}</strong><span className="text-[7px] text-[#808080]">{feedback === 'saved' ? 'As preferências desta conta foram atualizadas.' : feedback === 'error' ? 'Verifique o armazenamento do navegador.' : 'Salve ou descarte antes de mudar de seção.'}</span></div></div>{dirty && <div className="flex gap-2"><button onClick={discard} className="h-8 rounded-lg px-3 text-[8px] text-[#808080] hover:bg-white/[0.04] hover:text-white">Cancelar</button><button onClick={save} disabled={saving} className="flex h-8 items-center gap-2 rounded-lg bg-[#FF7F50] px-3 text-[8px] font-semibold text-black">{saving && <ClickoLoader size="tiny" tone="light" label="Salvando configurações" />}Salvar alterações</button></div>}</div></div>}{pendingSection && <div className="fixed inset-0 z-[90] grid place-items-center bg-black/75 p-4 backdrop-blur-sm" role="dialog" aria-modal="true"><div className="w-full max-w-sm rounded-2xl border border-white/[0.09] bg-[rgba(128,128,128,0.14)] p-5"><div className="flex items-start justify-between"><div><h3 className="text-[14px] font-semibold text-white">Descartar alterações?</h3><p className="mt-2 text-[9px] leading-5 text-[#808080]">Existem alterações não salvas. Você pode continuar editando ou descartá-las antes de navegar.</p></div><button onClick={() => setPendingSection(null)} className="grid h-8 w-8 place-items-center rounded-lg text-[#808080] hover:bg-white/[0.04] hover:text-white"><X className="h-4 w-4" /></button></div><div className="mt-5 flex justify-end gap-2"><button onClick={() => setPendingSection(null)} className="h-9 rounded-lg px-3 text-[9px] text-[rgba(255,255,255,0.72)] hover:bg-white/[0.04] hover:text-white">Continuar editando</button><button onClick={discardAndNavigate} className="h-9 rounded-lg bg-[#FF7F50] px-3 text-[9px] font-semibold text-black">Descartar e sair</button></div></div></div>}</div>;
};

const Empty: React.FC<{ icon: React.ComponentType<{ className?: string }>; title: string; text: string; badge?: string }> = ({ icon: Icon, title, text, badge }) => <div className="grid min-h-36 place-items-center rounded-xl border border-dashed border-white/[0.07] px-5 text-center"><div><Icon className="mx-auto h-5 w-5 text-[#808080]" /><h4 className="mt-3 text-[10px] font-medium text-white">{title}</h4><p className="mx-auto mt-1 max-w-md text-[8px] leading-4 text-[#808080]">{text}</p>{badge && <div className="mt-3"><Status state="development" label={badge} /></div>}</div></div>;
