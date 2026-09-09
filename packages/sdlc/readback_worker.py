"""Independent local package verifier. No database or model assertions are trusted."""
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath


def verify(path, expected):
    with Path(path).open('rb') as stream:
        raw = stream.read(64*1024*1024+1)
    assert len(raw) <= 64*1024*1024, 'Package exceeds the size budget'
    assert hashlib.sha256(raw).hexdigest() == expected, 'Delivered package digest differs'
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        names = [item.filename for item in entries]
        assert len(names) == len(set(names)) <= 50000, 'Duplicate or excessive package entries'
        assert sum(item.file_size for item in entries) <= 256*1024*1024, 'Expanded package exceeds budget'
        for item in entries:
            name = PurePosixPath(item.filename)
            assert not name.is_absolute() and '..' not in name.parts and '\\' not in item.filename, 'Unsafe package path'
            assert (item.external_attr >> 16) & 0o170000 != 0o120000, 'Symlink in package'
        manifest = json.loads(archive.read('manifest.json'))
        assert manifest['format'] == 'sdlc-local-delivery-2', 'Unknown package format'
        declared = manifest['files']
        assert set(declared) == set(names)-{'manifest.json'}, 'Package file closure differs'
        modes = manifest['modes']
        assert set(modes) == set(declared), 'Package mode closure differs'
        for name, hashed in declared.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == hashed, 'Package file differs: '+name
            assert type(modes[name]) is int and 0 <= modes[name] <= 0o777, 'Invalid package mode'
            actual_mode = archive.getinfo(name).external_attr >> 16
            assert actual_mode == (0o100000 | modes[name]), 'Package mode differs: '+name
    return {'package_sha256': expected, 'verified_files': len(declared), 'change_id': manifest['change_id'],
            'revision_id': manifest['revision_id'], 'snapshot_id': manifest['snapshot_id'], 'status': 'pass'}


if __name__ == '__main__':
    try:
        result = verify(sys.argv[1], sys.argv[2])
    except (AssertionError, OSError, ValueError, KeyError, zipfile.BadZipFile, IndexError) as exc:
        print(json.dumps({'status': 'fail', 'error': str(exc)}))
        sys.exit(1)
    print(json.dumps(result, sort_keys=True))
