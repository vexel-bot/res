import React from 'react';
import {
  Activity,
  Bell,
  BellRing,
  Bot,
  BookOpen,
  Bug,
  CalendarDays,
  Camera,
  Check,
  CheckCircle2,
  ChevronRight,
  Copy,
  CreditCard,
  ExternalLink,
  Eye,
  FileKey,
  HelpCircle,
  History,
  Keyboard,
  Languages,
  Laptop,
  LayoutGrid,
  LifeBuoy,
  Lightbulb,
  List,
  LogOut,
  Mail,
  MessageCircle,
  PanelLeftClose,
  PlayCircle,
  Plus,
  RefreshCw,
  Save,
  Search,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Smartphone,
  Sparkles,
  UserRound,
  Zap,
  Building2,
  PlugZap,
  MonitorSmartphone,
} from 'lucide-react';

import { useGovernance } from '../context/GovernanceContext';

type SectionId =
  | 'account'
  | 'company'
  | 'platform'
  | 'security'
  | 'preferences'
  | 'personal-ai'
  | 'billing'
  | 'support';

type ToggleProps = {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
};

type PersonalSettings = {
  account: {
    avatar: string;
    name: string;
    role: string;
    company: string;
    email: string;
    phone: string;
    language: string;
    timezone: string;
    dateFormat: string;
    signature: string;
  };
  appearance: {
    theme: 'dark' | 'light' | 'system';
    accent: string;
    layout: 'comfortable' | 'compact';
    uiSize: 'small' | 'medium' | 'large';
    sidebarCollapsed: boolean;
    animations: boolean;
    glass: boolean;
    rounded: boolean;
    density: 'low' | 'medium' | 'high';
  };
  preferences: {
    homePage: string;
    autoWorkspace: string;
    defaultView: string;
    calendarView: string;
    contentSort: string;
    persistentFilters: boolean;
    aiLanguage: string;
    openLastPage: boolean;
  };
  personalAI: {
    model: string;
    creativity: number;
    depth: string;
    language: string;
    writingStyle: string;
    formality: number;
    autoCta: boolean;
    improvements: boolean;
    proofreading: boolean;
    titles: boolean;
    hashtags: boolean;
    variations: boolean;
  };
  privacy: {
    usageData: boolean;
    aiHistory: boolean;
    personalizeAI: boolean;
    activityStatus: boolean;
  };
};

const STORAGE_KEY = 'clicko-studio:user-settings:pedro-henrique';

const defaultSettings: PersonalSettings = {
  account: {
    avatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=240&q=85',
    name: 'Pedro Henrique',
    role: 'Administrador',
    company: 'Clicko Studio',
    email: 'pedro@clickostudio.com',
    phone: '+55 (11) 99999-0000',
    language: 'pt-BR',
    timezone: 'America/Sao_Paulo',
    dateFormat: 'DD/MM/AAAA',
    signature: 'Pedro Henrique\nAdministrador · Clicko Studio',
  },
  appearance: {
    theme: 'dark',
    accent: '#ff5c5c',
    layout: 'comfortable',
    uiSize: 'medium',
    sidebarCollapsed: false,
    animations: true,
    glass: true,
    rounded: true,
    density: 'medium',
  },
  preferences: {
    homePage: 'dashboard',
    autoWorkspace: 'last',
    defaultView: 'cards',
    calendarView: 'week',
    contentSort: 'recent',
    persistentFilters: true,
    aiLanguage: 'pt-BR',
    openLastPage: true,
  },
  personalAI: {
    model: 'clicko-pro',
    creativity: 64,
    depth: 'balanced',
    language: 'pt-BR',
    writingStyle: 'direct',
    formality: 58,
    autoCta: true,
    improvements: true,
    proofreading: true,
    titles: true,
    hashtags: true,
    variations: false,
  },
  privacy: {
    usageData: true,
    aiHistory: true,
    personalizeAI: true,
    activityStatus: false,
  },
};

const sections: Array<{
  id: SectionId;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}> = [
  { id: 'account', label: 'Minha Conta', description: 'Perfil e informações pessoais', icon: UserRound },
  { id: 'company', label: 'Empresa', description: 'Identidade e dados corporativos', icon: Building2 },
  { id: 'platform', label: 'Plataforma', description: 'Tema, APIs e integrações gerais', icon: PlugZap },
  { id: 'security', label: 'Segurança', description: 'Senha, 2FA e sessões', icon: ShieldCheck },
  { id: 'preferences', label: 'Preferências', description: 'Experiência e notificações do sistema', icon: SlidersHorizontal },
  { id: 'personal-ai', label: 'IA Pessoal', description: 'Comportamento do assistente', icon: Bot },
  { id: 'billing', label: 'Plano e Assinatura', description: 'Uso, cobrança e assinatura', icon: CreditCard },
  { id: 'support', label: 'Ajuda e Suporte', description: 'Documentação e atendimento', icon: LifeBuoy },
];

const notificationEvents = [
  ['approvals', 'Aprovações', 'Quando um conteúdo precisar da sua aprovação'],
  ['comments', 'Comentários e menções', 'Respostas, comentários e marcações com @'],
  ['publications', 'Publicações', 'Sucesso, falha ou alteração em agendamentos'],
  ['tasks', 'Tarefas', 'Prazos, atribuições e mudanças de status'],
  ['ai', 'IA e automações', 'Sugestões, conclusões e alertas inteligentes'],
  ['invites', 'Convites', 'Novos times, clientes e colaborações'],
  ['system', 'Atualizações do sistema', 'Novidades, manutenção e segurança'],
  ['digest', 'Resumo diário', 'Consolidado da sua operação uma vez ao dia'],
] as const;

type AuxiliarySettings = {
  twoFactor: boolean;
  notificationChannels: { internal: boolean; email: boolean; push: boolean };
  notifications: Record<string, Record<'internal' | 'email' | 'push', boolean>>;
};

const defaultAuxiliarySettings: AuxiliarySettings = {
  twoFactor: true,
  notificationChannels: { internal: true, email: true, push: false },
  notifications: Object.fromEntries(notificationEvents.map(([id]) => [id, { internal: true, email: id !== 'system', push: id === 'approvals' || id === 'tasks' }])),
};

function loadSettings(): PersonalSettings {
  if (typeof window === 'undefined') return defaultSettings;
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) return defaultSettings;
    const parsed = JSON.parse(stored) as Partial<PersonalSettings>;
    return {
      ...defaultSettings,
      ...parsed,
      account: { ...defaultSettings.account, ...parsed.account },
      appearance: { ...defaultSettings.appearance, ...parsed.appearance },
      preferences: { ...defaultSettings.preferences, ...parsed.preferences },
      personalAI: { ...defaultSettings.personalAI, ...parsed.personalAI },
      privacy: { ...defaultSettings.privacy, ...parsed.privacy },
    };
  } catch {
    return defaultSettings;
  }
}

function loadAuxiliarySettings(): AuxiliarySettings {
  if (typeof window === 'undefined') return defaultAuxiliarySettings;
  try {
    const stored = window.localStorage.getItem(`${STORAGE_KEY}:auxiliary`);
    if (!stored) return defaultAuxiliarySettings;
    const parsed = JSON.parse(stored) as Partial<AuxiliarySettings>;
    return {
      ...defaultAuxiliarySettings,
      ...parsed,
      notificationChannels: { ...defaultAuxiliarySettings.notificationChannels, ...parsed.notificationChannels },
      notifications: { ...defaultAuxiliarySettings.notifications, ...parsed.notifications },
    };
  } catch {
    return defaultAuxiliarySettings;
  }
}

const Toggle: React.FC<ToggleProps> = ({ checked, onChange, label }) => (
  <button
    type="button"
    role="switch"
    aria-checked={checked}
    aria-label={label}
    onClick={() => onChange(!checked)}
    className={`relative h-[22px] w-10 shrink-0 rounded-full border transition-colors ${
      checked ? 'border-[#ff5c5c]/60 bg-[#ff5c5c]' : 'border-white/10 bg-[#30393e]'
    }`}
  >
    <span className={`absolute top-[2px] h-4 w-4 rounded-full bg-white transition-transform ${checked ? 'translate-x-[20px]' : 'translate-x-[2px]'}`} />
  </button>
);

const SettingsCard: React.FC<{ title?: string; description?: string; children: React.ReactNode; className?: string }> = ({ title, description, children, className = '' }) => (
  <section className={`border-b border-white/[0.065] py-6 first:pt-0 last:border-b-0 ${className}`}>
    {(title || description) && (
      <div className="mb-5">
        {title && <h3 className="text-[13px] font-semibold text-white">{title}</h3>}
        {description && <p className="mt-1 text-[10px] leading-relaxed text-[#879197]">{description}</p>}
      </div>
    )}
    {children}
  </section>
);

const Field: React.FC<React.InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string }> = ({ label, hint, className = '', ...props }) => (
  <label className="block">
    <span className="mb-1.5 block text-[10px] font-medium text-[#c7cdd0]">{label}</span>
    <input {...props} className={`h-10 w-full rounded-lg border border-white/[0.07] bg-[#11191d] px-3 text-[11px] text-white outline-none transition placeholder:text-[#596268] focus:border-[#ff5c5c]/55 ${className}`} />
    {hint && <span className="mt-1.5 block text-[9px] text-[#737d82]">{hint}</span>}
  </label>
);

const SelectField: React.FC<React.SelectHTMLAttributes<HTMLSelectElement> & { label: string; children: React.ReactNode }> = ({ label, children, ...props }) => (
  <label className="block">
    <span className="mb-1.5 block text-[10px] font-medium text-[#c7cdd0]">{label}</span>
    <select {...props} className="h-10 w-full rounded-lg border border-white/[0.07] bg-[#11191d] px-3 text-[11px] text-white outline-none focus:border-[#ff5c5c]/55">
      {children}
    </select>
  </label>
);

const ToggleRow: React.FC<{ title: string; description: string; checked: boolean; onChange: (value: boolean) => void }> = ({ title, description, checked, onChange }) => (
  <div className="flex items-center justify-between gap-5 border-b border-white/[0.045] py-3.5 last:border-b-0">
    <div>
      <div className="text-[11px] font-medium text-[#e7eaeb]">{title}</div>
      <div className="mt-0.5 text-[9px] text-[#79848a]">{description}</div>
    </div>
    <Toggle label={title} checked={checked} onChange={onChange} />
  </div>
);

export const SettingsView: React.FC = () => {
  const { environmentMode } = useGovernance();
  const isPersonal = environmentMode === 'personal';

  const [activeSection, setActiveSection] = React.useState<SectionId>('account');
  const [query, setQuery] = React.useState('');

  const visibleSections = React.useMemo(() => {
    if (isPersonal) {
      return sections.filter((s) => s.id !== 'company');
    }
    return sections;
  }, [isPersonal]);

  React.useEffect(() => {
    if (isPersonal && activeSection === 'company') {
      setActiveSection('account');
    }
  }, [isPersonal, activeSection]);
  const [settings, setSettings] = React.useState<PersonalSettings>(loadSettings);
  const [initialAuxiliary] = React.useState<AuxiliarySettings>(loadAuxiliarySettings);
  const [dirty, setDirty] = React.useState(false);
  const [saveState, setSaveState] = React.useState<'idle' | 'saving' | 'saved'>('idle');
  const [twoFactor, setTwoFactor] = React.useState(initialAuxiliary.twoFactor);
  const [showRecoveryCodes, setShowRecoveryCodes] = React.useState(false);
  const [sessions, setSessions] = React.useState([
    { id: 'current', device: 'Chrome em Windows', location: 'São Paulo, Brasil', time: 'Agora', current: true },
    { id: 'iphone', device: 'iPhone 16 Pro', location: 'São Paulo, Brasil', time: 'Há 2 horas', current: false },
    { id: 'mac', device: 'Safari em macOS', location: 'Campinas, Brasil', time: 'Ontem, 21:14', current: false },
  ]);
  const [notificationChannels, setNotificationChannels] = React.useState(initialAuxiliary.notificationChannels);
  const [notifications, setNotifications] = React.useState(initialAuxiliary.notifications);
  const [copied, setCopied] = React.useState(false);

  const currentSection = visibleSections.find((section) => section.id === activeSection) || visibleSections[0];
  const filteredSections = visibleSections.filter((section) => `${section.label} ${section.description}`.toLowerCase().includes(query.toLowerCase()));

  const patchSettings = <K extends keyof PersonalSettings>(group: K, values: Partial<PersonalSettings[K]>) => {
    setSettings((current) => ({ ...current, [group]: { ...current[group], ...values } }));
    setDirty(true);
    setSaveState('idle');
  };

  const markAuxiliaryDirty = () => {
    setDirty(true);
    setSaveState('idle');
  };

  const saveSettings = () => {
    setSaveState('saving');
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    window.localStorage.setItem(`${STORAGE_KEY}:auxiliary`, JSON.stringify({ twoFactor, notificationChannels, notifications }));
    window.setTimeout(() => {
      setSaveState('saved');
      setDirty(false);
    }, 450);
  };

  const handleAvatar = (file?: File) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => patchSettings('account', { avatar: String(reader.result) });
    reader.readAsDataURL(file);
  };

  const renderAccount = () => (
    <div className="space-y-4">
      <SettingsCard>
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
          <div className="relative">
            <img src={settings.account.avatar} alt="Pedro Henrique" className="h-20 w-20 rounded-2xl object-cover ring-1 ring-white/10" />
            <label className="absolute -bottom-1 -right-1 grid h-7 w-7 cursor-pointer place-items-center rounded-full border border-white/10 bg-[#273137] text-[#b9c0c4] hover:text-[#ff5c5c]">
              <Camera className="h-3.5 w-3.5" />
              <input type="file" accept="image/*" className="hidden" onChange={(event) => handleAvatar(event.target.files?.[0])} />
            </label>
          </div>
          <div className="flex-1">
            <h3 className="text-[15px] font-semibold text-white">{settings.account.name}</h3>
            <p className="mt-1 text-[10px] text-[#8d979c]">{settings.account.role} · {settings.account.company}</p>
            <p className="mt-2 text-[9px] text-[#667178]">JPG, PNG ou WebP · máximo recomendado de 5 MB</p>
          </div>
          <label className="cursor-pointer rounded-lg border border-white/[0.08] bg-white/[0.035] px-4 py-2 text-[10px] font-medium text-[#d9dddf] hover:border-[#ff5c5c]/30 hover:text-[#ff5c5c]">
            Alterar foto
            <input type="file" accept="image/*" className="hidden" onChange={(event) => handleAvatar(event.target.files?.[0])} />
          </label>
        </div>
      </SettingsCard>
      <SettingsCard title="Informações pessoais" description="Estes dados pertencem somente à sua conta Clicko Studio.">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Nome completo" value={settings.account.name} onChange={(e) => patchSettings('account', { name: e.target.value })} />
          <Field label="Cargo" value={settings.account.role} onChange={(e) => patchSettings('account', { role: e.target.value })} />
          <Field label="Empresa" value={settings.account.company} onChange={(e) => patchSettings('account', { company: e.target.value })} />
          <Field label="E-mail" type="email" value={settings.account.email} onChange={(e) => patchSettings('account', { email: e.target.value })} />
          <Field label="Telefone" value={settings.account.phone} onChange={(e) => patchSettings('account', { phone: e.target.value })} />
          <SelectField label="Idioma" value={settings.account.language} onChange={(e) => patchSettings('account', { language: e.target.value })}>
            <option value="pt-BR">Português (Brasil)</option><option value="en-US">Inglês (EUA)</option><option value="es">Español</option>
          </SelectField>
          <SelectField label="Fuso horário" value={settings.account.timezone} onChange={(e) => patchSettings('account', { timezone: e.target.value })}>
            <option value="America/Sao_Paulo">São Paulo · GMT-3</option><option value="America/New_York">Nova York · GMT-4</option><option value="Europe/Lisbon">Lisboa · GMT+1</option>
          </SelectField>
          <SelectField label="Formato de data" value={settings.account.dateFormat} onChange={(e) => patchSettings('account', { dateFormat: e.target.value })}>
            <option>DD/MM/AAAA</option><option>MM/DD/AAAA</option><option>AAAA-MM-DD</option>
          </SelectField>
        </div>
        <label className="mt-4 block">
          <span className="mb-1.5 block text-[10px] font-medium text-[#c7cdd0]">Assinatura personalizada</span>
          <textarea rows={4} value={settings.account.signature} onChange={(e) => patchSettings('account', { signature: e.target.value })} className="w-full resize-none rounded-lg border border-white/[0.07] bg-[#11191d] p-3 text-[11px] text-white outline-none focus:border-[#ff5c5c]/55" />
        </label>
      </SettingsCard>
    </div>
  );

  const renderSecurity = () => (
    <div className="space-y-4">
      <SettingsCard>
        <div className="flex items-center gap-5">
          <div className="relative grid h-20 w-20 place-items-center rounded-full border-[6px] border-[#ff5c5c]/20 text-xl font-semibold text-white"><span className="absolute inset-[-6px] rounded-full border-[6px] border-[#ff5c5c] border-r-transparent" />82%</div>
          <div className="flex-1"><div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-[#ff5c5c]" /><h3 className="text-[14px] font-semibold text-white">Sua conta está bem protegida</h3></div><p className="mt-1.5 max-w-xl text-[10px] leading-relaxed text-[#879197]">Ative a confirmação biométrica em dispositivos móveis para elevar sua pontuação de segurança.</p></div>
          <span className="rounded-full bg-[#ff5c5c]/10 px-3 py-1.5 text-[9px] font-medium text-[#ff5c5c]">Proteção forte</span>
        </div>
      </SettingsCard>
      <div className="grid gap-4 lg:grid-cols-2">
        <SettingsCard title="Senha" description="Use pelo menos 12 caracteres e não reutilize senhas.">
          <div className="space-y-3"><Field label="Senha atual" type="password" placeholder="••••••••••••" /><Field label="Nova senha" type="password" placeholder="Mínimo de 12 caracteres" /><Field label="Confirmar nova senha" type="password" placeholder="Repita a nova senha" /><button className="rounded-lg bg-[#ff5c5c] px-4 py-2.5 text-[10px] font-semibold text-[#14200e]">Atualizar senha</button></div>
        </SettingsCard>
        <SettingsCard title="Autenticação em dois fatores" description="Adicione uma segunda camada de proteção à sua conta.">
          <ToggleRow title="Autenticação 2FA" description={twoFactor ? 'Ativa via aplicativo autenticador' : 'Proteção adicional desativada'} checked={twoFactor} onChange={(value) => { setTwoFactor(value); markAuxiliaryDirty(); }} />
          <button onClick={() => setShowRecoveryCodes(!showRecoveryCodes)} className="mt-4 flex items-center gap-2 rounded-lg border border-white/[0.08] px-3 py-2 text-[10px] text-[#cbd0d3] hover:text-[#ff5c5c]"><FileKey className="h-3.5 w-3.5" />Gerar chaves de recuperação</button>
          {showRecoveryCodes && <div className="mt-3 grid grid-cols-2 gap-2 rounded-lg bg-[#11191d] p-3 font-mono text-[9px] text-[#9ba4a9]"><span>VX7A-82KP</span><span>Q9LM-34WT</span><span>R2DX-71CN</span><span>P6HV-90JS</span></div>}
        </SettingsCard>
      </div>
      <SettingsCard title="Sessões ativas" description="Dispositivos atualmente conectados à sua conta.">
        <div className="divide-y divide-white/[0.045]">
          {sessions.map((session) => <div key={session.id} className="flex items-center gap-3 py-3.5"><span className="grid h-9 w-9 place-items-center rounded-lg bg-white/[0.04] text-[#aeb6ba]">{session.id === 'iphone' ? <Smartphone className="h-4 w-4" /> : <Laptop className="h-4 w-4" />}</span><div className="flex-1"><div className="flex items-center gap-2 text-[11px] font-medium text-white">{session.device}{session.current && <span className="rounded-full bg-[#ff5c5c]/10 px-2 py-0.5 text-[8px] text-[#ff5c5c]">Esta sessão</span>}</div><div className="mt-1 text-[9px] text-[#778188]">{session.location} · {session.time}</div></div>{!session.current && <button onClick={() => setSessions((items) => items.filter((item) => item.id !== session.id))} className="text-[9px] text-[#9ea6aa] hover:text-red-400">Encerrar</button>}</div>)}
        </div>
        <button onClick={() => setSessions((items) => items.filter((item) => item.current))} className="mt-3 flex items-center gap-2 text-[10px] text-red-400"><LogOut className="h-3.5 w-3.5" />Encerrar todas as outras sessões</button>
      </SettingsCard>
      <SettingsCard title="Histórico de logins">
        {[['Hoje, 16:42', 'Chrome · Windows', 'São Paulo, Brasil'], ['Hoje, 09:18', 'iPhone · iOS', 'São Paulo, Brasil'], ['31 jul., 21:14', 'Safari · macOS', 'Campinas, Brasil']].map(([time, device, location]) => <div key={time} className="grid grid-cols-[120px_1fr_1fr_auto] items-center border-b border-white/[0.04] py-3 text-[9px] last:border-0"><span className="text-[#aab2b6]">{time}</span><span className="text-[#d5d9db]">{device}</span><span className="text-[#818b90]">{location}</span><span className="text-[#ff5c5c]">Sucesso</span></div>)}
      </SettingsCard>
    </div>
  );

  const renderNotifications = () => (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        {([['internal', 'Na plataforma', BellRing], ['email', 'Por e-mail', Mail], ['push', 'Notificações no celular', Smartphone]] as const).map(([id, label, Icon]) => <SettingsCard key={id}><div className="flex items-center justify-between"><span className="grid h-9 w-9 place-items-center rounded-lg bg-[#ff5c5c]/10 text-[#ff5c5c]"><Icon className="h-4 w-4" /></span><Toggle label={label} checked={notificationChannels[id]} onChange={(value) => { setNotificationChannels((current) => ({ ...current, [id]: value })); markAuxiliaryDirty(); }} /></div><div className="mt-4 text-[11px] font-medium text-white">{label}</div><div className="mt-1 text-[9px] text-[#7f898e]">{notificationChannels[id] ? 'Canal ativo' : 'Canal pausado'}</div></SettingsCard>)}
      </div>
      <SettingsCard title="Tipos de notificação" description="Escolha quais eventos devem chegar em cada canal.">
        <div className="overflow-x-auto">
          <div className="min-w-[650px]"><div className="grid grid-cols-[1fr_90px_90px_90px] border-b border-white/[0.055] pb-3 text-center text-[9px] uppercase tracking-wider text-[#707a80]"><span className="text-left">Evento</span><span>Interna</span><span>E-mail</span><span>Celular</span></div>{notificationEvents.map(([id, title, description]) => <div key={id} className="grid grid-cols-[1fr_90px_90px_90px] items-center border-b border-white/[0.04] py-3.5 last:border-0"><div><div className="text-[11px] font-medium text-white">{title}</div><div className="mt-0.5 text-[9px] text-[#778188]">{description}</div></div>{(['internal', 'email', 'push'] as const).map((channel) => <div key={channel} className="flex justify-center"><Toggle label={`${title} por ${channel}`} checked={notifications[id][channel]} onChange={(value) => { setNotifications((current) => ({ ...current, [id]: { ...current[id], [channel]: value } })); markAuxiliaryDirty(); }} /></div>)}</div>)}</div>
        </div>
      </SettingsCard>
    </div>
  );

  const renderPreferences = () => (
    <div className="space-y-7">
      <section className="space-y-4">
        <div className="flex items-center gap-3"><SlidersHorizontal className="h-4 w-4 text-[#ff5c5c]" /><div><h3 className="text-[12px] font-semibold text-white">Experiência e navegação</h3><p className="mt-0.5 text-[9px] text-[#748087]">Defina como a plataforma deve abrir e exibir seus conteúdos.</p></div></div>
        <div className="grid gap-4 lg:grid-cols-2">
          <SettingsCard title="Navegação inicial" description="Defina como a plataforma deve abrir para você.">
            <div className="space-y-4"><SelectField label="Página inicial" value={settings.preferences.homePage} onChange={(e) => patchSettings('preferences', { homePage: e.target.value })}><option value="dashboard">Painel</option><option value="calendar">Calendário</option><option value="content">Conteúdos</option><option value="analytics">Desempenho</option></SelectField><SelectField label="Ambiente automático" value={settings.preferences.autoWorkspace} onChange={(e) => patchSettings('preferences', { autoWorkspace: e.target.value })}><option value="last">Último acessado</option><option value="vitalis">Clínica Vitalis</option><option value="none">Sempre perguntar</option></SelectField><ToggleRow title="Reabrir última página" description="Continue exatamente de onde parou" checked={settings.preferences.openLastPage} onChange={(value) => patchSettings('preferences', { openLastPage: value })} /></div>
          </SettingsCard>
          <SettingsCard title="Visualizações padrão">
            <div className="space-y-4"><SelectField label="Conteúdos" value={settings.preferences.defaultView} onChange={(e) => patchSettings('preferences', { defaultView: e.target.value })}><option value="list">Lista</option><option value="cards">Cartões</option><option value="kanban">Kanban</option></SelectField><SelectField label="Calendário" value={settings.preferences.calendarView} onChange={(e) => patchSettings('preferences', { calendarView: e.target.value })}><option value="week">Semana</option><option value="month">Mês</option></SelectField><SelectField label="Ordenação de conteúdos" value={settings.preferences.contentSort} onChange={(e) => patchSettings('preferences', { contentSort: e.target.value })}><option value="recent">Mais recentes</option><option value="oldest">Mais antigos</option><option value="status">Por status</option><option value="performance">Por desempenho</option></SelectField></div>
          </SettingsCard>
          <SettingsCard title="Persistência e idioma" className="lg:col-span-2">
            <div className="grid gap-5 lg:grid-cols-2"><ToggleRow title="Filtros persistentes" description="Mantenha filtros entre sessões e páginas" checked={settings.preferences.persistentFilters} onChange={(value) => patchSettings('preferences', { persistentFilters: value })} /><SelectField label="Idioma padrão da IA" value={settings.preferences.aiLanguage} onChange={(e) => patchSettings('preferences', { aiLanguage: e.target.value })}><option value="pt-BR">Português (Brasil)</option><option value="en-US">Inglês (EUA)</option><option value="es">Español</option></SelectField></div>
          </SettingsCard>
        </div>
      </section>

      <section className="space-y-4 border-t border-white/[0.055] pt-6">
        <div className="flex items-center gap-3"><Bell className="h-4 w-4 text-[#ff5c5c]" /><div><h3 className="text-[12px] font-semibold text-white">Notificações</h3><p className="mt-0.5 text-[9px] text-[#748087]">Gerencie canais e eventos sem sair de Preferências.</p></div></div>
        {renderNotifications()}
      </section>
    </div>
  );

  const renderPersonalAI = () => (
    <div className="space-y-4">
      <SettingsCard>
        <div className="flex items-center gap-4"><span className="grid h-12 w-12 place-items-center rounded-xl bg-[#ff5c5c]/10 text-[#ff5c5c]"><Bot className="h-6 w-6" /></span><div><h3 className="text-[14px] font-semibold text-white">Seu assistente, do seu jeito</h3><p className="mt-1 text-[10px] text-[#7f898f]">Estas escolhas afetam somente as suas interações com a IA.</p></div></div>
      </SettingsCard>
      <div className="grid gap-4 lg:grid-cols-2">
        <SettingsCard title="Modelo e respostas">
          <div className="space-y-4"><SelectField label="Modelo de IA" value={settings.personalAI.model} onChange={(e) => patchSettings('personalAI', { model: e.target.value })}><option value="clicko-pro">Clicko Pro · Recomendado</option><option value="clicko-fast">Clicko Fast · Mais rápido</option><option value="clicko-reasoning">Clicko Reasoning · Análise profunda</option></SelectField><SelectField label="Profundidade das respostas" value={settings.personalAI.depth} onChange={(e) => patchSettings('personalAI', { depth: e.target.value })}><option value="concise">Concisa</option><option value="balanced">Equilibrada</option><option value="detailed">Detalhada</option></SelectField><SelectField label="Idioma padrão" value={settings.personalAI.language} onChange={(e) => patchSettings('personalAI', { language: e.target.value })}><option value="pt-BR">Português (Brasil)</option><option value="en-US">Inglês (EUA)</option><option value="es">Español</option></SelectField></div>
        </SettingsCard>
        <SettingsCard title="Estilo de criação">
          <SelectField label="Estilo de escrita" value={settings.personalAI.writingStyle} onChange={(e) => patchSettings('personalAI', { writingStyle: e.target.value })}><option value="direct">Direto e estratégico</option><option value="creative">Criativo e expressivo</option><option value="educational">Educacional</option><option value="executive">Executivo</option></SelectField>
          <div className="mt-5"><div className="flex justify-between text-[10px]"><span className="text-[#c7cdd0]">Criatividade</span><span className="text-[#ff5c5c]">{settings.personalAI.creativity}%</span></div><input type="range" min="0" max="100" value={settings.personalAI.creativity} onChange={(e) => patchSettings('personalAI', { creativity: Number(e.target.value) })} className="mt-3 w-full accent-[#ff5c5c]" /></div>
          <div className="mt-5"><div className="flex justify-between text-[10px]"><span className="text-[#c7cdd0]">Formalidade</span><span className="text-[#ff5c5c]">{settings.personalAI.formality}%</span></div><input type="range" min="0" max="100" value={settings.personalAI.formality} onChange={(e) => patchSettings('personalAI', { formality: Number(e.target.value) })} className="mt-3 w-full accent-[#ff5c5c]" /></div>
        </SettingsCard>
      </div>
      <SettingsCard title="Automações de conteúdo">
        <div className="grid gap-x-8 lg:grid-cols-2">{([['autoCta', 'Gerar CTAs automaticamente', 'Inclui chamadas para ação adequadas'], ['improvements', 'Sugerir melhorias', 'Aponta oportunidades antes de finalizar'], ['proofreading', 'Revisar textos', 'Corrige gramática, clareza e consistência'], ['titles', 'Gerar títulos', 'Cria headlines e variações de abertura'], ['hashtags', 'Sugerir hashtags', 'Seleciona termos relevantes por canal'], ['variations', 'Criar variações', 'Gera versões alternativas automaticamente']] as const).map(([key, title, description]) => <ToggleRow key={key} title={title} description={description} checked={settings.personalAI[key]} onChange={(value) => patchSettings('personalAI', { [key]: value })} />)}</div>
      </SettingsCard>
    </div>
  );

  const renderBilling = () => (
    <div className="space-y-4"><SettingsCard><div className="flex flex-wrap items-center gap-5"><span className="grid h-14 w-14 place-items-center rounded-xl bg-[#ff5c5c]/10 text-[#ff5c5c]"><Sparkles className="h-6 w-6" /></span><div className="flex-1"><div className="flex items-center gap-2"><h3 className="text-[16px] font-semibold text-white">Plano Profissional</h3><span className="rounded-full bg-[#ff5c5c]/10 px-2 py-1 text-[8px] text-[#ff5c5c]">Ativo</span></div><p className="mt-1 text-[9px] text-[#788389]">R$ 149/mês · próxima cobrança em 18 de agosto de 2026</p></div><button className="rounded-lg bg-[#ff5c5c] px-4 py-2.5 text-[10px] font-semibold text-[#14200e]">Mudar para plano superior</button></div></SettingsCard><div className="grid gap-4 lg:grid-cols-3">{[['Conteúdos', '320 / 500', 64], ['Armazenamento', '38 GB / 100 GB', 38], ['Requisições IA', '8.240 / 25.000', 33]].map(([label, value, percent]) => <SettingsCard key={String(label)}><div className="text-[10px] text-[#8d979c]">{label}</div><div className="mt-2 text-[16px] font-medium text-white">{value}</div><div className="mt-4 h-1.5 rounded-full bg-[#2b353a]"><div className="h-full rounded-full bg-[#ff5c5c]" style={{ width: `${percent}%` }} /></div></SettingsCard>)}</div><SettingsCard title="Histórico de pagamentos"><div className="divide-y divide-white/[0.045]">{[['01 ago. 2026', 'Plano Profissional', 'R$ 149,00'], ['01 jul. 2026', 'Plano Profissional', 'R$ 149,00'], ['01 jun. 2026', 'Plano Profissional', 'R$ 149,00']].map(([date, item, amount]) => <div key={date} className="grid grid-cols-[120px_1fr_auto_auto] items-center py-3 text-[9px]"><span className="text-[#7d878d]">{date}</span><span className="text-white">{item}</span><span className="mr-5 text-[#b8bec1]">{amount}</span><button className="text-[#ff5c5c]">Recibo</button></div>)}</div></SettingsCard><div className="flex gap-4 text-[9px]"><button className="text-[#899399] hover:text-white">Alterar forma de pagamento</button><button className="text-[#899399] hover:text-white">Mudar para plano inferior</button><button className="text-red-400/70 hover:text-red-400">Cancelar assinatura</button></div></div>
  );

  const renderCompany = () => <div className="space-y-4"><SettingsCard title="Dados da empresa" description="Informações usadas em contas, relatórios e integrações."><div className="grid gap-4 sm:grid-cols-2"><Field label="Razão social" defaultValue="Clicko Studio Tecnologia Ltda." /><Field label="Nome da marca" defaultValue="Clicko Studio" /><Field label="CNPJ" defaultValue="00.000.000/0001-00" /><Field label="Site" defaultValue="https://clickostudio.com" /><Field label="E-mail corporativo" defaultValue="contato@clickostudio.com" /><Field label="Telefone" defaultValue="+55 (11) 99999-0000" /></div></SettingsCard><SettingsCard title="Identidade operacional"><div className="grid gap-4 sm:grid-cols-2"><SelectField label="Idioma da empresa" defaultValue="pt-BR"><option value="pt-BR">Português (Brasil)</option><option value="en-US">Inglês (EUA)</option></SelectField><SelectField label="Fuso horário" defaultValue="America/Sao_Paulo"><option value="America/Sao_Paulo">São Paulo · GMT-3</option><option value="America/New_York">Nova York · GMT-4</option></SelectField></div><p className="mt-4 rounded-lg bg-[#ff5c5c]/[0.06] p-3 text-[9px] leading-relaxed text-[#9ca7ac]">Memória da marca, estratégia, equipe e contas conectadas utilizam estes dados como referência compartilhada.</p></SettingsCard></div>;

  const renderPlatform = () => <div className="space-y-4"><div className="grid gap-4 lg:grid-cols-2"><SettingsCard title="Tema e interface"><div className="space-y-4"><SelectField label="Tema" value={settings.appearance.theme} onChange={(event) => patchSettings('appearance', { theme: event.target.value as PersonalSettings['appearance']['theme'] })}><option value="dark">Escuro</option><option value="light">Claro</option><option value="system">Seguir sistema</option></SelectField><SelectField label="Densidade" value={settings.appearance.layout} onChange={(event) => patchSettings('appearance', { layout: event.target.value as PersonalSettings['appearance']['layout'] })}><option value="comfortable">Confortável</option><option value="compact">Compacta</option></SelectField><ToggleRow title="Animações" description="Transições e microinterações" checked={settings.appearance.animations} onChange={(value) => patchSettings('appearance', { animations: value })} /></div></SettingsCard><SettingsCard title="APIs da plataforma"><div className="space-y-3"><div className="flex items-center justify-between rounded-lg border border-white/[0.06] bg-[#11191d] p-3"><div><span className="block text-[10px] text-white">IA Gemini</span><span className="text-[8px] text-[#748087]">Processamento protegido no servidor</span></div><span className="rounded-full bg-[#ff5c5c]/10 px-2 py-1 text-[8px] text-[#ff5c5c]">Ativa</span></div><div className="flex items-center justify-between rounded-lg border border-white/[0.06] bg-[#11191d] p-3"><div><span className="block text-[10px] text-white">Webhooks</span><span className="text-[8px] text-[#748087]">Eventos para sistemas externos</span></div><button className="text-[8px] text-[#ff5c5c]">Configurar</button></div></div></SettingsCard></div><SettingsCard title="Integrações gerais" description="Serviços compartilhados por todos os módulos."><div className="grid gap-3 sm:grid-cols-3">{[['Armazenamento', 'Conectado'], ['Análises', 'Conectado'], ['E-mail transacional', 'Conectado']].map(([name, status]) => <div key={name} className="flex items-center gap-3 rounded-lg border border-white/[0.06] bg-[#11191d] p-3"><MonitorSmartphone className="h-4 w-4 text-[#ff5c5c]" /><div><span className="block text-[9px] text-white">{name}</span><span className="text-[8px] text-[#ff5c5c]">{status}</span></div></div>)}</div></SettingsCard></div>;

  const renderSupport = () => (
    <div className="space-y-4"><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{[[BookOpen, 'Central de Ajuda', 'Respostas e guias completos'], [PlayCircle, 'Vídeos tutoriais', 'Aprenda com exemplos práticos'], [MessageCircle, 'Chat com suporte', 'Atendimento em tempo real'], [Lightbulb, 'Sugerir recurso', 'Compartilhe uma ideia']].map(([Icon, title, description]) => { const IconComponent = Icon as React.ComponentType<{ className?: string }>; return <button key={String(title)} className="rounded-xl border border-white/[0.065] bg-[#182126] p-4 text-left hover:border-[#ff5c5c]/30"><IconComponent className="h-5 w-5 text-[#ff5c5c]" /><div className="mt-4 text-[11px] font-medium text-white">{String(title)}</div><div className="mt-1 text-[8px] text-[#758087]">{String(description)}</div><ExternalLink className="mt-4 h-3.5 w-3.5 text-[#5f6a70]" /></button>; })}</div><div className="grid gap-4 lg:grid-cols-2"><SettingsCard title="Abrir chamado"><div className="space-y-3"><SelectField label="Assunto" defaultValue="technical"><option value="technical">Problema técnico</option><option value="billing">Cobrança</option><option value="account">Minha conta</option></SelectField><Field label="Título" placeholder="Descreva o problema em uma frase" /><label className="block"><span className="mb-1.5 block text-[10px] font-medium text-[#c7cdd0]">Detalhes</span><textarea rows={4} className="w-full resize-none rounded-lg border border-white/[0.07] bg-[#11191d] p-3 text-[10px] text-white outline-none focus:border-[#ff5c5c]/55" placeholder="Conte o que aconteceu..." /></label><button className="rounded-lg bg-[#ff5c5c] px-4 py-2.5 text-[9px] font-semibold text-[#14200e]">Enviar chamado</button></div></SettingsCard><SettingsCard title="Produto e comunidade"><div className="space-y-2">{[[Bug, 'Reportar um problema', 'Envie detalhes diretamente para a equipe'], [History, 'Histórico de alterações', 'Veja tudo que mudou nas últimas versões'], [Activity, 'Planejamento público', 'Acompanhe o que estamos construindo'], [HelpCircle, 'Documentação', 'Guias técnicos e boas práticas']].map(([Icon, title, description]) => { const IconComponent = Icon as React.ComponentType<{ className?: string }>; return <button key={String(title)} className="flex w-full items-center gap-3 rounded-lg border border-white/[0.055] bg-[#11191d] p-3 text-left"><IconComponent className="h-4 w-4 text-[#ff5c5c]" /><span className="flex-1"><span className="block text-[10px] text-white">{String(title)}</span><span className="text-[8px] text-[#748087]">{String(description)}</span></span><ChevronRight className="h-4 w-4 text-[#59656b]" /></button>; })}</div></SettingsCard></div></div>
  );

  const renderSection = () => {
    switch (activeSection) {
      case 'account': return renderAccount();
      case 'company': return renderCompany();
      case 'platform': return renderPlatform();
      case 'security': return renderSecurity();
      case 'preferences': return renderPreferences();
      case 'personal-ai': return renderPersonalAI();
      case 'billing': return renderBilling();
      case 'support': return renderSupport();
      default: return renderAccount();
    }
  };

  return (
    <div className="clicko-settings-editorial mx-auto w-full min-w-0 max-w-[1580px] overflow-x-hidden p-5 md:p-7">
      <div className="mb-6 flex flex-col gap-4 border-b border-white/[0.055] pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2.5"><span className="grid h-8 w-8 place-items-center rounded-lg bg-[#ff5c5c]/10 text-[#ff5c5c]"><Settings className="h-4 w-4" /></span><h1 className="text-[20px] font-semibold tracking-[-0.02em] text-white">Configurações</h1></div>
          <p className="mt-2 text-[10px] text-[#7f898f]">Perfil, empresa, preferências, segurança, integrações e dados operacionais em uma única central.</p>
        </div>
        <div className="flex items-center gap-3">
          {dirty && <span className="text-[9px] text-[#9da6aa]">Alterações não salvas</span>}
          {saveState === 'saved' && <span className="flex items-center gap-1.5 text-[9px] text-[#ff5c5c]"><CheckCircle2 className="h-3.5 w-3.5" />Tudo salvo</span>}
          <button onClick={saveSettings} disabled={!dirty || saveState === 'saving'} className="flex h-9 items-center gap-2 rounded-lg bg-[#ff5c5c] px-4 text-[10px] font-semibold text-[#14200e] transition hover:bg-[#9be24d] disabled:cursor-not-allowed disabled:opacity-45"><Save className="h-3.5 w-3.5" />{saveState === 'saving' ? 'Salvando...' : 'Salvar alterações'}</button>
        </div>
      </div>

      <div className="grid min-w-0 gap-0 min-[980px]:grid-cols-[214px_minmax(0,1fr)] 2xl:grid-cols-[228px_minmax(0,1fr)]">
        <aside className="min-w-0 self-start overflow-hidden border-b border-white/[0.06] pb-4 min-[980px]:sticky min-[980px]:top-[84px] min-[980px]:border-b-0 min-[980px]:border-r min-[980px]:pb-0 min-[980px]:pr-5">
          <div className="mb-3 flex items-center gap-3 border-b border-white/[0.055] px-2 pb-4">
            <img src={settings.account.avatar} alt="" className="h-9 w-9 rounded-lg object-cover" />
            <div className="min-w-0"><div className="truncate text-[10px] font-medium text-white">{settings.account.name}</div><div className="mt-0.5 truncate text-[8px] text-[#78838a]">Conta pessoal</div></div>
          </div>
          <label className="relative mb-2 block"><Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#657178]" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar configurações" className="h-9 w-full rounded-lg border border-white/[0.055] bg-[#10181c] pl-9 pr-3 text-[9px] text-white outline-none placeholder:text-[#5e696f] focus:border-[#ff5c5c]/40" /></label>
          <nav className="custom-scrollbar max-h-[calc(100vh-260px)] space-y-0.5 overflow-y-auto max-[979px]:flex max-[979px]:max-h-none max-[979px]:gap-1 max-[979px]:space-y-0 max-[979px]:overflow-x-auto">
            {filteredSections.map((section) => { const Icon = section.icon; const selected = activeSection === section.id; return <button key={section.id} onClick={() => setActiveSection(section.id)} className={`group relative flex w-full items-center gap-3 rounded-md px-2.5 py-2.5 text-left transition max-[979px]:min-w-[175px] ${selected ? 'text-white' : 'text-[#879197] hover:bg-white/[0.025] hover:text-white'}`}>{selected && <span className="absolute inset-y-2 left-0 w-px bg-[#ff5c5c]" />}<Icon className={`h-4 w-4 shrink-0 ${selected ? 'text-[#ff5c5c]' : 'text-[#68747b] group-hover:text-[#aeb6ba]'}`} /><span className="min-w-0 flex-1"><span className="block truncate text-[9px] font-medium">{section.label}</span><span className="mt-0.5 block truncate text-[7px] text-[#566269]">{section.description}</span></span>{selected && <ChevronRight className="h-3.5 w-3.5 text-[#ff5c5c]" />}</button>; })}
          </nav>
        </aside>

        <main className="min-w-0 pt-6 min-[980px]:pl-7 min-[980px]:pt-0">
          <div className="mb-4 flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl border border-white/[0.06] bg-[#182126] text-[#ff5c5c]"><currentSection.icon className="h-[18px] w-[18px]" /></span>
            <div><h2 className="text-[16px] font-semibold text-white">{currentSection.label}</h2><p className="mt-0.5 text-[9px] text-[#78838a]">{currentSection.description}</p></div>
          </div>
          {renderSection()}
        </main>
      </div>
    </div>
  );
};
