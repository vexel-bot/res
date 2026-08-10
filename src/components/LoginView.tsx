import React from 'react';
import { ArrowRight, Eye, EyeOff, LockKeyhole, Mail } from 'lucide-react';
import { ClickoLoader, ClickoLogo } from './ClickoLogo';

export const LoginView: React.FC = () => {
  const [showPassword, setShowPassword] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    window.setTimeout(() => {
      window.location.href = '/';
    }, 700);
  };

  return (
    <main data-theme="dark" className="relative grid min-h-screen place-items-center overflow-hidden bg-black px-5 py-10 text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_30%,rgba(184,184,184,0.07),transparent_42%)]" />
      <section className="clicko-login-enter relative w-full max-w-[390px]">
        <div className="mb-9 flex justify-center">
          <a href="/" aria-label="Ir para o Painel" title="Ir para o Painel" className="rounded-sm focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white">
            <ClickoLogo appearance="seamless" className="h-[150px] w-[300px] max-w-[78vw]" />
          </a>
        </div>
        <div className="rounded-xl border border-white/[0.08] bg-[#111111] p-6">
          <div className="mb-7 text-center">
            <h1 className="text-[20px] font-semibold tracking-[-0.02em]">Acesse o Clicko Studio</h1>
            <p className="mt-2 text-[11px] text-[#7C7C7C]">Entre para continuar criando com inteligência.</p>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            <label className="block">
              <span className="mb-1.5 block text-[10px] font-medium text-[#B8B8B8]">E-mail</span>
              <span className="flex h-11 items-center gap-2.5 rounded-lg border border-white/[0.09] bg-[#0B0B0B] px-3 focus-within:border-[#B8B8B8]/60">
                <Mail className="h-4 w-4 text-[#7C7C7C]" />
                <input required type="email" defaultValue="pedro@clickostudio.com" className="min-w-0 flex-1 bg-transparent text-[11px] text-white outline-none" />
              </span>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-[10px] font-medium text-[#B8B8B8]">Senha</span>
              <span className="flex h-11 items-center gap-2.5 rounded-lg border border-white/[0.09] bg-[#0B0B0B] px-3 focus-within:border-[#B8B8B8]/60">
                <LockKeyhole className="h-4 w-4 text-[#7C7C7C]" />
                <input required type={showPassword ? 'text' : 'password'} defaultValue="clickostudio" className="min-w-0 flex-1 bg-transparent text-[11px] text-white outline-none" />
                <button type="button" onClick={() => setShowPassword((value) => !value)} className="text-[#7C7C7C] hover:text-white" aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}>
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </span>
            </label>
            <div className="flex items-center justify-between text-[9px]">
              <label className="flex items-center gap-2 text-[#7C7C7C]"><input type="checkbox" defaultChecked className="accent-white" />Lembrar de mim</label>
              <button type="button" className="text-[#B8B8B8] hover:text-white">Esqueci minha senha</button>
            </div>
            <button disabled={submitting} className="mt-2 flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-white text-[10px] font-semibold text-[#0B0B0B] transition-transform hover:scale-[1.01] disabled:opacity-70">
              {submitting ? <><ClickoLoader className="h-5 w-10" />Entrando...</> : <>Entrar no Estúdio<ArrowRight className="h-4 w-4" /></>}
            </button>
          </form>
          <div className="mt-6 border-t border-white/[0.06] pt-5 text-center text-[9px] text-[#7C7C7C]">Ainda não tem acesso? <button className="text-[#B8B8B8] hover:text-white">Solicitar convite</button></div>
        </div>
        <p className="mt-5 text-center text-[8px] uppercase tracking-[0.24em] text-[#3A3A3A]">Clicko Studio · criação em movimento</p>
      </section>
    </main>
  );
};
