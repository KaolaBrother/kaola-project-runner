import importlib.util, shutil
from pathlib import Path
root=Path('/Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-259')
p=root/'tests/contract/test-issue-123-shared-refs.py'
spec=importlib.util.spec_from_file_location('shared_copy_shape',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sandbox=m.Sandbox('997-copy-shape')
try:
    assert sandbox.env()['KAOLA_LAUNCH_BACKEND']=='direct'
    # Copy one generated Skill into the fixture HOME. Do not call an installer.
    target=sandbox.shared/'dsh-kaola-project-runner'
    shutil.copytree(root/'skills/dsh-kaola-project-runner',target)
    m.worker_chain(sandbox,'dsh')
    print('PASS isolated shared-root copy: existing worker_chain start/observe/send/capture/exact-stop')
    print('Checks:',len(m.CHECKS))
finally:
    sandbox.cleanup()
    assert not sandbox.dir.exists()
    print('Fixture cleanup: removed',sandbox.dir)
