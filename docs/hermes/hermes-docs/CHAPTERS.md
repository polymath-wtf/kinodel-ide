# Hermes docs: главы и диапазоны строк

[Краткая карта и бюджет контекста](README.md). Все пути ниже относительно `docs/hermes/hermes-docs/`.

Диапазоны исходников включительные, с 1: `Read(offset=start, limit=end-start+1)`. Указаны все H2 вне fenced code. Для больших глав добавлены H3: дочерние диапазоны входят в родительский, читать оба не нужно. «Введение» включает frontmatter/начало файла. В пяти больших справочниках выбор H3 вместо крупных H2 позволяет читать блоками до 400 строк.

## overview

Источник: [overview.md](overview.md) — 59 строк, ≈1 947 токенов.

| Строки | Глава |
| --- | --- |
| 1–14 | Введение |
| 15–23 | Core |
| 24–31 | Automation |
| 32–40 | Media & Web |
| 41–52 | Integrations |
| 53–59 | Customization; локальный маршрут к дистилляту Kanban |

## plugins

Источник: [backend/plugins.md](backend/plugins.md) — 1 020 строк, ≈15 591 токен.

| Строки | Глава |
| --- | --- |
| 1–18 | Введение |
| 19–94 | Quick overview |
| 95–122 | What plugins can do |
| 123–149 | Plugin discovery |
| 150–327 | Plugins are opt-in (with a few exceptions) |
| 328–338 | Available hooks |
| 339–351 | Plugin types |
| 352–380 | Pluggable interfaces — where to go for each |
| 381–397 | NixOS declarative plugins |
| **398–899** | **Managing plugins — читать подразделами ниже** |
| 398–420 | ↳ Введение Managing plugins |
| 421–445 | ↳ Update checks and provenance |
| 446–470 | ↳ Dependency preparation and preservation |
| 471–517 | ↳ One-click install links (Desktop) |
| 518–582 | ↳ Plugin capabilities and consent |
| 583–629 | ↳ Platform actions |
| 630–665 | ↳ Discovering plugins — the Hermes plugin catalog |
| 666–732 | ↳ Plugin packs |
| 733–802 | ↳ Install-time security scanning |
| 803–853 | ↳ Running plugins out of process (`plugins.isolation`) |
| 854–885 | ↳ Interactive UI |
| 886–899 | ↳ Enabled vs. disabled vs. neither |
| 900–978 | Injecting Messages |
| 979–1020 | Calling MCP servers from plugins |

## api-server

Источник: [backend/api-server.md](backend/api-server.md) — 841 строка, ≈11 038 токенов.

| Строки | Глава |
| --- | --- |
| 1–16 | Введение |
| 17–55 | Quick Start |
| 56–275 | Endpoints |
| 276–364 | Browser-extension control |
| 365–443 | Per-request model selection |
| 444–566 | Runs API (streaming-friendly alternative) |
| 567–602 | Jobs API (background scheduled work) |
| 603–632 | Sessions API (session control over REST) |
| 633–649 | Skills and toolsets discovery |
| 650–664 | Long-term memory scoping (`X-Hermes-Session-Key`) |
| 665–672 | System Prompt Handling |
| 673–711 | Authentication |
| 712–751 | Configuration |
| 752–757 | Security Headers |
| 758–775 | CORS |
| 776–793 | Compatible Frontends |
| 794–828 | Multi-User Setup with Profiles |
| 829–836 | Limitations |
| 837–841 | Proxy Mode |

## delegation

Источник: [backend/delegation.md](backend/delegation.md) — 674 строки, ≈12 700 токенов.

| Строки | Глава |
| --- | --- |
| 1–12 | Введение |
| 13–27 | Completion delivery |
| 28–33 | Background process lifetime |
| 34–42 | Single Task |
| 43–54 | Parallel Batch |
| 55–79 | Structured Output (`output_schema`) |
| 80–126 | How Subagent Context Works |
| 127–183 | Practical Examples |
| 184–263 | Batch Mode Details |
| 264–293 | Model Override |
| 294–328 | The `/review` Command |
| 329–342 | Inherited Tool Access |
| 343–354 | Max Iterations |
| 355–383 | Child Timeout |
| 384–397 | Failure Visibility |
| 398–433 | Stall Detection for Background Subagents |
| 434–478 | Monitoring Running Subagents (`/agents`) |
| 479–516 | Steering a Running Subagent |
| 517–532 | Live Transcripts |
| 533–554 | Depth Limit and Nested Orchestration |
| 555–571 | Lifetime and Durability |
| 572–581 | Key Properties |
| 582–617 | Worktree Isolation |
| 618–631 | Delegation vs execute_code |
| 632–674 | Configuration |

## hooks

Источник: [backend/hooks-big-context.md](backend/hooks-big-context.md) — 2 147 строк, ≈31 360 токенов.

| Строки | Глава |
| --- | --- |
| 1–19 | Введение |
| 20–370 | Gateway Event Hooks — подразделы ниже |
| 20–23 | ↳ Введение Gateway Event Hooks |
| 24–33 | ↳ Trust model: placing the files is the opt-in {#gateway-hook-trust} |
| 34–83 | ↳ Creating a Hook |
| 84–107 | ↳ Available Events |
| 108–202 | ↳ Examples |
| 203–358 | ↳ Tutorial: BOOT.md — Run a Startup Checklist on Every Gateway Boot |
| 359–370 | ↳ How It Works |
| **371–1784** | **Plugin Hooks — читать подразделами ниже** |
| 371–400 | ↳ Введение Plugin Hooks |
| 401–444 | ↳ Cache-safe system prompt sections |
| 445–497 | ↳ Shipped plugin-hook catalog |
| 498–545 | ↳ Streaming output hooks |
| 546–624 | ↳ `pre_tool_call` |
| 625–675 | ↳ `post_tool_call` |
| 676–759 | ↳ `pre_llm_call` |
| 760–822 | ↳ `post_llm_call` |
| 823–887 | ↳ `pre_verify` |
| 888–904 | ↳ `transform_api_error_classification` |
| 905–945 | ↳ `on_session_start` |
| 946–1013 | ↳ `on_session_end` |
| 1014–1057 | ↳ `on_session_finalize` |
| 1058–1087 | ↳ `on_session_reset` |
| 1088–1114 | ↳ `agent_loop_stopped` |
| 1115–1185 | ↳ `subagent_start` |
| 1186–1234 | ↳ `subagent_stop` |
| 1235–1298 | ↳ `pre_gateway_dispatch` |
| 1299–1319 | ↳ `post_gateway_admission` |
| 1320–1360 | ↳ `gateway_platform_event` |
| 1361–1412 | ↳ `pre_approval_request` |
| 1413–1452 | ↳ `post_approval_response` |
| 1453–1482 | ↳ `on_human_input_request` |
| 1483–1516 | ↳ `on_human_input_resolved` |
| 1517–1561 | ↳ `on_room_member_activity` |
| 1562–1608 | ↳ `pre_transcription` |
| 1609–1641 | ↳ `transform_tool_result` |
| 1642–1686 | ↳ `transform_terminal_output` |
| 1687–1732 | ↳ `transform_llm_output` |
| 1733–1746 | ↳ API-request observer hooks |
| 1747–1752 | ↳ Auxiliary-call observer hooks |
| 1753–1756 | ↳ `on_skill_lifecycle` |
| 1757–1772 | ↳ Kanban lifecycle observers |
| 1773–1784 | ↳ Kanban worker-lifecycle, task-mutation, and dispatch observers |
| 1785–2061 | Shell Hooks — подразделы ниже |
| 1785–1799 | ↳ Введение Shell Hooks |
| 1800–1813 | ↳ Comparison at a glance |
| 1814–1831 | ↳ Configuration schema |
| 1832–1880 | ↳ JSON wire protocol |
| 1881–1898 | ↳ Exit code 2 = block (Claude Code / Cursor compatible) |
| 1899–1925 | ↳ Fail-open vs fail-closed |
| 1926–2008 | ↳ Worked examples |
| 2009–2039 | ↳ Consent model |
| 2040–2048 | ↳ The `hermes hooks` CLI |
| 2049–2057 | ↳ Security |
| 2058–2061 | ↳ Ordering and precedence |
| 2062–2147 | Outbound Webhooks |

## context-files

Источник: [context/context-files.md](context/context-files.md) — 249 строк, ≈3 095 токенов.

| Строки | Глава |
| --- | --- |
| 1–10 | Введение |
| 11–28 | Supported Context Files |
| 29–98 | AGENTS.md |
| 99–115 | SOUL.md |
| 116–121 | .cursorrules |
| 122–165 | How Context Files Are Loaded |
| 166–199 | Security: Prompt Injection Protection |
| 200–215 | Size Limits |
| 216–249 | Tips for Effective Context Files |

## context-references

Источник: [context/context-references.md](context/context-references.md) — 142 строки, ≈1 347 токенов.

| Строки | Глава |
| --- | --- |
| 1–11 | Введение |
| 12–23 | Supported References |
| 24–45 | Usage Examples |
| 46–53 | CLI Tab Completion |
| 54–64 | Line Ranges |
| 65–75 | Size Limits |
| 76–97 | Security |
| 98–103 | Platform Availability |
| 104–111 | Interaction with Context Compression |
| 112–129 | Common Patterns |
| 130–142 | Error Handling |

## personality

Источник: [context/personality.md](context/personality.md) — 289 строк, ≈2 436 токенов.

| Строки | Глава |
| --- | --- |
| 1–15 | Введение |
| 16–42 | How SOUL.md works now |
| 43–51 | Why this design |
| 52–65 | Where to edit it |
| 66–83 | What should go in SOUL.md? |
| 84–118 | Good SOUL.md content |
| 119–128 | What Hermes injects into the prompt |
| 129–134 | Security scanning |
| 135–158 | SOUL.md vs AGENTS.md |
| 159–172 | SOUL.md vs `/personality` |
| 173–193 | Built-in personalities |
| 194–211 | Switching personalities with commands |
| 212–231 | Custom personalities in config |
| 232–247 | Resetting to the default |
| 248–260 | Recommended workflow |
| 261–274 | How personality interacts with the full prompt |
| 275–281 | Related docs |
| 282–289 | CLI appearance vs conversational personality |

## tools

Источник: [tools/tools.md](tools/tools.md) — 265 строк, ≈3 787 токенов.

| Строки | Глава |
| --- | --- |
| 1–14 | Введение |
| 15–42 | Available Tools |
| 43–59 | Using Toolsets |
| 60–66 | Tool result annotations |
| 67–218 | Terminal Backends |
| 219–254 | Background Process Management |
| 255–265 | Sudo Support |

## batch-processing

Источник: [tools/batch-processing.md](tools/batch-processing.md) — 230 строк, ≈2 259 токенов.

| Строки | Глава |
| --- | --- |
| 1–10 | Введение |
| 11–14 | Overview |
| 15–40 | Quick Start |
| 41–54 | Dataset Format |
| 55–96 | Configuration Options |
| 97–102 | Toolset Distributions |
| 103–152 | Output Format |
| 153–169 | Checkpointing |
| 170–177 | Quality Filtering |
| 178–188 | Statistics |
| 189–230 | Use Cases |

## kanban

Источник: [kanban/kanban-big-context.md](kanban/kanban-big-context.md) — 1 449 строк, ≈30 568 токенов.

| Строки | Глава |
| --- | --- |
| 1–47 | Введение |
| 48–96 | PR completion contracts |
| 97–123 | Kanban vs. `delegate_task` |
| 124–140 | Core concepts |
| 141–256 | Boards (multi-project) |
| 257–289 | File attachments |
| 290–433 | Quick start |
| 434–456 | Enabling tools for a chat profile |
| 457–766 | How workers interact with the board — подразделы ниже |
| 457–514 | ↳ Введение How workers interact with the board |
| 515–526 | ↳ Why tools instead of shelling to `hermes kanban` |
| 527–560 | ↳ Recommended handoff evidence |
| 561–631 | ↳ The worker lifecycle |
| 632–668 | ↳ Pinning extra skills to a specific task |
| 669–684 | ↳ Per-task model override |
| 685–704 | ↳ Cost strategy: frontier orchestrator, inexpensive workers |
| 705–715 | ↳ Lifecycle plugin hooks |
| 716–737 | ↳ Goal-mode cards (`--goal`) |
| 738–766 | ↳ How the orchestrator behaves |
| 767–936 | Dashboard (GUI) |
| 937–1071 | CLI command reference |
| 1072–1143 | `/kanban` slash command {#kanban-slash-command} |
| 1144–1159 | Collaboration patterns |
| 1160–1229 | Handing context to follow-up cards (the parent link) |
| 1230–1242 | Multi-tenant usage |
| 1243–1248 | Desktop notifications |
| 1249–1341 | Gateway notifications |
| 1342–1399 | Runs — one row per attempt |
| 1400–1446 | Event reference |
| 1447–1449 | Out of scope |

## kanban-tutorial

Источник: [kanban/kanban-tutorial.md](kanban/kanban-tutorial.md) — 310 строк, ≈4 995 токенов.

| Строки | Глава |
| --- | --- |
| 1–4 | Введение |
| 5–18 | Setup |
| 19–39 | The board at a glance |
| 40–106 | Story 1 — Solo dev shipping a feature |
| 107–143 | Story 2 — Fleet farming |
| 144–206 | Story 3 — Role pipeline with retry |
| 207–261 | Story 4 — Circuit breaker and crash recovery |
| 262–274 | Structured handoff — why `summary` and `metadata` matter |
| 275–296 | Follow-up on a done card — CI remediation via the parent link |
| 297–304 | Inspecting a task currently running |
| 305–310 | Next steps |

## worker-lanes

Источник: [kanban/kanban-worker-lanes.md](kanban/kanban-worker-lanes.md) — 143 строки, ≈3 349 токенов.

| Строки | Глава |
| --- | --- |
| 1–11 | Введение |
| 12–22 | The hierarchy |
| 23–84 | What a lane provides |
| 85–96 | Outputs and the review handoff |
| 97–106 | Logs and audit trail |
| 107–118 | Existing lane shapes |
| 119–126 | Adding an external CLI worker lane |
| 127–138 | Failure modes the dispatcher handles |
| 139–143 | Related |

## multi-gateway

Источник: [kanban/kanban-multi-gateway.md](kanban/kanban-multi-gateway.md) — 52 строки, ≈562 токена.

| Строки | Глава |
| --- | --- |
| 1–18 | Введение |
| 19–30 | Single-dispatcher posture |
| 31–42 | Configuration |
| 43–52 | What each gateway does |

## tool-gateway

Источник: [tools/tool-gateway.md](tools/tool-gateway.md) — 249 строк, ≈4 124 токена.

| Строки | Глава |
| --- | --- |
| 1–17 | Введение |
| 18–28 | What's included |
| 29–39 | Why it's here |
| 40–80 | Get started |
| 81–86 | Eligibility |
| 87–95 | The enablement checklist |
| 96–111 | Mix and match |
| 112–121 | Using individual image models |
| 122–145 | Multiple connector accounts |
| 146–228 | Configuration reference |
| 229–249 | FAQ |

## adding-tools

Источник: [tools/adding-tools.md](tools/adding-tools.md) — 211 строк, ≈1 672 токена.

| Строки | Глава |
| --- | --- |
| 1–26 | Введение |
| 27–35 | Overview |
| 36–120 | Step 1: Create the Built-in Tool File |
| 121–139 | Step 2: Add the Built-in Tool to a Toolset |
| 140–143 | ~~Step 3: Add Discovery Import~~ (No longer needed) |
| 144–165 | Async Handlers |
| 166–181 | Handlers That Need task_id |
| 182–185 | Agent-Loop Intercepted Tools |
| 186–202 | Optional: Setup Wizard Integration |
| 203–211 | Checklist |

## architecture

Источник: [backend/architecture.md](backend/architecture.md) — 280 строк, ≈3 694 токена.

| Строки | Глава |
| --- | --- |
| 1–10 | Введение |
| 11–50 | System Overview |
| 51–138 | Directory Structure |
| 139–175 | Data Flow |
| 176–190 | Recommended Reading Order |
| 191–256 | Major Subsystems |
| 257–267 | Design Principles |
| 268–280 | File Dependency Chain |

## image-gen-provider-plugin

Источник: [tools/image-gen-provider-plugin.md](tools/image-gen-provider-plugin.md) — 321 строка, ≈3 310 токенов.

| Строки | Глава |
| --- | --- |
| 1–14 | Введение |
| 15–26 | How discovery works |
| 27–36 | Directory structure |
| 37–214 | The ImageGenProvider ABC |
| 215–228 | plugin.yaml |
| 229–242 | ABC reference |
| 243–272 | Response format |
| 273–276 | Handling base64 vs URL output |
| 277–280 | User overrides |
| 281–300 | Testing |
| 301–306 | Reference implementations |
| 307–316 | Distribute via pip |
| 317–321 | Related pages |

## subagent-lifecycle-api

Источник: [backend/subagent-lifecycle-api.md](backend/subagent-lifecycle-api.md) — 61 строка, ≈737 токенов. H2/H3 нет: читать целиком `offset=1, limit=61`.

| Строки | Глава |
| --- | --- |
| 1–61 | Вся страница: launch, status, wait, cancel, result, reconnect и ограничения lifetime |

## tools-runtime

Источник: [tools/tools-runtime.md](tools/tools-runtime.md) — 250 строк, ≈2 997 токенов.

| Строки | Глава |
| --- | --- |
| 1–18 | Введение |
| 19–70 | Tool registration model |
| 71–96 | Tool availability checking (`check_fn`) |
| 97–123 | Toolset resolution |
| 124–183 | Dispatch |
| 184–207 | The DANGEROUS_PATTERNS approval flow |
| 208–240 | Terminal/runtime environments |
| 241–244 | Concurrency |
| 245–250 | Related docs |

## video-gen-provider-plugin

Источник: [tools/video-gen-provider-plugin.md](tools/video-gen-provider-plugin.md) — 233 строки, ≈2 327 токенов.

| Строки | Глава |
| --- | --- |
| 1–14 | Введение |
| 15–23 | The unified surface (one tool, two modalities) |
| 24–33 | How discovery works |
| 34–41 | Directory structure |
| 42–153 | The VideoGenProvider ABC |
| 154–166 | The plugin manifest |
| 167–186 | The `video_generate` schema |
| 187–207 | Model families and endpoint routing (the FAL pattern) |
| 208–218 | Selection precedence |
| 219–226 | Response shape |
| 227–230 | Where to save artifacts |
| 231–233 | Testing |

## kanban-context

Документ: [kanban/kanban-context.md](kanban/kanban-context.md) — 500 строк, ≈8 761 токен. Авторский дистиллят с источниками и явными разночтениями; для общего понимания Kanban читать раньше больших справочников.

| Строки | Глава |
| --- | --- |
| 1–25 | Введение: границы исполнения и обозначения источников |
| 26–50 | Сущности и места хранения |
| 51–75 | Состояния карточки и зависимый запуск |
| 76–100 | Dispatcher, профиль и worker lane |
| 101–125 | Claim, идентичность попытки и восстановление |
| 126–150 | Протокол исполнения и причины остановки |
| 151–175 | Handoff, workspace и сохраняемые результаты |
| 176–200 | Проверка, доработка и новые задачи |
| 201–225 | Три разных источника оркестрации |
| 226–250 | События, уведомления и доставка обратно |
| 251–275 | delegate_task: контекст и область ответственности |
| 276–300 | Делегирование: lifetime, batch и процессы |
| 301–325 | Долговечность результатов и рабочей копии child |
| 326–350 | Goal engine и отдельное состояние /goal |
| 351–375 | Публичный Subagent Lifecycle API |
| 376–400 | Сквозной сценарий: одна работа, несколько исполнителей |
| 401–425 | Разночтения источников и пределы выводов |
| 426–500 | Кастомный плагин: подключение существующего Hermes backend |
| 426–450 | ↳ Введение: регистрация, REST/WS и корреляция сущностей |
| 451–475 | ↳ Активный turn, child lifecycle и доставка сообщения |
| 476–500 | ↳ Hooks, HTTP-границы и минимальная приёмка адаптера |
