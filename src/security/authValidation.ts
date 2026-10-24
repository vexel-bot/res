export const CURRENT_TERMS_VERSION = '1.0.0';
export const CURRENT_PRIVACY_VERSION = '1.0.0';

export type LoginFieldErrors = Partial<Record<'email' | 'password', string>>;
export type SignupFieldErrors = Partial<Record<'name' | 'email' | 'password' | 'confirmation' | 'terms', string>>;

export type LoginValidationInput = {
  email: string;
  password: string;
};

export type SignupValidationInput = {
  name: string;
  email: string;
  password: string;
  confirmation: string;
  termsAccepted: boolean;
  privacyAccepted: boolean;
};

export const normalizeEmail = (value: unknown) => String(value ?? '').trim().toLowerCase();
export const normalizeFullName = (value: unknown) => String(value ?? '').trim().replace(/\s+/g, ' ');

export const isValidEmail = (value: unknown) => {
  const email = normalizeEmail(value);
  if (!email || email.length > 254 || email.includes('..')) return false;
  const match = /^([^\s@]+)@([^\s@]+)$/.exec(email);
  if (!match || match[1].length > 64) return false;
  const labels = match[2].split('.');
  return labels.length >= 2
    && labels.at(-1)!.length >= 2
    && labels.every(label => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/i.test(label));
};

export const isValidFullName = (value: unknown) => {
  const parts = normalizeFullName(value).split(' ').filter(Boolean);
  return parts.length >= 2
    && parts.every(part => part.length >= 2 && /^[\p{L}][\p{L}'’\-]*$/u.test(part));
};

export const isValidPassword = (value: unknown) => {
  const password = typeof value === 'string' ? value : '';
  return password.length >= 8
    && password.length <= 128
    && /[a-z]/.test(password)
    && /[A-Z]/.test(password)
    && /\d/.test(password);
};

export function validateLogin(input: LoginValidationInput): LoginFieldErrors {
  const errors: LoginFieldErrors = {};
  if (!normalizeEmail(input.email)) errors.email = 'O e-mail é obrigatório.';
  else if (!isValidEmail(input.email)) errors.email = 'Digite um e-mail válido.';
  if (!input.password || !input.password.trim()) errors.password = 'A senha é obrigatória.';
  else if (input.password.length > 128) errors.password = 'Preencha este campo corretamente.';
  return errors;
}

export function validateSignup(input: SignupValidationInput): SignupFieldErrors {
  const errors: SignupFieldErrors = {};
  if (!isValidFullName(input.name)) errors.name = 'Informe seu nome completo.';
  if (!normalizeEmail(input.email)) errors.email = 'O e-mail é obrigatório.';
  else if (!isValidEmail(input.email)) errors.email = 'Digite um e-mail válido.';
  if (!input.password || !input.password.trim()) errors.password = 'A senha é obrigatória.';
  else if (!isValidPassword(input.password)) errors.password = 'Use ao menos 8 caracteres, com maiúscula, minúscula e número.';
  if (!input.confirmation) errors.confirmation = 'Confirme sua senha.';
  else if (input.password !== input.confirmation) errors.confirmation = 'As senhas não coincidem.';
  if (!input.termsAccepted || !input.privacyAccepted) errors.terms = 'Você precisa aceitar os Termos de Uso e a Política de Privacidade.';
  return errors;
}

export const firstError = (errors: Record<string, string | undefined>) => Object.values(errors).find(Boolean);
