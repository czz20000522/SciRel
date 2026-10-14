"""Build private full-core GPDF scientific wheel from an explicit closure.

Development artifact only. Human endorsement and redistribution are separate.
No source MATLAB, source checkout, workflow tools or evidence are packaged.
"""
from pathlib import Path
import argparse,json,shutil,subprocess,sys,hashlib
from scientific_runtime import baseline_receipt,build_requirements,pin_dependencies,python_requirement

MODULES={
 'cauchy_transform':['evaluate_cauchy_transform'],
 'maxwellian_electrostatic':['evaluate_maxwellian_electrostatic','solve_maxwellian_electrostatic_mode'],
 'plasma_dispersion':['evaluate_plasma_dispersion'],
 'faddeeva_variants':['evaluate_faddeeva_gpdf','evaluate_faddeeva_dr','evaluate_maxwellian_fft','evaluate_maxwellian_jpole'],
 'generalized_dispersion':[],
 'vlasov_poisson':[],
 '_gpdf_pole_data':[],
}
VERSION='0.1.0.dev9'

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--notices',type=Path,required=True);args=p.parse_args()
 root=Path(__file__).resolve().parents[1]
 args.output.mkdir(parents=True,exist_ok=False)
 stage=args.output/'source';target=stage/'src/scirel/kinetic';target.mkdir(parents=True)
 modules={k:list(v) for k,v in MODULES.items()}
 # Export declarations are explicit source-authored, parsed as literal data only.
 import ast
 for name in ('generalized_dispersion','vlasov_poisson'):
  for node in ast.parse((root/f'src/scirel/kinetic/{name}.py').read_text()).body:
   if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='__all__' for t in node.targets):
    modules[name]=ast.literal_eval(node.value)
 exports=[s for values in modules.values() for s in values]
 for name in modules:shutil.copyfile(root/f'src/scirel/kinetic/{name}.py',target/f'{name}.py')
 (target.parent/'__init__.py').write_text(f'"""SciRel private kinetic development candidate."""\n__version__={VERSION!r}\n__all__=["kinetic"]\n')
 (target/'__init__.py').write_text('\n'.join([f'from .{m} import '+', '.join(v) for m,v in modules.items() if v])+f'\n__all__={exports!r}\n')
 notices=stage/'licenses';notices.mkdir()
 for file in args.notices.iterdir():
  if file.is_file():shutil.copyfile(file,notices/file.name)
 (stage/'pyproject.toml').write_text(f'''[build-system]
requires={json.dumps(build_requirements())}
build-backend="setuptools.build_meta"
[project]
name="scirel"
version="{VERSION}"
description="SciRel private complete GPDF core development candidate"
requires-python={json.dumps(python_requirement())}
dependencies={json.dumps(pin_dependencies(['numpy','scipy']))}
license-files=["licenses/*"]
[tool.setuptools.packages.find]
where=["src"]
include=["scirel","scirel.kinetic"]
''')
 wheels=args.output/'wheel'
 subprocess.run([sys.executable,'-m','pip','wheel','--no-index','--no-build-isolation','--no-deps','--wheel-dir',str(wheels),str(stage)],check=True)
 wheel=next(wheels.glob('*.whl'))
 receipt={'schema':'scirel.gpdf-core-build.v1','baseline':baseline_receipt(),'version':VERSION,'modules':modules,'exports':exports,'wheel':str(wheel),'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'runtime_dependencies':pin_dependencies(['numpy','scipy']),'source_sha256':{m:hashlib.sha256((target/f'{m}.py').read_bytes()).hexdigest() for m in modules},'human_approval':False,'redistribution_approval':False}
 (args.output/'BUILD.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
