import React from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './KlicMarkdown.css';
const plugins=[remarkGfm];
export const KlicMarkdown=React.memo(function KlicMarkdown({content}:{content:string}) {
  return <div className="klic-markdown"><Markdown remarkPlugins={plugins} skipHtml components={{
    a:({href,children})=>href?<a href={href} target="_blank" rel="noopener noreferrer">{children}</a>:<span>{children}</span>,
    img:()=>null,
    table:({children})=><div className="klic-table-scroll"><table>{children}</table></div>,
  }}>{content}</Markdown></div>;
});
