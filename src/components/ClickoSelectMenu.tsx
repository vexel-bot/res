import React from 'react';
import { Check, ChevronDown } from 'lucide-react';
import './ClickoSelectMenu.css';

export type ClickoSelectOption = readonly string[];

type ClickoSelectMenuProps = {
  label: string;
  value: string;
  options: readonly ClickoSelectOption[];
  onChange: (value: string) => void;
  className?: string;
  triggerClassName?: string;
  menuClassName?: string;
};

export function ClickoSelectMenu({ label, value, options, onChange, className = '', triggerClassName = '', menuClassName = '' }: ClickoSelectMenuProps) {
  const [open, setOpen] = React.useState(false);
  const rootRef = React.useRef<HTMLDivElement>(null);
  const optionRefs = React.useRef<Array<HTMLButtonElement | null>>([]);
  const menuId = React.useId();
  const selectedIndex = Math.max(0, options.findIndex(([id]) => id === value));
  const selectedName = options[selectedIndex]?.[1] || '';

  const close = React.useCallback((restoreFocus = false) => {
    setOpen(false);
    if (restoreFocus) rootRef.current?.querySelector<HTMLButtonElement>('.clicko-select-menu__trigger')?.focus({ preventScroll: true });
  }, []);

  React.useEffect(() => {
    if (!open) return;
    const closeOnOutside = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) close();
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') close(true);
    };
    document.addEventListener('mousedown', closeOnOutside);
    document.addEventListener('keydown', closeOnEscape);
    const viewport = window.visualViewport;
    const fitMenu = () => {
      const trigger = rootRef.current?.querySelector<HTMLElement>('.clicko-select-menu__trigger');
      if (!trigger || !rootRef.current) return;
      const bottom = (viewport?.offsetTop ?? 0) + (viewport?.height ?? window.innerHeight);
      rootRef.current.style.setProperty('--clicko-select-available-height', `${Math.max(44, bottom - trigger.getBoundingClientRect().bottom - 18)}px`);
    };
    const frame = requestAnimationFrame(() => {
      const trigger = rootRef.current?.querySelector<HTMLElement>('.clicko-select-menu__trigger');
      const bottom = (viewport?.offsetTop ?? 0) + (viewport?.height ?? window.innerHeight);
      if (trigger && bottom - trigger.getBoundingClientRect().bottom < 180) trigger.scrollIntoView({ block: 'center', behavior: 'instant' });
      fitMenu();
      optionRefs.current[selectedIndex]?.focus({ preventScroll: true });
      optionRefs.current[selectedIndex]?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    });
    window.addEventListener('resize', fitMenu);
    document.addEventListener('scroll', fitMenu, true);
    viewport?.addEventListener('resize', fitMenu);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('resize', fitMenu);
      document.removeEventListener('scroll', fitMenu, true);
      viewport?.removeEventListener('resize', fitMenu);
      document.removeEventListener('mousedown', closeOnOutside);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [close, open, selectedIndex]);

  const moveFocus = (index: number) => {
    if (!options.length) return;
    const next = (index + options.length) % options.length;
    optionRefs.current[next]?.focus({ preventScroll: true });
    optionRefs.current[next]?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  };

  return <div className={`clicko-select-menu ${className}`.trim()} ref={rootRef}>
    <span className="clicko-select-menu__label">{label}</span>
    <button
      type="button"
      className={`clicko-select-menu__trigger ${triggerClassName}`.trim()}
      aria-haspopup="listbox"
      aria-controls={menuId}
      aria-expanded={open}
      onClick={() => setOpen(current => !current)}
      onKeyDown={(event) => {
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
          event.preventDefault();
          setOpen(true);
        }
      }}
    >
      <span>{selectedName}</span><ChevronDown aria-hidden="true" />
    </button>
    {open && <div id={menuId} className={`clicko-select-menu__popover ${menuClassName}`.trim()} role="listbox" aria-label={label}>
      {options.map(([id, name], index) => <button
        ref={element => { optionRefs.current[index] = element; }}
        type="button"
        role="option"
        aria-selected={id === value}
        className="clicko-select-menu__option"
        onKeyDown={(event) => {
          if (event.key === 'ArrowDown') { event.preventDefault(); moveFocus(index + 1); }
          if (event.key === 'ArrowUp') { event.preventDefault(); moveFocus(index - 1); }
          if (event.key === 'Home') { event.preventDefault(); moveFocus(0); }
          if (event.key === 'End') { event.preventDefault(); moveFocus(options.length - 1); }
          if (event.key === 'Tab') close();
        }}
        onClick={() => { onChange(id); close(true); }}
        key={id}
      ><span>{name}</span>{id === value && <Check aria-hidden="true" />}</button>)}
    </div>}
  </div>;
}
