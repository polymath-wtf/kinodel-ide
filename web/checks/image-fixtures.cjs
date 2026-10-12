const f = require('./continue-fixtures.cjs');
const hash = value => `sha256:${value.repeat(64)}`;
const images = { schema_version: '1', execution_id: f.consumer, project_id: f.id, group_id: f.digest,
  total_units: 3, available_units: 1, result: null, units: f.plan.batch_prompt.map((u, index) => {
    const media_ref = { execution_id: f.consumer, group_id: f.digest, unit_key: u.unit_key, job_id: hash('b'),
      attempt_id: hash('c'), unit_input_digest: hash('d'), origin_execution_id: f.consumer, candidate_id: hash(String(index + 1)),
      candidate_digest: hash('e'), candidate_metadata_digest: hash('f') };
    const { execution_id, candidate_id, ...selectors } = media_ref;
    return { unit_key: u.unit_key, use_case: u.use_case, available: index === 0, reason: index === 0 ? null : 'unstarted',
      original: index === 0 ? { media_ref, mime_type: 'image/png', byte_length: 100, width: 512, height: 768,
        url: `/api/executions/${execution_id}/images/candidates/${encodeURIComponent(candidate_id)}/original?${new URLSearchParams(selectors)}` } : null };
  }) };
const full = structuredClone(images);
full.available_units = 3;
full.units = images.units.map((u, index) => {
  const media_ref = { ...images.units[0].original.media_ref, unit_key: u.unit_key, candidate_id: hash(String(index + 1)) };
  const { execution_id, candidate_id, ...selectors } = media_ref;
  return { ...u, available: true, reason: null, original: { ...images.units[0].original, media_ref,
    width: index === 0 ? 512 : 1024, height: index === 0 ? 768 : 512,
    url: `/api/executions/${execution_id}/images/candidates/${encodeURIComponent(candidate_id)}/original?${new URLSearchParams(selectors)}` } };
});
const result = { result_id: hash('9'), digest: hash('8'), status: 'complete', issue: null };
const process = { ...f.process, effective_execution_id: f.consumer, group_id: f.digest, status: 'waiting_job',
  action: 'open', reason: 'external_work', allowed_actions: ['continue', 'cancel'], image_progress: { completed: 1, total: 3 }, production: f.production };
module.exports = { ...f, images, full, result, process };
