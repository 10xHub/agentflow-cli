from pathlib import Path

import mkdocs_gen_files


src_root = Path("./src")
for path in src_root.glob("**/*.py"):
    if path.stem == "__init__":
        continue
    doc_path = Path("reference", path.relative_to(src_root)).with_suffix(".md")

    with mkdocs_gen_files.open(doc_path, "w") as f:
        ident = ".".join(path.with_suffix("").parts)
        print("::: " + ident, file=f)
