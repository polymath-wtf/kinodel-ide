// View-only standalone demo: positions and navigation are local UI state, never pipeline execution.
const idea = 'Mira returns to a quiet island before the last ferry. She finds the lighthouse dark, but sees a light move inside.';
const groups = {
  storytell: {
    title: 'Storytell', stages: ['storytell', 'story-hitl'], result: 'story v2',
    agent: 'Storytell agent', status: 'Approved',
    inputs: 'Submitted brief · The Magic begin\nSelected narrative context · example only',
    prompt: 'Write a restrained two-shot story. S01: Mira arrives on the island and notices the dark lighthouse. S02: she follows a moving light toward its door. Preserve her location and intention between shots.',
    output: 'Story v2\nS01 · Arrival — Mira steps off the ferry. State after: she sees a light in the lighthouse.\nS02 · Approach — Mira crosses the shore and stops at the closed door. State after: the light moves upstairs.'
  },
  wardrobe: {
    title: 'Wardrobe', stages: ['wardrobe', 'anchor-gen', 'anchor-hitl'], result: 'wardrobe_plan',
    agent: 'Wardrobe agent', status: 'Needs review',
    inputs: 'Submitted brief + approved story v2\nCharacter/style references: Mira · coastal island · worn practical clothing',
    prompt: 'Keep Mira recognisable across both shots: dark bob, ochre raincoat, canvas satchel, sea spray. Generate hero_face first; derive hero_sheet from that exact portrait. Generate an empty island location independently.',
    output: 'wardrobe_plan\nhero_face: weathered close portrait, dark bob, natural daylight.\nhero_sheet: same face, ochre raincoat and canvas satchel. Parent: hero_face.\nlocation: empty grey coastline with the distant lighthouse; no character.'
  },
  storyboard: {
    title: 'Storyboard', stages: ['storyboard', 'frames-gen', 'frames-hitl'], result: 'storyboard_plan',
    agent: 'Storyboard agent', status: 'Waiting on anchors',
    inputs: 'Submitted brief + approved Story v2 + Wardrobe plan + approved anchor frames\nFace, sheet and location references by role',
    prompt: 'One start frame per shot, before its action unfolds. S01: wide pier, Mira has just stepped ashore, dark lighthouse far away; face + outfit + coastline refs. S02: Mira stands at the beginning of the shoreline path, before approaching the door.',
    output: 'storyboard_plan · example only\nS01 start frame: Wide static composition. Mira on the wet pier, lighthouse a small dark silhouette.\nS02 start frame: Medium rear three-quarter view at the start of the path; no open door and no completed turn.'
  },
  filmmaker: {
    title: 'Filmmaker', stages: ['filmmaker', 'video-gen', 'video-hitl'], result: 'video_plan',
    agent: 'Filmmaker agent', status: 'Waiting on frames',
    inputs: 'Submitted brief + approved Story v2 + exact approved start frame for each shot (required)',
    prompt: 'S01 motion prompt: begin from the exact pier start frame; Mira steps forward, wind lifts her coat, then she notices a light inside the dark lighthouse. 6s, restrained camera. S02: begin from the exact path start frame; follow Mira slowly until she stops at the closed door. 6s.',
    output: 'video_plan · example only\nS01 · start image = approved s01 frame · 6s.\nS02 · start image = approved s02 frame · 6s.\nOne clip per Story shot, same order; no invented final approval.'
  }
};

const scopes = {};
const systemPrompts = {
  storytell: 'You are Storytell. Turn the prepared brief into an ordered story with explicit shot actions and continuity. Return the requested story schema.',
  wardrobe: 'You are Wardrobe. Plan consistent character and location anchors from the approved story. Preserve reference identity and return the wardrobe plan schema.',
  storyboard: 'You are Storyboard. Plan one start frame per shot using approved anchors. Describe the opening state before action and return the storyboard plan schema.',
  filmmaker: 'You are Filmmaker. Plan silent motion from each exact approved start frame. Preserve shot order and return the video plan schema.'
};
const n = (id, title, status, x, y, extra = {}) => ({ id, title, status, x, y, kind: 'Stage', ...extra });
const ports = (inputs = [], outputs = []) => ({ inputs, outputs });
const productionForMedia = { anchors: 'wardrobe', frames: 'storyboard', videos: 'filmmaker' };
const path = ['Brief', 'Storytell', 'Wardrobe', 'Storyboard', 'Filmmaker', 'Montage', 'Final'];
// L0 summarizes boundaries; route arrows below are approval order, not artifact wires.
const pipelinePorts = [ports([], ['brief']), ports(['brief'], ['story']),
  ports(['brief', 'story'], ['wardrobe plan', 'anchor frames']),
  ports(['brief', 'story', 'wardrobe plan', 'anchor frames'], ['storyboard plan', 'story frames']),
  ports(['brief', 'story', 'story frames'], ['video plan', 'shot videos']),
  ports(['brief', 'story', 'shot videos'], ['final video']), ports(['final video'])];
const outer = path.map((title, index) => {
  const id = title.toLowerCase();
  const detail = groups[id] ? [['Stages', groups[id].stages.join(' → ')], ['Example result', groups[id].output]]
    : id === 'brief' ? [['Submitted idea', idea]]
    : id === 'montage' ? [['Inputs', 'Approved shot videos in Story order'], ['Result', 'Verified silent final video; not yet available in this example.']]
    : [['Result', 'The verified Montage video appears here; no extra approval gate.']];
  return n(id, title, ['Submitted', 'Approved', 'Needs review', 'Waiting on anchors', 'Waiting on frames', 'Waiting on clips', 'Waiting on montage'][index],
     24 + index * 213, 195, { kind: 'Production stage', inside: id, detail, ports: pipelinePorts[index] });
});
scopes.pipeline = { title: 'Pipeline', hint: '', nodes: outer,
  edges: path.slice(1).map((title, i) => [path[i].toLowerCase(), title.toLowerCase(), null, null, 'route']) };

const media = [
  n('hero_face', 'Portrait', 'Candidate', 443, 495, { kind: 'Anchor image', image: '../assets/portrait.jpg', workflow: 't2i', ports: ports([], ['image']), detail: [['Prompt', 'Portrait of Mira on a windswept island. Dark bob, sea spray, weathered face, soft overcast daylight.'], ['Reference', 'hero_face · attempt 2'], ['Lineage', 'First character anchor. Illustrative stock image.']] }),
  n('hero_sheet', 'Wardrobe sheet', 'Candidate', 633, 495, { kind: 'Anchor image', image: '../assets/wardrobe.jpg', workflow: 'i2i', ports: ports(['image'], ['image']), detail: [['Prompt', 'Full-body wardrobe sheet for the exact selected Mira portrait: worn ochre raincoat, canvas satchel, practical boots. Preserve the face and silhouette from hero_face.'], ['Reference', 'hero_sheet · attempt 2'], ['Lineage', 'Parent: hero_face attempt 2. Illustrative stock image.']] }),
  n('location', 'Island location', 'Candidate', 823, 495, { kind: 'Anchor image', image: '../assets/coast.jpg', workflow: 't2i', ports: ports([], ['image']), detail: [['Prompt', 'Empty island coast under a low grey sky. Wet shoreline and a distant unlit lighthouse, no people.'], ['Reference', 'location · attempt 1'], ['Lineage', 'Independent of character anchors. Illustrative stock image.']] })
];

const frames = Array.from({ length: 9 }, (_, i) => {
  const shot = i < 5 ? 'S01' : 'S02';
  const title = `${shot} · take ${i < 5 ? i + 1 : i - 4}`;
  return n(`frame:${i + 1}`, title, i < 2 ? 'Example image' : i === 2 ? 'Generating…' : 'Queued',
    120 + i % 3 * 235, 175 + Math.floor(i / 3) * 245,
    { kind: 'Start-frame attempt', ports: ports(['anchors'], ['image']), image: i < 2 ? ['../assets/coast.jpg', '../assets/portrait.jpg'][i] : null,
      placeholder: i >= 2, workflow: 't2i', editable: true, prompt: `${shot}: ${i < 5 ? 'Mira steps onto a wet pier; dark lighthouse in the distance.' : 'Mira at the start of the shoreline path; closed door ahead.'} Opening of the shot, not its ending.`, seed: 41001 + i, generatedSeed: 41001 + i,
      detail: [['Shot', `${shot} · candidate ${i < 5 ? i + 1 : i - 4}`], ['Settings', 'Krea2 example · 1024 × 1024 · 8 steps · Euler ancestral'], ['References', 'Approved face, wardrobe sheet and location required before real submission.']] });
});
const clips = ['S01', 'S02'].map((shot, i) => n(`clip:${shot}`, `${shot} clip`, 'Waiting on approved frame', 160 + i * 280, 245,
  { kind: 'Video attempt', ports: ports(['start image', 'motion'], ['video']), placeholder: true, poster: ['../assets/coast.jpg', '../assets/portrait.jpg'][i], workflow: 'i2v',
    detail: [['Start image', `${shot} · exact approved start frame required`], ['Motion prompt', i ? 'Follow Mira slowly until she stops at the closed door.' : 'Mira steps off the ferry; wind lifts her coat; the lighthouse light moves.'], ['Duration', '6s planned · example MiniMax workflow is set to 5s; adapter mapping requires reconciliation. No video in this example.']] }));

// Subsets of the actual API-prompt graphs: ids, class_type and displayed links come from the JSON files.
const workflows = {
  t2i: { title: 'Krea2 · text → image', file: 'txt2img krea2 api v1_local.json', nodes: [
    ['815', 'easy int', 90, 650, 'Width · 1024'], ['814', 'easy int', 90, 790, 'Height · 1024'],
    ['817', 'CLIPLoader', 90, 160, 'Text encoder'], ['819', 'Power Lora Loader', 310, 160, 'LoRA'],
    ['864', 'CLIPTextEncode', 530, 160, 'Prompt'], ['854', 'EmptyLatentImage', 530, 360, '1024 × 1024'],
    ['844', 'DiffusionModelLoaderKJ', 90, 380, 'Model'], ['669', 'ConditioningZeroOut', 530, 570, 'Negative'],
    ['856', 'KSampler', 770, 240, '8 steps · Euler a'], ['803', 'VAELoader', 1000, 450, 'VAE'],
    ['668', 'VAEDecode', 1000, 240, 'Decode'], ['865', 'SaveImage', 1220, 240, 'Output']
  ], outputs: { '815': ['INT'], '814': ['INT'], '817': ['CLIP'], '844': ['MODEL'], '819': ['MODEL', 'CLIP'],
    '864': ['CONDITIONING'], '669': ['CONDITIONING'], '854': ['LATENT'], '856': ['LATENT'], '803': ['VAE'], '668': ['IMAGE'] },
    links: [['817',0,'819','clip'], ['844',0,'819','model'], ['819',1,'864','clip'], ['819',0,'856','model'],
      ['864',0,'856','positive'], ['864',0,'669','conditioning'], ['669',0,'856','negative'],
      ['815',0,'854','width'], ['814',0,'854','height'], ['854',0,'856','latent_image'],
      ['856',0,'668','samples'], ['803',0,'668','vae'], ['668',0,'865','images']],
    literals: { '864': ['text'], '856': ['seed', 'steps'] },
    fields: [['864.text', 'Positive prompt'], ['856.seed', 'Seed'], ['856.steps', 'Steps: 8'], ['815/814.value', 'Width / height: 1024 × 1024']] },
  i2i: { title: 'Qwen · image → image', file: 'qwen img2img api v1.json', nodes: [
    ['485', 'easy int', 90, 60, 'Width · 1024'], ['484', 'easy int', 90, 480, 'Height · 1024'],
    ['470', 'LoadImage', 90, 240, 'Input image'], ['488', 'ImageResizeKJv2', 310, 240, 'Resize'],
    ['459_474', 'TextEncodeQwenImage21', 530, 240, 'Prompt + image'], ['459_458', 'KSampler', 770, 240, '25 steps · Euler'],
    ['459_451', 'UNETLoader', 90, 660, 'Model'], ['491', 'ModelAttentionBackend', 310, 660, 'Attention'],
    ['459_469', 'QwenImage21Cache', 310, 805, 'Cache'], ['459_453', 'CLIPLoader', 310, 450, 'CLIP'],
    ['495', 'Power Lora Loader (rgthree)', 530, 565, 'LoRA'], ['459_454', 'VAELoader', 1000, 450, 'VAE'],
    ['459_457', 'VAEDecode', 1000, 240, 'Decode'], ['494', 'SaveImage', 1220, 240, 'Output']
  ], outputs: { '470': ['IMAGE'], '485': ['INT'], '484': ['INT'], '488': ['IMAGE'], '459_451': ['MODEL'],
    '491': ['MODEL'], '459_469': ['MODEL'], '459_453': ['CLIP'], '495': ['MODEL','CLIP'], '459_454': ['VAE'],
    '459_474': ['POSITIVE', 'NEGATIVE', 'LATENT'], '459_458': ['LATENT'], '459_457': ['IMAGE'] },
    links: [['470',0,'488','image'], ['485',0,'488','width'], ['484',0,'488','height'],
      ['488',0,'459_474','images.image_1'], ['485',0,'459_474','resolution'],
      ['459_451',0,'491','model'], ['491',0,'459_469','model'], ['459_469',0,'495','model'], ['459_453',0,'495','clip'],
      ['495',1,'459_474','clip'], ['495',0,'459_458','model'], ['459_454',0,'459_474','vae'], ['459_454',0,'459_457','vae'],
      ['459_474',0,'459_458','positive'], ['459_474',1,'459_458','negative'], ['459_474',2,'459_458','latent_image'],
      ['459_458',0,'459_457','samples'], ['459_457',0,'494','images']],
    literals: { '459_474': ['prompt', 'negative_prompt'], '459_458': ['seed', 'steps'] },
    fields: [['470.image', 'Exact input portrait'], ['459_474.prompt / negative_prompt', 'Positive / negative prompts'], ['459_458.seed', 'Seed'], ['485/484.value', 'Width / height: 1024 × 1024']] },
  i2v: { title: 'MiniMax · image → video', file: 'minimax img2vid api v1.json', nodes: [
    ['152', 'Int', 90, 50, 'Width · 480'], ['153', 'Int', 310, 790, 'Height · 480'],
    ['132', 'PrimitiveFloat', 90, 420, 'Seconds · 5'], ['131', 'ComfyMathExpression', 530, 790, 'Frame length'],
    ['160', 'LoadImage', 90, 240, 'Start frame'], ['149', 'ImageResizeKJv2', 310, 240, 'Resize'],
    ['136', 'MiniMaxH3ReferenceToVideo', 530, 240, 'Prompt + frame'], ['126', 'BasicGuider', 770, 130, 'Guide'],
    ['125', 'SamplerCustomAdvanced', 780, 350, 'Sample'], ['122', 'VAEDecode', 1000, 350, 'Decode'],
    ['127', 'UNETLoader', 90, 610, 'Model'], ['156', 'ModelAttentionBackend', 310, 610, 'Attention'],
    ['155', 'MiniMaxH3SigmaShift', 530, 610, 'Sigma shift'], ['154', 'BasicScheduler', 770, 610, '8 steps'],
    ['128', 'CLIPLoader', 310, 60, 'CLIP'], ['119', 'VAELoader', 1000, 130, 'Video VAE'],
    ['129', 'RandomNoise', 90, 790, 'Seed 42'], ['123', 'KSamplerSelect', 770, 820, 'Sampler'],
    ['120', 'VAELoader', 1000, 610, 'Audio VAE'], ['121', 'VAEDecodeAudio', 1210, 610, 'Audio decode'],
    ['158', 'RIFE VFI', 1210, 350, 'Interpolate'], ['157', 'VHS_VideoCombine', 1430, 350, 'MP4']
  ], outputs: { '152': ['INT'], '153': ['INT'], '132': ['FLOAT'], '131': ['FLOAT','INT'],
    '160': ['IMAGE'], '149': ['IMAGE'], '128': ['CLIP'], '119': ['VAE'], '120': ['VAE'],
    '127': ['MODEL'], '156': ['MODEL'], '155': ['MODEL'], '136': ['CONDITIONING','LATENT'],
    '126': ['GUIDER'], '129': ['NOISE'], '123': ['SAMPLER'], '154': ['SIGMAS'], '125': ['LATENT'],
    '122': ['IMAGE'], '121': ['AUDIO'], '158': ['IMAGE'] },
    links: [['152',0,'149','width'], ['153',0,'149','height'], ['160',0,'149','image'],
      ['152',0,'136','width'], ['153',0,'136','height'], ['132',0,'131','values.a'], ['131',1,'136','length'],
      ['149',0,'136','ref_images.ref_image_0'], ['128',0,'136','clip'], ['119',0,'136','vae'], ['120',0,'136','audio_vae'],
      ['127',0,'156','model'], ['156',0,'155','model'], ['155',0,'126','model'], ['155',0,'154','model'],
      ['136',0,'126','conditioning'], ['136',1,'125','latent_image'], ['126',0,'125','guider'],
      ['129',0,'125','noise'], ['123',0,'125','sampler'], ['154',0,'125','sigmas'],
      ['125',0,'122','samples'], ['119',0,'122','vae'], ['125',0,'121','samples'], ['120',0,'121','vae'],
      ['122',0,'158','frames'], ['158',0,'157','images'], ['121',0,'157','audio']],
    literals: { '136': ['prompt'], '129': ['noise_seed'], '132': ['value'] },
    fields: [['160.image', 'Exact approved start frame'], ['136.prompt', 'Motion prompt'], ['129.noise_seed', 'Seed: 42'], ['132.value', 'Seconds: 5'], ['157.frame_rate', 'Output: 30 fps H.264 MP4']] }
};
function workflowScope(id, parent, type) {
  const graph = workflows[type];
  scopes[id] = { title: graph.title, parent, hint: `API workflow · ${graph.file} · selected nodes`,
    nodes: graph.nodes.map(([nodeId, classType, x, y, caption]) => n(`wf:${nodeId}`, caption, `#${nodeId}`, x, y,
      { kind: classType, detail: [['ComfyUI node', `${nodeId} · ${classType}`], ['Workflow file', graph.file],
        ['Mapped fields', graph.fields.map(([field, meaning]) => `${field} — ${meaning}`).join('\n')]],
        ports: ports([...graph.links.filter(([, , target]) => target === nodeId).map(([, , , input]) => input), ...(graph.literals?.[nodeId] || [])],
          (graph.outputs[nodeId] || []).map((_, index) => String(index))),
        outputNames: graph.outputs[nodeId] || [], literals: graph.literals?.[nodeId] || [] })),
    edges: graph.links.map(([from, out, to, input]) => [ `wf:${from}`, `wf:${to}`, String(out), input,
      graph.outputs[from][out] ]) };
}
for (const [items, owner, category] of [[media, 'wardrobe', 'anchors'], [frames, 'storyboard', 'frames'], [clips, 'filmmaker', 'videos']]) {
  for (const item of items) {
    item.category = category;
    item.inside = `${owner}:${item.id}`;
    workflowScope(item.inside, 'canvas', item.workflow);
  }
}

for (const [key, group] of Object.entries(groups)) {
  const hasGen = group.stages.length === 3;
  const inputs = { storytell: ['brief'], wardrobe: ['brief', 'story'], storyboard: ['brief', 'story', 'wardrobe_plan', 'anchor_frames'], filmmaker: ['brief', 'story', 'story_frames'] }[key];
  const planName = { storytell: 'story', wardrobe: 'wardrobe_plan', storyboard: 'storyboard_plan', filmmaker: 'video_plan' }[key];
  const mediaName = { wardrobe: 'anchor_frames', storyboard: 'story_frames', filmmaker: 'shot_videos' }[key];
  const genInputs = { wardrobe: ['wardrobe_plan', 'refs · image profile'], storyboard: ['storyboard_plan', 'anchor_frames', 'image profile'], filmmaker: ['video_plan', 'story_frames', 'video profile'] }[key];
  const stageNodes = [n(group.stages[0], group.agent, key === 'storytell' ? 'Story v2 saved' : key === 'wardrobe' ? 'Plan saved' : 'Example plan', 120, 230,
    { kind: 'llm-agent', config: key, label: group.stages[0], inside: `${key}:agent`, ports: ports(inputs, [planName]), detail: [['Inputs', group.inputs], ['System prompt · demo summary', systemPrompts[key]], ['Example instruction', group.prompt], ['System prompt source', `.agents/${key}/system.md · application instructions; this mock shows a short illustrative summary, not the full file`], ['Saved result', group.output]] })];
  if (hasGen) stageNodes.push(n(group.stages[1], key === 'wardrobe' ? 'Anchor generation' : key === 'storyboard' ? 'Batch generation' : 'Video generation',
    key === 'wardrobe' ? '3 candidates' : 'Waiting on approved inputs', 500, 230,
    { kind: 'Generation tool', label: group.stages[1], inside: `${key}:tool`, ports: ports(genInputs, ['current set']), detail: [['Inputs', group.result + ' + exact approved references'], ['Output', key === 'wardrobe' ? 'Three example candidates. Selection and approval are separate.' : 'No generated output in this example run.']] }));
  stageNodes.push(n(group.stages.at(-1), key === 'storytell' ? 'Story review' : key === 'wardrobe' ? 'Anchor review' : key === 'storyboard' ? 'Frame review' : 'Video review',
    key === 'storytell' ? 'Approved story v2' : key === 'wardrobe' ? 'Decision needed · set 2' : 'Not started', hasGen ? 880 : 500, 230,
    { kind: 'Human review', label: group.stages.at(-1), ports: ports([hasGen ? 'current set' : 'story', ...(hasGen ? [planName] : [])], [hasGen ? mediaName : 'approved story']), detail: [['Subject', key === 'storytell' ? 'Story v2 · approved in example' : key === 'wardrobe' ? 'Complete anchor set 2 · request r4 · not approved' : 'Waiting for a complete generated set'], ['Decision', 'Preview only. No approval or generation commands in this prototype.']] }));
  scopes[key] = { title: group.title, parent: 'pipeline', hint: '',
    nodes: stageNodes,
    edges: hasGen ? [[stageNodes[0].id, stageNodes[1].id, planName, planName], [stageNodes[0].id, stageNodes[2].id, planName, planName], [stageNodes[1].id, stageNodes[2].id, 'current set', 'current set']]
      : [[stageNodes[0].id, stageNodes[1].id, 'story', 'story']] };
  const plan = n(`${key}:plan`, key === 'storytell' ? 'Story v2' : group.title + ' plan', 'Example output', 1020, 230,
    { kind: 'Validated result', label: group.result, detail: [['Saved result', group.output]] });
  scopes[`${key}:agent`] = { title: `${group.title} · llm-agent`, parent: key,
    hint: 'LangGraph pattern · one optional read-only tool · illustrative topology, not a live execution trace.',
    nodes: [n(`${key}:input`, 'START', 'HumanMessage', 70, 230, { kind: 'Input', ports: ports([], ['messages']), detail: [['Inputs', group.inputs], ['State', 'MessagesState accumulates model responses and tool results using add_messages.']] }),
      n(`${key}:owner`, 'Model', 'System + messages', 370, 230, { kind: 'llm-agent', config: key, ports: ports(['messages', 'tool result'], ['final answer', 'tool calls']), detail: [['System prompt · demo summary', systemPrompts[key]], ['HumanMessage · example task', group.prompt], ['Call', 'model.bind_tools([read_selected_reference]).invoke([SystemMessage(system_prompt), ...state.messages])'], ['Routing', 'If the AIMessage contains tool_calls, run tools; otherwise END. The system message is supplied on each call, not appended repeatedly to history.']] }),
      n(`${key}:tool`, 'ToolNode', '1 read-only tool', 710, 530, { kind: 'Tool', ports: ports(['tool calls'], ['tool result']), detail: [['Available tool · proposed demo', 'read_selected_reference(alias)'], ['Boundary', 'Only a bounded text projection of an already-selected, authorized reference. Unknown aliases are rejected; no arbitrary paths, network or writes.'], ['Return', 'ToolMessage with the matching tool_call_id is appended to messages; then Model is called again. One tool may be skipped or called more than once.']] }),
      n(`${key}:end`, 'END', 'No tool calls', 710, 230, { kind: 'Output', ports: ports(['final answer'], ['response']), detail: [['Graph boundary', 'The agent loop ends with an AIMessage without tool_calls. Kinodel then validates and saves the response outside this loop.']] }),
      { ...plan, ports: ports(['response'], []) }],
    edges: [[`${key}:input`, `${key}:owner`, 'messages', 'messages'], [`${key}:owner`, `${key}:tool`, 'tool calls', 'tool calls'], [`${key}:tool`, `${key}:owner`, 'tool result', 'tool result'], [`${key}:owner`, `${key}:end`, 'final answer', 'final answer'], [`${key}:end`, `${key}:plan`, 'response', 'response']] };
}

let mediaFilter = 'all';
const canvas = document.querySelector('#canvas');
scopes.canvas = { title: 'Canvas', hint: '', nodes: [], edges: [], labels: [] };
let canvasCardWidth = 190;
function arrangeMedia() {
  const scope = scopes.canvas;
  scope.nodes = []; scope.edges = []; scope.labels = [];
  canvasCardWidth = canvas.clientWidth <= 700 ? 176 : Math.max(120, Math.min(150, Math.floor((canvas.clientWidth - 44 - 8 * 10) / 9)));
  let y = 150;
  for (const [category, title, items] of [['anchors', 'Anchors', media], ['frames', 'Images', frames], ['videos', 'Video', clips]]) {
    if (mediaFilter !== 'all' && mediaFilter !== category) continue;
    scope.labels.push({ title, x: 22, y: y - 27 });
    items.forEach((item, i) => {
      item.x = 22 + i * (canvasCardWidth + 10);
      item.y = y;
      scope.nodes.push(item);
    });
    if (category === 'videos') scope.labels.push({ title: '+ New shot · coming soon', x: 22 + 2 * (canvasCardWidth + 10), y, future: true });
    y += 210;
  }
  // Gallery tiles have no sockets or wires; exact portrait → sheet lineage lives in details.
}
arrangeMedia();

scopes.brief = { title: 'Brief', parent: 'pipeline', hint: '', nodes: [], edges: [] };
scopes.montage = { title: 'Montage', parent: 'pipeline', hint: '', nodes: [], edges: [] };
scopes.final = { title: 'Final', parent: 'pipeline', hint: 'A verified Montage output, not an additional agent or approval gate.', nodes: [
  n('final:output', 'Final video', 'Waiting on montage', 240, 250, { kind: 'Output', ports: ports(['final_video']), detail: [['Output', 'A playable, downloadable final_video appears here after technical verification. No file exists in this example.']] })], edges: [] };

const world = document.querySelector('#world');
const connections = document.querySelector('#connections');
const nodesElement = document.querySelector('#nodes');
const inspector = document.querySelector('#inspector');
const icons = {
  brief: '<path d="M6 2h8l4 4v16H6z M14 2v5h5 M9 11h6 M9 15h6 M9 19h4"/>',
  text: '<path d="M6 3h13v15a3 3 0 0 1-3 3H5a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v12a3 3 0 0 0 3 3 M10 8h6 M10 12h6 M10 16h4"/>',
  image: '<rect x="2" y="3" width="20" height="18" rx="2"/><circle cx="8" cy="9" r="2"/><path d="m3 19 6-6 4 4 3-3 5 5"/>',
  video: '<rect x="2" y="5" width="15" height="14" rx="2"/><path d="m17 9 5-3v12l-5-3 M8 9l4 3-4 3z"/>',
  review: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  montage: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 3v18 M17 3v18 M3 8h4 M3 16h4 M17 8h4 M17 16h4"/>',
  final: '<path d="m7 4 13 8-13 8z"/>',
  agent: '<path d="M9 3h6 M12 3v3 M5 10a7 7 0 0 1 14 0v4a7 7 0 0 1-14 0z M9 12h.01 M15 12h.01 M9 16c2 2 4 2 6 0"/>',
  workflow: '<rect x="2" y="9" width="5" height="5" rx="1"/><rect x="17" y="4" width="5" height="5" rx="1"/><rect x="17" y="16" width="5" height="5" rx="1"/><path d="M7 11h5l5-5 M12 11l5 7"/>'
};
function iconFor(node) {
  if (node.kind === 'Human review' || node.id.endsWith('-hitl')) return 'review';
  if (node.kind === 'llm-agent') return 'agent';
  if (node.kind === 'Generation tool') return node.id === 'video-gen' ? 'video' : 'image';
  if (node.workflow || node.kind === 'Anchor image' || node.kind === 'Start-frame attempt') return node.kind === 'Video attempt' ? 'video' : 'image';
  if (node.id.startsWith('wf:')) return 'workflow';
  if (node.id === 'brief' || node.id.startsWith('brief:')) return 'brief';
  if (node.id === 'storytell' || node.id.startsWith('storytell:')) return 'text';
  if (node.id === 'wardrobe' || node.id === 'storyboard') return 'image';
  if (node.id === 'filmmaker') return 'video';
  if (node.id === 'montage') return 'montage';
  if (node.id === 'final') return 'final';
  return 'workflow';
}
function icon(name) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24'); svg.setAttribute('aria-hidden', 'true');
  svg.innerHTML = icons[name]; return svg;
}
const viewports = {};
let scopeId = 'pipeline';
let selectedId = null;
let interaction = null;
let rightPointer = null;
let dragged = false;
let pendingClick = null;

function viewport() { return viewports[scopeId === 'canvas' ? `canvas:${mediaFilter}` : scopeId] ??= { x: 0, y: scopeId === 'canvas' ? (canvas.clientWidth <= 700 ? 10 : 0) : 25, z: 1 }; }
function paintViewport() {
  const { x, y, z } = viewport();
  world.style.transform = `translate(${x}px, ${y}px) scale(${z})`;
  document.querySelector('#zoom-value').textContent = `${Math.round(z * 100)}%`;
}
function nodeById(id) { return scopes[scopeId].nodes.find(node => node.id === id); }
function syncFrame(id, fields) {
  Object.assign(frames.find(item => item.id === id), fields);
}
function nodeWidth(node) { return node.category ? canvasCardWidth : node.kind === 'Production stage' ? 200 : node.kind === 'llm-agent' ? 260 : node.id.startsWith('wf:') ? 206 : 220; }
function nodeHeight(node) {
  const rows = Math.max(node.ports?.inputs.length || 0, node.ports?.outputs.length || 0);
  if (node.category) return node.category === 'videos' ? 142 : 128;
  if (node.kind === 'Production stage') return 390;
  return Math.max(node.config ? (scopeId === node.config ? 290 : 395) : node.kind === 'Generation tool' ? 310 : 195,
    node.id.startsWith('wf:') ? 103 + rows * 22 : 128 + rows * 24);
}
function portY(node, side, key) {
  const index = node.ports?.[side].indexOf(key) ?? -1;
  if (index < 0) throw new Error(`Missing ${side} port ${key} on ${node.id}`);
  return node.id.startsWith('wf:') ? 82 + index * 22 : node.category ? 107 + index * 24 :
    node.kind === 'Production stage' ? 266 + index * 23 : node.kind === 'Generation tool' ? 224 + index * 24 : 112 + index * 24;
}
function wireType(label) {
  if (/image|frame|anchor|video/i.test(label)) return 'media';
  if (/model|vae|clip/i.test(label)) return 'model';
  if (/latent|samples/i.test(label)) return 'latent';
  if (/conditioning|positive|negative/i.test(label)) return 'conditioning';
  if (/int|float|width|height|length|seed|seconds|steps|sigmas/i.test(label)) return 'number';
  return 'data';
}
function edges() {
  connections.replaceChildren();
  const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
  marker.setAttribute('id', 'arrow'); marker.setAttribute('viewBox', '0 0 10 10'); marker.setAttribute('refX', '17'); marker.setAttribute('refY', '5');
  marker.setAttribute('markerWidth', '7'); marker.setAttribute('markerHeight', '7'); marker.setAttribute('orient', 'auto-start-reverse');
  const point = document.createElementNS('http://www.w3.org/2000/svg', 'path'); point.setAttribute('d', 'M1 1 9 5 1 9'); marker.append(point);
  const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs'); defs.append(marker); connections.append(defs);
  for (const [from, to, output, input, type = output] of scopes[scopeId].edges) {
    const a = nodeById(from), b = nodeById(to);
    const x1 = a.x + nodeWidth(a), y1 = a.y + (type === 'route' ? 230 : portY(a, 'outputs', output));
    const x2 = b.x, y2 = b.y + (type === 'route' ? 230 : portY(b, 'inputs', input));
    const source = type === 'route' ? { x: x1, y: y1 } : socketCenter(from, 'output', output, connections);
    const target = type === 'route' ? { x: x2, y: y2 } : socketCenter(to, 'input', input, connections);
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    const bypass = scopes[scopeId].nodes.some(node => node !== a && node !== b && node.x > a.x && node.x < b.x && node.y < Math.max(y1, y2) && node.y + nodeHeight(node) > Math.min(y1, y2));
    const lane = Math.max(a.y + nodeHeight(a), b.y + nodeHeight(b)) + 32;
    line.setAttribute('d', wirePath(source, target, type === 'route' ? null : bypass || x2 <= x1 ? lane : null));
    line.dataset.type = wireType(type);
    if (type !== 'route') { line.dataset.from = `${from}:${output}`; line.dataset.to = `${to}:${input}`; }
    else line.dataset.route = 'approval order';
    if (!from.startsWith('wf:')) line.setAttribute('marker-end', 'url(#arrow)');
    connections.append(line);
  }
}
// Read the rendered socket centres, so borders, nested boards and zoom share one geometry.
function elementCenter(element, svg) {
  const rect = element.getBoundingClientRect();
  return new DOMPoint(rect.x + rect.width / 2, rect.y + rect.height / 2).matrixTransform(svg.getScreenCTM().inverse());
}
function socketCenter(id, side, port, svg) {
  const card = [...nodesElement.querySelectorAll('.node')].find(card => card.dataset.nodeId === id);
  const row = [...card.querySelectorAll(`.port-row.${side}`)].find(row => row.dataset.port === port);
  return elementCenter(row.querySelector('.port'), svg);
}
function wirePath(a, b, lane) {
  if (lane !== null) return `M${a.x} ${a.y} H${a.x + 20} V${lane} H${b.x - 20} V${b.y} H${b.x}`;
  const middle = (a.x + b.x) / 2;
  if (Math.abs(a.y - b.y) < 1) return `M${a.x} ${a.y} L${middle} ${a.y} L${b.x} ${b.y}`;
  return `M${a.x} ${a.y} C${middle} ${a.y}, ${middle} ${b.y}, ${b.x} ${b.y}`;
}
function renderNodes() {
  nodesElement.replaceChildren();
  for (const group of scopes[scopeId].labels || []) {
    if (group.future) {
      const future = document.createElement('button'); future.className = 'new-shot'; future.type = 'button'; future.disabled = true;
      future.textContent = group.title; future.setAttribute('aria-label', 'New shot — coming soon');
      Object.assign(future.style, { left: `${group.x}px`, top: `${group.y}px`, width: `${canvasCardWidth}px` });
      nodesElement.append(future); continue;
    }
    const label = document.createElement('div'); label.className = 'media-group-label'; label.textContent = group.title;
    label.style.left = `${group.x}px`; label.style.top = `${group.y}px`; nodesElement.append(label);
  }
  for (const node of scopes[scopeId].nodes) {
    const card = document.createElement('article');
    card.className = `node${node.image || node.placeholder ? ' media' : ''}${node.inside ? ' has-inside' : ''}${node.kind === 'Human review' ? ' human-review' : ''}${/needs review|decision/i.test(node.status) ? ' review' : ''}${node.id.startsWith('wf:') ? ' workflow-node' : ''}`;
    card.dataset.nodeId = node.id;
    card.dataset.nodeType = node.kind;
    card.style.width = `${nodeWidth(node)}px`;
    card.style.left = `${node.x}px`;
    card.style.top = `${node.y}px`;
    card.style.minHeight = `${nodeHeight(node)}px`;
    card.tabIndex = 0;
    card.setAttribute('aria-label', `${node.title}, ${node.status}`);
    if (scopeId === 'canvas' && node.category) card.title = `${node.title} · ${node.status}`;
    const head = document.createElement('div');
    head.className = 'node-head';
    head.append(icon(iconFor(node)));
    if (node.id.startsWith('wf:')) { const kind = document.createElement('span'); kind.className = 'node-kind'; kind.textContent = node.kind; head.append(kind); }
    const title = document.createElement('span'); title.className = 'node-title';
    title.textContent = scopeId === 'canvas' && canvasCardWidth < 132 && node.category === 'anchors' ?
      node.id === 'hero_sheet' ? 'Wardrobe' : node.id === 'location' ? 'Location' : node.title : node.title;
    const status = document.createElement('span'); status.className = 'node-status';
    status.textContent = scopeId === 'canvas' && node.category ? node.category === 'videos' ? 'Waiting' : node.status === 'Example image' ? 'Example' : node.status : node.status;
    head.append(title, status); card.append(head);
    if (node.kind === 'Production stage' || node.kind === 'Generation tool') {
      card.classList.add('stage-card');
      const preview = document.createElement('div'); preview.className = 'stage-preview';
      const key = node.id === 'anchor-gen' ? 'wardrobe' : node.id === 'frames-gen' ? 'storyboard' : node.id === 'video-gen' ? 'filmmaker' : node.id;
      if (key === 'wardrobe' || key === 'storyboard') {
        for (const item of key === 'wardrobe' ? media : frames.slice(0, 2)) {
          if (item.image) { const img = document.createElement('img'); img.src = item.image; img.alt = item.title + ' · illustrative preview'; preview.append(img); }
          else { const empty = document.createElement('span'); empty.textContent = 'Queued'; preview.append(empty); }
        }
      } else if (key === 'brief' || key === 'storytell') {
        preview.classList.add('text-preview'); preview.textContent = key === 'brief' ? 'Mira returns before the last ferry. A light moves inside the dark lighthouse.' : 'S01 · Arrival\nS02 · Approach';
      } else {
        preview.classList.add('empty-preview'); preview.append(icon(key === 'montage' ? 'montage' : 'video'));
        const note = document.createElement('span'); note.textContent = key === 'filmmaker' ? '2 clips · awaiting frames' : key === 'montage' ? 'Assembly awaits clips' : 'Your final film'; preview.append(note);
      }
      if (scopeId === 'pipeline') {
        const description = document.createElement('p'); description.className = 'stage-description';
        description.textContent = {
          brief: 'The idea, submitted for this run.', storytell: 'Two shots · Story v2 approved.',
          wardrobe: '3 anchors ready for review · not approved.', storyboard: 'Opening frames follow approved anchors.',
          filmmaker: 'Clips begin from approved frames.', montage: 'Assemble approved clips in order.',
          final: 'Verified film appears here.'
        }[key];
        card.append(description);
      }
      card.append(preview);
    }
    if (node.config && scopeId !== node.config) {
      card.classList.add('llm-agent');
      const config = document.createElement('div'); config.className = 'agent-config';
      for (const [label, value] of [['Node type', 'llm-agent'], ['System prompt', `${node.config}/system.md`], ['Model', 'Not connected · demo']]) {
        const field = document.createElement('div');
        const caption = document.createElement('span'); caption.textContent = label;
        const text = document.createElement('strong'); text.textContent = value;
        field.append(caption, text); config.append(field);
      }
      card.append(config);
    }
    if (node.image) { const img = document.createElement('img'); img.src = node.image; img.alt = `Example ${node.title.toLowerCase()}`; card.append(img); }
    else if (node.placeholder) { const frame = document.createElement('div'); frame.className = 'media-placeholder';
      if (node.poster) frame.style.backgroundImage = `linear-gradient(#101012bb, #101012ee), url("${node.poster}")`;
      if (node.status.includes('Generating')) { const spinner = document.createElement('span'); spinner.className = 'spinner'; frame.append(spinner); }
      else frame.append(icon(node.kind === 'Video attempt' ? 'video' : 'image'));
      card.append(frame); }
    if (node.image || node.placeholder) card.classList.add('media-card');
    if (node.category) {
      card.dataset.category = node.category;
      const caption = document.createElement('div'); caption.className = 'media-caption';
      caption.textContent = node.category === 'videos' ? '06s planned · no video file' : node.category === 'anchors' ? 'Anchor set 2 · illustrative stock' : `${node.title.slice(0, 3)} · illustrative attempt`;
      if (scopeId !== 'canvas') card.append(caption);
    }
    if (node.id.startsWith('wf:')) card.classList.add('technical');
    if (!(scopeId === 'canvas' && node.category)) for (const side of ['inputs', 'outputs']) for (const key of (node.ports?.[side] || [])) {
      const row = document.createElement('span'); row.className = `port-row ${side === 'inputs' ? 'input' : 'output'}`;
      row.style.top = `${portY(node, side, key)}px`; row.dataset.port = key;
      const type = side === 'outputs' && node.outputNames ? node.outputNames[Number(key)] :
        scopes[scopeId].edges.find(([, to, , input]) => to === node.id && input === key)?.[4] || key;
      row.dataset.type = wireType(type);
      const socket = document.createElement('span'); socket.className = 'port';
      const name = document.createElement('span'); name.className = 'port-label';
       name.textContent = side === 'outputs' && node.outputNames ? node.outputNames[Number(key)].toLowerCase() : key.replace(/^images\.|^ref_images\./, '').replaceAll('_', ' ');
      row.append(socket, name); row.setAttribute('aria-label', `${side === 'inputs' ? 'Input' : 'Output'} ${name.textContent}`);
      card.append(row);
    }
    if (node.inside && !(scopeId === 'canvas' && node.category)) {
      const open = document.createElement('button'); open.type = 'button'; open.className = 'node-open';
      open.textContent = scopeId === 'pipeline' && node.id === 'wardrobe' ? 'Review anchors ↗' : node.category ? 'Workflow ↗' : node.kind === 'Generation tool' ? 'View in Canvas ↗' : 'Open inside ↗';
      open.setAttribute('aria-label', `${open.textContent.replace(' ↗', '')} ${node.title}`);
      open.addEventListener('click', event => { event.stopPropagation(); go(node.inside); if (node.id === 'wardrobe' && event.currentTarget.textContent.startsWith('Review anchors')) details(nodeById('anchor-hitl')); }); card.append(open);
    }
    nodesElement.append(card);
  }
  edges();
}
function breadcrumbs() {
  const chain = [];
  for (let id = scopeId; id; id = scopes[id].parent) chain.unshift(id);
  document.querySelector('.topbar').classList.toggle('nested-scope', chain.length > 1);
  const nav = document.querySelector('#breadcrumbs'); nav.replaceChildren();
  chain.forEach((id, index) => {
    if (index) { const separator = document.createElement('span'); separator.className = 'separator'; separator.textContent = '/'; nav.append(separator); }
    if (index === chain.length - 1) {
      const label = document.createElement('span'); label.setAttribute('aria-current', 'page'); label.textContent = scopes[id].title; nav.append(label);
    } else {
      const button = document.createElement('button'); button.type = 'button'; button.textContent = scopes[id].title; button.dataset.scope = id; nav.append(button);
    }
  });
}
function renderScope() {
  breadcrumbs();
  document.querySelector('#brief-page').hidden = scopeId !== 'brief';
  document.querySelector('#montage-page').hidden = scopeId !== 'montage';
  canvas.hidden = ['brief', 'montage'].includes(scopeId);
  canvas.classList.toggle('media-scope', scopeId === 'canvas');
  canvas.classList.toggle('pipeline-scope', scopeId === 'pipeline');
  document.querySelector('#media-filters').hidden = scopeId !== 'canvas';
  document.querySelectorAll('[data-filter]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.filter === mediaFilter)));
  const destination = scopeId === 'canvas' || scopes[scopeId].parent === 'canvas' ? 'canvas' : ['brief', 'montage'].includes(scopeId) ? scopeId : 'pipeline';
  document.querySelectorAll('[data-nav]').forEach(button => {
    if (button.dataset.nav === destination) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
  });
  document.querySelector('#scope-title').textContent = scopes[scopeId].title;
  document.querySelector('#scope-hint').textContent = scopes[scopeId].hint;
  renderNodes(); paintViewport();
}
function go(id) {
  const mediaRoutes = { 'wardrobe:tool': 'anchors', 'storyboard:tool': 'frames', 'filmmaker:tool': 'videos' };
  if (mediaRoutes[id]) { mediaFilter = mediaRoutes[id]; arrangeMedia(); id = 'canvas'; }
  if (!scopes[id]) return;
  setChatView(false);
  if (!['canvas', 'brief', 'montage', 'final'].includes(scopeId) && scopes[scopeId].parent !== 'canvas') lastPipelineScope = scopeId;
  clearTimeout(pendingClick);
  const fresh = !viewports[id];
  scopeId = id; selectedId = null; inspector.hidden = true;
  if (id === 'canvas') arrangeMedia();
  canvas.scrollLeft = 0; canvas.scrollTop = 0;
  renderScope();
  if (fresh && canvas.clientWidth <= 700 && !['canvas', 'brief', 'montage'].includes(id)) {
    const first = scopes[id].nodes[0];
    viewport().x = 28 - first.x;
    viewport().y = 150 - Math.min(...scopes[id].nodes.map(node => node.y));
    paintViewport();
  }
  if (fresh && canvas.clientWidth > 700 && !['pipeline', 'canvas', 'brief', 'montage'].includes(id)) fit();
}
function select(id) {
  selectedId = id;
  nodesElement.querySelectorAll('.node').forEach(card => card.classList.toggle('selected', card.dataset.nodeId === id));
}
function details(node) {
  select(node.id);
  document.querySelector('#detail-kind').textContent = node.kind;
  document.querySelector('#detail-title').textContent = node.title;
  const body = document.querySelector('#detail-body'); body.replaceChildren();
  if (node.category) { mediaDetails(node, body); inspector.hidden = false; return; }
  const sections = node.detail ?? (groups[node.id] ? [['Scope', `${groups[node.id].stages.join(' → ')}\nDouble-click to inspect each stage.`]] : [['Scope', `Double-click to inspect ${node.title}.`]]);
  if (node.image) { const img = document.createElement('img'); img.className = 'detail-image'; img.src = node.image; img.alt = `Example ${node.title.toLowerCase()}`; body.append(img); }
  for (const [label, text] of sections) {
    const section = document.createElement('section'); section.className = 'detail-section';
    const heading = document.createElement('h3'); heading.textContent = label;
    const copy = document.createElement('p'); copy.textContent = text;
    section.append(heading, copy); body.append(section);
  }
  if (node.inside) {
    const open = document.createElement('button'); open.type = 'button'; open.className = 'workflow-link'; open.textContent = 'Open inside ↗';
    open.addEventListener('click', () => go(node.inside)); body.prepend(open);
  }
  inspector.hidden = false;
}
const mediaTabs = {};
// Values describe the checked-in example API prompts, never a completed render receipt.
const workflowExamples = {
  t2i: [['Model', 'Krea2 turbo · example API prompt'], ['Request size', '1024 × 1024'], ['Sampler', 'Euler ancestral'], ['Steps', '8']],
  i2i: [['Model', 'Qwen Image 2.1 · example API prompt'], ['Request size', '1024 × 1024'], ['Sampler', 'Euler'], ['Steps', '25']],
  i2v: [['Model', 'MiniMax H3 · example API prompt'], ['Request size', '480 × 480'], ['Sampler', 'res_multistep'], ['Steps', '8'], ['Workflow duration', '5s · differs from 6s shot plan']]
};
function detailRows(parent, entries) {
  const rows = document.createElement('dl'); rows.className = 'detail-rows';
  for (const [label, value] of entries) {
    const term = document.createElement('dt'); term.textContent = label;
    const description = document.createElement('dd'); description.textContent = value;
    rows.append(term, description);
  }
  parent.append(rows);
}
function mediaDetails(node, body) {
  const preview = document.createElement(node.image ? 'img' : 'div'); preview.className = node.image ? 'detail-image' : 'detail-empty';
  if (node.image) { preview.src = node.image; preview.alt = `Example ${node.title}`; }
  else { preview.append(icon(node.category === 'videos' ? 'video' : 'image')); const text = document.createElement('span'); text.textContent = node.category === 'videos' ? 'No video yet · waiting on approved frame' : node.status; preview.append(text); }
  const status = document.createElement('p'); status.className = 'detail-status'; status.textContent = `${node.status} · ${node.image ? 'illustrative stock, not a verified render' : 'no media file'}`;
  const open = document.createElement('button'); open.type = 'button'; open.className = 'workflow-link'; open.textContent = 'Open in workflow ↗'; open.addEventListener('click', () => go(node.inside));
  const tabs = document.createElement('div'); tabs.className = 'inspector-tabs'; tabs.setAttribute('aria-label', 'Media details');
  const content = document.createElement('div'); content.className = 'tab-content';
  body.append(status, preview, tabs, content, open);
  for (const name of ['Details', 'Prompt', 'Settings', 'Lineage']) {
    const button = document.createElement('button'); button.type = 'button'; button.textContent = name;
    button.setAttribute('aria-pressed', String((mediaTabs[node.id] || 'Details') === name));
    button.addEventListener('click', () => {
      mediaTabs[node.id] = name; details(node);
      body.querySelector('.inspector-tabs [aria-pressed="true"]').focus({ preventScroll: true });
    }); tabs.append(button);
  }
  const tab = mediaTabs[node.id] || 'Details';
  if (tab === 'Prompt' && node.editable) {
    const initialSeed = node.generatedSeed;
    const promptLabel = document.createElement('label'); promptLabel.className = 'edit-field'; promptLabel.textContent = 'Prompt · local draft';
    const prompt = document.createElement('textarea'); prompt.value = node.prompt; prompt.rows = 5; prompt.required = true;
    prompt.addEventListener('input', () => { prompt.setCustomValidity(''); syncFrame(node.id, { prompt: prompt.value }); }); promptLabel.append(prompt);
    const seedLabel = document.createElement('label'); seedLabel.className = 'edit-field'; seedLabel.textContent = 'Seed · local draft';
    const seed = document.createElement('input'); seed.type = 'number'; seed.min = '0'; seed.max = '4294967295'; seed.required = true; seed.value = node.seed;
    seed.addEventListener('input', () => { if (seed.validity.valid && seed.value !== '') syncFrame(node.id, { seed: Number(seed.value) }); }); seedLabel.append(seed);
    const regenerate = document.createElement('button'); regenerate.type = 'button'; regenerate.className = 'regenerate'; regenerate.textContent = 'Regenerate · mock';
    regenerate.addEventListener('click', () => {
      if (!prompt.value.trim()) prompt.setCustomValidity('Enter a prompt');
      if (!prompt.reportValidity() || !seed.reportValidity()) return;
      let nextSeed = Number(seed.value) === initialSeed ? crypto.getRandomValues(new Uint32Array(1))[0] : Number(seed.value);
      if (nextSeed === initialSeed) nextSeed = (nextSeed + 1) >>> 0;
      syncFrame(node.id, { prompt: prompt.value, seed: nextSeed, generatedSeed: nextSeed, status: 'Queued · mock', image: null, placeholder: true });
      seed.value = node.seed; renderNodes(); details(node);
    });
    const note = document.createElement('p'); note.className = 'draft-note'; note.textContent = 'Local draft only. No render is submitted.';
    content.append(promptLabel, seedLabel, note, regenerate);
  } else {
    const sections = tab === 'Details' ? [['Seed', node.seed === undefined ? 'Not recorded' : `${node.seed} · local draft`],
      ['Prompt', node.prompt || node.detail.find(([label]) => /prompt/i.test(label))?.[1] || 'Not prepared; waiting on approved inputs.']] :
      tab === 'Settings' ? [['Example workflow', workflows[node.workflow].title], ...workflowExamples[node.workflow]] :
      tab === 'Lineage' ? [['ID', node.id], ...node.detail.filter(([label]) => !/prompt|settings|duration/i.test(label))] :
        node.detail.filter(([label]) => /prompt/i.test(label));
    if (!sections.length) sections.push(['Prompt', node.prompt || 'Prepared prompt unavailable.']);
    if (tab === 'Prompt') {
      const copy = document.createElement('p'); copy.className = 'detail-copy'; copy.textContent = sections.map(([label, value]) => `${label}: ${value}`).join('\n'); content.append(copy);
    } else detailRows(content, sections);
    if (tab === 'Settings') {
      const note = document.createElement('p'); note.className = 'draft-note'; note.textContent = 'Checked-in example API prompt, not settings of the stock preview or a submitted job.'; content.append(note);
    }
  }
}
function zoom(value, cx = canvas.clientWidth / 2, cy = canvas.clientHeight / 2) {
  const state = viewport();
  const z = Math.max(.55, Math.min(1.5, value));
  state.x = cx - (cx - state.x) * z / state.z;
  state.y = cy - (cy - state.y) * z / state.z;
  state.z = z; paintViewport();
}
function center(node) {
  const state = viewport();
  state.x = canvas.clientWidth / 2 - (node.x + nodeWidth(node) / 2) * state.z;
  state.y = canvas.clientHeight / 2 - (node.y + nodeHeight(node) / 2) * state.z;
  paintViewport();
}
function fit() {
  const nodes = scopes[scopeId].nodes;
  const x0 = Math.min(...nodes.map(node => node.x)), x1 = Math.max(...nodes.map(node => node.x + nodeWidth(node)), scopeId === 'brief' ? 800 : -Infinity);
  const y0 = Math.min(...nodes.map(node => node.y)), y1 = Math.max(...nodes.map(node => node.y + nodeHeight(node)), scopeId === 'brief' ? 540 : -Infinity);
  const state = viewport();
  if (scopeId === 'canvas') {
    // Keep media labels legible; when the inspector narrows the board, Fit starts at the left and pan reaches the rest.
    state.z = 1;
    state.x = x1 * state.z > canvas.clientWidth - 24 ? 0 : (canvas.clientWidth - (x0 + x1) * state.z) / 2;
    state.y = 0; paintViewport(); return;
  }
  state.z = Math.max(.55, Math.min(1, (canvas.clientWidth - 80) / (x1 - x0), (canvas.clientHeight - 240) / (y1 - y0)));
  state.x = (canvas.clientWidth - (x0 + x1) * state.z) / 2;
  state.y = Math.max(scopeId === 'canvas' ? 165 : 100, (canvas.clientHeight - (y1 - y0) * state.z) / 2) - y0 * state.z;
  paintViewport();
}

nodesElement.addEventListener('click', event => {
  if (event.target.closest('button')) return;
  const card = event.target.closest('.node'); if (!card || dragged) return;
  const id = card.dataset.nodeId;
  select(id);
  clearTimeout(pendingClick);
  // Wait for the second click before opening the panel, especially on mobile where it covers the canvas.
  pendingClick = setTimeout(() => { if (nodeById(id)) details(nodeById(id)); }, 220);
});
nodesElement.addEventListener('dblclick', event => {
  clearTimeout(pendingClick);
  const node = nodeById(event.target.closest('.node')?.dataset.nodeId);
  if (node?.inside) go(node.inside);
  else if (node) details(node);
});
nodesElement.addEventListener('keydown', event => {
  if (scopeId === 'canvas' && event.target.matches('.node[data-category]') && (event.key === 'ContextMenu' || (event.shiftKey && event.key === 'F10'))) {
    event.preventDefault(); go(productionForMedia[event.target.dataset.category]); return;
  }
  if (event.target.matches('.node') && (event.key === 'Enter' || event.key === ' ')) {
    event.preventDefault();
    const node = nodeById(event.target.dataset.nodeId);
    if (event.shiftKey && node.inside) go(node.inside);
    else details(node);
  }
});
canvas.addEventListener('pointerdown', event => {
  if (event.button === 2) { rightPointer = { id: event.pointerId, x: event.clientX, y: event.clientY, moved: false }; return; }
  if (![0, 1].includes(event.button) || event.target.closest('button, input, label, fieldset')) return;
  if (event.button !== 0) event.preventDefault();
  const card = event.button === 0 ? event.target.closest('.node') : null;
  if (card && !event.target.closest('.node-head')) return;
  if (card) select(card.dataset.nodeId);
  const capture = card ?? canvas;
  interaction = { id: card?.dataset.nodeId, x: event.clientX, y: event.clientY, moved: false, capture };
  capture.setPointerCapture(event.pointerId);
});
canvas.addEventListener('pointermove', event => {
  if (rightPointer?.id === event.pointerId && Math.abs(event.clientX - rightPointer.x) + Math.abs(event.clientY - rightPointer.y) > 2) rightPointer.moved = true;
  if (!interaction) return;
  const dx = event.clientX - interaction.x, dy = event.clientY - interaction.y;
  if (Math.abs(dx) + Math.abs(dy) > 2) interaction.moved = true;
  if (!interaction.moved) return;
  if (interaction.id) {
    const node = nodeById(interaction.id);
    node.x += dx / viewport().z; node.y += dy / viewport().z;
    const card = [...nodesElement.querySelectorAll('.node')].find(element => element.dataset.nodeId === node.id);
    card.style.left = `${node.x}px`;
    card.style.top = `${node.y}px`; edges();
  } else {
    viewport().x += dx; viewport().y += dy; paintViewport();
  }
  interaction.x = event.clientX; interaction.y = event.clientY;
});
function finishPointer(event) {
  if (rightPointer?.id === event.pointerId) {
    rightPointer.moved ||= Math.abs(event.clientX - rightPointer.x) + Math.abs(event.clientY - rightPointer.y) > 2;
    return;
  }
  if (!interaction) return;
  dragged = interaction.moved;
  const capture = interaction.capture;
  interaction = null;
  if (capture.hasPointerCapture(event.pointerId)) capture.releasePointerCapture(event.pointerId);
  setTimeout(() => { dragged = false; }, 0);
}
canvas.addEventListener('pointerup', finishPointer);
canvas.addEventListener('pointercancel', event => { if (rightPointer?.id === event.pointerId) rightPointer = null; finishPointer(event); });
canvas.addEventListener('contextmenu', event => {
  const wasDrag = rightPointer?.moved;
  rightPointer = null;
  if (wasDrag) { event.preventDefault(); return; }
  if (event.target.closest('button, input, textarea, select, [contenteditable]')) return;
  if (scopeId === 'canvas') {
    const asset = event.target.closest('.node[data-category]');
    event.preventDefault();
    go(asset ? productionForMedia[asset.dataset.category] : lastPipelineScope);
  } else if (scopes[scopeId].parent) {
    event.preventDefault(); go(scopes[scopeId].parent);
  } else if (!inspector.hidden) {
    event.preventDefault(); inspector.hidden = true;
  }
});
canvas.addEventListener('dblclick', event => event.preventDefault());
document.querySelector('#breadcrumbs').addEventListener('click', event => { if (event.target.dataset.scope) go(event.target.dataset.scope); });
document.querySelector('#close-details').addEventListener('click', () => { clearTimeout(pendingClick); inspector.hidden = true; nodesElement.querySelector(`[data-node-id="${selectedId}"]`)?.focus(); });
document.querySelector('#zoom-in').addEventListener('click', () => zoom(viewport().z + .15));
document.querySelector('#zoom-out').addEventListener('click', () => zoom(viewport().z - .15));
document.querySelector('#fit').addEventListener('click', fit);
document.querySelector('#current').addEventListener('click', () => { if (scopeId !== 'pipeline') go('pipeline'); center(nodeById('wardrobe')); });
canvas.addEventListener('wheel', event => {
  if (event.target.closest('select, button, input')) return;
  event.preventDefault();
  const rect = canvas.getBoundingClientRect();
  zoom(viewport().z + (event.deltaY < 0 ? .1 : -.1), event.clientX - rect.left, event.clientY - rect.top);
}, { passive: false });
document.addEventListener('keydown', event => { if (event.key === 'Escape' && !inspector.hidden) document.querySelector('#close-details').click(); });
document.querySelectorAll('[data-icon]').forEach(element => element.append(icon(element.dataset.icon)));
let lastPipelineScope = 'pipeline';
document.querySelector('.rail').addEventListener('click', event => {
  const destination = event.target.closest('[data-nav]')?.dataset.nav;
  if (!destination) return;
  if (destination === 'canvas') go('canvas');
  else if (destination === 'pipeline') go(lastPipelineScope);
  else if (destination === 'review') { go('wardrobe'); details(nodeById('anchor-hitl')); }
  else go(destination);
});
document.querySelector('#media-filters').addEventListener('click', event => {
  const filter = event.target.closest('[data-filter]')?.dataset.filter;
  if (!filter) return;
  mediaFilter = filter; arrangeMedia(); go('canvas');
});
new ResizeObserver(() => {
  if (scopeId !== 'canvas') return;
  arrangeMedia(); renderNodes();
  if (inspector.hidden && canvas.clientWidth > 700 && viewport().z === 1) {
    const right = Math.max(...scopes.canvas.nodes.map(node => node.x + nodeWidth(node)));
    if (right <= canvas.clientWidth - 24) viewport().x = Math.min(viewport().x, canvas.clientWidth - 24 - right);
    paintViewport();
  }
  if (selectedId) select(selectedId);
}).observe(canvas);
renderScope();

// Chat is a presentation of the same fixture, with local drafts only.
function setChatView(active) {
  document.querySelector('#chat').hidden = !active;
  canvas.hidden = active || ['brief', 'montage'].includes(scopeId);
  document.querySelector('#brief-page').hidden = active || scopeId !== 'brief';
  document.querySelector('#montage-page').hidden = active || scopeId !== 'montage';
  document.querySelector('#breadcrumbs').hidden = active;
  document.querySelectorAll('[data-view]').forEach(button => button.setAttribute('aria-pressed', String((button.dataset.view === 'chat') === active)));
  const destination = active ? 'pipeline' : scopeId === 'canvas' || scopes[scopeId].parent === 'canvas' ? 'canvas' : ['brief', 'montage'].includes(scopeId) ? scopeId : 'pipeline';
  document.querySelectorAll('[data-nav]').forEach(button => {
    if (button.dataset.nav === destination) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
  });
  if (active) { clearTimeout(pendingClick); inspector.hidden = true; }
}
document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => setChatView(button.dataset.view === 'chat')));
document.querySelector('#chat-idea').textContent = idea;
document.querySelector('#chat-story-output').textContent = groups.storytell.output;
for (const item of media) {
  const button = document.createElement('button'); button.type = 'button';
  button.setAttribute('aria-label', `Inspect ${item.title} in Canvas`);
  const image = document.createElement('img'); image.src = item.image; image.alt = `Illustrative ${item.title.toLowerCase()}`;
  const title = document.createElement('span'); title.textContent = item.title;
  button.append(image, title);
  button.addEventListener('click', () => { go('wardrobe:tool'); details(item); });
  document.querySelector('#chat-media').append(button);
}
document.querySelector('#chat-pipeline').addEventListener('click', () => go('wardrobe'));
document.querySelector('#chat-review').addEventListener('click', () => { go('wardrobe'); details(nodeById('anchor-hitl')); });
document.querySelector('#chat-composer').addEventListener('submit', event => {
  event.preventDefault();
  const input = document.querySelector('#chat-message');
  if (!input.value.trim()) { input.setCustomValidity('Write a question or a change.'); input.reportValidity(); return; }
  const entry = document.createElement('article'); entry.className = 'chat-draft';
  const heading = document.createElement('strong');
  heading.textContent = `You · ${document.querySelector('#chat-mode').value === 'revise' ? 'Request changes' : 'Question'}`;
  const copy = document.createElement('p'); copy.textContent = input.value.trim();
  const note = document.createElement('small'); note.textContent = 'Local draft · anchor set 2 / r4 · not sent';
  entry.append(heading, copy, note); document.querySelector('#chat-messages').append(entry);
  input.value = ''; input.focus();
  entry.scrollIntoView({ block: 'nearest' });
});
document.querySelector('#chat-message').addEventListener('input', event => event.target.setCustomValidity(''));

// Neither local form nor illustrative timeline can modify the frozen example execution.
document.querySelector('#submitted-idea').textContent = idea;
document.querySelector('#brief-idea').value = idea;
document.querySelector('#brief-form').addEventListener('submit', event => {
  event.preventDefault();
  const field = document.querySelector('#brief-idea');
  if (!field.value.trim()) { field.setCustomValidity('Describe the film before saving.'); field.reportValidity(); return; }
  document.querySelector('#brief-feedback').textContent = 'Saved locally until reload · not submitted. Current run unchanged.';
});
document.querySelector('#brief-idea').addEventListener('input', event => { event.target.setCustomValidity(''); document.querySelector('#brief-feedback').textContent = 'Unsaved changes · current run unchanged.'; });
document.querySelector('#brief-form').addEventListener('change', () => { document.querySelector('#brief-feedback').textContent = 'Unsaved changes · current run unchanged.'; });
document.querySelector('#brief-ratio').addEventListener('change', event => {
  const sizes = { '16:9': ['1920 × 1080', '1280 × 720'], '9:16': ['1080 × 1920', '720 × 1280'], '1:1': ['1080 × 1080', '768 × 768'] }[event.target.value];
  document.querySelector('#brief-size').replaceChildren(...sizes.map(size => new Option(size, size)));
});
const montageShots = { S01: ['S01 · Arrival', 'Mira steps off the ferry and notices the light in the lighthouse.'], S02: ['S02 · Approach', 'Mira crosses the shore and stops at the closed lighthouse door.'] };
document.querySelector('.timeline-clips').addEventListener('click', event => {
  const button = event.target.closest('[data-shot]'); if (!button) return;
  document.querySelectorAll('[data-shot]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
  document.querySelector('#montage-shot').textContent = montageShots[button.dataset.shot][0];
  document.querySelector('#montage-description').textContent = montageShots[button.dataset.shot][1];
  document.querySelector('#montage-scrub').value = button.dataset.shot === 'S01' ? 0 : 6;
  document.querySelector('#montage-time').textContent = `00:${String(document.querySelector('#montage-scrub').value).padStart(2, '0')} / 00:12 planned`;
});
document.querySelector('#montage-scrub').addEventListener('input', event => {
  document.querySelector('#montage-time').textContent = `00:${String(event.target.value).padStart(2, '0')} / 00:12 planned`;
  const shot = Number(event.target.value) < 6 ? 'S01' : 'S02';
  document.querySelectorAll('[data-shot]').forEach(item => item.setAttribute('aria-pressed', String(item.dataset.shot === shot)));
  document.querySelector('#montage-shot').textContent = montageShots[shot][0];
  document.querySelector('#montage-description').textContent = montageShots[shot][1];
});
