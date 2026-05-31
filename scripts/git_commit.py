#!/usr/bin/env python3
"""
Git plumbing commit helper.
Works around stale index.lock by using git low-level commands directly.
Usage: python3 scripts/git_commit.py "commit message"
"""
import os, subprocess, sys
from pathlib import Path

# -------------------------------------------------------------------
# What to exclude (mirrors .gitignore + always-skip)
# -------------------------------------------------------------------
SKIP_NAMES  = {'.env', 'node_modules', '__pycache__', '.venv', '.git',
               'exports', 'logs', '.DS_Store'}
SKIP_EXTS   = {'.pyc', '.log', '.jsonl'}
KEEP_DOTFILES = {'.gitignore', '.env.example'}

def git(*args, inp=None):
    env = os.environ.copy()
    env.update({
        'GIT_AUTHOR_NAME':     'Vaani Build',
        'GIT_AUTHOR_EMAIL':    'sagar@vaani.ai',
        'GIT_COMMITTER_NAME':  'Vaani Build',
        'GIT_COMMITTER_EMAIL': 'sagar@vaani.ai',
    })
    r = subprocess.run(['git'] + list(args), capture_output=True,
                       text=True, input=inp, env=env)
    return r.stdout.strip(), r.returncode

def hash_blob(path: Path) -> str:
    out, rc = git('hash-object', '-w', str(path))
    if rc != 0:
        raise RuntimeError(f'hash-object failed: {path}')
    return out

def mktree(entries: list[tuple]) -> str:
    """entries: [(mode, type, hash, name), ...]"""
    lines = ''.join(f'{m} {t} {h}\t{n}\n' for m, t, h, n in entries)
    out, rc = git('mktree', inp=lines)
    if rc != 0:
        raise RuntimeError(f'mktree failed')
    return out

def build_tree(path: Path) -> str | None:
    entries = []
    for item in sorted(path.iterdir()):
        n = item.name
        if n in SKIP_NAMES:                              continue
        if n.startswith('.') and n not in KEEP_DOTFILES: continue
        if item.suffix in SKIP_EXTS:                     continue
        if item.is_symlink():                            continue

        if item.is_file():
            h = hash_blob(item)
            entries.append(('100644', 'blob', h, n))
        elif item.is_dir():
            sub = build_tree(item)
            if sub:
                entries.append(('040000', 'tree', sub, n))

    return mktree(entries) if entries else None

def current_branch_ref() -> str:
    head = Path('.git/HEAD').read_text().strip()
    if head.startswith('ref: '):
        return head[5:]
    raise RuntimeError('Detached HEAD')

def read_ref(ref: str) -> str | None:
    p = Path('.git') / ref
    if p.exists():
        return p.read_text().strip()
    packed = Path('.git/packed-refs')
    if packed.exists():
        for line in packed.read_text().splitlines():
            if not line.startswith('#') and line.endswith(ref):
                return line.split()[0]
    return None

def write_ref(ref: str, commit: str):
    p = Path('.git') / ref
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(commit + '\n')

def commit_tree(tree: str, parent: str | None, msg: str) -> str:
    args = ['commit-tree', tree]
    if parent:
        args += ['-p', parent]
    args += ['-m', msg]
    out, rc = git(*args)
    if rc != 0:
        raise RuntimeError('commit-tree failed')
    return out

def main():
    if len(sys.argv) < 2:
        print('Usage: python3 scripts/git_commit.py "message"')
        sys.exit(1)

    msg = sys.argv[1]
    ref = current_branch_ref()
    parent = read_ref(ref)
    print(f'Branch : {ref}')
    print(f'Parent : {parent or "(root)"}')

    tree = build_tree(Path('.'))
    if not tree:
        print('Nothing to commit.')
        sys.exit(0)
    print(f'Tree   : {tree}')

    commit = commit_tree(tree, parent, msg)
    write_ref(ref, commit)
    print(f'Commit : {commit}')
    print(f'Done   ✓  ({ref})')

if __name__ == '__main__':
    main()
