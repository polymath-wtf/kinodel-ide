// View-only demo: positions and navigation are local UI state, never pipeline execution.
const idea = 'Mira returns to a quiet island before the last ferry. She finds the lighthouse dark, but sees a light move inside.';
const groups = {
  storytell: {
    title: 'Storytell', stages: ['storytell', 'story-hitl'], result: 'story v2',
    agent: 'Storytell agent', status: 'Approved',
    inputs: 'Submitted brief · The Magic begin\nTwo ordered shots · 6 seconds each',
    prompt: 'Write a restrained two-shot story. S01: Mira arrives on the island and notices the dark lighthouse. S02: she follows a moving light toward its door. Preserve her location and intention between shots.',
    output: 'Story v2\nS01 · Arrival — Mira steps off the ferry. State after: she sees a light in the lighthouse.\nS02 · Approach — Mira crosses the shore and stops at the closed door. State after: the light moves upstairs.'
  },
  wardrobe: {
    title: 'Wardrobe', stages: ['wardrobe', 'anchor-gen', 'anchor-hitl'], result: 'wardrobe_plan',
    agent: 'Wardrobe agent', status: 'Needs review',
    inputs: 'Submitted brief + approved story v2\nCharacter: Mira · coastal island · worn practical clothing',
    prompt: 'Keep Mira recognisable across both shots: dark bob, ochre raincoat, canvas satchel, sea spray. Generate hero_face first; derive hero_sheet from that exact portrait. Generate an empty island location independently.',
    output: 'wardrobe_plan\nhero_face: weathered close portrait, dark bob, natural daylight.\nhero_sheet: same face, ochre raincoat and canvas satchel. Parent: hero_face.\nlocation: empty grey coastline with the distant lighthouse; no character.'
  },
  storyboard: {
    title: 'Storyboard', stages: ['storyboard', 'frames-gen', 'frames-hitl'], result: 'storyboard_plan',
    agent: 'Storyboard agent', status: 'Waiting on anchors',
    inputs: 'Approved Story v2 + approved anchor set (required)\nFace, sheet and location references by role',
    prompt: 'One start frame per shot, before its action unfolds. S01: wide pier, Mira has just stepped ashore, dark lighthouse far away; face + outfit + coastline refs. S02: Mira stands at the beginning of the shoreline path, before approaching the door.',
    output: 'storyboard_plan · example only\nS01 start frame: Wide static composition. Mira on the wet pier, lighthouse a small dark silhouette.\nS02 start frame: Medium rear three-quarter view at the start of the path; no open door and no completed turn.'
  },
  filmmaker: {
    title: 'Filmmaker', stages: ['filmmaker', 'video-gen', 'video-hitl'], result: 'video_plan',
    agent: 'Filmmaker agent', status: 'Waiting on frames',
    inputs: 'Approved Story v2 + exact approved start frame for each shot (required)',
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
const path = ['Brief', 'Storytell', 'Wardrobe', 'Storyboard', 'Filmmaker', 'Montage', 'Final'];
const pipelinePorts = [ports([], ['brief', 'character']), ports(['brief', 'character'], ['story']), ports(['story', 'character'], ['anchors']),
  ports(['anchors'], ['frames']), ports(['frames'], ['clips']), ports(['clips'], ['final']), ports(['final'])];
const outer = path.map((title, index) => {
  const id = title.toLowerCase();
  const detail = groups[id] ? [['Stages', groups[id].stages.join(' → ')], ['Example result', groups[id].output]]
    : id === 'brief' ? [['Submitted idea', idea]]
    : id === 'montage' ? [['Inputs', 'Approved shot videos in Story order'], ['Result', 'Verified silent final video; not yet available in this example.']]
    : [['Result', 'The verified Montage video appears here; no extra approval gate.']];
  return n(id, title, ['Submitted', 'Approved', 'Needs review', 'Waiting', 'Waiting', 'Waiting', 'Waiting'][index],
    70 + index * 244, 295, { kind: 'Production stage', inside: id, detail, ports: pipelinePorts[index] });
});
scopes.pipeline = { title: 'Pipeline', hint: '', nodes: outer,
  edges: [...path.slice(1).map((title, i) => [path[i].toLowerCase(), title.toLowerCase(), pipelinePorts[i].outputs[0], pipelinePorts[i + 1].inputs[0]]),
    ['brief', 'storytell', 'character', 'character'], ['brief', 'wardrobe', 'character', 'character']] };

const media = [
  n('hero_face', 'Portrait', 'Candidate', 443, 495, { kind: 'Anchor image', image: 'assets/portrait.jpg', workflow: 't2i', ports: ports([], ['image']), detail: [['Prompt', 'Portrait of Mira on a windswept island. Dark bob, sea spray, weathered face, soft overcast daylight.'], ['Reference', 'hero_face · attempt 2'], ['Lineage', 'First character anchor. Illustrative stock image.']] }),
  n('hero_sheet', 'Wardrobe sheet', 'Candidate', 633, 495, { kind: 'Anchor image', image: 'assets/wardrobe.jpg', workflow: 'i2i', ports: ports(['image'], ['image']), detail: [['Prompt', 'Full-body wardrobe sheet for the exact selected Mira portrait: worn ochre raincoat, canvas satchel, practical boots. Preserve the face and silhouette from hero_face.'], ['Reference', 'hero_sheet · attempt 2'], ['Lineage', 'Parent: hero_face attempt 2. Illustrative stock image.']] }),
  n('location', 'Island location', 'Candidate', 823, 495, { kind: 'Anchor image', image: 'assets/coast.jpg', workflow: 't2i', ports: ports([], ['image']), detail: [['Prompt', 'Empty island coast under a low grey sky. Wet shoreline and a distant unlit lighthouse, no people.'], ['Reference', 'location · attempt 1'], ['Lineage', 'Independent of character anchors. Illustrative stock image.']] })
];

const frames = Array.from({ length: 9 }, (_, i) => {
  const shot = i < 5 ? 'S01' : 'S02';
  const title = `${shot} · take ${i < 5 ? i + 1 : i - 4}`;
  return n(`frame:${i + 1}`, title, i < 2 ? 'Example image' : i === 2 ? 'Generating…' : 'Queued',
    120 + i % 3 * 235, 175 + Math.floor(i / 3) * 245,
    { kind: 'Start-frame attempt', ports: ports(['anchors'], ['image']), image: i < 2 ? ['assets/coast.jpg', 'assets/portrait.jpg'][i] : null,
      placeholder: i >= 2, workflow: 't2i', editable: true, prompt: `${shot}: ${i < 5 ? 'Mira steps onto a wet pier; dark lighthouse in the distance.' : 'Mira at the start of the shoreline path; closed door ahead.'} Opening of the shot, not its ending.`, seed: 41001 + i,
      detail: [['Shot', `${shot} · candidate ${i < 5 ? i + 1 : i - 4}`], ['Settings', 'Krea2 example · 1024 × 1024 · 8 steps · Euler ancestral'], ['References', 'Approved face, wardrobe sheet and location required before real submission.']] });
});
const clips = ['S01', 'S02'].map((shot, i) => n(`clip:${shot}`, `${shot} clip`, 'Waiting on approved frame', 160 + i * 280, 245,
  { kind: 'Video attempt', ports: ports(['start image', 'motion'], ['video']), placeholder: true, poster: ['assets/coast.jpg', 'assets/portrait.jpg'][i], workflow: 'i2v',
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
for (const item of media) workflowScope(`wardrobe:${item.id}`, 'wardrobe', item.workflow);
for (const item of frames) workflowScope(`storyboard:${item.id}`, 'storyboard:tool', item.workflow);
for (const item of clips) workflowScope(`filmmaker:${item.id}`, 'filmmaker:tool', item.workflow);

for (const [key, group] of Object.entries(groups)) {
  const hasGen = group.stages.length === 3;
  const stageNodes = [n(group.stages[0], group.agent, key === 'storytell' ? 'Story v2 saved' : key === 'wardrobe' ? 'Plan saved' : 'Example plan', 120, 230,
    { kind: 'llm-agent', config: key, label: group.stages[0], inside: `${key}:agent`, ports: ports(['context'], [hasGen ? 'plan' : 'story']), detail: [['Inputs', group.inputs], ['System prompt · demo summary', systemPrompts[key]], ['Example instruction', group.prompt], ['System prompt source', `.agents/${key}/system.md · application instructions; this mock shows a short illustrative summary, not the full file`], ['Saved result', group.output]] })];
  if (hasGen) stageNodes.push(n(group.stages[1], key === 'wardrobe' ? 'Anchor generation' : key === 'storyboard' ? 'Batch generation' : 'Video generation',
    key === 'wardrobe' ? '3 candidates' : 'Waiting on approved inputs', 430, 230,
    { kind: 'Generation tool', label: group.stages[1], inside: `${key}:tool`, ports: ports(['plan', 'references'], ['candidates']), detail: [['Inputs', group.result + ' + exact approved references'], ['Output', key === 'wardrobe' ? 'Three example candidates. Selection and approval are separate.' : 'No generated output in this example run.']] }));
  stageNodes.push(n(group.stages.at(-1), key === 'storytell' ? 'Story review' : key === 'wardrobe' ? 'Anchor review' : key === 'storyboard' ? 'Frame review' : 'Video review',
    key === 'storytell' ? 'Approved story v2' : key === 'wardrobe' ? 'Decision needed · set 2' : 'Not started', hasGen ? 740 : 460, 230,
    { kind: 'Human review', label: group.stages.at(-1), ports: ports([hasGen ? 'candidates' : 'story'], ['decision']), detail: [['Subject', key === 'storytell' ? 'Story v2 · approved in example' : key === 'wardrobe' ? 'Complete anchor set 2 · request r4 · not approved' : 'Waiting for a complete generated set'], ['Decision', 'Preview only. No approval or generation commands in this prototype.']] }));
  scopes[key] = { title: group.title, parent: 'pipeline', hint: '',
    nodes: key === 'wardrobe' ? [...stageNodes, ...media.map(item => ({ ...item, inside: `wardrobe:${item.id}` }))] : stageNodes,
    preview: key === 'wardrobe' ? { title: 'Anchor set · Portrait → sheet · location independent', x: 430, y: 445, width: 580, height: 290 } : key === 'storyboard' ? { title: 'Batch · 2 ready · 1 generating', x: 430, y: 445, width: 580, height: 290 } : key === 'filmmaker' ? { title: 'Shot clips · waiting on frames', x: 430, y: 445, width: 390, height: 290 } : null,
    edges: stageNodes.slice(1).map((node, i) => [stageNodes[i].id, node.id, i ? 'candidates' : hasGen ? 'plan' : 'story', i ? 'candidates' : hasGen ? 'plan' : 'story']) };
  if (key === 'wardrobe') scopes[key].edges.push(['hero_face', 'hero_sheet', 'image', 'image', 'IMAGE']);
  if (key === 'storyboard') scopes[key].nodes.push(...frames.slice(0, 3).map((item, i) => ({ ...item, x: 443 + i * 190, y: 495, inside: `storyboard:${item.id}` })));
  if (key === 'filmmaker') scopes[key].nodes.push(...clips.map((item, i) => ({ ...item, x: 443 + i * 190, y: 495, inside: `filmmaker:${item.id}` })));
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
  if (hasGen) {
    if (key === 'wardrobe') workflowScope(`${key}:tool`, key, 't2i');
    else scopes[`${key}:tool`] = { title: stageNodes[1].title, parent: key,
      hint: key === 'storyboard' ? 'Two shots · nine illustrative attempts. Select to edit; double-click for workflow.' : 'One clip per shot · exact approved start frames required.',
      nodes: (key === 'storyboard' ? frames : clips).map(item => ({ ...item, inside: `${key}:${item.id}` })),
      preview: key === 'storyboard' ? { title: 'Start frames · S01 / S02', x: 102, y: 135, width: 708, height: 810 }
        : { title: 'Shot videos · waiting on approved frames', x: 140, y: 200, width: 562, height: 315 }, edges: [] };
  }
}

scopes.brief = { title: 'Brief', parent: 'pipeline', hint: 'Choose character context for this example; selection is local to the mock.', nodes: [
  n('brief:input', 'Submitted brief', 'Submitted', 120, 245, { kind: 'Input', ports: ports([], ['brief', 'characters']), detail: [['Idea', idea], ['Settings', 'Example: two shots · 16:9 · 6s each · silent output']] })], edges: [] };
scopes.montage = { title: 'Montage', parent: 'pipeline', hint: 'A deterministic tool assembles approved clips in Story order.', nodes: [
  n('montage:tool', 'FFMPEG', 'Basic montage', 240, 250, { kind: 'Tool', ports: ports(['clips'], ['final']), detail: [['Inputs', 'Approved s01 and s02 videos in Story order'], ['Output', 'Verified final_video · full clips, simple cuts, no audio. No result yet in this example.']] })], edges: [] };
scopes.final = { title: 'Final', parent: 'pipeline', hint: 'A verified Montage output, not an additional agent or approval gate.', nodes: [
  n('final:output', 'Final video', 'Waiting on montage', 240, 250, { kind: 'Output', ports: ports(['final']), detail: [['Output', 'A playable, downloadable final_video appears here after technical verification. No file exists in this example.']] })], edges: [] };

const canvas = document.querySelector('#canvas');
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
const selectedChunks = new Set();
let scopeId = 'pipeline';
let selectedId = null;
let interaction = null;
let dragged = false;
let pendingClick = null;

function viewport() { return viewports[scopeId] ??= { x: 35, y: 45, z: 1 }; }
function paintViewport() {
  const { x, y, z } = viewport();
  world.style.transform = `translate(${x}px, ${y}px) scale(${z})`;
  document.querySelector('#zoom-value').textContent = `${Math.round(z * 100)}%`;
}
function nodeById(id) { return scopes[scopeId].nodes.find(node => node.id === id); }
function syncFrame(id, fields) {
  for (const item of [frames.find(item => item.id === id), ...scopes.storyboard.nodes, ...scopes['storyboard:tool'].nodes].filter(item => item?.id === id)) Object.assign(item, fields);
}
function nodeWidth(node) { return node.kind === 'llm-agent' ? 260 : node.id.startsWith('wf:') ? 206 : scopeId === 'storyboard:tool' && (node.image || node.placeholder) ? 206 : node.image || node.placeholder ? 166 : 188; }
function nodeHeight(node) {
  const rows = Math.max(node.ports?.inputs.length || 0, node.ports?.outputs.length || 0);
  return Math.max(node.config ? 355 : node.image || node.placeholder ? scopeId === 'storyboard:tool' ? 265 : 235 : 118,
    node.id.startsWith('wf:') ? 103 + rows * 22 : 128 + rows * 24);
}
function portY(node, side, key) {
  const index = node.ports?.[side].indexOf(key) ?? -1;
  if (index < 0) throw new Error(`Missing ${side} port ${key} on ${node.id}`);
  return node.id.startsWith('wf:') ? 82 + index * 22 : node.image || node.placeholder ?
    (scopeId === 'storyboard:tool' ? 231 : 200) + index * 24 : 112 + index * 24;
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
  const previewConnections = nodesElement.querySelector('.preview-connections');
  previewConnections?.replaceChildren();
  const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
  marker.setAttribute('id', 'arrow'); marker.setAttribute('viewBox', '0 0 10 10'); marker.setAttribute('refX', '17'); marker.setAttribute('refY', '5');
  marker.setAttribute('markerWidth', '7'); marker.setAttribute('markerHeight', '7'); marker.setAttribute('orient', 'auto-start-reverse');
  const point = document.createElementNS('http://www.w3.org/2000/svg', 'path'); point.setAttribute('d', 'M1 1 9 5 1 9'); marker.append(point);
  const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs'); defs.append(marker); connections.append(defs);
  for (const [from, to, output, input, type = output] of scopes[scopeId].edges) {
    if (from === 'brief' && output === 'character' && !selectedChunks.size) continue;
    const a = nodeById(from), b = nodeById(to);
    const onBoard = previewConnections && (a.image || a.placeholder) && (b.image || b.placeholder);
    const x1 = a.x + nodeWidth(a) - (onBoard ? scopes[scopeId].preview.x : 0);
    const y1 = a.y + portY(a, 'outputs', output) - (onBoard ? scopes[scopeId].preview.y : 0);
    const x2 = b.x - (onBoard ? scopes[scopeId].preview.x : 0);
    const y2 = b.y + portY(b, 'inputs', input) - (onBoard ? scopes[scopeId].preview.y : 0);
    const source = socketCenter(from, 'output', output, onBoard ? previewConnections : connections);
    const target = socketCenter(to, 'input', input, onBoard ? previewConnections : connections);
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    const bypass = scopes[scopeId].nodes.some(node => node !== a && node !== b && node.x > a.x && node.x < b.x && node.y < Math.max(y1, y2) && node.y + nodeHeight(node) > Math.min(y1, y2));
    const lane = Math.max(a.y + nodeHeight(a), b.y + nodeHeight(b)) + 32;
    line.setAttribute('d', wirePath(source, target, bypass || x2 <= x1 ? lane : null));
    line.dataset.type = wireType(type);
    line.dataset.from = `${from}:${output}`; line.dataset.to = `${to}:${input}`;
    if (!from.startsWith('wf:')) line.setAttribute('marker-end', 'url(#arrow)');
    (onBoard ? previewConnections : connections).append(line);
  }
  if (scopes[scopeId].preview) {
    const { x, y } = scopes[scopeId].preview;
    if (['wardrobe', 'storyboard', 'filmmaker'].includes(scopeId)) {
      const generator = scopes[scopeId].nodes[1];
      const source = socketCenter(generator.id, 'output', 'candidates', connections);
      const target = elementCenter(nodesElement.querySelector('.preview-socket'), connections);
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      line.setAttribute('d', `M${source.x} ${source.y} H${source.x + 28} V${target.y - 24} H${target.x} V${target.y}`);
      line.dataset.type = 'media'; line.dataset.preview = 'true'; connections.append(line);
    }
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
  const preview = scopes[scopeId].preview;
  let board;
  if (preview) {
    board = document.createElement('div'); board.className = 'preview-board';
    board.style.left = `${preview.x}px`; board.style.top = `${preview.y}px`; board.style.width = `${preview.width}px`; board.style.height = `${preview.height}px`;
    const label = document.createElement('div'); label.className = 'preview-head'; label.textContent = preview.title; board.append(label);
    const socket = document.createElement('span'); socket.className = 'preview-socket'; socket.setAttribute('aria-label', 'Candidate media input'); board.append(socket);
    const lines = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); lines.classList.add('preview-connections');
    lines.setAttribute('aria-hidden', 'true'); board.append(lines);
    nodesElement.append(board);
  }
  if (scopeId === 'brief') {
    const library = document.createElement('fieldset'); library.className = 'chunk-library';
    const heading = document.createElement('legend'); heading.textContent = 'Character chunks'; library.append(heading);
    const note = document.createElement('p'); note.textContent = 'Demo library · local selection only'; library.append(note);
    for (const name of ['Mira', 'Nico']) {
      const label = document.createElement('label'); const checkbox = document.createElement('input'); checkbox.type = 'checkbox';
      checkbox.value = name; checkbox.checked = selectedChunks.has(name); checkbox.setAttribute('aria-label', `Select ${name} character chunk`);
      checkbox.addEventListener('change', () => {
        if (checkbox.checked) selectedChunks.add(name); else selectedChunks.delete(name);
        library.querySelector('.chunk-selection').textContent = selectedChunks.size ? `Selected: ${[...selectedChunks].join(', ')}` : 'No character chunks selected';
        if (selectedId === 'brief:input') details(nodeById(selectedId));
      });
      label.append(checkbox, document.createTextNode(`${name} · example character`)); library.append(label);
    }
    const selection = document.createElement('p'); selection.className = 'chunk-selection'; selection.textContent = selectedChunks.size ? `Selected: ${[...selectedChunks].join(', ')}` : 'No character chunks selected'; library.append(selection);
    nodesElement.append(library);
  }
  for (const node of scopes[scopeId].nodes) {
    const card = document.createElement('article');
    card.className = `node${node.image || node.placeholder ? ' media' : ''}${node.inside ? ' has-inside' : ''}${node.kind === 'Human review' ? ' human-review' : ''}${/needs review|decision/i.test(node.status) ? ' review' : ''}${node.id.startsWith('wf:') ? ' workflow-node' : ''}`;
    card.dataset.nodeId = node.id;
    card.dataset.nodeType = node.kind;
    card.style.width = `${nodeWidth(node)}px`;
    const onBoard = board && (node.image || node.placeholder);
    card.style.left = `${onBoard ? node.x - preview.x : node.x}px`;
    card.style.top = `${onBoard ? node.y - preview.y : node.y}px`;
    card.style.minHeight = `${nodeHeight(node)}px`;
    card.tabIndex = 0;
    card.setAttribute('aria-label', `${node.title}, ${node.status}`);
    const head = document.createElement('div');
    head.className = 'node-head';
    head.append(icon(iconFor(node)));
    if (node.id.startsWith('wf:')) { const kind = document.createElement('span'); kind.className = 'node-kind'; kind.textContent = node.kind; head.append(kind); }
    const title = document.createElement('span'); title.className = 'node-title'; title.textContent = node.title;
    const status = document.createElement('span'); status.className = 'node-status'; status.textContent = node.status;
    head.append(title, status); card.append(head);
    if (node.config) {
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
    if (scopeId === 'storyboard:tool') card.classList.add('grid-media');
    if (node.id.startsWith('wf:')) card.classList.add('technical');
    for (const side of ['inputs', 'outputs']) for (const [index, key] of (node.ports?.[side] || []).entries()) {
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
    (onBoard ? board : nodesElement).append(card);
  }
  edges();
}
function breadcrumbs() {
  const chain = [];
  for (let id = scopeId; id; id = scopes[id].parent) chain.unshift(id);
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
  document.querySelector('#scope-title').textContent = scopes[scopeId].title;
  document.querySelector('#scope-hint').textContent = scopes[scopeId].hint;
  renderNodes(); paintViewport();
}
function go(id) {
  if (!scopes[id]) return;
  clearTimeout(pendingClick);
  const fresh = !viewports[id];
  scopeId = id; selectedId = null; inspector.hidden = true;
  canvas.scrollLeft = 0; canvas.scrollTop = 0;
  renderScope();
  if (fresh && canvas.clientWidth > 700 && id !== 'pipeline') fit();
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
  const sections = node.id === 'brief:input' ? [...node.detail, ['Character chunks · local draft', selectedChunks.size ? [...selectedChunks].join(', ') : 'None selected']] :
    node.detail ?? (groups[node.id] ? [['Scope', `${groups[node.id].stages.join(' → ')}\nDouble-click to inspect each stage.`]] : [['Scope', `Double-click to inspect ${node.title}.`]]);
  if (node.image) { const img = document.createElement('img'); img.className = 'detail-image'; img.src = node.image; img.alt = `Example ${node.title.toLowerCase()}`; body.append(img); }
  for (const [label, text] of sections) {
    const section = document.createElement('section'); section.className = 'detail-section';
    const heading = document.createElement('h3'); heading.textContent = label;
    const copy = document.createElement('p'); copy.textContent = text;
    section.append(heading, copy); body.append(section);
  }
  if (node.editable) {
    const initialSeed = node.seed;
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
      syncFrame(node.id, { prompt: prompt.value, seed: nextSeed, status: 'Queued · mock', image: null, placeholder: true });
      seed.value = node.seed; renderNodes(); details(node);
    });
    body.append(promptLabel, seedLabel, regenerate);
  }
  inspector.hidden = false;
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
  state.y = canvas.clientHeight / 2 - (node.y + 63) * state.z;
  paintViewport();
}
function fit() {
  const nodes = scopes[scopeId].nodes;
  const preview = scopes[scopeId].preview;
  const x0 = Math.min(...nodes.map(node => node.x), preview?.x ?? Infinity), x1 = Math.max(...nodes.map(node => node.x + nodeWidth(node)), preview ? preview.x + preview.width : -Infinity, scopeId === 'brief' ? 800 : -Infinity);
  const y0 = Math.min(...nodes.map(node => node.y), preview?.y ?? Infinity), y1 = Math.max(...nodes.map(node => node.y + nodeHeight(node)), preview ? preview.y + preview.height : -Infinity, scopeId === 'brief' ? 540 : -Infinity);
  const state = viewport();
  state.z = Math.max(.55, Math.min(1, (canvas.clientWidth - 80) / (x1 - x0), (canvas.clientHeight - 240) / (y1 - y0)));
  state.x = (canvas.clientWidth - (x0 + x1) * state.z) / 2;
  state.y = (canvas.clientHeight - (y0 + y1) * state.z) / 2;
  paintViewport();
}

nodesElement.addEventListener('click', event => {
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
  if (event.target.matches('.node') && (event.key === 'Enter' || event.key === ' ')) {
    event.preventDefault();
    const node = nodeById(event.target.dataset.nodeId);
    if (event.shiftKey && node.inside) go(node.inside);
    else details(node);
  }
});
canvas.addEventListener('pointerdown', event => {
  if (![0, 1].includes(event.button) || event.target.closest('button, input, label, fieldset')) return;
  if (event.button !== 0) event.preventDefault();
  const card = event.button === 0 ? event.target.closest('.node') : null;
  if (card && !event.target.closest('.node-head')) return;
  const board = event.button === 0 && !card ? event.target.closest('.preview-board') : null;
  if (card) select(card.dataset.nodeId);
  const capture = card ?? board ?? canvas;
  interaction = { id: card?.dataset.nodeId, board: !!board, x: event.clientX, y: event.clientY, moved: false, capture };
  capture.setPointerCapture(event.pointerId);
});
canvas.addEventListener('pointermove', event => {
  if (!interaction) return;
  const dx = event.clientX - interaction.x, dy = event.clientY - interaction.y;
  if (Math.abs(dx) + Math.abs(dy) > 2) interaction.moved = true;
  if (!interaction.moved) return;
  if (interaction.id) {
    const node = nodeById(interaction.id);
    node.x += dx / viewport().z; node.y += dy / viewport().z;
    const card = [...nodesElement.querySelectorAll('.node')].find(element => element.dataset.nodeId === node.id);
    const board = card.closest('.preview-board');
    card.style.left = `${node.x - (board ? scopes[scopeId].preview.x : 0)}px`;
    card.style.top = `${node.y - (board ? scopes[scopeId].preview.y : 0)}px`; edges();
  } else if (interaction.board) {
    const preview = scopes[scopeId].preview;
    preview.x += dx / viewport().z; preview.y += dy / viewport().z;
    for (const node of scopes[scopeId].nodes.filter(item => item.image || item.placeholder)) {
      node.x += dx / viewport().z; node.y += dy / viewport().z;
    }
    const board = nodesElement.querySelector('.preview-board');
    board.style.left = `${preview.x}px`; board.style.top = `${preview.y}px`; edges();
  } else {
    viewport().x += dx; viewport().y += dy; paintViewport();
  }
  interaction.x = event.clientX; interaction.y = event.clientY;
});
function finishPointer(event) {
  if (!interaction) return;
  dragged = interaction.moved;
  const capture = interaction.capture;
  interaction = null;
  if (capture.hasPointerCapture(event.pointerId)) capture.releasePointerCapture(event.pointerId);
  setTimeout(() => { dragged = false; }, 0);
}
canvas.addEventListener('pointerup', finishPointer);
canvas.addEventListener('pointercancel', finishPointer);
canvas.addEventListener('contextmenu', event => {
  event.preventDefault();
  if (scopes[scopeId].parent) go(scopes[scopeId].parent);
  else if (!inspector.hidden) inspector.hidden = true;
});
canvas.addEventListener('dblclick', event => event.preventDefault());
document.querySelector('#breadcrumbs').addEventListener('click', event => { if (event.target.dataset.scope) go(event.target.dataset.scope); });
document.querySelector('#close-details').addEventListener('click', () => { clearTimeout(pendingClick); inspector.hidden = true; nodesElement.querySelector(`[data-node-id="${selectedId}"]`)?.focus(); });
document.querySelector('#zoom-in').addEventListener('click', () => zoom(viewport().z + .15));
document.querySelector('#zoom-out').addEventListener('click', () => zoom(viewport().z - .15));
document.querySelector('#fit').addEventListener('click', fit);
document.querySelector('#current').addEventListener('click', () => { if (scopeId !== 'pipeline') go('pipeline'); center(nodeById('wardrobe')); });
canvas.addEventListener('wheel', event => {
  event.preventDefault();
  const rect = canvas.getBoundingClientRect();
  zoom(viewport().z + (event.deltaY < 0 ? .1 : -.1), event.clientX - rect.left, event.clientY - rect.top);
}, { passive: false });
document.addEventListener('keydown', event => { if (event.key === 'Escape' && !inspector.hidden) { clearTimeout(pendingClick); inspector.hidden = true; } });
renderScope();
