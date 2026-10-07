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
    expected_total = (522, 199, 721)
    expected_per_file = {
        "scripts/kaola-dispatch.py": (208, 25, 233, "64fcb90de126a684"),
        "scripts/kaola-acp-holder.py": (51, 158, 209, "f455cd271d20b2f1"),
        "scripts/kaola-acp.py": (195, 12, 207, "d957f86e1efc5b26"),
        "scripts/kaola-record-contract.py": (68, 4, 72, "b5b61d8fdf4f30de"),
    }
    ok = (t, n, a) == expected_total
    for f in FILES:
        p_ = Path(f)
        top, nested, all_ = counts(p_)
        sha = hashlib.sha256(p_.read_bytes()).hexdigest()[:16]
        exp = expected_per_file[f]
        if (top, nested, all_, sha) != exp:
            print(f"MISMATCH {f}: got ({top},{nested},{all_},{sha}) expected {exp}")
            ok = False
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
