import React from 'react';
import { usePresence } from '../motion/usePresence';
import { createPortal } from 'react-dom';
import { X, ArrowLeft, LogIn, PlusCircle, Building2, User, KeyRound, Sparkles } from 'lucide-react';
import { useGovernance } from '../context/GovernanceContext';
import { ClickoLoader } from './ClickoLoader';

interface AddAccountModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type ModalStep = 'choose' | 'login' | 'create-type' | 'create-form';

export const AddAccountModal: React.FC<AddAccountModalProps> = ({ isOpen, onClose }) => {
  const { addAccount } = useGovernance();
  const presence = usePresence(isOpen);

  const [step, setStep] = React.useState<ModalStep>('choose');
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState('');

  // Login form state
  const [loginEmail, setLoginEmail] = React.useState('');
  const [loginPassword, setLoginPassword] = React.useState('');
  const [loginType, setLoginType] = React.useState<'personal' | 'company'>('company');
  const [loginAccountName, setLoginAccountName] = React.useState('');

  // Create account form state
  const [createType, setCreateType] = React.useState<'personal' | 'company'>('company');
  const [createName, setCreateName] = React.useState('');
  const [createEmail, setCreateEmail] = React.useState('');
  const [selectedPlan, setSelectedPlan] = React.useState('Plano Team');

  React.useEffect(() => {
    if (isOpen) {
      setStep('choose');
      setLoading(false);
      setError('');
      setLoginEmail('');
      setLoginPassword('');
      setLoginType('company');
      setLoginAccountName('');
      setCreateType('company');
      setCreateName('');
      setCreateEmail('');
      setSelectedPlan('Plano Team');
    }
  }, [isOpen]);

  React.useEffect(() => {
    if (!isOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen]);

  if (!presence.present) return null;

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginEmail || !loginPassword) return;
    setError('O login de contas existentes exige um provedor de autenticação configurado. Nenhuma conta foi vinculada nem nenhuma credencial foi armazenada.');
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createName.trim()) return;

    setLoading(true);
    const created = await addAccount({
        name: createName.trim(),
        type: createType,
        email: createEmail.trim() || undefined,
        planName: selectedPlan,
        role: createType === 'company' ? 'Master / Admin' : 'Solo Creator',
        membersCount: createType === 'company' ? 1 : undefined,
      });
    setLoading(false);
    if (created) onClose();
    else setError('Não foi possível criar o ambiente isolado. Verifique o servidor e tente novamente.');
  };

  return createPortal(
    <div
      {...presence.props}
      className="fixed inset-0 z-[100] overflow-y-auto overscroll-contain bg-black/70 backdrop-blur-xl animate-in fade-in duration-150"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="flex min-h-full items-center justify-center p-4 sm:p-6">
      <div role="dialog" aria-modal="true" aria-labelledby="add-account-title" className="relative flex max-h-[calc(100dvh-2rem)] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-white/10 bg-[rgba(10,10,10,0.96)] shadow-[0_28px_90px_rgba(0,0,0,0.72)] sm:max-h-[calc(100dvh-3rem)]">
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-white/[0.08] bg-[rgba(10,10,10,0.94)] px-5 py-4 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            {step !== 'choose' && (
              <button
                type="button"
                onClick={() => {
                  if (step === 'create-form') setStep('create-type');
                  else setStep('choose');
                }}
                className="grid h-8 w-8 place-items-center rounded-lg border border-white/10 bg-white/[0.04] text-[rgba(255,255,255,0.72)] transition hover:bg-white/10 hover:text-white"
                title="Voltar"
              >
                <ArrowLeft className="h-4 w-4" />
              </button>
            )}
            <div>
              <h2 id="add-account-title" className="text-base font-bold text-white">Adicionar Conta</h2>
              <p className="text-[11px] text-[#808080]">
                {step === 'choose' && 'Vincule uma conta existente ou assine um novo ambiente.'}
                {step === 'login' && 'Informe as credenciais da conta que deseja conectar.'}
                {step === 'create-type' && 'Selecione a modalidade da nova conta.'}
                {step === 'create-form' && 'Defina o nome do ambiente e escolha o plano.'}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="grid h-8 w-8 place-items-center rounded-lg border border-white/10 bg-white/[0.04] text-[rgba(255,255,255,0.72)] transition hover:bg-white/10 hover:text-white"
            aria-label="Fechar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="min-h-0 overflow-y-auto px-5 pb-5 pt-5 [scrollbar-color:rgba(128,128,128,0.45)_transparent] [scrollbar-width:thin]">

        {error && <div role="alert" className="mb-4 rounded-lg border border-[#F28500]/20 bg-[#F28500]/[0.06] p-3 text-[10px] leading-relaxed text-[#F28500]">{error}</div>}

        {/* STEP 1: Choose Option */}
        {step === 'choose' && (
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => setStep('login')}
              className="group flex w-full items-start gap-4 rounded-xl border border-white/[0.08] bg-[rgba(128,128,128,0.14)] p-4 text-left transition-all hover:border-[#FF7F50]/40 hover:bg-[#000000]"
            >
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-white/10 bg-white/[0.04] text-[#FF7F50] group-hover:bg-[#FF7F50]/10 transition-colors">
                <LogIn className="h-5 w-5" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-xs font-bold text-white group-hover:text-[#FF7F50] transition-colors">
                  Entrar em uma conta existente
                </h3>
                <p className="mt-1 text-[11px] text-[#808080] leading-relaxed">
                  Fazer login em outra conta já criada para alternar rapidamente pelo seletor.
                </p>
              </div>
            </button>

            <button
              type="button"
              onClick={() => setStep('create-type')}
              className="group flex w-full items-start gap-4 rounded-xl border border-white/[0.08] bg-[rgba(128,128,128,0.14)] p-4 text-left transition-all hover:border-[#FF7F50]/40 hover:bg-[#000000]"
            >
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-white/10 bg-white/[0.04] text-[#FF7F50] group-hover:bg-[#FF7F50]/10 transition-colors">
                <PlusCircle className="h-5 w-5" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-xs font-bold text-white group-hover:text-[#FF7F50] transition-colors">
                  Criar / Assinar uma nova conta
                </h3>
                <p className="mt-1 text-[11px] text-[#808080] leading-relaxed">
                  Criar uma nova Conta Pessoal ou Workspace Corporativo com plano dedicado.
                </p>
              </div>
            </button>
          </div>
        )}

        {/* STEP 2A: Login into existing account */}
        {step === 'login' && (
          <form onSubmit={handleLoginSubmit} className="space-y-4">
            <div>
              <label className="block text-[11px] font-semibold text-[rgba(255,255,255,0.72)] mb-1.5">Tipo de Conta</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setLoginType('company')}
                  className={`flex items-center justify-center gap-2 rounded-xl border p-2.5 text-xs font-bold transition-all ${
                    loginType === 'company'
                      ? 'border-[#FF7F50]/50 bg-[#FF7F50]/10 text-white'
                      : 'border-white/[0.08] bg-[rgba(128,128,128,0.14)] text-[#808080] hover:text-white'
                  }`}
                >
                  <Building2 className="h-4 w-4 text-[#FF7F50]" />
                  <span>Workspace</span>
                </button>
                <button
                  type="button"
                  onClick={() => setLoginType('personal')}
                  className={`flex items-center justify-center gap-2 rounded-xl border p-2.5 text-xs font-bold transition-all ${
                    loginType === 'personal'
                      ? 'border-[#FF7F50]/50 bg-[#FF7F50]/10 text-white'
                      : 'border-white/[0.08] bg-[rgba(128,128,128,0.14)] text-[#808080] hover:text-white'
                  }`}
                >
                  <User className="h-4 w-4 text-[#FF7F50]" />
                  <span>Pessoal</span>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-[rgba(255,255,255,0.72)] mb-1">E-mail de acesso</label>
              <input
                type="email"
                required
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                placeholder="seu.email@empresa.com"
                className="w-full rounded-xl border border-white/10 bg-[rgba(128,128,128,0.14)] px-3.5 py-2.5 text-xs text-white placeholder-[#808080] outline-none focus:border-[#FF7F50]"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-[rgba(255,255,255,0.72)] mb-1">Senha de acesso</label>
              <input
                type="password"
                required
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-xl border border-white/10 bg-[rgba(128,128,128,0.14)] px-3.5 py-2.5 text-xs text-white placeholder-[#808080] outline-none focus:border-[#FF7F50]"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-[rgba(255,255,255,0.72)] mb-1">Nome do Workspace / Conta (opcional)</label>
              <input
                type="text"
                value={loginAccountName}
                onChange={(e) => setLoginAccountName(e.target.value)}
                placeholder={loginType === 'company' ? 'Ex: Agência Digital' : 'Ex: Nome Pessoal'}
                className="w-full rounded-xl border border-white/10 bg-[rgba(128,128,128,0.14)] px-3.5 py-2.5 text-xs text-white placeholder-[#808080] outline-none focus:border-[#FF7F50]"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-[#FF7F50] py-3 text-xs font-bold text-[#000000] transition hover:bg-[#FF7F50] disabled:opacity-50"
            >
              {loading ? (
                <ClickoLoader size="small" tone="light" label="Autenticando conta" />
              ) : (
                <>
                  <KeyRound className="h-4 w-4" />
                  <span>Autenticar e Vincular Conta</span>
                </>
              )}
            </button>
          </form>
        )}

        {/* STEP 2B-1: Select Account Type */}
        {step === 'create-type' && (
          <div className="space-y-4">
            <span className="block text-xs font-semibold text-[rgba(255,255,255,0.72)]">Selecione o tipo de ambiente para a nova conta:</span>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => {
                  setCreateType('personal');
                  setSelectedPlan('Plano Solo');
                  setStep('create-form');
                }}
                className="group flex flex-col items-center justify-center rounded-xl border border-white/[0.08] bg-[rgba(128,128,128,0.14)] p-4 text-center transition-colors hover:border-[#FF7F50]/50 hover:bg-[#FF7F50]/5"
              >
                <div className="grid h-12 w-12 place-items-center rounded-xl border border-[#FF7F50]/30 bg-[#FF7F50]/10 text-[#FF7F50] mb-3">
                  <User className="h-6 w-6" />
                </div>
                <h3 className="text-xs font-bold text-white group-hover:text-[#FF7F50]">Conta Pessoal</h3>
                <p className="mt-1 text-[10px] text-[#808080] leading-tight">
                  Para criadores solo, marcas pessoais e projetos individuais.
                </p>
              </button>

              <button
                type="button"
                onClick={() => {
                  setCreateType('company');
                  setSelectedPlan('Plano Team');
                  setStep('create-form');
                }}
                className="group flex flex-col items-center justify-center rounded-xl border border-white/[0.08] bg-[rgba(128,128,128,0.14)] p-4 text-center transition-colors hover:border-[#FF7F50]/50 hover:bg-[#FF7F50]/5"
              >
                <div className="grid h-12 w-12 place-items-center rounded-xl border border-[#FF7F50]/30 bg-[#FF7F50]/10 text-[#FF7F50] mb-3">
                  <Building2 className="h-6 w-6" />
                </div>
                <h3 className="text-xs font-bold text-white group-hover:text-[#FF7F50]">Workspace</h3>
                <p className="mt-1 text-[10px] text-[#808080] leading-tight">
                  Para empresas, equipes, agências e gestão colaborativa.
                </p>
              </button>
            </div>
          </div>
        )}

        {/* STEP 2B-2: Create Account Form & Plan Selection */}
        {step === 'create-form' && (
          <form onSubmit={handleCreateSubmit} className="space-y-4">
            <div>
              <label className="block text-[11px] font-semibold text-[rgba(255,255,255,0.72)] mb-1">
                Nome da {createType === 'company' ? 'Empresa / Workspace' : 'Conta Pessoal'}
              </label>
              <input
                type="text"
                required
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                placeholder={createType === 'company' ? 'Ex: TechLab Inovação' : 'Ex: Pedro Henrique Solo'}
                className="w-full rounded-xl border border-white/10 bg-[rgba(128,128,128,0.14)] px-3.5 py-2.5 text-xs text-white placeholder-[#808080] outline-none focus:border-[#FF7F50]"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-[rgba(255,255,255,0.72)] mb-1">E-mail administrativo</label>
              <input
                type="email"
                value={createEmail}
                onChange={(e) => setCreateEmail(e.target.value)}
                placeholder="contato@empresa.com"
                className="w-full rounded-xl border border-white/10 bg-[rgba(128,128,128,0.14)] px-3.5 py-2.5 text-xs text-white placeholder-[#808080] outline-none focus:border-[#FF7F50]"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-[rgba(255,255,255,0.72)] mb-1.5">Escolha o Plano da Nova Conta</label>
              <div className="space-y-2">
                {createType === 'personal' ? (
                  <>
                    {[
                      { id: 'Plano Solo', price: 'R$ 49/mês', desc: '1 usuário · KLIC e posts ilimitados' },
                      { id: 'Plano Pro Creator', price: 'R$ 99/mês', desc: '1 usuário · Créditos estendidos + Studio HD' },
                    ].map((plan) => (
                      <button
                        key={plan.id}
                        type="button"
                        onClick={() => setSelectedPlan(plan.id)}
                        className={`flex w-full items-center justify-between rounded-xl border p-3 text-left transition-all ${
                          selectedPlan === plan.id
                            ? 'border-[#FF7F50] bg-[#FF7F50]/10 text-white'
                            : 'border-white/[0.08] bg-[rgba(128,128,128,0.14)] text-[#808080] hover:border-white/20'
                        }`}
                      >
                        <div>
                          <span className="text-xs font-bold text-white block">{plan.id}</span>
                          <span className="text-[10px] text-[#808080]">{plan.desc}</span>
                        </div>
                        <span className="text-xs font-bold text-[#FF7F50]">{plan.price}</span>
                      </button>
                    ))}
                  </>
                ) : (
                  <>
                    {[
                      { id: 'Plano Team', price: 'R$ 149/mês', desc: 'Até 5 membros · Fila de aprovação & Governança' },
                      { id: 'Plano Business', price: 'R$ 299/mês', desc: 'Até 15 membros · Automações avançadas' },
                      { id: 'Plano Enterprise', price: 'R$ 599/mês', desc: 'Membros ilimitados · Suporte VIP & SLA' },
                    ].map((plan) => (
                      <button
                        key={plan.id}
                        type="button"
                        onClick={() => setSelectedPlan(plan.id)}
                        className={`flex w-full items-center justify-between rounded-xl border p-3 text-left transition-all ${
                          selectedPlan === plan.id
                            ? 'border-[#FF7F50] bg-[#FF7F50]/10 text-white'
                            : 'border-white/[0.08] bg-[rgba(128,128,128,0.14)] text-[#808080] hover:border-white/20'
                        }`}
                      >
                        <div>
                          <span className="text-xs font-bold text-white block">{plan.id}</span>
                          <span className="text-[10px] text-[#808080]">{plan.desc}</span>
                        </div>
                        <span className="text-xs font-bold text-[#FF7F50]">{plan.price}</span>
                      </button>
                    ))}
                  </>
                )}
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-[#FF7F50] py-3 text-xs font-bold text-[#000000] transition hover:bg-[#FF7F50] disabled:opacity-50"
            >
              {loading ? (
                <ClickoLoader size="small" tone="light" label="Criando conta" />
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  <span>Criar e Iniciar Conta</span>
                </>
              )}
            </button>
          </form>
        )}
        </div>
      </div>
      </div>
    </div>,
    document.body,
  );
};
