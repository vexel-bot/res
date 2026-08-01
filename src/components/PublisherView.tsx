import React from 'react';
import {
  Share2,
  CheckCircle2,
  Plus,
  Zap,
  TrendingUp,
  Clock,
  RefreshCw,
  SlidersHorizontal,
} from 'lucide-react';
import { ConnectedAccount } from '../types';
import { CONNECTED_ACCOUNTS } from '../data/mockData';

export const PublisherView: React.FC = () => {
  const [accounts, setAccounts] = React.useState<ConnectedAccount[]>(CONNECTED_ACCOUNTS);

  const toggleConnect = (id: string) => {
    setAccounts(
      accounts.map((acc) =>
        acc.id === id ? { ...acc, connected: !acc.connected } : acc
      )
    );
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-4">
        <div>
          <h2 className="text-lg font-bold text-[#ededed] flex items-center gap-2">
            <Share2 className="w-5 h-5 text-indigo-400" /> Publicação & Canais Conectados
          </h2>
          <p className="text-xs text-white/40">
            Gerencie integrações com Instagram, TikTok, LinkedIn, YouTube, Threads, Pinterest e X com disparo simultâneo
          </p>
        </div>

        <button className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-indigo-600/20">
          <Plus className="w-4 h-4" /> Conectar Nova Conta
        </button>
      </div>

      {/* Connected Channels Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {accounts.map((acc) => (
          <div
            key={acc.id}
            className="p-5 rounded-2xl bg-[#0A0A0A] border border-white/5 flex flex-col justify-between space-y-4 hover:border-indigo-500/30 transition-all"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-white/[0.03] border border-white/5 flex items-center justify-center font-bold text-xs uppercase text-indigo-300">
                  {acc.platform.slice(0, 2)}
                </div>
                <div>
                  <h4 className="text-xs font-bold text-[#ededed] capitalize">{acc.platform}</h4>
                  <p className="text-[11px] text-white/40">{acc.handle}</p>
                </div>
              </div>

              <button
                onClick={() => toggleConnect(acc.id)}
                className={`px-2.5 py-1 rounded-full text-[10px] font-bold transition-all ${
                  acc.connected
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    : 'bg-white/[0.03] text-white/40 border border-white/5'
                }`}
              >
                {acc.connected ? 'Conectado' : 'Desconectado'}
              </button>
            </div>

            <div className="grid grid-cols-3 gap-2 pt-2 border-t border-white/5 text-center text-xs">
              <div>
                <div className="text-[10px] text-white/40">Seguidores</div>
                <div className="font-bold text-[#ededed] mt-0.5">{acc.followers}</div>
              </div>
              <div>
                <div className="text-[10px] text-white/40">Engajamento</div>
                <div className="font-bold text-emerald-400 mt-0.5">{acc.engagement}</div>
              </div>
              <div>
                <div className="text-[10px] text-white/40">Melhor Horário</div>
                <div className="font-bold text-indigo-300 mt-0.5 text-[10px]">{acc.bestTime}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* AI Recycling Engine Banner */}
      <div className="p-5 rounded-2xl bg-[#0A0A0A] border border-indigo-500/30 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
            Motor de Reciclagem Inteligente
          </span>
          <h3 className="text-sm font-bold text-[#ededed]">Reciclar Automaticamente Conteúdos Virais Past</h3>
          <p className="text-xs text-neutral-300">
            A IA detecta posts com engajamento acima de 8% e re-formata automaticamente para outros canais.
          </p>
        </div>

        <button className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shrink-0 shadow-lg shadow-indigo-600/20">
          Ativar Reciclagem Automática
        </button>
      </div>
    </div>
  );
};
