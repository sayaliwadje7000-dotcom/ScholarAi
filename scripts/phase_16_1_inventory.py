from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"

TERMS = (
    "user",
    "preference",
    "activity",
    "interaction",
    "feedback",
    "recommendation",
    "learning",
    "context",
    "hybrid",
)


def is_relevant(path: Path) -> bool:
    normalized = str(path).replace("\\", "/").casefold()
    return any(term in normalized for term in TERMS)


def inspect_file(path: Path) -> None:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:
        print(f"\nFILE: {path.relative_to(ROOT)}")
        print(f"INSPECTION ERROR: {exc}")
        return

    print(f"\n{'=' * 88}")
    print(f"FILE: {path.relative_to(ROOT)}")
    print(f"{'=' * 88}")

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            print(f"\nCLASS {node.name} (line {node.lineno})")

            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    print(f"  METHOD {member.name} (line {member.lineno})")

                elif isinstance(member, ast.AnnAssign) and isinstance(member.target, ast.Name):
                    annotation = ast.unparse(member.annotation)
                    print(f"  FIELD {member.target.id}: {annotation}")

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            print(f"\nFUNCTION {node.name} (line {node.lineno})")


def main() -> None:
    if not APP.is_dir():
        raise SystemExit(f"Application directory not found: {APP}")

    all_python_files = sorted(APP.rglob("*.py"))
    selected = [path for path in all_python_files if is_relevant(path)]

    print("SCHOLARAI — PHASE 16.1 ARCHITECTURE INVENTORY")
    print(f"Project root: {ROOT}")
    print(f"Python files discovered: {len(all_python_files)}")
    print(f"Relevant files selected: {len(selected)}")

    for path in selected:
        inspect_file(path)

    print("\nINVENTORY COMPLETED — no application files were modified.")


if __name__ == "__main__":
    main()
