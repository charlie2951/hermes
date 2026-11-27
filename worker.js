let tcadFactoryPromise = null;

async function getTCADFactory() {
  if (!tcadFactoryPromise) {
    tcadFactoryPromise = (async () => {
      // Try ES6 module import first (works when compiled with -sEXPORT_ES6=1)
      try {
        const mod = await import('./hermes2d.js');
        if (typeof mod.default === 'function') return mod.default;
        if (typeof mod.createTCADModule === 'function') return mod.createTCADModule;
      } catch (_) {
        // Fallback if hermes2d.js was compiled without -sEXPORT_ES6=1
      }

      // Fallback: evaluate script in worker scope and grab global createTCADModule
      const resp = await fetch('./hermes2d.js');
      if (!resp.ok) {
        throw new Error(`Failed to fetch hermes2d.js (HTTP ${resp.status})`);
      }
      const code = await resp.text();
      (0, eval)(code);

      if (typeof self.createTCADModule === 'function') {
        return self.createTCADModule;
      }
      if (typeof createTCADModule === 'function') {
        return createTCADModule;
      }
      throw new Error('createTCADModule factory not found in hermes2d.js');
    })();
  }
  return tcadFactoryPromise;
}

self.onmessage = async (e) => {
  const { deckText, outCsvName } = e.data;
  const targetCsv = (outCsvName || 'iv_output.csv').replace(/^\/+/, '');

  self.postMessage({ type: 'stdout', text: '[WASM] Loading HERMES-2D module...' });

  try {
    const createTCADModule = await getTCADFactory();

    const Module = await createTCADModule({
      locateFile: (path) => './' + path,
      print: (text) => self.postMessage({ type: 'stdout', text }),
      printErr: (text) => self.postMessage({ type: 'stderr', text }),
    });

    self.postMessage({ type: 'stdout', text: '[WASM] Writing /input.deck and starting solver...' });
    Module.FS.writeFile('/input.deck', deckText);

    // Execute C main(argc, argv)
    const exitCode = Module.callMain(['/input.deck']);
    if (exitCode !== undefined && exitCode !== 0) {
      self.postMessage({ type: 'stderr', text: `[WASM] Solver exited with code ${exitCode}` });
    }

    // Read generated CSV and VTK outputs from virtual RAM
    let csv = null;
    let vtk = null;

    try {
      csv = Module.FS.readFile('/' + targetCsv, { encoding: 'utf8' });
    } catch (_) {
      self.postMessage({ type: 'stderr', text: `[WASM] Warning: Output file '/${targetCsv}' was not generated.` });
    }

    try {
      vtk = Module.FS.readFile('/device_final.vtk', { encoding: 'utf8' });
    } catch (_) {
      // Optional VTK output
    }

    self.postMessage({ type: 'done', csv, vtk });
  } catch (err) {
    self.postMessage({
      type: 'error',
      text: err && err.stack ? err.stack : String(err),
    });
  }
};