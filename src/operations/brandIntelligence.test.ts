import test from 'node:test';
import assert from 'node:assert/strict';
import { brandIntelligenceCompleteness, buildBrandIntelligenceContext } from './brandIntelligence';
import type { AIMemoryEntry, ClientIntelligenceProfile, Workspace } from '../types';

const workspace: Workspace = { id: 'ws-1', name: 'Agência', avatar: '', plan: 'Equipe', membersCount: 2, brandProfile: { name: 'Agência', industry: '', tone: 'Direto', targetAudience: '', keywords: [], doAndDonts: '', primaryColor: '#FF7F50' } };
const client = (id: string, name: string): ClientIntelligenceProfile => ({ id, workspaceId: workspace.id, name, segment: 'SaaS', products: 'Produto', audience: 'Gestores', positioning: 'Premium', toneOfVoice: 'Claro', visualIdentity: 'Editorial', differentiators: 'Contexto', competitors: 'Referência', featuredOffer: '', currentObjective: 'Crescer', highlightedContentIds: [], activeCampaignIds: [], recommendedActions: [], updatedAt: new Date(0).toISOString() });
const memory = (clientId: string, value: string): AIMemoryEntry => ({ id: `m-${clientId}`, workspaceId: workspace.id, clientId, category: 'communication', label: 'Tom de voz', value, scope: 'permanent', confidence: 90, source: 'user', occurrences: 2, createdAt: new Date(0).toISOString(), updatedAt: new Date(0).toISOString() });

test('brand intelligence never mixes memories from another client', () => {
  const alpha = client('alpha', 'Alpha');
  alpha.toneOfVoice = '';
  const result = buildBrandIntelligenceContext(workspace, [memory('alpha', 'Sóbrio'), memory('beta', 'Irreverente')], alpha);
  assert.equal(result.company, 'Alpha');
  assert.equal(result.toneOfVoice, 'Sóbrio');
  assert.equal(result.history.includes('Irreverente'), false);
});

test('client brand fields take precedence and completeness is deterministic', () => {
  const alpha = client('alpha', 'Alpha');
  alpha.brandColors = ['#000000', '#FF7F50'];
  alpha.typography = 'Inter';
  alpha.visualReferences = 'Editorial';
  alpha.keywords = 'clareza';
  alpha.avoidTopics = 'promessas';
  const context = buildBrandIntelligenceContext(workspace, [memory('alpha', 'Outro tom')], alpha);
  assert.equal(context.toneOfVoice, 'Claro');
  assert.match(context.visualIdentity, /#FF7F50/);
  assert.equal(context.requiredWords, 'clareza');
  assert.equal(context.forbiddenWords, 'promessas');
  assert.equal(brandIntelligenceCompleteness(alpha).percent, 100);
});
