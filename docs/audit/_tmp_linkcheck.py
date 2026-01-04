import pathlib, re

# docs root
root = pathlib.Path(__file__).resolve().parents[1]
link_re = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
problems = []

for f in sorted(root.glob('**/*.md')):
    text = f.read_text(encoding='utf-8', errors='ignore')
    for m in link_re.finditer(text):
        tgt = m.group(2).strip()
        if tgt.startswith(('http://', 'https://', 'mailto:', '#')):
            continue
        path_part = tgt.split(' ')[0].split('#')[0]

        candidates = []
        if path_part.startswith('docs/'):
            candidates.append(root.parent / path_part)  # repo-root relative
        candidates.append(f.parent / path_part)        # relative to current file
        candidates.append(root / path_part.lstrip('./'))  # docs-root relative

        target_path = next((p for p in candidates if p.exists()), None)
        if target_path is None:
            problems.append((f, tgt, 'missing', f'File not found (tried: ' + ', '.join(str(p) for p in candidates) + ')'))
            continue

        if 'bulk/' in path_part and 'bulk-operations' not in str(target_path):
            problems.append((f, tgt, 'legacy-path', 'Replace bulk/ with bulk-operations/'))
        if target_path.name.lower() in ('tag_space_endpoint.md', 'auto_tag_endpoint.md'):
            problems.append((f, tgt, 'nonexistent-endpoint-doc', 'Remove or replace nonexistent TAG_SPACE/AUTO_TAG docs'))

lines = ['# docs broken links audit', '', 'Generated: 2026-01-02', '', '| Файл | Проблемний лінк | Тип проблеми | Рекомендація |', '|------|------------------|--------------|--------------|']
if not problems:
    lines.append('| - | - | - | - |')
else:
    seen = set()
    for f, tgt, typ, note in problems:
        rel = f.relative_to(root.parent).as_posix()
        key = (rel, tgt, typ)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"| [{rel}]({rel}) | `{tgt}` | {typ} | {note} |")
out = pathlib.Path(__file__).resolve().parent / '04_broken_links.md'
out.write_text('\n'.join(lines), encoding='utf-8')
print('problems', len(problems))
