#!/usr/bin/env node
/**
 * gvskb_gate.js — 하네스 집행 게이트 (Node.js 래퍼)
 *
 * 판정 로직은 전부 gvskb_gate.py에 있다. 이 파일은 그걸 감싸는 얇은 래퍼일 뿐,
 * 같은 보안 판단을 두 언어로 각자 구현하지 않는다(각자 구현하면 반드시
 * 드리프트가 생긴다 — 예: Python은 쿨다운을 차단하는데 JS는 깜빡 잊는 식).
 *
 * npm/yarn/pnpm 프로젝트(Track B·N)에서 새 패키지를 설치할 때는
 * `npm install X` 를 직접 쓰지 말고 항상 이 스크립트를 거친다:
 *
 *   node .claude/enforcement/gvskb_gate.js check   <패키지명> [--json]
 *   node .claude/enforcement/gvskb_gate.js install <패키지명> [--version V]
 *
 * 전제조건: gvskb_gate.py가 같은 폴더에 있고, gvskb(vibecode-checker)가
 * GVSKB_GATE_PYTHON(또는 PATH의 python3/python)으로 실행 가능한 파이썬 환경에
 * 설치되어 있어야 한다.
 */

'use strict';

const path = require('path');
const { spawnSync } = require('child_process');

const EXIT_PASS = 0;
const EXIT_WARN = 1;
const EXIT_BLOCK = 2;
const EXIT_USAGE = 64;

function resolvePython() {
  // Windows의 "python"이 실제 인터프리터가 아니라 Microsoft Store 스텁으로
  // 연결된 경우가 흔하다 — 그래서 명시적 override를 최우선으로 둔다.
  if (process.env.GVSKB_GATE_PYTHON) return process.env.GVSKB_GATE_PYTHON;
  return process.platform === 'win32' ? 'python' : 'python3';
}

function gatePyPath() {
  return path.join(__dirname, 'gvskb_gate.py');
}

/**
 * gvskb_gate.py를 서브프로세스로 실행하고 표준 출력을 그대로 사람이 보게 흘려보낸다.
 * 판정 로직은 절대 여기서 다시 구현하지 않는다 — Python 프로세스의 종료 코드가
 * 곧 최종 판정이다(0=통과, 1=경고, 2=차단).
 */
function runGate(subcommand, name, opts) {
  const python = resolvePython();
  const args = [gatePyPath(), subcommand, name, '--ecosystem', 'npm'];
  if (opts.version) args.push('--version', opts.version);
  if (opts.mode) args.push('--mode', opts.mode);
  if (opts.env) args.push('--env', opts.env);
  if (opts.exceptionCode) args.push('--exception-code', opts.exceptionCode);
  if (opts.json) args.push('--json');

  const result = spawnSync(python, args, { encoding: 'utf-8' });

  if (result.error && result.error.code === 'ENOENT') {
    console.error(
      `[gvskb_gate.js] 파이썬 실행 파일을 찾을 수 없습니다: ${python}\n` +
      '  GVSKB_GATE_PYTHON 환경변수로 실제 파이썬 경로를 지정하세요 ' +
      '(예: set GVSKB_GATE_PYTHON=C:\\Python312\\python.exe).'
    );
    return { code: EXIT_USAGE, stdout: '', stderr: '' };
  }
  return { code: result.status == null ? EXIT_USAGE : result.status, stdout: result.stdout, stderr: result.stderr };
}

function cliCheck(name, opts) {
  const { code, stdout, stderr } = runGate('check', name, opts);
  if (stdout) process.stdout.write(stdout);
  if (stderr) process.stderr.write(stderr);
  return code;
}

function cliInstall(name, opts) {
  // 먼저 gate 판정만 받는다(설치는 아직 안 함) — Python쪽 install 서브커맨드는
  // pip 전용이므로 npm 설치는 이 JS 파일이 직접 수행한다.
  const checkOpts = Object.assign({}, opts, { json: true });
  const { code, stdout, stderr } = runGate('check', name, checkOpts);
  if (stderr) process.stderr.write(stderr);

  let decision;
  try {
    decision = JSON.parse(stdout);
  } catch (e) {
    console.error('[gvskb_gate.js] gvskb_gate.py 출력 파싱 실패 — 게이트를 신뢰할 수 없어 설치를 진행하지 않습니다.');
    console.error(stdout);
    return EXIT_USAGE;
  }

  printDecision(decision);

  if (decision.action === 'block') {
    console.error('[gvskb_gate.js] 설치를 진행하지 않았습니다.');
    return EXIT_BLOCK;
  }

  const spec = opts.version ? `${name}@${opts.version}` : name;
  const npmArgs = ['install', spec];
  if (!opts.allowScripts) {
    // VCPS C2 — 설치 스크립트는 보안 점검보다 먼저 실행되므로 기본 차단한다.
    npmArgs.push('--ignore-scripts');
  }
  console.error(`[gvskb_gate.js] 설치 진행: npm ${npmArgs.join(' ')}`);
  const install = spawnSync('npm', npmArgs, { stdio: 'inherit', shell: process.platform === 'win32' });
  return install.status == null ? EXIT_USAGE : install.status;
}

function printDecision(decision) {
  const label = { pass: '[통과]', warn: '[경고]', block: '[차단]' }[decision.action] || '[?]';
  console.log(`${label} ${decision.ecosystem}:${decision.package} (모드=${decision.mode}, 등급=${decision.env_grade})`);
  (decision.reasons || []).forEach((r) => console.log(`  - ${r}`));
}

function parseArgs(argv) {
  const [command, name, ...rest] = argv;
  const opts = { json: false, version: null, mode: null, env: null, allowScripts: false, exceptionCode: null };
  for (let i = 0; i < rest.length; i += 1) {
    const a = rest[i];
    if (a === '--json') opts.json = true;
    else if (a === '--version') opts.version = rest[++i];
    else if (a === '--mode') opts.mode = rest[++i];
    else if (a === '--env') opts.env = rest[++i];
    else if (a === '--allow-scripts') opts.allowScripts = true;
    else if (a === '--exception-code') opts.exceptionCode = rest[++i];
  }
  return { command, name, opts };
}

function main() {
  const { command, name, opts } = parseArgs(process.argv.slice(2));
  if (!command || !name || !['check', 'install'].includes(command)) {
    console.error(
      '사용법:\n' +
      '  node gvskb_gate.js check   <패키지명> [--version V] [--mode MONITOR|WARN|ENFORCE] [--env E0|E1|E2] [--exception-code CODE] [--json]\n' +
      '  node gvskb_gate.js install <패키지명> [--version V] [--allow-scripts] [--exception-code CODE]'
    );
    process.exit(EXIT_USAGE);
  }
  const code = command === 'check' ? cliCheck(name, opts) : cliInstall(name, opts);
  process.exit(code);
}

if (require.main === module) {
  main();
}

module.exports = { runGate, resolvePython };
