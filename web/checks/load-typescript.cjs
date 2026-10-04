// Pure TypeScript check modules only; no runner or extra compiler dependency.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const frontend = path.resolve(__dirname, '..');
const cache = new Map();

function load(file) {
  file = path.resolve(frontend, file);
  assert.ok(fs.existsSync(file), `TypeScript module must exist: ${file}`);
  if (cache.has(file)) return cache.get(file).exports;
  const compiled = new Module(file, module);
  compiled.filename = file;
  compiled.paths = Module._nodeModulePaths(path.dirname(file));
  compiled.require = name => name.startsWith('.')
    ? load(path.resolve(path.dirname(file), name.endsWith('.ts') ? name : `${name}.ts`))
    : Module.prototype.require.call(compiled, name);
  cache.set(file, compiled);
  try {
    compiled._compile(ts.transpileModule(fs.readFileSync(file, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText, file);
    compiled.loaded = true;
    return compiled.exports;
  } catch (error) {
    cache.delete(file);
    throw error;
  }
}
module.exports = load;
