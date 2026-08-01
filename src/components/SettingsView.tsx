import React from 'react';
import {
  Settings,
  Sparkles,
  Key,
  SlidersHorizontal,
  Command,
  CheckCircle2,
  Moon,
  Sun,
  Maximize2,
  Minimize2,
  RefreshCw,
} from 'lucide-react';
import { Workspace } from '../types';

interface SettingsViewProps {
  activeWorkspace: Workspace;
  onUpdateWorkspace: (updated: Workspace) => void;
  isCompact: boolean;
  onToggleCompact: () => void;
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  activeWorkspace,
  onUpdateWorkspace,
  isCompact,
  onToggleCompact,
  isDarkMode,
  onToggleDarkMode,
}) => {
  const [brandName, setBrandName] = React.useState(activeWorkspace.brandProfile.name);
  const [industry, setIndustry] = React.useState(activeWorkspace.brandProfile.industry);
  const [tone, setTone] = React.useState(activeWorkspace.brandProfile.tone);
  const [targetAudience, setTargetAudience] = React.useState(
    activeWorkspace.brandProfile.targetAudience
  );
  const [doAndDonts, setDoAndDonts] = React.useState(
    activeWorkspace.brandProfile.doAndDonts
  );
  const [savedSuccess, setSavedSuccess] = React.useState(false);

  const handleSaveSettings = () => {
    onUpdateWorkspace({
      ...activeWorkspace,
      brandProfile: {
        ...activeWorkspace.brandProfile,
        name: brandName,
        industry,
        tone,
        targetAudience,
        doAndDonts,
      },
    });
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-4">
        <div>
          <h2 className="text-lg font-bold text-[#ededed] flex items-center gap-2">
            <Settings className="w-5 h-5 text-indigo-400" /> Configurações do Sistema & Cérebro da Marca
          </h2>
          <p className="text-xs text-white/40">
            Ajuste os parâmetros que alimentam a Inteligência Artificial, chaves de API e preferências da interface
          </p>
        </div>

        <button
          onClick={handleSaveSettings}
          className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/20 border border-indigo-400/30 flex items-center gap-2"
        >
          {savedSuccess ? (
            <>
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Configurações Salvas!</span>
            </>
          ) : (
            <span>Salvar Alterações</span>
          )}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Brand Config Panel */}
        <div className="lg:col-span-2 bg-[#0A0A0A] border border-white/5 p-6 rounded-2xl space-y-5">
          <h3 className="text-sm font-bold text-[#ededed] flex items-center gap-2 border-b border-white/5 pb-3">
            <Sparkles className="w-4 h-4 text-indigo-400" /> Parâmetros do Cérebro de IA da Marca
          </h3>

          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-neutral-300 font-semibold mb-1">Nome da Marca / Projeto</label>
                <input
                  type="text"
                  value={brandName}
                  onChange={(e) => setBrandName(e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/5 rounded-xl p-2.5 text-[#ededed] focus:outline-none focus:border-indigo-500/50"
                />
              </div>

              <div>
                <label className="block text-neutral-300 font-semibold mb-1">Indústria / Nicho</label>
                <input
                  type="text"
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/5 rounded-xl p-2.5 text-[#ededed] focus:outline-none focus:border-indigo-500/50"
                />
              </div>
            </div>

            <div>
              <label className="block text-neutral-300 font-semibold mb-1">Tom de Voz Padrão</label>
              <input
                type="text"
                value={tone}
                onChange={(e) => setTone(e.target.value)}
                className="w-full bg-white/[0.03] border border-white/5 rounded-xl p-2.5 text-[#ededed] focus:outline-none focus:border-indigo-500/50"
                placeholder="Ex: Sofisticado, Inovador, Direto ao ponto e Confiável"
              />
            </div>

            <div>
              <label className="block text-neutral-300 font-semibold mb-1">Público-Alvo Prioritário</label>
              <textarea
                value={targetAudience}
                onChange={(e) => setTargetAudience(e.target.value)}
                rows={2}
                className="w-full bg-white/[0.03] border border-white/5 rounded-xl p-2.5 text-[#ededed] focus:outline-none focus:border-indigo-500/50 resize-none"
              />
            </div>

            <div>
              <label className="block text-neutral-300 font-semibold mb-1">Diretrizes (O que Fazer e Não Fazer)</label>
              <textarea
                value={doAndDonts}
                onChange={(e) => setDoAndDonts(e.target.value)}
                rows={3}
                className="w-full bg-white/[0.03] border border-white/5 rounded-xl p-2.5 text-[#ededed] focus:outline-none focus:border-indigo-500/50 resize-none"
              />
            </div>
          </div>
        </div>

        {/* API Keys & Shortcuts Side Column */}
        <div className="space-y-6">
          {/* Gemini API Status */}
          <div className="bg-[#0A0A0A] border border-white/5 p-5 rounded-2xl space-y-4">
            <h3 className="text-sm font-bold text-[#ededed] flex items-center gap-2 border-b border-white/5 pb-3">
              <Key className="w-4 h-4 text-indigo-400" /> Status da API Gemini
            </h3>

            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-neutral-200 space-y-1">
              <div className="font-bold text-emerald-400 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" /> Gemini API Conectada
              </div>
              <p className="text-[11px] text-white/40">
                A chave de API é injetada com segurança no servidor backend para chamadas server-side sem exposição ao navegador.
              </p>
            </div>
          </div>

          {/* Interface Preferences */}
          <div className="bg-[#0A0A0A] border border-white/5 p-5 rounded-2xl space-y-4 text-xs">
            <h3 className="text-sm font-bold text-[#ededed] flex items-center gap-2 border-b border-white/5 pb-3">
              <SlidersHorizontal className="w-4 h-4 text-indigo-400" /> Preferências de Interface
            </h3>

            <div className="flex items-center justify-between p-2.5 rounded-xl bg-white/[0.03] border border-white/5">
              <div>
                <div className="font-bold text-[#ededed]">Densidade de Layout</div>
                <div className="text-[10px] text-white/40">
                  {isCompact ? 'Modo Compacto Ativo' : 'Modo Confortável Ativo'}
                </div>
              </div>

              <button
                onClick={onToggleCompact}
                className="p-2 rounded-lg bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600/30"
              >
                {isCompact ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
              </button>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-xl bg-white/[0.03] border border-white/5">
              <div>
                <div className="font-bold text-[#ededed]">Tema Visual</div>
                <div className="text-[10px] text-white/40">
                  {isDarkMode ? 'Dark Mode Padrão (Enterprise)' : 'Light Mode Opcional'}
                </div>
              </div>

              <button
                onClick={onToggleDarkMode}
                className="p-2 rounded-lg bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600/30"
              >
                {isDarkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-indigo-400" />}
              </button>
            </div>
          </div>

          {/* Keyboard Shortcuts Cheat Sheet */}
          <div className="bg-[#0A0A0A] border border-white/5 p-5 rounded-2xl space-y-3 text-xs">
            <h3 className="text-xs font-bold text-[#ededed] flex items-center gap-2">
              <Command className="w-3.5 h-3.5 text-indigo-400" /> Atalhos de Teclado
            </h3>

            <div className="space-y-1.5 text-[11px] text-white/40">
              <div className="flex justify-between">
                <span>Busca Spotlight Global</span>
                <kbd className="bg-white/10 px-1.5 py-0.5 rounded font-mono text-white">⌘K</kbd>
              </div>
              <div className="flex justify-between">
                <span>Novo Conteúdo</span>
                <kbd className="bg-white/10 px-1.5 py-0.5 rounded font-mono text-white">⌘N</kbd>
              </div>
              <div className="flex justify-between">
                <span>Assistente IA</span>
                <kbd className="bg-white/10 px-1.5 py-0.5 rounded font-mono text-white">⌘I</kbd>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
