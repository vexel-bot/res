import React from 'react';
import {
  BookOpen,
  ChevronDown,
  ExternalLink,
  FileText,
  HelpCircle,
  Info,
  LifeBuoy,
  Scale,
  Search,
  ShieldCheck,
} from 'lucide-react';
import {
  LEGAL_UPDATED_AT,
  LEGAL_VERSION,
  SUPPORT_CONTACT_URL,
  supportDocuments,
  supportFaqs,
} from '../data/supportContent';

const normalize = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR');

export const SupportCenterView: React.FC = () => {
  const [query, setQuery] = React.useState('');
  const normalizedQuery = normalize(query.trim());
  const documents = React.useMemo(() => supportDocuments.filter((document) => {
    if (!normalizedQuery) return true;
    const body = document.sections.flatMap((section) => [section.title, ...(section.paragraphs || []), ...(section.items || [])]);
    return normalize([document.title, document.summary, ...body].join(' ')).includes(normalizedQuery);
  }), [normalizedQuery]);
  const faqs = React.useMemo(() => supportFaqs.filter((faq) => !normalizedQuery || normalize(`${faq.category} ${faq.question} ${faq.answer}`).includes(normalizedQuery)), [normalizedQuery]);
  const hasResults = documents.length > 0 || faqs.length > 0;
  const environmentLabel = ['localhost', '127.0.0.1'].includes(window.location.hostname) ? 'Desenvolvimento' : 'Produção';

  return (
    <div className="clicko-support-center">
      <section className="clicko-support-intro" aria-labelledby="support-intro-title">
        <div className="clicko-support-intro-copy">
          <span className="clicko-support-eyebrow"><LifeBuoy aria-hidden="true" />Central da Clicko</span>
          <h3 id="support-intro-title">Ajuda, documentos e atendimento em um só lugar.</h3>
          <p>Consulte orientações de uso, termos, políticas e respostas para as principais dúvidas sobre a plataforma.</p>
        </div>
        <div className="clicko-support-contact-card">
          <span className="clicko-support-icon" aria-hidden="true"><ShieldCheck /></span>
          <div>
            <strong>Suporte realizado pela VEXEL</strong>
            <p>A Clicko é uma plataforma desenvolvida pela VEXEL. Nosso time atende dúvidas técnicas, operacionais e institucionais.</p>
          </div>
          <a href={SUPPORT_CONTACT_URL} target="_blank" rel="noopener noreferrer" className="clicko-support-primary-link">
            Falar com o suporte <ExternalLink aria-hidden="true" />
          </a>
        </div>
      </section>

      <nav className="clicko-support-shortcuts" aria-label="Seções da central de ajuda">
        <a href="#support-legal"><Scale aria-hidden="true" /><span>Termos e políticas</span></a>
        <a href="#support-faq"><HelpCircle aria-hidden="true" /><span>Dúvidas frequentes</span></a>
        <a href="#support-about"><Info aria-hidden="true" /><span>Sobre a Clicko</span></a>
      </nav>

      <label className="clicko-support-search">
        <Search aria-hidden="true" />
        <span className="sr-only">Pesquisar na central de ajuda</span>
        <input value={query} onChange={(event) => setQuery(event.target.value)} type="search" placeholder="Pesquisar termos, políticas ou dúvidas" />
      </label>

      {!hasResults && (
        <div className="clicko-support-empty" role="status">
          <Search aria-hidden="true" />
          <strong>Nenhum resultado encontrado</strong>
          <p>Tente uma palavra diferente ou limpe a pesquisa.</p>
          <button type="button" onClick={() => setQuery('')}>Limpar pesquisa</button>
        </div>
      )}

      {documents.length > 0 && (
        <section id="support-legal" className="clicko-support-section" aria-labelledby="support-legal-title">
          <header>
            <div><span>Documentos</span><h3 id="support-legal-title">Termos e Políticas</h3></div>
            <p>Abra um documento para consultar seu conteúdo completo.</p>
          </header>
          <div className="clicko-support-document-list">
            {documents.map((document) => (
              <details key={document.id} className="clicko-support-disclosure">
                <summary>
                  <span className="clicko-support-document-icon" aria-hidden="true"><FileText /></span>
                  <span className="clicko-support-document-copy">
                    <strong>{document.title}</strong>
                    <small>{document.summary}</small>
                  </span>
                  <span className="clicko-support-document-meta">v{document.version}<small>{document.updatedAt}</small></span>
                  <ChevronDown className="clicko-support-chevron" aria-hidden="true" />
                </summary>
                <div className="clicko-support-document-body">
                  <div className="clicko-support-document-notice">
                    <BookOpen aria-hidden="true" />
                    <p>Documento institucional da Clicko. O conteúdo pode ser atualizado para refletir mudanças legais, operacionais ou da plataforma.</p>
                  </div>
                  {document.sections.map((section) => (
                    <section key={section.title}>
                      <h4>{section.title}</h4>
                      {section.paragraphs?.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
                      {!!section.items?.length && <ul>{section.items.map((item) => <li key={item}>{item}</li>)}</ul>}
                    </section>
                  ))}
                  <footer><span>Versão {document.version}</span><span>{document.acceptance === 'required-on-material-change' ? 'Novo aceite previsto para alterações materiais' : 'Documento informativo'}</span><span>Última atualização: {document.updatedAt}</span></footer>
                </div>
              </details>
            ))}
          </div>
        </section>
      )}

      {faqs.length > 0 && (
        <section id="support-faq" className="clicko-support-section" aria-labelledby="support-faq-title">
          <header>
            <div><span>Orientação</span><h3 id="support-faq-title">Dúvidas Frequentes</h3></div>
            <p>Respostas diretas sobre o uso cotidiano da Clicko.</p>
          </header>
          <div className="clicko-support-faq-list">
            {faqs.map((faq) => (
              <details key={faq.id} className="clicko-support-disclosure clicko-support-faq">
                <summary>
                  <span className="clicko-support-faq-category">{faq.category}</span>
                  <strong>{faq.question}</strong>
                  <ChevronDown className="clicko-support-chevron" aria-hidden="true" />
                </summary>
                <p>{faq.answer}</p>
              </details>
            ))}
          </div>
        </section>
      )}

      {!normalizedQuery && (
        <section id="support-about" className="clicko-support-section" aria-labelledby="support-about-title">
          <header>
            <div><span>Institucional</span><h3 id="support-about-title">Sobre a Clicko</h3></div>
          </header>
          <div className="clicko-support-about-grid">
            <article>
              <span className="clicko-support-icon" aria-hidden="true"><Info /></span>
              <h4>Clicko Studios</h4>
              <p>Uma plataforma para organizar a operação de conteúdo, conectar planejamento, criação, colaboração, publicação e análise em uma experiência integrada.</p>
              <strong>Clicko — Desenvolvido pela VEXEL</strong>
            </article>
            <article>
              <span className="clicko-support-icon" aria-hidden="true"><ShieldCheck /></span>
              <h4>Informações do sistema</h4>
              <dl>
                <div><dt>Versão da Clicko</dt><dd>Beta 2026.09</dd></div>
                <div><dt>Versão dos termos</dt><dd>{LEGAL_VERSION}</dd></div>
                <div><dt>Atualização dos termos</dt><dd>{LEGAL_UPDATED_AT}</dd></div>
                <div><dt>Ambiente</dt><dd>{environmentLabel}</dd></div>
              </dl>
            </article>
          </div>
          <div className="clicko-support-institutional-links">
            <a href={SUPPORT_CONTACT_URL} target="_blank" rel="noopener noreferrer">Contato e suporte VEXEL <ExternalLink aria-hidden="true" /></a>
            <span>Powered by VEXEL</span>
          </div>
        </section>
      )}
    </div>
  );
};
