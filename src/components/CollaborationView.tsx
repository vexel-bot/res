import React from 'react';
import {
  Users,
  UserPlus,
  ShieldCheck,
  CheckCircle2,
  Clock,
  MessageSquare,
  Send,
  MoreHorizontal,
} from 'lucide-react';
import { TeamMember, Post } from '../types';
import { INITIAL_TEAM } from '../data/mockData';

interface CollaborationViewProps {
  posts: Post[];
}

export const CollaborationView: React.FC<CollaborationViewProps> = ({ posts }) => {
  const [members, setMembers] = React.useState<TeamMember[]>(INITIAL_TEAM);
  const pendingPosts = posts.filter((p) => p.status === 'pending_approval');
  const [commentText, setCommentText] = React.useState('');
  const [commentsList, setCommentsList] = React.useState([
    {
      author: 'Marcus Thorne',
      text: 'Visualmente impecável. Apenas ajustem o tom da frase inicial!',
      time: '14:20',
    },
  ]);

  const handleAddComment = () => {
    if (!commentText.trim()) return;
    setCommentsList([
      ...commentsList,
      { author: 'Elena Vance', text: commentText, time: 'Agora mesmo' },
    ]);
    setCommentText('');
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-4">
        <div>
          <h2 className="text-lg font-bold text-[#ededed] flex items-center gap-2">
            <Users className="w-5 h-5 text-indigo-400" /> Colaboração & Fluxo de Aprovação
          </h2>
          <p className="text-xs text-white/40">
            Workspaces multi-tenant, gestão de clientes, comentários em linha e esteira de aprovação
          </p>
        </div>

        <button className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-indigo-600/20">
          <UserPlus className="w-4 h-4" /> Convidar Membro / Cliente
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Team Members List */}
        <div className="space-y-4 bg-[#0A0A0A] border border-white/5 p-5 rounded-2xl">
          <h3 className="text-sm font-bold text-[#ededed] border-b border-white/5 pb-3">
            Membros do Workspace ({members.length})
          </h3>

          <div className="space-y-3">
            {members.map((m) => (
              <div
                key={m.id}
                className="p-3 rounded-xl bg-white/[0.02] border border-white/5 flex items-center justify-between gap-3 text-xs"
              >
                <div className="flex items-center gap-3">
                  <img
                    src={m.avatar}
                    alt={m.name}
                    className="w-8 h-8 rounded-full object-cover ring-1 ring-indigo-500/30"
                    referrerPolicy="no-referrer"
                  />
                  <div>
                    <div className="font-bold text-[#ededed]">{m.name}</div>
                    <div className="text-[10px] text-white/40">{m.email}</div>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300">
                    {m.role}
                  </span>
                  <div className="text-[9px] text-white/40 mt-1">{m.lastActive}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Approval Queue & Line Comments */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-[#0A0A0A] border border-white/5 p-5 rounded-2xl space-y-4">
            <h3 className="text-sm font-bold text-[#ededed] flex items-center gap-2 border-b border-white/5 pb-3">
              <Clock className="w-4 h-4 text-amber-400" /> Fila de Conteúdos para Aprovação ({pendingPosts.length})
            </h3>

            {pendingPosts.length === 0 ? (
              <div className="p-6 text-center text-white/40 text-xs">
                Nenhum conteúdo aguardando aprovação no momento.
              </div>
            ) : (
              pendingPosts.map((post) => (
                <div
                  key={post.id}
                  className="p-4 rounded-xl bg-white/[0.03] border border-white/5 space-y-4"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-[10px] uppercase font-bold text-indigo-400">
                        {post.platform} • {post.format}
                      </span>
                      <h4 className="text-xs font-bold text-[#ededed] mt-0.5">{post.title}</h4>
                    </div>

                    <div className="flex items-center gap-2">
                      <button className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md">
                        Aprovar
                      </button>
                    </div>
                  </div>

                  <p className="text-xs text-neutral-300 bg-[#050505] p-3 rounded-xl border border-white/5">
                    {post.copy}
                  </p>

                  {/* Comment thread */}
                  <div className="space-y-2 pt-2 border-t border-white/5">
                    <span className="text-[11px] font-bold text-neutral-300 flex items-center gap-1.5">
                      <MessageSquare className="w-3.5 h-3.5 text-indigo-400" /> Comentários e Revisão
                    </span>

                    <div className="space-y-2 max-h-36 overflow-y-auto custom-scrollbar">
                      {commentsList.map((c, i) => (
                        <div key={i} className="p-2.5 rounded-lg bg-white/[0.03] text-xs text-neutral-300 border border-white/5">
                          <div className="flex items-center justify-between text-[10px] font-bold text-indigo-300 mb-0.5">
                            <span>{c.author}</span>
                            <span className="text-white/40 font-normal">{c.time}</span>
                          </div>
                          <div>{c.text}</div>
                        </div>
                      ))}
                    </div>

                    <div className="flex items-center gap-2 pt-1">
                      <input
                        type="text"
                        value={commentText}
                        onChange={(e) => setCommentText(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleAddComment()}
                        placeholder="Escreva um comentário de revisão..."
                        className="flex-1 bg-white/[0.03] border border-white/5 rounded-xl px-3 py-2 text-xs text-[#ededed] focus:outline-none focus:border-indigo-500/50"
                      />
                      <button
                        onClick={handleAddComment}
                        className="px-3 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs"
                      >
                        <Send className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
