import { useState } from 'react';
import { Clapperboard, MessagesSquare, Route, Sparkles } from 'lucide-react';

type View = 'pipeline' | 'chat';

export function Workspace() {
  const [view, setView] = useState<View>(() => window.matchMedia('(max-width: 767px)').matches ? 'chat' : 'pipeline');
  const choose = (next: View) => setView(next);

  return <div className="shell">
    <header className="topbar">
      <strong className="brand">KINODEL</strong>
      <span className="project-name">Рабочее пространство</span>
      <nav className="breadcrumbs" aria-label="Путь"><span>Проект</span><span aria-hidden="true">/</span><span aria-current="page">Story</span></nav>
      <span className="model-badge">Story foundation · тестовая модель</span>
      <div className="view-switch" aria-label="Вид рабочего пространства">
        <button type="button" aria-pressed={view === 'pipeline'} onClick={() => choose('pipeline')}>Pipeline</button>
        <button type="button" aria-pressed={view === 'chat'} onClick={() => choose('chat')}>Chat</button>
      </div>
    </header>
    <nav className="rail" aria-label="Разделы">
      <button type="button" aria-current={view === 'pipeline' ? 'page' : undefined} onClick={() => choose('pipeline')}><Route aria-hidden="true" />Pipeline</button>
      <button type="button" aria-current={view === 'chat' ? 'page' : undefined} onClick={() => choose('chat')}><MessagesSquare aria-hidden="true" />Chat</button>
      <span className="rail-divider" />
      <span className="rail-soon"><Clapperboard aria-hidden="true" />Canvas<small>Позже</small></span>
      <span className="rail-foot" aria-hidden="true">K</span>
    </nav>
    <main className="workspace">
      {view === 'pipeline' ? <section className="workspace-content" aria-labelledby="page-title">
        <div className="surface-title"><span className="eyebrow">01 / PRODUCTION</span><h1 id="page-title">Pipeline</h1><p>Здесь появится сохранённый путь от вашего ввода к версии Story и решению.</p></div>
        <div className="stage-line" aria-label="Этапы рабочего процесса">
          <article className="stage stage-input"><span className="stage-icon"><Sparkles aria-hidden="true" /></span><span className="eyebrow">ВВОД · ПОКА НЕТ ЗАПУСКА</span><h2>Ваша идея</h2><p>Запуск из интерфейса станет доступен после подключения команд.</p></article>
          <span className="stage-arrow" aria-hidden="true">→</span>
          <article className="stage stage-agent"><span className="stage-icon"><Route aria-hidden="true" /></span><span className="eyebrow">АГЕНТ · НЕ ЗАПУЩЕН</span><h2>Storytell</h2><p>Результат, версия и review появятся только из сохранённого запуска.</p></article>
        </div>
        <p className="workspace-footnote">Только Story foundation. Следующие этапы cinematic пока не подключены.</p>
      </section> : <section className="chat-content" aria-labelledby="page-title">
        <div className="surface-title"><span className="eyebrow">01 / CONVERSATION</span><h1 id="page-title">Chat</h1><p>История обсуждения будет показана из сохранённых решений, без имитации ответа агента.</p></div>
        <div className="chat-empty"><MessagesSquare aria-hidden="true" /><h2>Истории пока нет</h2><p>Откройте сохранённый запуск, когда подключится чтение Story. Сообщения и решения здесь пока недоступны.</p></div>
      </section>}
      <aside className="readiness" role="status"><span className="readiness-dot" aria-hidden="true" />Пустое пространство · чтение запусков и действия ещё не подключены</aside>
    </main>
  </div>;
}
