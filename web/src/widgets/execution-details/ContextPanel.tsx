import { useEffect, useRef, type ReactNode } from 'react';

// The two contextual readers share native presentation, not their subject/state ownership.
export function ContextPanel({ title, className, opener, close, children }: { title: string; className: string; opener: HTMLElement | null; close: () => void; children: ReactNode }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialog.current!;
    const narrow = window.matchMedia('(max-width: 1279px)');
    const present = () => {
      const focused = document.activeElement instanceof HTMLElement && element.contains(document.activeElement) ? document.activeElement : null;
      element.close();
      if (narrow.matches) element.showModal(); else element.show();
      (focused ?? element.querySelector<HTMLButtonElement>('.context-close'))?.focus({ preventScroll: true });
    };
    present(); narrow.addEventListener('change', present);
    return () => { narrow.removeEventListener('change', present); element.close(); };
  }, []);
  const dismiss = () => {
    dialog.current?.close();
    if (opener?.isConnected) opener.focus({ preventScroll: true });
    close();
  };
  return <dialog ref={dialog} className={`context-panel ${className}`} aria-label={title}
    onCancel={event => { event.preventDefault(); dismiss(); }} onClick={event => { if (event.target === dialog.current) dismiss(); }}
    onKeyDown={event => {
      if (event.key === 'Escape') {
        event.preventDefault(); // Also suppress native dialog cancellation while a shell menu owns Escape.
        if (!document.querySelector('.shell-menu, .topbar .run-controls[open]')) { event.stopPropagation(); dismiss(); }
      }
      if (event.key === 'Tab' && dialog.current?.matches(':modal')) {
        const stops = [...dialog.current.querySelectorAll<HTMLElement>('button:not(:disabled), summary, a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])')].filter(e => e.getClientRects().length);
        const first = stops[0], last = stops.at(-1);
        if (event.shiftKey && document.activeElement === first || !event.shiftKey && document.activeElement === last) {
          event.preventDefault(); (event.shiftKey ? last : first)?.focus({ preventScroll: true });
        }
      }
    }}>
    <header className="card-header"><h2>{title}</h2><button className="context-close details-close" autoFocus onClick={dismiss}>Закрыть</button></header>
    {children}
  </dialog>;
}
