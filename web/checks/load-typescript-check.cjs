// Loader regression: real source imports/packages, normalized cache and missing files.
const assert = require('node:assert/strict');
const path = require('node:path');
const load = require('./load-typescript.cjs');
const http = load('src/shared/api/http.ts');
assert.equal(load(path.resolve(__dirname, '../src/shared/api/http.ts')), http);
assert.equal(load('src/shared/api/../api/http.ts').ReadError, http.ReadError, 'one class identity per source module');
const queries = load('src/entities/execution/queries.ts');
assert.equal(typeof queries.useProjection, 'function', 'recursive relative imports and frontend packages load');
assert.throws(() => load('src/shared/api/missing-loader-check.ts'), /TypeScript module must exist/);
console.log('PASS: shared TypeScript loader, recursive relative imports, frontend packages, stable module/class cache, existence assertion');
