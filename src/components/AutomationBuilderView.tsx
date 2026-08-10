import React from 'react';
import {
  GitFork,
  Plus,
  Play,
  CheckCircle2,
  Sparkles,
  ArrowRight,
  Zap,
  Layers,
  Settings2,
  MessageSquare,
  UserPlus,
  PhoneCall,
  Mail,
  BarChart,
  CheckSquare,
  FilePlus,
  RefreshCw,
  Clock,
  ShieldCheck
} from 'lucide-react';
import { AutomationFlow, AutomationNode } from '../types';

const INITIAL_ROBUST_FLOWS: AutomationFlow[] = [
  {
    id: 'flow-1',
    title: 'Gatilho de Comentário Instagram → Conversão Completa em Lead & WhatsApp',
    trigger: 'Novo comentário recebido no Instagram com palavra-chave "SISTEMA"',
    isActive: true,
    executionsCount: 142,
    lastRun: 'Há 12 minutos',
    nodes: [
      { id: 'n1', type: 'trigger', label: 'Instagram: Comentário Recebido', details: 'Detecta palavra "SISTEMA" em qualquer publicação' },
      { id: 'n2', type: 'ai_generate', label: 'IA Central: Resposta Automática no Post', details: 'Responde publicamente com mensagem personalizada via Brain' },
      { id: 'n3', type: 'ai_generate', label: 'IA Central: Envio de DM com Oferta', details: 'Envia link do briefing inteligente e cupom exclusivo' },
      { id: 'n4', type: 'notify', label: 'CRM: Registro do Lead', details: 'Cria ficha de contato no CRM do Clicko Studio' },
      { id: 'n5', type: 'notify', label: 'WhatsApp: Mensagem Automática', details: 'Dispara mensagem de onboarding e boas-vindas' },
      { id: 'n6', type: 'schedule', label: 'Tarefas: Agendar Follow-up para Equipe', details: 'Cria tarefa para o time comercial em 24h' },
      { id: 'n7', type: 'notify', label: 'Email: Envio de Proposta Comercial', details: 'Dispara e-mail com apresentação do Clicko AI Studio' },
      { id: 'n8', type: 'ai_generate', label: 'Analytics & Sugestão de Conteúdo IA', details: 'Atualiza métricas de conversão e sugere post de reforço' }
    ]
  },
  {
    id: 'flow-2',
    title: 'Repostagem Automática Multicanal com Recriação por IA',
    trigger: 'Publicação de alto desempenho atingiu +10% de engajamento',
    isActive: true,
    executionsCount: 89,
    lastRun: 'Há 2 horas',
    nodes: [
      { id: 'n10', type: 'trigger', label: 'Analytics: Post Campeão Detectado', details: 'Alcance 3x maior que a média do perfil' },
      { id: 'n11', type: 'ai_generate', label: 'IA Central: Adaptar para LinkedIn & Twitter', details: 'Reescreve mantendo o tom profissional e estrutura B2B' },
      { id: 'n12', type: 'image_studio', label: 'Estúdio de Imagem: Adaptar Formato 16:9', details: 'Redimensiona a capa com upscale e ajuste de iluminação' },
      { id: 'n13', type: 'schedule', label: 'Agendador: Inserir nos Melhores Horários', details: 'Agenda para os horários de maior pico da audiência' }
    ]
  },
  {
    id: 'flow-3',
    title: 'Monitoramento de Menções & Gestão de Crise por IA',
    trigger: 'Menção direta à marca ou palavra proibida do Brain',
    isActive: false,
    executionsCount: 34,
    lastRun: 'Ontem',
    nodes: [
      { id: 'n20', type: 'trigger', label: 'Social Listening: Menção Detectada', details: 'Monitora Instagram, LinkedIn e Twitter' },
      { id: 'n21', type: 'ai_generate', label: 'IA Central: Análise de Sentimento', details: 'Classifica o tom do comentário (Positivo, Neutro ou Crítico)' },
      { id: 'n22', type: 'notify', label: 'Notificar Equipe de Suporte', details: 'Alerta urgente via WhatsApp e E-mail para a equipe' }
    ]
  }
];

export const AutomationBuilderView: React.FC = () => {
  const [flows, setFlows] = React.useState<AutomationFlow[]>(INITIAL_ROBUST_FLOWS);
  const [selectedFlow, setSelectedFlow] = React.useState<AutomationFlow>(flows[0]);
  const [isTesting, setIsTesting] = React.useState(false);
  const [testLog, setTestLog] = React.useState<string | null>(null);

  const toggleFlowActive = (id: string) => {
    setFlows(
      flows.map((f) => (f.id === id ? { ...f, isActive: !f.isActive } : f))
    );
  };

  const handleTestFlow = () => {
    setIsTesting(true);
    setTestLog('Simulando acionamento do fluxo...');
    setTimeout(() => {
      setTestLog(`Fluxo "${selectedFlow.title}" testado! Todos os ${selectedFlow.nodes.length} nós executaram com êxito sem erros.`);
      setIsTesting(false);
    }, 1800);
  };

  const handleCreateNewFlow = () => {
    const newFlow: AutomationFlow = {
      id: `flow-${Date.now()}`,
      title: 'Novo Fluxo de Automação Inteligente',
      trigger: 'Formulário do site preenchido ou novo seguidor',
      isActive: true,
      executionsCount: 0,
      nodes: [
        { id: 'n_new_1', type: 'trigger', label: 'Novo Lead Cadastrado', details: 'Gatilho via Webhook' },
        { id: 'n_new_2', type: 'ai_generate', label: 'IA: Gerar Boas-Vindas Personalizadas', details: 'Consulta o Brain da marca' },
        { id: 'n_new_3', type: 'notify', label: 'WhatsApp & Email: Disparo Simultâneo', details: 'Comunicação multicanal' }
      ]
    };
    setFlows([newFlow, ...flows]);
    setSelectedFlow(newFlow);
  };

  return (
    <div className="clicko-automations-view mx-auto max-w-[1500px] space-y-5 p-5">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.06] pb-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <GitFork className="w-5 h-5 text-[#8bd132]" /> Construtor de Automações Operacionais com IA
          </h2>
          <p className="text-xs text-[#78858e]">
            Conecte Instagram, WhatsApp, CRM, Email, Analytics e Tarefas em fluxos de trabalho autônomos
          </p>
        </div>

        <button
          onClick={handleCreateNewFlow}
          className="flex items-center gap-1.5 rounded-lg bg-[#8bd132] px-4 py-2.5 text-xs font-semibold text-[#0b1208] transition-colors hover:bg-[#9be24d]"
        >
          <Plus className="w-4 h-4" /> Criar Novo Fluxo
        </button>
      </div>

      {/* Main Flow Canvas Grid */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* Left List of Flows */}
        <div className="lg:col-span-4 space-y-3">
          <span className="text-xs font-bold text-[#aeb7bb]">Fluxos de Automação ({flows.length})</span>
          {flows.map((f) => (
            <div
              key={f.id}
              onClick={() => setSelectedFlow(f)}
              className={`clicko-interactive-surface cursor-pointer rounded-xl border p-4 transition-colors ${
                selectedFlow.id === f.id
                  ? 'border-[#8bd132]/25 bg-[#8bd132]/[0.07] text-white'
                  : 'bg-[#182126] border-white/[0.06] hover:border-white/15 text-[#cbd2d5]'
              }`}
            >
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold truncate pr-2">{f.title}</h4>
                <input
                  type="checkbox"
                  checked={f.isActive}
                  onChange={(e) => {
                    e.stopPropagation();
                    toggleFlowActive(f.id);
                  }}
                  className="w-4 h-4 accent-[#8bd132] rounded cursor-pointer"
                />
              </div>
              <p className="text-[10px] text-[#7d888d] mt-1 line-clamp-2">Gatilho: {f.trigger}</p>
              <div className="mt-3 pt-2 border-t border-white/[0.05] flex items-center justify-between text-[10px] text-[#8e989d]">
                <span>{f.nodes.length} etapas no fluxo</span>
                <span>{f.executionsCount} execuções</span>
              </div>
            </div>
          ))}
        </div>

        {/* Visual Node Flow Stage */}
        <div className="clicko-automation-canvas space-y-5 rounded-xl border border-white/[0.07] bg-[#101316] p-5 lg:col-span-8">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
            <div>
              <span className="text-[9px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded bg-[#8bd132]/20 text-[#8bd132] border border-[#8bd132]/30">
                Construtor Visual de Processos
              </span>
              <h3 className="text-base font-bold text-white mt-1">{selectedFlow.title}</h3>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleTestFlow}
                disabled={isTesting}
                className="px-3.5 py-2 rounded-xl bg-black/30 hover:bg-black/50 text-xs font-bold text-white border border-white/[0.08] flex items-center gap-1.5"
              >
                {isTesting ? <RefreshCw className="h-3.5 w-3.5 animate-spin text-[#8bd132]" /> : <Play className="h-3.5 w-3.5 text-[#8bd132]" />}
                <span>{isTesting ? 'Simulando...' : 'Testar Fluxo IA'}</span>
              </button>
            </div>
          </div>

          {testLog && (
            <div className="rounded-xl border border-[#8bd132]/30 bg-[#8bd132]/[0.08] p-3 text-[10px] font-bold text-[#8bd132] flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 shrink-0" />
              <span>{testLog}</span>
            </div>
          )}

          {/* Node Visual Chain */}
          <div className="clicko-automation-chain relative space-y-3">
            {selectedFlow.nodes.map((node, index) => (
              <div key={node.id} className="relative">
                <div className="p-4 rounded-xl bg-black/25 border border-white/[0.06] hover:border-[#8bd132]/40 transition-all flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-[#8bd132]/10 border border-[#8bd132]/30 flex items-center justify-center font-bold text-xs text-[#8bd132] shrink-0">
                      {index + 1}
                    </div>
                    <div>
                      <span className="text-[9px] uppercase font-bold text-[#8bd132] tracking-wider">
                        {node.type === 'trigger' ? 'Gatilho Inicial' : node.type === 'ai_generate' ? 'Ação com IA' : 'Integração de Sistema'}
                      </span>
                      <h5 className="text-xs font-bold text-white">{node.label}</h5>
                      <p className="text-[10px] text-[#7b868a] mt-0.5">{node.details}</p>
                    </div>
                  </div>

                  <span className="text-[9px] font-bold text-[#8bd132] bg-[#8bd132]/10 px-2 py-1 rounded">
                    Ativo
                  </span>
                </div>

                {index < selectedFlow.nodes.length - 1 && (
                  <div className="flex justify-center py-1">
                    <div className="w-0.5 h-4 bg-[#8bd132]/30" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
