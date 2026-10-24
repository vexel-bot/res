import './CreativeFeedback.css';
import { ClickoLoader } from './ClickoLoader';

type CreativeLoadingStateProps = {
  label: string;
  variant: 'decisions' | 'table';
};

export function CreativeLoadingState({ label, variant }: CreativeLoadingStateProps) {
  return <section className={`cw-loading-state cw-loading-state--${variant}`}>
    <ClickoLoader context="section" label={label} message={label} />
  </section>;
}
