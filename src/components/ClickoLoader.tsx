import './ClickoLoader.css';

type ClickoLoaderProps = {
  size?: 'tiny' | 'small' | 'medium' | 'large';
  context?: 'inline' | 'section' | 'page';
  tone?: 'auto' | 'dark' | 'light';
  label?: string;
  message?: string;
  className?: string;
};

/** The official Clicko symbol is the only visual loading indicator in the app. */
export function ClickoLoader({
  size = 'medium',
  context = 'inline',
  tone = 'auto',
  label = 'Carregando',
  message,
  className = '',
}: ClickoLoaderProps) {
  return <span className={`clicko-loader clicko-loader--${size} clicko-loader--${context} ${className}`} data-tone={tone} role="status" aria-label={label}>
    <span className="clicko-loader__symbol" aria-hidden="true" />
    {message && <span className="clicko-loader__message">{message}</span>}
  </span>;
}
