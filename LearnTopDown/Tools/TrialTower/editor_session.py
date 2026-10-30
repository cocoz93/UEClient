"""Task-owned editor command queue; runs only inside this task's editor."""
import json
import os
from pathlib import Path
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = Path(os.environ['TRIAL_TOWER_OUTPUT'])
QUEUE = OUT / 'queue'
QUEUE.mkdir(parents=True, exist_ok=True)
CONTEXT = {'unreal': unreal, 'ROOT': ROOT, 'OUT': OUT, '__name__': '__trial_tower__'}
BUSY = False

def tick(delta):
    global BUSY
    if BUSY:
        return
    requests = sorted(QUEUE.glob('*.request.json'))
    if not requests:
        return
    request_file = requests[0]
    request = json.loads(request_file.read_text(encoding='utf-8-sig'))
    request_file.rename(request_file.with_suffix('.running'))
    BUSY = True
    result = {'id': request['id'], 'passed': False}
    try:
        CONTEXT.pop('RESULT', None)
        exec(compile(request['code'], str(request_file), 'exec'), CONTEXT)
        result.update(passed=True, result=CONTEXT.get('RESULT'))
    except Exception:
        result['error'] = traceback.format_exc()
        unreal.log_error(result['error'])
    finally:
        (QUEUE / (request['id'] + '.result.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        BUSY = False

HANDLE = unreal.register_slate_post_tick_callback(tick)
(OUT / 'ready.json').write_text(json.dumps({'ready': True, 'pid': os.getpid()}), encoding='utf-8')
unreal.log('TRIAL_TOWER_SESSION_READY')
