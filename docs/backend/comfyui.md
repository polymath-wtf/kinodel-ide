# ComfyUI Boundary

Status: **Provider/service design**

ComfyUI is a first-class local or remote render backend. A large deterministic ComfyUI graph appears to Kinodel as one provider workflow with typed inputs, outputs, and capability metadata.

## Contract

Creative agents produce provider-neutral image/video/audio intent. The ComfyUI adapter owns:

- workflow registration and versioning;
- semantic-input to node-input mapping;
- endpoint health/readiness;
- upload and asset materialization;
- submit, queue reconciliation, progress, cancellation where supported;
- output discovery, download/import, and technical audit.

## Rules

- One workflow registry is authoritative; do not duplicate aliases in Python and JSON.
- Every workflow declares accepted job kinds and required inputs.
- Workflow version participates in the render job fingerprint.
- Secrets, raw workflows, queue IDs, and logs stay out of creative artifacts.
- A local `/view` URL is a preview, not durable asset identity.
- Timeout may mean the GPU job still runs; reconcile queue/history before retry.
- Provider health checks use real readiness endpoints and do not generate paid content.

## ALM

Audio analysis may be implemented through ComfyUI when a validated workflow exists. To Kinodel it remains a typed analysis service: audio asset in, timing/section/features artifact out. The pipeline must not depend on which backend produced the analysis.

Implementation reference: `skills/comfyui-skill/`.
