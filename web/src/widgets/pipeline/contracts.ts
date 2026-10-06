// View-only declarations from docs/pipelines/cinematic.md and the cited owner contracts.
// These descriptions do not register capabilities or compile/execute a pipeline.
// Storytell shows the request boundary directly; storytell:graph is backend orchestration.
import { isStoryApproved, statusLabel, type Projection, type WardrobeActivity } from '../../entities/execution/contracts';

export type NodeState = 'idle' | 'queued' | 'active' | 'review' | 'blocked' | 'done' | 'stopped';
// Work is durable stage activity, not proof of an in-flight provider call or a node trace.
export function storyNodeState(id: string, p?: Projection, activity?: WardrobeActivity): { state: NodeState; status?: string; reason?: string } {
  if (!p) return id === 'wardrobe' ? { state: 'idle', status: 'После approval Story' } : { state: 'idle' };
  if (id === 'brief' || id === 'storytell:start') return { state: 'done' };
  const handoff = p.graph.id === 'kinodel.story-wardrobe' && p.stories.some(s => s.current && isStoryApproved(p, s.ref));
  if (id.startsWith('wardrobe:')) {
    if (p.graph.id !== 'kinodel.story-wardrobe') return { state: 'idle', status: 'Не подключено' };
    if (id === 'wardrobe:start' && activity?.operation_id) return { state: 'done', status: 'Ввод подготовлен' };
    if (id === 'wardrobe:end' || id === 'wardrobe:output') return p.wardrobe_plan_ref ? { state: 'done', status: 'План сохранён' }
      : p.wardrobe_stop ? { state: 'blocked', status: 'План не сохранён', reason: p.wardrobe_stop.explanation }
      : ['cancelled', 'cancelling', 'failed'].includes(p.status) ? { state: 'stopped', status: 'План не сохранён' }
      : { state: 'idle', status: 'Ждём сохранённый план' };
    if (id === 'wardrobe:start') return p.wardrobe_stop ? { state: 'blocked', status: 'Ввод не подготовлен', reason: p.wardrobe_stop.explanation }
      : { state: 'idle', status: 'Ввод ещё не подготовлен' };
    return storyNodeState('wardrobe', p);
  }
  if (id === 'wardrobe' && p.graph.id === 'kinodel.story-wardrobe') {
    if (p.wardrobe_plan_ref) return { state: 'done', status: 'План сохранён · без рендера' };
    if (p.wardrobe_stop) return { state: 'blocked', status: 'Wardrobe приостановлен', reason: p.wardrobe_stop.explanation };
    if (['cancelled', 'cancelling', 'failed'].includes(p.status)) return { state: 'stopped', status: statusLabel[p.status] };
    if (!handoff) return { state: 'idle', status: 'После approval Story' };
    const work = p.work.find(w => w.kind === 'resume' && ['pending', 'claimed', 'blocked'].includes(w.status));
    if (!work) return { state: 'idle', status: 'Ждём работу Wardrobe' };
    return { state: work?.status === 'blocked' ? 'blocked' : work?.status === 'pending' ? 'queued' : 'active',
      status: work?.status === 'blocked' ? 'Wardrobe приостановлен' : work?.status === 'pending' ? 'План в очереди' : 'Подготовка плана' };
  }
  if (!['storytell', 'story-hitl', 'storytell:model', 'storytell:end', 'storytell:output'].includes(id)) return { state: 'idle' };
  if (handoff) return { state: 'done', status: id === 'storytell' || id === 'story-hitl' || id === 'storytell:output' ? 'Story утверждена' : 'Ответ сохранён' };
  const current = p.stories.find(s => s.current);
  const latestWork = [...p.work].reverse();
  const work = latestWork.find(w => w.kind !== 'cancel' && ['pending', 'claimed', 'blocked'].includes(w.status));
  const decision = p.reviews.find(r => r.work_id === work?.work_id && r.accepted);
  const action = work?.kind === 'start' && !current ? 'generate'
    : work?.kind === 'resume' && !decision?.result && (decision?.action === 'revise' || decision?.action === 'clarify') ? decision.action : undefined;
  const stopped = ['cancelled', 'cancelling', 'failed'].includes(p.status);
  const reason = latestWork.find(w => w.status === 'blocked')?.blocked_reason ?? undefined;
  const saved = !!current || p.reviews.some(r => r.result?.kind === 'owner_response');
  if (id === 'storytell') {
    if (stopped) return { state: 'stopped', status: statusLabel[p.status] };
    if (p.status === 'completed') return { state: 'done' };
    if (p.status === 'blocked') return { state: 'blocked', reason };
    if (work?.status === 'pending') return { state: 'queued', status: 'В очереди' };
    if (work?.status === 'claimed') return { state: 'active', status: action === 'clarify' ? 'Ответ на вопрос' : action === 'revise' ? 'Правка в работе' : action === 'generate' ? 'Генерация в работе' : 'Применяем состояние' };
    return { state: p.review ? 'review' : 'idle' };
  }
  if (id === 'storytell:model') {
    if (!['kinodel.live-story', 'kinodel.story-wardrobe'].includes(p.graph.id)) return { state: 'idle' };
    if (stopped) return { state: 'stopped', status: statusLabel[p.status] };
    if (p.status !== 'completed' && action) {
      if (p.status === 'blocked') return { state: 'blocked', status: 'Работа заблокирована', reason };
      if (work?.status === 'pending') return { state: 'queued', status: 'Запрос в очереди' };
      if (work?.status === 'claimed') return { state: 'active', status: action === 'clarify' ? 'Ответ на вопрос' : action === 'revise' ? 'Правка в работе' : 'Генерация в работе' };
    }
    return saved ? { state: 'done', status: 'Ответ сохранён' } : { state: 'idle' };
  }
  if (id === 'storytell:end') {
    if (!stopped && action) return { state: 'idle', status: 'Ждём ответ' };
    return saved ? { state: 'done', status: 'Ответ сохранён' } : { state: 'idle', status: 'Нет сохранённого ответа' };
  }
  return current && p.review && !stopped && p.status !== 'completed' ? { state: 'review', status: 'Ваше решение' }
    : current ? { state: 'done' } : { state: 'idle' };
}

export const scopes = ['pipeline', 'storytell', 'wardrobe', 'wardrobe:request', 'storyboard', 'filmmaker', 'montage', 'storytell:graph'] as const;
export type Scope = typeof scopes[number];
export type StageContract = {
  id: string; title: string; kind: 'input' | 'agent' | 'tool' | 'review' | 'output' | 'internal';
  summary: string; inputs: string[]; outputs: string[]; config: string; source: string;
};
const cinematic = 'docs/pipelines/cinematic.md';
export const stages: Record<string, StageContract> = {
   brief: { id: 'brief', title: 'Brief', kind: 'input', summary: 'Идея, контекст и настройки', inputs: ['Идея автора', 'Явные references и видимые production settings'], outputs: ['brief · неизменяемый submitted ввод'], config: 'Ввод фиксируется при Start. Подключён текстовый Storytell, не полный cinematic Brief.', source: cinematic },
  storytell: { id: 'storytell', title: 'Storytell', kind: 'agent', summary: 'История и действия шотов', inputs: ['Submitted brief', 'Выбранный narrative context', 'При правке: exact previous Story и feedback'], outputs: ['story · StoryV1: hook, story, ordered shots'], config: 'Создаёт историю, не image/video prompts. Tools: обычно нет. Один bounded structured response, без придуманного model/tool-loop.', source: 'docs/agents/storytell.md' },
    'story-hitl': { id: 'story-hitl', title: 'Проверка истории', kind: 'review', summary: 'Ваше решение о сохранённой истории', inputs: ['Текущая exact Story revision'], outputs: ['Та же Story с exact approval'], config: 'Утверждается только открытая точная версия. Вопрос/правка адресуются Storytell. Story-Wardrobe передаёт approved Story в Wardrobe; исторический text route завершает Story.', source: cinematic },
  wardrobe: { id: 'wardrobe', title: 'Wardrobe', kind: 'agent', summary: 'Визуальные опоры и промпты', inputs: ['Brief', 'Approved story', 'Character/style references с явными ролями'], outputs: ['wardrobe_plan · VisualAnchorPlanV1: direction, anchor units, prompts, dependencies'], config: 'План сохраняется перед anchor-gen. Агент не ждёт рендера, не выбирает provider и не утверждает anchors. Отдельного plan gate нет.', source: 'docs/agents/wardrobe.md' },
  'anchor-gen': { id: 'anchor-gen', title: 'Anchor generation', kind: 'tool', summary: 'Варианты визуальных опор', inputs: ['Exact wardrobe_plan', 'Exact reference images и зависимости units', 'Закреплённый image profile'], outputs: ['Anchor image attempts · candidates', 'anchor_frames · выбранный полный набор после review'], config: 'Единственный writer anchor_frames. Новый face требует нового зависимого sheet; независимая location сохраняется. Provider не подключён.', source: 'docs/tools/comfyui-tool.md' },
  'anchor-hitl': { id: 'anchor-hitl', title: 'Anchor review', kind: 'review', summary: 'Выбор полного набора', inputs: ['Полный текущий anchor set', 'Exact wardrobe_plan и lineage'], outputs: ['Approved anchor_frames'], config: 'Exactly one candidate на каждый required unit. Несовместимые face/sheet отвергаются. Правка → Wardrobe; seed-only regeneration → tool. Approval открывает Storyboard только в cinematic.', source: cinematic },
  storyboard: { id: 'storyboard', title: 'Storyboard', kind: 'agent', summary: 'Начальный кадр каждого шота', inputs: ['Brief', 'Approved story', 'Exact wardrobe_plan', 'Approved anchor_frames'], outputs: ['storyboard_plan · FramePlanV1: start-frame prompts и reference bindings'], config: 'Один start frame на Story shot, в том же порядке. Показывает начало действия, не его финал. Следующий tool: frames-gen; не переписывает approved ancestors.', source: 'docs/agents/storyboard.md' },
  'frames-gen': { id: 'frames-gen', title: 'Frame generation', kind: 'tool', summary: 'Варианты начальных кадров', inputs: ['Exact storyboard_plan', 'Exact anchor_frames с обязательными ролями', 'Закреплённый image profile'], outputs: ['Frame attempts · candidates', 'story_frames · выбранные frames после review'], config: 'Все required reference roles должны дойти до workflow. Недостаточная multi-image capacity блокирует submit. Единственный writer story_frames. Provider не подключён.', source: 'docs/tools/comfyui-tool.md' },
  'frames-hitl': { id: 'frames-hitl', title: 'Frame review', kind: 'review', summary: 'Проверка всех start frames', inputs: ['Полный текущий frame set', 'Exact storyboard_plan'], outputs: ['Approved story_frames'], config: 'Один frame на каждый Story shot. Правка адресуется Storyboard и возвращается через frames-gen. Approved Story/anchors не меняются.', source: cinematic },
  filmmaker: { id: 'filmmaker', title: 'Filmmaker', kind: 'agent', summary: 'Движение внутри шотов', inputs: ['Brief', 'Approved story в исходном порядке', 'Exact approved story_frames'], outputs: ['video_plan · MotionPlanV1: motion, start image, duration для каждого shot'], config: 'Silent i2v: каждый clip начинается с exact approved frame. Без скрытых cuts, soundtrack или замены start image. Следующий tool: video-gen.', source: 'docs/agents/filmmaker.md' },
  'video-gen': { id: 'video-gen', title: 'Video generation', kind: 'tool', summary: 'Видеодубли каждого шота', inputs: ['Exact video_plan', 'Exact story_frames как start images', 'Закреплённый video profile'], outputs: ['Video attempts · candidates', 'shot_videos · выбранный набор после review'], config: 'Один video на каждый Story shot, без пропусков. Reference conditioning не доказывает i2v; start-frame mapping требует проверки. Единственный writer shot_videos. Provider не подключён.', source: 'docs/tools/comfyui-tool.md' },
  'video-hitl': { id: 'video-hitl', title: 'Video review', kind: 'review', summary: 'Проверка всех видеошотов', inputs: ['Полный текущий video set', 'Exact video_plan'], outputs: ['Approved shot_videos'], config: 'Правка адресуется Filmmaker → video-gen → video-hitl. Наличие файла не означает approval. Только полный approved набор передаётся Montage.', source: cinematic },
  montage: { id: 'montage', title: 'Сборка', kind: 'tool', summary: 'Клипы в порядке истории', inputs: ['Approved shot_videos', 'Approved Story shot order', 'Brief output settings и measured metadata'], outputs: ['final_video · MontageResultV1 с provenance'], config: 'Детерминированный ffmpeg tool: все full clips, simple cuts, supported normalization, remove audio. Internal MontagePlanV1 закрепляет exact sources; не новый агент или gate.', source: 'docs/tools/montage.md' },
  'view:montage-output': { id: 'view:montage-output', title: 'Проверенный файл', kind: 'output', summary: 'Размер, длительность, silent', inputs: ['Собранный файл Montage'], outputs: ['Технически проверенный immutable final_video'], config: 'ffprobe проверяет bytes/format, dimensions, duration и отсутствие audio streams. Проверка — часть montage tool, не отдельный runtime stage или human approval.', source: 'docs/tools/montage.md' },
  final: { id: 'final', title: 'Final', kind: 'output', summary: 'Готовое видео для просмотра', inputs: ['final_video · verified Montage result'], outputs: ['Просмотр / download после появления реального файла'], config: 'Поверхность выхода Montage. Не новый агент и не final HITL. Файл не создан; player/download пока недоступны.', source: cinematic },
};
export const groups = [
  { id: 'brief', title: 'Brief', stages: ['brief'] },
  { id: 'storytell', title: 'Storytell', stages: ['storytell', 'story-hitl'] },
  { id: 'wardrobe', title: 'Wardrobe', stages: ['wardrobe', 'anchor-gen', 'anchor-hitl'] },
  { id: 'storyboard', title: 'Storyboard', stages: ['storyboard', 'frames-gen', 'frames-hitl'] },
  { id: 'filmmaker', title: 'Filmmaker', stages: ['filmmaker', 'video-gen', 'video-hitl'] },
  { id: 'montage', title: 'Montage', stages: ['montage', 'view:montage-output'] },
  { id: 'final', title: 'Final', stages: ['final'] },
] as const;
// Declared request diagram, never an execution trace. Tools are not connected.
export const storyRequest: StageContract[] = [
  { id: 'storytell:start', title: 'START', kind: 'input', summary: 'Сохранённый ввод → messages', inputs: ['Frozen submitted idea, shots, subjects'], outputs: ['Prepared messages'], config: 'Точные входы закреплены на запуске. При вопросе/правке базовый запрос доступен у Model.', source: 'backend/openrouter.py:produce_live_story' },
  { id: 'storytell:model', title: 'Model', kind: 'agent', summary: 'System prompt + messages', inputs: ['Frozen system prompt', 'Saved base request messages'], outputs: ['Structured response'], config: 'Один bounded structured request с ограниченным исправлением формата. У fixture нет LLM-вызова или системного промпта.', source: 'backend/openrouter.py:produce_live_story' },
  { id: 'storytell:end', title: 'END', kind: 'output', summary: 'Ответ → validation / save', inputs: ['Structured response'], outputs: ['Validated saved Story или owner response'], config: 'Граница запроса, не human approval и не END производственного графа. Валидация и сохранение выполняются backend за этой границей; вопрос может сохранить только объяснение.', source: 'backend/story_graph.py:story' },
  { id: 'storytell:output', title: 'Story', kind: 'output', summary: 'Сохранённый результат', inputs: ['Exact immutable Story ref'], outputs: ['Story reader · версии и exact review'], config: 'Существование Story не означает approval. Общий reader сохраняет выбранную версию и адресный черновик.', source: 'docs/agents/storytell.md' },
  { id: 'storytell:tools', title: 'ToolNode', kind: 'tool', summary: 'Optional · без связей и вызовов', inputs: [], outputs: [], config: 'Не подключён. В текущем Storytell нет tools, tool calls или tool-loop. Это отключённый элемент объявленной схемы, не выполненная ветка и не runtime capability.', source: 'docs/agents/storytell.md#tools' },
];
export const wardrobeRequest: StageContract[] = [
  { id: 'wardrobe:start', title: 'START', kind: 'input', summary: 'Approved Story + Character evidence', inputs: ['Exact approved Story', 'Frozen narrative, ordered Character text and labelled original images'], outputs: ['Prepared messages'], config: 'Вход закрепляется при Wardrobe preparation после exact approval Story. Нет подмены latest или пропуска изображений.', source: 'backend/wardrobe_operation.py:produce_wardrobe_operation' },
  { id: 'wardrobe:model', title: 'Model', kind: 'agent', summary: 'System prompt + messages', inputs: ['Frozen system prompt', 'Prepared messages с ordered image labels'], outputs: ['Structured response'], config: 'Закреплённая модель появляется только после preparation. Durable работа не доказывает HTTP в полёте; максимум две зарезервированные попытки, включая одно исправление формата.', source: 'backend/openrouter_wardrobe.py:complete_wardrobe' },
  { id: 'wardrobe:end', title: 'END', kind: 'output', summary: 'Ответ → validation / save', inputs: ['Structured response'], outputs: ['Validated saved plan или объяснение остановки'], config: 'Граница запроса: backend проверяет и сохраняет результат. Это не human approval, не рендер и не trace внутренних шагов.', source: 'backend/wardrobe_operation.py:produce_wardrobe_operation' },
  { id: 'wardrobe:output', title: 'Plan', kind: 'output', summary: 'Сохранённый wardrobe_plan', inputs: ['Exact immutable wardrobe_plan ref'], outputs: ['Полные prompts и ordered dependencies'], config: 'Validated supporting plan без отдельного approval. Anchor generation и review ещё не подключены.', source: 'docs/agents/wardrobe.md' },
];
// Authored source structure, not an execution/checkpoint trace. backend/story_graph.py.
export const internalStory: StageContract[] = [
  { id: '__start__', title: 'START', kind: 'internal', summary: 'Вход внутреннего графа', inputs: ['Project / execution identity, story_activation'], outputs: ['StoryState → storytell'], config: 'initial_story_state: compact refs/identities; graph state не содержит body или media.', source: 'backend/story_graph.py:initial_story_state' },
  { id: 'storytell', title: 'storytell', kind: 'internal', summary: 'Prepare → owner → commit', inputs: ['Frozen test input, shots', 'Previous Story / feedback / discussion при resume'], outputs: ['Exact story_ref / binding_revision или owner_response'], config: 'prepare_story_operation возвращает committed replay; иначе bounded produce_story и validated commit. Это функция story, не model/tool-loop.', source: 'backend/story_graph.py:story' },
  { id: 'story_prepare_review', title: 'story_prepare_review', kind: 'internal', summary: 'Подготовка exact request', inputs: ['story_ref, binding_revision'], outputs: ['review_ref: request_id, revision, digest, binding_revision'], config: 'prepare_story_review создаёт или возвращает сохранённый exact request.', source: 'backend/story_graph.py:prepare' },
  { id: 'story_wait', title: 'story_wait', kind: 'internal', summary: 'interrupt(review_ref)', inputs: ['Exact review_ref'], outputs: ['Durable decision_id после resume'], config: 'До interrupt нет side effects. Node replays при resume; decision reference валидируется.', source: 'backend/story_graph.py:wait' },
  { id: 'story_apply', title: 'story_apply', kind: 'internal', summary: 'Применение решения', inputs: ['request_id и совпадающий decision_id'], outputs: ['Approve → END', 'Clarify / revise → storytell'], config: 'apply_story_decision применяет exact решение. Command маршрутизирует: approve → __end__; clarify/revise → storytell. Никогда Wardrobe.', source: 'backend/story_graph.py:apply' },
  { id: '__end__', title: 'END', kind: 'internal', summary: 'Только Story fixture', inputs: ['approved_story · exact story_ref'], outputs: ['Завершение internal Story'], config: 'END завершает kinodel.internal-story. Не продолжает cinematic и не создаёт media.', source: 'backend/story_graph.py:build_story_graph' },
];
