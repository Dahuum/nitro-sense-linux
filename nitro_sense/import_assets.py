"""Import the user's original artwork without executing or redistributing Acer code."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import struct
import zipfile

ASSEMBLY_SHA256 = 'f71a2eebf07f11e91337a0f5de7feefda54e96d8b007d3904adf4f459856b2cd'
STREAM_SHA256 = '501a274df16fc191f9172fc1fbb3f86c1fba668e494e216eb464f86d01dc0f8b'
MAX_INPUT = 100 * 1024 * 1024


def assembly_from_zip(data, depth=0):
    if depth > 3:
        raise ValueError('Archive nesting exceeds the supported Acer package layout.')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for item in archive.infolist():
            name = item.filename.lower()
            if item.file_size > MAX_INPUT:
                continue
            if name.endswith('/nitrosense.exe') or name == 'nitrosense.exe':
                payload = archive.read(item)
                if hashlib.sha256(payload).hexdigest() == ASSEMBLY_SHA256:
                    return payload
            if name.endswith(('.appxbundle', '_x64.appx')):
                found = assembly_from_zip(archive.read(item), depth + 1)
                if found is not None:
                    return found
    return None


def extract(data, output):
    if hashlib.sha256(data).hexdigest() != ASSEMBLY_SHA256:
        raise ValueError('This importer supports only the verified NitroSense 3.1.3056.0 assembly.')
    def u16(p): return struct.unpack_from('<H', data, p)[0]
    def u32(p): return struct.unpack_from('<I', data, p)[0]
    pe = u32(0x3c)
    sections = pe + 24 + u16(pe + 20)
    base = None
    for index in range(u16(pe + 6)):
        virtual_size, rva, raw_size, raw = struct.unpack_from('<IIII', data, sections + 40 * index + 8)
        if rva <= 748156 < rva + min(virtual_size, raw_size):
            base = raw + 748156 - rva
            break
    if base is None:
        raise ValueError('Verified resource stream is not file-backed.')
    resource = data[base + 4:base + 4 + u32(base)]
    if hashlib.sha256(resource).hexdigest() != STREAM_SHA256:
        raise ValueError('Resource stream identity mismatch.')
    position = 0
    def integer():
        nonlocal position
        value = struct.unpack_from('<i', resource, position)[0]
        position += 4
        return value
    def seven():
        nonlocal position
        result = 0
        for shift in range(0, 35, 7):
            value = resource[position]
            position += 1
            result |= (value & 127) << shift
            if value < 128:
                return result
        raise ValueError('Invalid resource integer.')
    if integer() != -1091581234:
        raise ValueError('Invalid .NET resource magic.')
    integer()
    skip = integer()
    position += skip
    if integer() != 2:
        raise ValueError('Unsupported resource format.')
    count, types = integer(), integer()
    for _ in range(types):
        size = seven()
        position += size
    position = (position + 7) // 8 * 8
    position += 4 * count
    names = [integer() for _ in range(count)]
    data_start = integer()
    names_start = position
    output = Path(output).resolve()
    extracted = []
    for offset in names:
        position = names_start + offset
        size = seven()
        name = resource[position:position + size].decode('utf-16le')
        position += size
        data_offset = integer()
        position = data_start + data_offset
        resource_type = seven()
        if resource_type not in (32, 33) or not name.lower().endswith(('.png', '.ttf', '.otf')):
            continue
        size = integer()
        payload = resource[position:position + size]
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name:
            raise ValueError('Unsafe resource path.')
        target = output.joinpath(*relative.parts)
        if not target.resolve().is_relative_to(output):
            raise ValueError('Resource escapes output directory.')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        extracted.append({'name': name, 'sha256': hashlib.sha256(payload).hexdigest()})
    output.mkdir(parents=True, exist_ok=True)
    (output / 'import-manifest.json').write_text(json.dumps({'assembly_sha256': ASSEMBLY_SHA256, 'resources': extracted}, indent=2) + '\n')
    return len(extracted)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path, help='Your original Acer ZIP or NitroSense.exe (3.1.3056.0 only)')
    parser.add_argument('--output', type=Path, default=Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'nitro-sense/assets')
    args = parser.parse_args()
    try:
        if args.package.stat().st_size > MAX_INPUT:
            raise ValueError('Input exceeds the supported package size.')
        data = args.package.read_bytes()
        assembly = data if hashlib.sha256(data).hexdigest() == ASSEMBLY_SHA256 else assembly_from_zip(data)
        if assembly is None:
            raise ValueError('The verified NitroSense assembly was not found in this archive.')
        count = extract(assembly, args.output)
    except (OSError, ValueError, zipfile.BadZipFile, struct.error, IndexError) as error:
        parser.exit(1, f'Import failed: {error}\n')
    print(f'Imported {count} artwork/font resources into {args.output}. Acer code was not executed.')


if __name__ == '__main__':
    main()
