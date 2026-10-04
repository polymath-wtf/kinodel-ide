import { useEffect, useRef, useState } from 'react';

export function SuccessToast({ text, close }: { text: string; close: () => void }) {
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const remaining = useRef(4000);
  const dismiss = useRef(close); dismiss.current = close;
  useEffect(() => {
    if (hovered || focused) return;
    const started = performance.now();
    const timer = window.setTimeout(() => dismiss.current(), remaining.current);
    return () => { clearTimeout(timer); remaining.current = Math.max(0, remaining.current - (performance.now() - started)); };
  }, [hovered, focused]);
  return <aside className="success-toast" onPointerOver={() => setHovered(true)} onPointerOut={event => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setHovered(false); }}
    onFocusCapture={() => setFocused(true)} onBlurCapture={event => { if (!event.currentTarget.contains(event.relatedTarget)) setFocused(false); }}>
    <p role="status" aria-live="polite" aria-atomic="true">{text}</p>
    <button type="button" aria-label="Закрыть уведомление" onClick={close}>×</button>
  </aside>;
}
