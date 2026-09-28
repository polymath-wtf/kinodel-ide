# Kinodel cinematic prototype

Open `index.html` directly in a browser. No installation, build, server or network access is required.

- Wheel zooms around the cursor; middle-button or empty-canvas drag pans. Drag a card by its header. `Fit` and `Current stage` help navigate.
- Single-click a node/image for its inspector; double-click to enter; right-click canvas to go up one scope. Keyboard: Enter opens details, Shift+Enter enters a nested node. Breadcrumbs also go back; each scope retains its layout until reload.
- Brief includes a local **demo character-chunk picker**; selection survives scope navigation until reload, but no canonical library or submission is connected.
- Storytell, Wardrobe, Storyboard and Filmmaker show agent / generation tool / review stages. Storyboard's `frames-gen` is labeled **Batch generation** in the UI. Wardrobe has one three-anchor preview; Batch generation opens a 3×3 candidate canvas; Video generation has one clip per shot. Double-click a candidate or clip for a diagram of nodes and connections from its corresponding ComfyUI API-prompt JSON in `workflow/comfyui/` (selected nodes only).
- Drag the header or empty area of an anchor/frame/video preview window to move its entire contents. Sockets are labeled by input/output; workflow wires attach to the source output index and exact target input in the API prompt. Only the canvas has the blurred blue-gray/warm-stone backdrop.
- All four creative roles use one `llm-agent` shell with role-specific system-prompt configuration. Its interior illustrates `START → Model → END`, with conditional `Model → ToolNode → Model` for one proposed read-only `read_selected_reference(alias)` tool. Instructions/model settings are configuration, not executable nodes; validation/saving is outside the loop. This is a design specimen, not the currently integrated backend agent. Pattern: [LangGraph quickstart](https://docs.langchain.com/oss/python/langgraph/quickstart), [ToolNode loop](https://docs.langchain.com/langsmith/trace-with-langgraph#3-log-a-trace).
- A frame's inspector lets you edit a local prompt/seed; `Regenerate · mock` changes its example tile to queued and resets the seed unless you entered a new one. No job is submitted.

All outputs, statuses and prompts are **mock data**. Workflow diagrams use real API node IDs, class types, source output indices and target input names; socket type labels are UI descriptions inferred from their role, not provider socket schemas. These are partial projections of unaudited provider files, not registered profiles. No backend, job execution, approval or working Chat. `Final` represents Montage output, not a separate approval.

Photographs in `assets/` are illustrative stock images, not a consistent generated character: [portrait](https://images.unsplash.com/photo-1534528741775-53994a69daeb?fm=jpg&w=720&q=82&fit=crop), [wardrobe](https://images.unsplash.com/photo-1544022613-e87ca75a784a?fm=jpg&w=720&q=82&fit=crop), [coast](https://images.unsplash.com/photo-1518837695005-2083093ee35b?fm=jpg&w=1000&q=82&fit=crop). [Unsplash license](https://unsplash.com/license).

Optional browser check: `prototype-check.cjs` uses Playwright if installed separately (`PLAYWRIGHT_MODULE` may point to its installed package). The prototype itself has no dependencies.
