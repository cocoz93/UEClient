"""One unattended editor per project: avoid competing for the same GPU budget."""
from contextlib import contextmanager
import msvcrt
from pathlib import Path
import time

@contextmanager
def render_slot(project: Path, timeout=1200):
    path=project/'Saved/QA/CharacterPipeline/render.lock'
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as handle:
        handle.seek(0,2)
        if handle.tell()==0:
            handle.write(b'0')
            handle.flush()
        started=time.monotonic()
        announced=False
        while True:
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
                break
            except OSError:
                if time.monotonic()-started>=timeout:
                    raise TimeoutError('Another CharacterPipeline editor still owns the project render slot')
                if not announced:
                    print('Waiting for the project CharacterPipeline render slot',flush=True)
                    announced=True
                time.sleep(.1)
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
