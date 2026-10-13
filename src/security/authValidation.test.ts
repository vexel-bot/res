import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeEmail, normalizeFullName, validateLogin, validateSignup } from './authValidation';

test('authentication validation normalizes identity fields without transforming passwords', () => {
  assert.equal(normalizeEmail('  Pedro.Silva@Example.COM  '), 'pedro.silva@example.com');
  assert.equal(normalizeFullName('  Pedro   Henrique  Silva '), 'Pedro Henrique Silva');
  assert.deepEqual(validateLogin({ email: '', password: '' }), { email: 'O e-mail é obrigatório.', password: 'A senha é obrigatória.' });
  assert.equal(validateLogin({ email: 'pedro@dominio', password: 'SenhaForte9' }).email, 'Digite um e-mail válido.');
});

test('signup validation requires a real full name, matching strong passwords, and explicit legal consent', () => {
  const valid = { name: 'Maria de Souza', email: 'maria@example.com', password: 'SenhaForte9', confirmation: 'SenhaForte9', termsAccepted: true, privacyAccepted: true };
  assert.deepEqual(validateSignup(valid), {});
  assert.equal(validateSignup({ ...valid, name: 'Maria' }).name, 'Informe seu nome completo.');
  assert.equal(validateSignup({ ...valid, name: '123 Souza' }).name, 'Informe seu nome completo.');
  assert.equal(validateSignup({ ...valid, password: 'senha', confirmation: 'senha' }).password, 'Use ao menos 8 caracteres, com maiúscula, minúscula e número.');
  assert.equal(validateSignup({ ...valid, confirmation: 'OutraSenha9' }).confirmation, 'As senhas não coincidem.');
  assert.equal(validateSignup({ ...valid, termsAccepted: false }).terms, 'Você precisa aceitar os Termos de Uso e a Política de Privacidade.');
  assert.equal(validateSignup({ ...valid, privacyAccepted: false }).terms, 'Você precisa aceitar os Termos de Uso e a Política de Privacidade.');
});
