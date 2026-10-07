#!/usr/bin/env python3
"""Machine-checkable inventory recount for docs/designs/modular-core-2026-10-07.

Counts ast.FunctionDef + ast.AsyncFunctionDef: module top level vs nested
(class/method/nested). nested = all - top, never counted twice. Prints the
per-file table with source sha256; exit 1 if any number differs from
inventory-appendix.md's stated totals. Run from the repo root:
    python3 docs/designs/modular-core-2026-10-07/recount.py
"""
import ast, hashlib, sys
from pathlib import Path

FILES = ("scripts/kaola-dispatch.py", "scripts/kaola-acp-holder.py",
         "scripts/kaola-acp.py", "scripts/kaola-record-contract.py")

def counts(path: Path):
    tree = ast.parse(path.read_bytes())
    top = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in tree.body)
    all_ = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               for n in ast.walk(tree))
    return top, all_ - top, all_

def main():
    t = n = a = 0
    for f in FILES:
        p = Path(f)
        top, nested, all_ = counts(p)
        sha = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        print(f"{f}: top {top}, nested {nested}, all {all_}, sha256:{sha}")
        t += top; n += nested; a += all_
    print(f"TOTAL: top {t}, nested {n}, all {a}")
    expected = (522, 199, 721)
    sys.exit(0 if (t, n, a) == expected else 1)

if __name__ == "__main__":
    main()
