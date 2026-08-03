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
} from 'lucide-react';
import { AutomationFlow } from '../types';
import { INITIAL_AUTOMATIONS } from '../data/mockData';

export const AutomationBuilderView: React.FC = () => {
  const [flows, setFlows] = React.useState<AutomationFlow[]>(INITIAL_AUTOMATIONS);
  const [selectedFlow, setSelectedFlow] = React.useState<AutomationFlow>(flows[0]);

  const toggleFlowActive = (id: string) => {
    setFlows(
      flows.map((f) => (f.id === id ? { ...f, isActive: !f.isActive } : f))
    );
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-4">
        <div>
          <h2 className="text-lg font-bold text-[#ededed] flex items-center gap-2">
            <GitFork className="w-5 h-5 text-indigo-400" /> Central de Automações
          </h2>
          <p className="text-xs text-white/40">
            Fluxos, gatilhos, webhooks e execuções programadas em um construtor visual escalável
          </p>
        </div>

        <button className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-indigo-600/20">
          <Plus className="w-4 h-4" /> Criar Novo Fluxo
        </button>
      </div>

      {/* Main Flow Canvas Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left List of Flows */}
        <div className="space-y-3">
          <span className="text-xs font-bold text-white/40">Fluxos Ativos ({flows.length})</span>
          {flows.map((f) => (
            <div
              key={f.id}
              onClick={() => setSelectedFlow(f)}
              className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                selectedFlow.id === f.id
                  ? 'bg-indigo-600/15 border-indigo-500/50 text-[#ededed] shadow-lg shadow-indigo-600/10'
                  : 'bg-[#0A0A0A] border-white/5 hover:border-white/10 text-neutral-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold truncate">{f.title}</h4>
                <input
                  type="checkbox"
                  checked={f.isActive}
                  onChange={() => toggleFlowActive(f.id)}
                  className="w-4 h-4 accent-indigo-600 rounded cursor-pointer"
                />
              </div>
              <p className="text-[11px] text-white/40 mt-1">Gatilho: {f.trigger}</p>
              <div className="mt-3 pt-2 border-t border-white/5 flex items-center justify-between text-[10px] text-white/40">
                <span>{f.nodes.length} nós ativos</span>
                <span>{f.executionsCount} execuções</span>
              </div>
            </div>
          ))}
        </div>

        {/* Visual Node Flow Stage */}
        <div className="lg:col-span-2 bg-[#0A0A0A] border border-white/5 rounded-2xl p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-white/5 pb-4">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Construtor Visual de Fluxos
              </span>
              <h3 className="text-base font-bold text-[#ededed] mt-1">{selectedFlow.title}</h3>
            </div>

            <div className="flex items-center gap-2">
              <button className="px-3 py-1.5 rounded-xl bg-white/[0.03] hover:bg-white/10 text-xs font-bold text-neutral-300 border border-white/5">
                Testar Fluxo
              </button>
            </div>
          </div>

          {/* Node Visual Chain */}
          <div className="space-y-3 relative">
            {selectedFlow.nodes.map((node, index) => (
              <div key={node.id} className="relative">
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/5 hover:border-indigo-500/40 transition-all flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center font-bold text-xs text-indigo-300 shrink-0">
                      {index + 1}
                    </div>
                    <div>
                      <div className="text-xs font-bold text-[#ededed]">{node.label}</div>
                      <div className="text-[11px] text-white/40">{node.details}</div>
                    </div>
                  </div>

                  <span className="text-[10px] font-mono text-white/40 uppercase px-2 py-1 rounded bg-white/[0.03]">
                    {node.type}
                  </span>
                </div>

                {index < selectedFlow.nodes.length - 1 && (
                  <div className="flex justify-center my-1.5">
                    <ArrowRight className="w-4 h-4 text-indigo-400 rotate-90" />
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
