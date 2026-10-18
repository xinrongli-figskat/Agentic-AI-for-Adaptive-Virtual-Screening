"""Prepare locally from verified existing evidence; execute/resume with bounded GLM calls."""
import argparse
import json
import platform
import shutil
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .controller import GLM
from .engine import Engine, import_catalog, read, save, sha, signature

PACKAGE = Path(__file__).parent


def source_hashes():
    return {str(p.relative_to(PACKAGE)).replace('\\', '/'): sha(p)
            for p in sorted(PACKAGE.rglob('*')) if p.is_file() and p.suffix in ('.py', '.json', '.md')
            and '__pycache__' not in p.parts}


def environment():
    import rdkit
    import numpy
    return {'python': platform.python_version(), 'rdkit': rdkit.__version__, 'numpy': numpy.__version__}


def validate_protocol(p):
    integer_fields = ['minimum_usable_compounds', 'minimum_hits', 'minimum_nonhits',
        'minimum_confidence_score', 'minimum_scaffold_buckets', 'query_budget',
        'initialization_queries', 'feedback_batch_size', 'maximum_target_window',
        'maximum_assay_records', 'maximum_pairwise_compounds', 'maximum_http_requests',
        'maximum_llm_attempts', 'page_size', 'maximum_output_tokens', 'request_timeout_seconds']
    for field in integer_fields:
        if type(p[field]) is not int or p[field] <= 0:
            raise ValueError('Invalid positive-integer protocol field: ' + field)
    for field in ['maximum_largest_cluster_fraction', 'maximum_initial_single_class_probability']:
        if not isinstance(p[field], (int, float)) or not 0 < p[field] <= 1:
            raise ValueError('Invalid fraction: ' + field)
    if not 0 < p['initialization_queries'] < p['query_budget'] <= p['minimum_usable_compounds']:
        raise ValueError('Invalid proposed campaign budget')
    if p['model'] != 'glm-5.3-flash' or p['hit_threshold_nM'] != '1000':
        raise ValueError('This prototype has reviewed settings only for glm-5.3-flash and IC50 1000 nM')


def prepare(source, output_root, protocol_path=PACKAGE / 'protocol.json'):
    p = read(protocol_path)
    validate_protocol(p)
    catalog, release = import_catalog(source)
    folder = Path(output_root) / ('curation_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:8])
    folder.mkdir(parents=True, exist_ok=False)
    save(folder / 'catalog.json', catalog)
    hashes = source_hashes()
    for relative in hashes:
        destination = folder / 'source_snapshot' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PACKAGE / relative, destination)
    state = {'schema': 'task1_agent_v1.0', 'status': 'prepared', 'release': release,
             'protocol': p, 'protocol_sha256': signature(p), 'code_sha256': hashes,
             'catalog_sha256': sha(folder / 'catalog.json'),
             'seed_discovery_source': str(Path(source).resolve()),
             'seed_metadata_sha256': sha(Path(source) / 'run_metadata.json'),
             'requests': [], 'profiles': {}, 'known_assays': {}, 'assays': {}, 'evidence': {},
             'shortlist': [], 'events': [], 'llm_attempts': 0, 'pending_action': None,
             'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
             'environment': environment(),
             'created_at_utc': datetime.now(timezone.utc).isoformat()}
    save(folder / 'state.json', state)
    engine = Engine(folder, state)
    engine.import_seed_profiles(source)
    engine.report()
    save(Path(output_root) / 'latest_prepared.json', {'run_dir': str(folder.resolve())})
    return folder


def load_engine(folder):
    folder = Path(folder)
    state = read(folder / 'state.json')
    validate_protocol(state['protocol'])
    if signature(state['protocol']) != state['protocol_sha256'] or source_hashes() != state['code_sha256']:
        raise ValueError('Protocol or code changed since preparation; create a new run/version')
    if state['environment'] != environment():
        raise ValueError('Scientific runtime changed since preparation; create a new run/version')
    if sha(folder / 'catalog.json') != state['catalog_sha256']:
        raise ValueError('Catalog hash mismatch')
    for relative, expected in state['code_sha256'].items():
        if sha(folder / 'source_snapshot' / relative) != expected:
            raise ValueError('Saved code snapshot hash mismatch')
    engine = Engine(folder, state)
    for key in state['evidence']:
        engine.cited(key)
    for receipt in state['requests']:
        if receipt.get('sha256') and sha(folder / receipt['raw_file']) != receipt['sha256']:
            raise ValueError('Saved source-response hash mismatch')
    return engine


@contextmanager
def single_writer(folder):
    """OS lock releases even after a crash; concurrent resume cannot duplicate actions."""
    with (Path(folder) / '.writer.lock').open('a+b') as handle:
        handle.seek(0)
        handle.write(b'0')
        handle.flush()
        handle.seek(0)
        if platform.system() == 'Windows':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if platform.system() == 'Windows':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def refresh_usage(engine):
    totals = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
    for path in (engine.folder / 'llm').glob('*.json'):
        usage = read(path).get('usage') or {}
        for key in totals:
            totals[key] += int(usage.get(key) or 0)
    engine.state['usage'] = totals
    engine.checkpoint()


def run_steps(engine, controller, steps):
    state = engine.state
    if state['status'] == 'finished':
        return engine.report()
    # Fresh status check on EVERY invocation; never reuse a previous status response.
    status = engine.client.get('status')
    if status.get('chembl_db_version') != state['release']:
        raise ValueError('ChEMBL release changed; create a new discovery snapshot and version')
    state['status'] = 'running'
    engine.checkpoint()
    for _ in range(steps):
        if state['pending_action'] is None:
            if state['llm_attempts'] >= engine.p['maximum_llm_attempts']:
                state['status'] = 'llm_budget_exhausted'
                break
            number = state['llm_attempts'] + 1
            state['llm_attempts'] = number
            receipt = engine.folder / 'llm' / f'{number:04d}.json'
            engine.checkpoint()  # Interrupted requests still consume an attempt.
            try:
                decision = controller.call(engine.context(), receipt)
                state['pending_action'] = {'decision': decision, 'attempt': number,
                                           'receipt': str(receipt.relative_to(engine.folder))}
                engine.checkpoint()
            except (ValueError, RuntimeError):
                state['events'].append({'kind': 'llm_failure', 'attempt': number,
                                        'receipt': str(receipt.relative_to(engine.folder))})
                state['status'] = 'paused_after_llm_failure'
                engine.checkpoint()
                refresh_usage(engine)
                engine.report()
                raise
            refresh_usage(engine)
        pending = state['pending_action']
        decision = pending['decision']
        started = time.monotonic()
        event = {'kind': 'tool_action', 'decision': decision, 'llm_attempt': pending['attempt'],
                 'receipt': pending['receipt']}
        try:
            value = engine.execute(decision['action'], decision['arguments'])
            event['result'] = value
            event['status'] = 'success'
        except Exception as error:
            # Tool failure is evidence for the next choice; no fabricated fallback result.
            event['status'] = 'tool_error'
            event['error_type'] = type(error).__name__
            event['error'] = str(error)[:500]
        event['elapsed_seconds'] = time.monotonic() - started
        state['events'].append(event)
        state['pending_action'] = None
        engine.checkpoint()
        print(json.dumps({'attempt': pending['attempt'], 'action': decision['action'],
                          'arguments': decision['arguments'], 'status': event['status'],
                          'shortlist': state['shortlist']}, ensure_ascii=False), flush=True)
        engine.report()
        if state['status'] == 'finished':
            break
        if len(state['requests']) >= engine.p['maximum_http_requests']:
            state['status'] = 'http_budget_exhausted'
            break
    if state['status'] == 'running':
        state['status'] = 'paused_at_step_limit'
    engine.checkpoint()
    return engine.report()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prep = commands.add_parser('prepare', help='Offline, verified import; no API key needed')
    prep.add_argument('--discovery-run', type=Path, required=True)
    prep.add_argument('--output-root', type=Path, required=True)
    execute = commands.add_parser('execute', help='Execute or resume the SAME run')
    execute.add_argument('--run-dir', type=Path, required=True)
    execute.add_argument('--steps', type=int, default=8)
    inspect = commands.add_parser('status', help='Read and verify progress; no API key needed')
    inspect.add_argument('--run-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        folder = prepare(args.discovery_run, args.output_root)
        print(json.dumps({'prepared_dir': str(folder.resolve()), 'uses_glm': False,
                          'status': 'prepared_not_executed'}, indent=2))
        return
    if args.command == 'execute' and not 1 <= args.steps <= 30:
        parser.error('--steps must be 1..30')
    with single_writer(args.run_dir):
        engine = load_engine(args.run_dir)
        if args.command == 'execute':
            try:
                report = run_steps(engine, GLM(engine.p), args.steps)
            except (ValueError, RuntimeError, OSError) as error:
                engine.report()
                print(json.dumps({'paused': True, 'error_type': type(error).__name__,
                                  'message': str(error), 'run_dir': str(args.run_dir)}, ensure_ascii=False))
                raise SystemExit(1)
        else:
            report = engine.report()
        print(json.dumps({k: report[k] for k in ('status', 'profiles_examined', 'assays_inspected',
            'shortlist', 'llm_attempts', 'http_attempts', 'llm_usage_returned', 'campaign_ready')}, indent=2))


if __name__ == '__main__':
    main()
