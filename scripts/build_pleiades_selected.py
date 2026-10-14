"""Build a selected scientific wheel from exact source and license bindings.

A selection identifies bytes and exports; it does not grant scientific, human or
release approval. No checkout, workflow package or discovery catalog is bundled.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys

from scientific_runtime import baseline_receipt, build_requirements, pin_dependencies, python_requirement


def bound_source(root, record):
    relative = PurePosixPath(record['path'])
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError(f'invalid selection path: {relative}')
    path = root.joinpath(*relative.parts)
    if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
        raise ValueError(f'selection must bind a regular in-tree file: {relative}')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != record['sha256']:
        raise ValueError(f'selection digest mismatch: {relative}')
    return relative, data


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('profile', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = p.parse_args()
    profile = json.loads(args.profile.read_text())
    if profile['schema'] != 'scirel.selected-scientific-wheel.v1':
        raise ValueError('unsupported selection schema')
    dependencies = pin_dependencies(profile['dependencies'])
    # Validate every binding before creating the isolated staging tree.
    files = [bound_source(args.source_root, row) for row in profile['files']]
    licenses = [bound_source(args.source_root, row) for row in profile['licenses']]
    data_files = [bound_source(args.source_root, row) for row in profile.get('data_files', [])]
    if len({str(p) for p, _ in files + licenses + data_files}) != len(files) + len(licenses) + len(data_files):
        raise ValueError('duplicate selected path')
    for relative, _ in files:
        if relative.parts[:2] != ('src', 'scirel') or relative.suffix != '.py' or relative.name == '__init__.py':
            raise ValueError(f'not an explicit scientific implementation: {relative}')
    for relative, _ in data_files:
        if relative.parts[:2] != ('src', 'scirel') or relative.suffix not in ('.m', '.in', '.json'):
            raise ValueError(f'not an explicit scientific runtime resource: {relative}')
    for relative, _ in licenses:
        if relative.parts[0] != 'licenses':
            raise ValueError(f'not a license/notice path: {relative}')
    initializers = profile['initializers']
    for name in initializers:
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or relative.parts[:2] != ('src', 'scirel') or relative.name != '__init__.py':
            raise ValueError(f'invalid initializer: {name}')
    args.output.mkdir(parents=True, exist_ok=False)
    stage = args.output / 'source'
    for relative, data in files + licenses + data_files:
        target = stage.joinpath(*relative.parts); target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
    for name, content in initializers.items():
        target = stage / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(content, encoding='utf-8')
    # JSON string syntax is a valid TOML basic string for these simple metadata fields.
    q = json.dumps
    project = '\n'.join([
        '[build-system]', 'requires = '+q(build_requirements()), 'build-backend = "setuptools.build_meta"',
        '[project]', 'name = "scirel"', 'version = '+q(profile['version']),
        'description = '+q(profile.get('description', 'SciRel selected Pleiades scientific development distribution')),
        'requires-python = '+q(python_requirement()), 'dependencies = '+q(dependencies),
        'license-files = '+q([str(path) for path, _ in licenses]), '[tool.setuptools.packages.find]',
        'where = ["src"]', 'include = ["scirel", "scirel.*"]', ''])
    if data_files:
        project += '\n[tool.setuptools.package-data]\n'+q('scirel')+' = '+q([str(path.relative_to('src/scirel')) for path, _ in data_files])+'\n'
    (stage / 'pyproject.toml').write_text(project)
    wheels = (args.output / 'wheel').resolve(); wheels.mkdir()
    env = dict(os.environ, SOURCE_DATE_EPOCH='315532800', PYTHONDONTWRITEBYTECODE='1')
    subprocess.run([sys.executable, '-c',
        'import setuptools.build_meta,sys; print(setuptools.build_meta.build_wheel(sys.argv[1]))',str(wheels)],
        cwd=stage, env=env, check=True)
    wheel = next(wheels.glob('*.whl'))
    result = {'scientific_runtime_baseline':baseline_receipt(), 'profile_sha256':hashlib.sha256(args.profile.read_bytes()).hexdigest(),
              'wheel':str(wheel), 'sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),
              'bytes':wheel.stat().st_size, 'implementation_count':len(files), 'runtime_resource_count':len(data_files),
              'native_runtime':profile.get('native_runtime'),
              'human_approval':False, 'release_approval':False}
    (args.output/'BUILD_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__ == '__main__':
    main()
