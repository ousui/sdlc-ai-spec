#!/usr/bin/env python3
"""Build one self-contained local plugin; do not install into host settings."""
import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ('sdlc-init', 'sdlc-000-ctx', 'sdlc-100-req', 'sdlc-200-dsn', 'sdlc-300-pln',
          'sdlc-400-imp', 'sdlc-500-vfy', 'sdlc-600-rls', 'sdlc-status')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_files(root=ROOT):
    selected = [root/'scripts/sdlc.py', root/'contracts/v2.json', root/'USAGE.md']
    selected += [root/name/'plugin.json' for name in ('.codex-plugin', '.claude-plugin', '.cursor-plugin')]
    selected += [p for p in (root/'packages/sdlc').iterdir() if p.suffix in {'.py', '.sql'}]
    for folder in (*SKILLS, '_shared'):
        selected += [p for p in (root/'skills'/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    result = {}
    for path in sorted(selected):
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing or symbolic-link bundle source: '+str(path))
        result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def verify(path):
    manifest = json.loads((path/'install-manifest.json').read_bytes())
    files = manifest['files']
    for name, expected in files.items():
        target = path/name
        if target.is_symlink() or not target.is_file() or sha(target.read_bytes()) != expected:
            raise ValueError('Installed file mismatch: '+name)
    actual = {p.relative_to(path).as_posix() for p in path.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    if actual != set(files) | {'install-manifest.json'}:
        raise ValueError('Installed bundle contains unexpected files')
    if sha(canonical(files)) != manifest['package_digest']:
        raise ValueError('Installed manifest digest mismatch')
    return manifest


def build(output, root=ROOT):
    output = Path(output).expanduser().resolve()
    files = source_files(root)
    hashes = {name: sha(raw) for name, raw in files.items()}
    package_digest = sha(canonical(hashes))
    git = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    dirty = subprocess.run(['git', '-C', str(root), 'status', '--porcelain'], capture_output=True, text=True)
    manifest = {'format': 'sdlc-plugin-2', 'package_digest': package_digest, 'files': hashes,
                'source_head': git.stdout.strip() if git.returncode == 0 else None,
                'source_dirty': bool(dirty.stdout), 'skills': list(SKILLS)}
    if output.exists():
        old = verify(output)
        if old['package_digest'] != package_digest:
            raise ValueError('Output already contains a different bundle; choose a new output directory')
        manifest = old
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix='.sdlc-package-', dir=output.parent))
        try:
            for name, raw in files.items():
                path = stage/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            (stage/'install-manifest.json').write_bytes(canonical(manifest)+b'\n')
            os.rename(stage, output)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    verify(output)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted([*files, 'install-manifest.json']):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (output/name).read_bytes())
    raw = buffer.getvalue()
    archive_path = output.with_name(output.name+'.zip')
    if archive_path.exists():
        if archive_path.read_bytes() != raw:
            raise ValueError('Existing package archive differs; preserve it and choose another output path')
    else:
        with archive_path.open('xb') as stream:
            stream.write(raw)
    return {'path': str(output), 'archive': str(archive_path), 'package_digest': package_digest,
            'archive_sha256': sha(raw), 'file_count': len(files), 'source_head': manifest['source_head'],
            'source_dirty': manifest['source_dirty']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.output), ensure_ascii=False, indent=2))
