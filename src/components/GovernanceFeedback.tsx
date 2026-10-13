import React from 'react';
import { CheckCircle2, X, XCircle } from 'lucide-react';
import { useGovernance } from '../context/GovernanceContext';

export const GovernanceFeedback: React.FC = () => {
  const { feedback, clearFeedback } = useGovernance();
  React.useEffect(() => {
    if (!feedback) return;
    const timer = window.setTimeout(clearFeedback, 4200);
    return () => window.clearTimeout(timer);
  }, [feedback, clearFeedback]);
  if (!feedback) return null;
  return <div role="status" className={`fixed bottom-5 right-5 z-[120] flex max-w-[calc(100vw-40px)] items-start gap-3 rounded-xl border p-4 shadow-lg shadow-black/30 ${feedback.type === 'success' ? 'border-[#FF7F50]/15 bg-[rgba(128,128,128,0.14)]/95' : 'border-[#FF7F50]/15 bg-[rgba(128,128,128,0.14)]/95'}`}>{feedback.type === 'success' ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#FF7F50]" /> : <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-[#FF7F50]" />}<p className="text-[9px] leading-relaxed text-[rgba(255,255,255,0.88)]">{feedback.message}</p><button onClick={clearFeedback} className="ml-2 text-[#808080] hover:text-white"><X className="h-3.5 w-3.5" /></button></div>;
};
