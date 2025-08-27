/*
  @license
	Rollup.js v4.48.1
	Mon, 25 Aug 2025 05:42:43 GMT - commit 8b6b06b16c2198f1e61749f17cbdbc25f2d3d214

	https://github.com/rollup/rollup

	Released under the MIT License.
*/
export { version as VERSION, defineConfig, rollup, watch } from './shared/node-entry.js';
import './shared/parseAst.js';
import '../native.js';
import 'node:path';
import 'path';
import 'node:process';
import 'node:perf_hooks';
import 'node:fs/promises';
