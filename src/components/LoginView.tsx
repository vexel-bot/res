import React from 'react';
import { ArrowLeft, ArrowRight, Eye, EyeOff, KeyRound, LockKeyhole, Mail, UserRound } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import {
  isValidEmail,
  isValidPassword,
  normalizeEmail,
  normalizeFullName,
  validateLogin,
  validateSignup,
  type LoginFieldErrors,
  type SignupFieldErrors,
} from '../security/authValidation';
import { ClickoLogo } from './ClickoLogo';
import { ClickoLoader } from './ClickoLoader';
import { AuthAtmosphere } from './AuthAtmosphere';

type Mode = 'login' | 'signup' | 'forgot' | 'reset' | 'verify' | 'check-email';
type FeedbackState = { tone: 'error' | 'success' | 'neutral'; text: string };
type LoginFields = { email: string; password: string; remember: boolean };
type SignupFields = { name: string; email: string; password: string; confirmation: string; terms: boolean };
type SpecialFieldErrors = Partial<Record<'email' | 'password' | 'confirmation', string>>;
const initialMode = (): Mode => ({ '/signup': 'signup', '/forgot-password': 'forgot', '/reset-password': 'reset', '/verify-email': 'verify' }[window.location.pathname.replace(/\/+$/, '')] as Mode || 'login');
const titles = {
  forgot: ['Recuperação de acesso', 'Redefina sua senha', 'Informe o e-mail cadastrado para receber as instruções.'],
  reset: ['Novo acesso', 'Crie uma nova senha', 'Escolha uma senha segura e diferente da anterior.'],
  verify: ['Confirmação de identidade', 'Verifique seu e-mail', 'Confirme o endereço para ativar seu acesso à Clicko.'],
  'check-email': ['Cadastro concluído', 'Confira seu e-mail', 'Use o link de confirmação para fazer sua primeira entrada.'],
} satisfies Record<Exclude<Mode, 'login' | 'signup'>, [string, string, string]>;

export const LoginView: React.FC = () => {
  const auth = useAuth();
  const [mode, setModeState] = React.useState<Mode>(initialMode);
  const [login, setLogin] = React.useState<LoginFields>({ email: '', password: '', remember: true });
  const [signup, setSignup] = React.useState<SignupFields>({ name: '', email: '', password: '', confirmation: '', terms: false });
  const [showLoginPassword, setShowLoginPassword] = React.useState(false);
  const [showSignupPassword, setShowSignupPassword] = React.useState(false);
  const [submitting, setSubmitting] = React.useState<'login' | 'signup' | 'special'>();
  const [loginMessage, setLoginMessage] = React.useState<FeedbackState>();
  const [signupMessage, setSignupMessage] = React.useState<FeedbackState>();
  const [loginErrors, setLoginErrors] = React.useState<LoginFieldErrors>({});
  const [signupErrors, setSignupErrors] = React.useState<SignupFieldErrors>({});
  const [specialErrors, setSpecialErrors] = React.useState<SpecialFieldErrors>({});
  const [specialMessage, setSpecialMessage] = React.useState<FeedbackState>();
  const [actionToken, setActionToken] = React.useState(() => new URLSearchParams(window.location.search).get('token') || '');
  const submissionLock = React.useRef(false);
  const isInitial = mode === 'login' || mode === 'signup';
  const setMode = (next: Mode) => {
    if (next === mode) return;
    const routes: Record<Mode, string> = { login: '/login', signup: '/signup', forgot: '/forgot-password', reset: '/reset-password', verify: '/verify-email', 'check-email': '/login' };
    const invitation = new URLSearchParams(window.location.hash.replace(/^#/, ''));
    const inviteHash = invitation.get('clientInvite') && invitation.get('token') && (next === 'login' || next === 'signup') ? `#${invitation.toString()}` : '';
    window.history.replaceState({}, '', `${routes[next]}${inviteHash}`);
    setModeState(next); setLoginMessage(undefined); setSignupMessage(undefined); setLoginErrors({}); setSignupErrors({}); setSpecialErrors({}); setSpecialMessage(undefined);
  };
  const enterPlatform = () => { window.history.replaceState({}, '', '/dashboard'); window.dispatchEvent(new PopStateEvent('popstate')); };
  const updateLogin = <K extends keyof LoginFields>(field: K, value: LoginFields[K]) => {
    setLogin(current => {
      const next = { ...current, [field]: value };
      const errors = validateLogin(next);
      if (field === 'email' && loginErrors.email) setLoginErrors(currentErrors => ({ ...currentErrors, email: errors.email }));
      if (field === 'password' && loginErrors.password) setLoginErrors(currentErrors => ({ ...currentErrors, password: errors.password }));
      return next;
    });
  };
  const updateSignup = <K extends keyof SignupFields>(field: K, value: SignupFields[K]) => {
    setSignup(current => {
      const next = { ...current, [field]: value };
      const errors = validateSignup({ ...next, termsAccepted: next.terms, privacyAccepted: next.terms });
      if (field === 'name' && signupErrors.name) setSignupErrors(currentErrors => ({ ...currentErrors, name: errors.name }));
      if (field === 'email' && signupErrors.email) setSignupErrors(currentErrors => ({ ...currentErrors, email: errors.email }));
      if (field === 'password') {
        if (signupErrors.password) setSignupErrors(currentErrors => ({ ...currentErrors, password: errors.password }));
        if (signupErrors.confirmation) setSignupErrors(currentErrors => ({ ...currentErrors, confirmation: errors.confirmation }));
      }
      if (field === 'confirmation' && signupErrors.confirmation) setSignupErrors(currentErrors => ({ ...currentErrors, confirmation: errors.confirmation }));
      if (field === 'terms' && signupErrors.terms) setSignupErrors(currentErrors => ({ ...currentErrors, terms: errors.terms }));
      return next;
    });
  };
  const submitLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    if (submissionLock.current) return;
    setLoginMessage(undefined);
    const normalized = { ...login, email: normalizeEmail(login.email) };
    const validation = validateLogin(normalized);
    setLogin(normalized); setLoginErrors(validation);
    if (Object.keys(validation).length) return;
    submissionLock.current = true;
    setSubmitting('login');
    try { await auth.login(normalized.email, normalized.password, normalized.remember); enterPlatform(); }
    catch (error) {
      const status = (error as Error & { status?: number }).status;
      setLoginMessage({ tone: 'error', text: status === 400 || status === 401 ? 'E-mail ou senha incorretos.' : error instanceof Error ? error.message : 'Não foi possível entrar. Tente novamente.' });
    }
    finally { submissionLock.current = false; setSubmitting(undefined); }
  };
  const submitSignup = async (event: React.FormEvent) => {
    event.preventDefault();
    if (submissionLock.current) return;
    setSignupMessage(undefined);
    const normalized = { ...signup, name: normalizeFullName(signup.name), email: normalizeEmail(signup.email) };
    const validation = validateSignup({ ...normalized, termsAccepted: normalized.terms, privacyAccepted: normalized.terms });
    setSignup(normalized); setSignupErrors(validation);
    if (Object.keys(validation).length) return;
    submissionLock.current = true;
    setSubmitting('signup');
    try {
      const response = await auth.signup(normalized.name, normalized.email, normalized.password, normalized.confirmation, normalized.terms, normalized.terms, true);
      if (response.verificationRequired) {
        if (response.developmentToken) setActionToken(response.developmentToken);
        setModeState('check-email');
        setSpecialMessage({ tone: 'success', text: response.deliveryConfigured ? 'Enviamos o link de confirmação para seu e-mail.' : 'Conta criada. A entrega de e-mail precisa ser configurada pelo administrador.' });
      } else enterPlatform();
    } catch (error) {
      const details = (error as Error & { details?: { fieldErrors?: SignupFieldErrors } }).details;
      if (details?.fieldErrors) setSignupErrors(details.fieldErrors);
      setSignupMessage({ tone: 'error', text: error instanceof Error ? error.message : 'Não foi possível criar sua conta. Tente novamente.' });
    }
    finally { submissionLock.current = false; setSubmitting(undefined); }
  };
  const submitSpecial = async (event: React.FormEvent) => {
    event.preventDefault();
    if (submissionLock.current) return;
    setSpecialMessage(undefined); setSpecialErrors({});
    if (mode === 'forgot' && !isValidEmail(login.email)) return setSpecialErrors({ email: 'Digite um e-mail válido.' });
    if (mode === 'reset' && !isValidPassword(signup.password)) return setSpecialErrors({ password: 'Use ao menos 8 caracteres, com maiúscula, minúscula e número.' });
    if (mode === 'reset' && signup.password !== signup.confirmation) return setSpecialErrors({ confirmation: 'As senhas não coincidem.' });
    if ((mode === 'reset' || mode === 'verify') && !actionToken) return setSpecialMessage({ tone: 'error', text: 'O link está incompleto. Solicite um novo e-mail.' });
    submissionLock.current = true; setSubmitting('special');
    try {
      if (mode === 'forgot') { const response = await auth.forgotPassword(login.email.trim()); if (response.developmentToken) { setActionToken(response.developmentToken); setModeState('reset'); } setSpecialMessage({ tone: 'success', text: response.message }); }
      if (mode === 'reset') { await auth.resetPassword(actionToken, signup.password); enterPlatform(); }
      if (mode === 'verify') { await auth.verifyEmail(actionToken); enterPlatform(); }
    } catch (error) { setSpecialMessage({ tone: 'error', text: error instanceof Error ? error.message : 'Não foi possível concluir. Tente novamente.' }); }
    finally { submissionLock.current = false; setSubmitting(undefined); }
  };

  return <main data-theme="dark" className="clicko-auth-scene relative min-h-[100svh] overflow-x-hidden bg-black text-white">
    <AuthAtmosphere mode={mode} />
    <div className="clicko-auth-layout relative mx-auto flex min-h-[100svh] max-w-[500px] flex-col justify-center px-5 py-7">
      <div className="clicko-auth-brand-independent flex w-full justify-center"><ClickoLogo authentication appearance="seamless" className="clicko-auth-logo" /></div>
      <section className="clicko-login-enter clicko-auth-panel w-full">
        {isInitial ? <>
          <div className="clicko-auth-card clicko-auth-single relative overflow-hidden rounded-2xl border border-white/[0.07] bg-[rgba(10,10,10,0.74)] p-5 shadow-2xl shadow-black/50 backdrop-blur-xl sm:p-8">
            <header className="mb-5"><h1 className="text-[24px] font-semibold tracking-[-0.04em]">{mode === 'login' ? 'Acesse sua conta' : 'Crie sua conta'}</h1><p className="mt-1.5 text-[10px] leading-5 text-[#808080]">{mode === 'login' ? 'Continue sua operação na Clicko.' : 'Comece com o essencial.'}</p></header>
            <div className="clicko-auth-tabs mb-6 flex gap-7 border-b border-white/[0.07]" role="tablist" aria-label="Forma de acesso"><button id="auth-tab-login" type="button" role="tab" aria-controls="auth-form-panel" tabIndex={mode === 'login' ? 0 : -1} aria-selected={mode === 'login'} onClick={() => setMode('login')} className={mode === 'login' ? 'is-active' : ''}>Entrar</button><button id="auth-tab-signup" type="button" role="tab" aria-controls="auth-form-panel" tabIndex={mode === 'signup' ? 0 : -1} aria-selected={mode === 'signup'} onClick={() => setMode('signup')} className={mode === 'signup' ? 'is-active' : ''}>Criar conta</button></div>
            <AuthFormHeight mode={mode}>
            <div key={mode} id="auth-form-panel" role="tabpanel" aria-labelledby={`auth-tab-${mode}`} className="clicko-auth-state">
              {mode === 'login' ? <form onSubmit={submitLogin} noValidate className="space-y-4">
                <Field id="login-email" label="E-mail" icon={<Mail />} error={loginErrors.email}><input required value={login.email} onChange={event => updateLogin('email', event.target.value)} onBlur={() => { const email = normalizeEmail(login.email); setLogin(current => ({ ...current, email })); setLoginErrors(current => ({ ...current, email: validateLogin({ ...login, email }).email })); }} autoComplete="email" inputMode="email" maxLength={254} placeholder="voce@empresa.com" /></Field>
                <Field id="login-password" label="Senha" icon={<LockKeyhole />} error={loginErrors.password} action={<PasswordButton visible={showLoginPassword} onClick={() => setShowLoginPassword(value => !value)} />}><input required value={login.password} onChange={event => updateLogin('password', event.target.value)} onBlur={() => setLoginErrors(current => ({ ...current, password: validateLogin(login).password }))} type={showLoginPassword ? 'text' : 'password'} autoComplete="current-password" maxLength={128} placeholder="Sua senha" /></Field>
                <div className="flex items-center justify-between gap-4 text-[10px]"><label className="flex cursor-pointer items-center gap-2 text-[#808080]"><input type="checkbox" checked={login.remember} onChange={event => updateLogin('remember', event.target.checked)} className="h-3.5 w-3.5 accent-[#FF7F50]" />Lembrar de mim</label><button type="button" onClick={() => setMode('forgot')} className="text-[rgba(255,255,255,0.72)] transition hover:text-white">Esqueci minha senha</button></div>
                {loginMessage && <Feedback {...loginMessage} />}<SubmitButton loading={submitting === 'login'} label="Entrar" />
              </form>
              : <form onSubmit={submitSignup} noValidate className="space-y-3.5">
                <Field id="signup-name" label="Nome completo" icon={<UserRound />} error={signupErrors.name}><input required value={signup.name} onChange={event => updateSignup('name', event.target.value)} onBlur={() => { const name = normalizeFullName(signup.name); setSignup(current => ({ ...current, name })); setSignupErrors(current => ({ ...current, name: validateSignup({ ...signup, name, termsAccepted: signup.terms, privacyAccepted: signup.terms }).name })); }} autoComplete="name" maxLength={100} placeholder="Nome e sobrenome" /></Field>
                <Field id="signup-email" label="E-mail" icon={<Mail />} error={signupErrors.email}><input required value={signup.email} onChange={event => updateSignup('email', event.target.value)} onBlur={() => { const email = normalizeEmail(signup.email); setSignup(current => ({ ...current, email })); setSignupErrors(current => ({ ...current, email: validateSignup({ ...signup, email, termsAccepted: signup.terms, privacyAccepted: signup.terms }).email })); }} autoComplete="email" inputMode="email" maxLength={254} placeholder="voce@empresa.com" /></Field>
                <Field id="signup-password" label="Senha" icon={<LockKeyhole />} error={signupErrors.password} action={<PasswordButton visible={showSignupPassword} onClick={() => setShowSignupPassword(value => !value)} />}><input required value={signup.password} onChange={event => updateSignup('password', event.target.value)} onBlur={() => setSignupErrors(current => ({ ...current, password: validateSignup({ ...signup, termsAccepted: signup.terms, privacyAccepted: signup.terms }).password }))} type={showSignupPassword ? 'text' : 'password'} autoComplete="new-password" maxLength={128} placeholder="Sua senha" /></Field>
                <Field id="signup-confirmation" label="Confirmar senha" icon={<KeyRound />} error={signupErrors.confirmation}><input required value={signup.confirmation} onChange={event => updateSignup('confirmation', event.target.value)} onBlur={() => setSignupErrors(current => ({ ...current, confirmation: validateSignup({ ...signup, termsAccepted: signup.terms, privacyAccepted: signup.terms }).confirmation }))} type={showSignupPassword ? 'text' : 'password'} autoComplete="new-password" maxLength={128} placeholder="Digite novamente" /></Field>
                <div><label className="flex cursor-pointer items-start gap-2.5 text-[9px] leading-4 text-[#808080]"><input required aria-invalid={Boolean(signupErrors.terms)} aria-describedby={signupErrors.terms ? 'signup-terms-error' : undefined} type="checkbox" checked={signup.terms} onChange={event => updateSignup('terms', event.target.checked)} onBlur={() => setSignupErrors(current => ({ ...current, terms: validateSignup({ ...signup, termsAccepted: signup.terms, privacyAccepted: signup.terms }).terms }))} className={`mt-0.5 h-3.5 w-3.5 shrink-0 accent-[#FF7F50] ${signupErrors.terms ? 'outline outline-1 outline-offset-1 outline-[#EF4444]' : ''}`} /><span>Li e aceito os <a href="/terms" target="_blank" rel="noopener noreferrer" className="text-white underline decoration-white/25 underline-offset-2">Termos de Uso</a> e a <a href="/privacy" target="_blank" rel="noopener noreferrer" className="text-white underline decoration-white/25 underline-offset-2">Política de Privacidade</a>.</span></label>{signupErrors.terms && <FieldError id="signup-terms-error">{signupErrors.terms}</FieldError>}</div>
                {signupMessage && <Feedback {...signupMessage} />}<SubmitButton loading={submitting === 'signup'} label="Criar conta" />
              </form>}
            </div>
            </AuthFormHeight>
            <p className="clicko-auth-discovery mt-4 text-center text-[10px] text-[#808080]">{mode === 'login' ? 'Ainda não tem uma conta?' : 'Já possui uma conta?'}{' '}<button type="button" onClick={() => setMode(mode === 'login' ? 'signup' : 'login')}>{mode === 'login' ? 'Criar conta' : 'Entrar'}</button></p>
          </div>
        </> : <SpecialFlow mode={mode} login={login} signup={signup} errors={specialErrors} showPassword={showSignupPassword} submitting={submitting === 'special'} message={specialMessage} actionToken={actionToken} setLogin={setLogin} setSignup={setSignup} setErrors={setSpecialErrors} setShowPassword={setShowSignupPassword} setMode={setMode} setModeState={setModeState} setMessage={setSpecialMessage} onSubmit={submitSpecial} />}
        <p className="mt-5 text-center text-[8px] uppercase tracking-[0.22em] text-[rgba(128,128,128,0.42)]">Acesso seguro à sua operação</p>
      </section>
    </div>
  </main>;
};

/** Measure only the changing form, keeping the gallery and heading mounted. */
function AuthFormHeight({ mode, children }: { mode: Mode; children: React.ReactNode }) {
  const frame = React.useRef<HTMLDivElement>(null);
  const content = React.useRef<HTMLDivElement>(null);
  React.useLayoutEffect(() => {
    const outer = frame.current, inner = content.current;
    if (!outer || !inner) return;
    const measure = () => {
      const height = `${inner.offsetHeight}px`;
      if (outer.style.height !== height) outer.style.height = height;
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(inner);
    return () => observer.disconnect();
  }, []);
  React.useLayoutEffect(() => {
    if (frame.current && content.current) frame.current.style.height = `${content.current.offsetHeight}px`;
  }, [mode]);
  return <div ref={frame} className="clicko-auth-form-height"><div ref={content}>{children}</div></div>;
}

function AuthCard({ eyebrow, title, description, className = '', children }: { eyebrow: string; title: string; description: string; className?: string; children: React.ReactNode }) { return <section className={`clicko-auth-card clicko-auth-flow-card relative overflow-hidden rounded-2xl border border-white/[0.08] bg-[rgba(14,14,14,0.84)] p-5 shadow-2xl shadow-black/50 backdrop-blur-xl sm:p-7 ${className}`}><header className="mb-5"><span className="text-[9px] font-semibold uppercase tracking-[0.22em] text-[#FF7F50]">{eyebrow}</span><h2 className="mt-2 text-[22px] font-semibold tracking-[-0.035em]">{title}</h2><p className="mt-1.5 max-w-[340px] text-[10px] leading-5 text-[#808080]">{description}</p></header>{children}</section>; }

type SpecialProps = { mode: Exclude<Mode, 'login' | 'signup'>; login: LoginFields; signup: SignupFields; errors: SpecialFieldErrors; showPassword: boolean; submitting: boolean; message?: FeedbackState; actionToken: string; setLogin: React.Dispatch<React.SetStateAction<LoginFields>>; setSignup: React.Dispatch<React.SetStateAction<SignupFields>>; setErrors: React.Dispatch<React.SetStateAction<SpecialFieldErrors>>; setShowPassword: React.Dispatch<React.SetStateAction<boolean>>; setMode: (mode: Mode) => void; setModeState: React.Dispatch<React.SetStateAction<Mode>>; setMessage: React.Dispatch<React.SetStateAction<FeedbackState | undefined>>; onSubmit: (event: React.FormEvent) => void };
function SpecialFlow({ mode, login, signup, errors, showPassword, submitting, message, actionToken, setLogin, setSignup, setErrors, setShowPassword, setMode, setModeState, setMessage, onSubmit }: SpecialProps) {
  const copy = titles[mode];
  return <AuthCard eyebrow={copy[0]} title={copy[1]} description={copy[2]} className="clicko-auth-content mx-auto max-w-[420px]">{mode !== 'check-email' && <button type="button" onClick={() => setMode(mode === 'reset' ? 'forgot' : 'login')} className="clicko-auth-back mb-5 inline-flex items-center gap-2 text-[10px] text-[#808080] transition hover:text-white"><ArrowLeft className="h-3.5 w-3.5" />Voltar para as opções de acesso</button>}{mode === 'check-email' ? <div className="space-y-5"><div className="grid h-12 w-12 place-items-center rounded-xl border border-[#FF7F50]/25 bg-[#FF7F50]/10 text-[#FF7F50]"><Mail className="h-5 w-5" /></div>{message && <Feedback {...message} />}{actionToken && <button type="button" onClick={() => { setModeState('verify'); setMessage(undefined); }} className="clicko-auth-submit h-11 w-full rounded-lg bg-white text-[10px] font-semibold text-black">Verificar no ambiente local</button>}<button type="button" onClick={() => setMode('login')} className="clicko-auth-link w-full text-[10px] text-[#808080] hover:text-white">Voltar para o acesso</button></div> : <form onSubmit={onSubmit} noValidate className="space-y-4">{mode === 'forgot' && <Field id="recovery-email" label="E-mail" icon={<Mail />} error={errors.email}><input value={login.email} onChange={event => { const email = event.target.value; setLogin(current => ({ ...current, email })); if (errors.email) setErrors(current => ({ ...current, email: isValidEmail(email) ? undefined : current.email })); }} autoComplete="email" inputMode="email" maxLength={254} placeholder="voce@empresa.com" /></Field>}{mode === 'reset' && <><Field id="reset-password" label="Nova senha" icon={<LockKeyhole />} error={errors.password} action={<PasswordButton visible={showPassword} onClick={() => setShowPassword(value => !value)} />}><input value={signup.password} onChange={event => { const password = event.target.value; setSignup(current => ({ ...current, password })); setErrors(current => ({ ...current, password: current.password && isValidPassword(password) ? undefined : current.password, confirmation: current.confirmation && password === signup.confirmation ? undefined : current.confirmation })); }} type={showPassword ? 'text' : 'password'} autoComplete="new-password" maxLength={128} placeholder="Sua nova senha" /></Field><Field id="reset-confirmation" label="Confirmar senha" icon={<KeyRound />} error={errors.confirmation}><input value={signup.confirmation} onChange={event => { const confirmation = event.target.value; setSignup(current => ({ ...current, confirmation })); if (errors.confirmation) setErrors(current => ({ ...current, confirmation: confirmation === signup.password ? undefined : current.confirmation })); }} type={showPassword ? 'text' : 'password'} autoComplete="new-password" maxLength={128} placeholder="Digite novamente" /></Field></>}{message && <Feedback {...message} />}<SubmitButton loading={submitting} label={mode === 'forgot' ? 'Enviar instruções' : mode === 'verify' ? 'Verificar e entrar' : 'Salvar nova senha'} /></form>}</AuthCard>;
}

function PasswordButton({ visible, onClick }: { visible: boolean; onClick: () => void }) { return <button type="button" onClick={onClick} aria-label={visible ? 'Ocultar senha' : 'Mostrar senha'}>{visible ? <EyeOff /> : <Eye />}</button>; }
function SubmitButton({ loading, label, accent = false }: { loading: boolean; label: string; accent?: boolean }) { return <button disabled={loading} className={`clicko-auth-submit flex h-11 w-full items-center justify-center gap-2 rounded-lg text-[10px] font-semibold text-black transition disabled:cursor-wait disabled:opacity-60 ${accent ? 'bg-[#FF7F50] hover:bg-[#ff906a]' : 'bg-white hover:bg-[#f0f0f0]'}`}>{loading ? <ClickoLoader size="small" tone="light" label={label} /> : <>{label}<ArrowRight className="h-4 w-4" /></>}</button>; }
function Field({ id, label, icon, error, action, children }: { id?: string; label: string; icon: React.ReactNode; error?: string; action?: React.ReactNode; children: React.ReactElement<React.InputHTMLAttributes<HTMLInputElement>> }) {
  const generatedId = React.useId();
  const inputId = id || generatedId;
  const errorId = `${inputId}-error`;
  return <div className="clicko-auth-field block"><label htmlFor={inputId} className="mb-1.5 block text-[10px] font-medium text-[rgba(255,255,255,0.72)]">{label}</label><span className={`clicko-auth-control flex h-11 items-center gap-2.5 rounded-lg border bg-black px-3 transition focus-within:ring-2 ${error ? 'border-[#EF4444] focus-within:border-[#EF4444] focus-within:ring-[#EF4444]/15' : 'border-white/[0.09] focus-within:border-[#FF7F50]/60 focus-within:ring-[#FF7F50]/10'}`}><span className={error ? 'text-[#EF4444] [&>svg]:h-4 [&>svg]:w-4' : 'text-[#808080] [&>svg]:h-4 [&>svg]:w-4'}>{icon}</span>{React.cloneElement(children, { id: inputId, 'aria-invalid': Boolean(error), 'aria-describedby': error ? errorId : undefined, className: 'min-w-0 flex-1 bg-transparent text-[11px] text-white outline-none placeholder:text-[#808080]/60' })}{action && <span className="[&>button]:text-[#808080] [&>button:hover]:text-white [&_svg]:h-4 [&_svg]:w-4">{action}</span>}</span>{error && <FieldError id={errorId}>{error}</FieldError>}</div>;
}
function FieldError({ id, children }: { id: string; children: React.ReactNode }) { return <p id={id} role="alert" className="mt-1.5 text-[8px] leading-3.5 text-[#F87171]">{children}</p>; }
function Feedback({ tone, text }: FeedbackState) { return <div role={tone === 'error' ? 'alert' : 'status'} aria-live="polite" className={`rounded-lg border px-3 py-2.5 text-[9px] leading-4 ${tone === 'error' ? 'border-[#EF4444]/45 bg-[#EF4444]/10 text-[#F87171]' : 'border-white/[0.08] bg-white/[0.025] text-[rgba(255,255,255,0.72)]'}`}>{text}</div>; }
