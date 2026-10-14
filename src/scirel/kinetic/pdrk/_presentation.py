"""Private corrected legacy plots: explicit science arrays, units and artifacts."""
from pathlib import Path
import hashlib,json
import numpy as np


def save_program(model,result,output_dir):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    root=Path(output_dir);root.mkdir(parents=True,exist_ok=False)
    fig,axes=plt.subplots(2,1,figsize=(7,7),layout='constrained')
    arrays={}
    carriers=[]
    if model=='generator':
        x=np.asarray(result['x']);y=np.asarray(result['y']);Z=np.asarray(result['ZJ'])
        arrays.update(x=x,y=y,ZJ=Z,bzj=result['bzj'],czj=result['czj'])
        for ax,values,title in zip(axes,[Z.real,Z.imag],['Re Z_J','Im Z_J']):
            image=ax.pcolormesh(x,y,values,shading='auto');fig.colorbar(image,ax=ax);ax.set(xlabel='Re z (dimensionless)',ylabel='Im z (dimensionless)',title=title)
    else:
        points=np.asarray(result['points']);eq=result['equilibrium']['state']
        coordinate=points[:,0] if model=='es1d' else np.linalg.norm(points,axis=1)
        unit='dimensionless k'
        scale=1.
        if model=='em':coordinate=coordinate*float(np.asarray(eq['cwp']).item());scale=float(np.asarray(eq['wci']).item());unit='k c / omega_pi'
        arrays['points']=points
        for i,(x,point) in enumerate(zip(coordinate,result['spectra'])):
            solution=point['solution'];w=solution.get('w',solution.get('omega'))
            arrays['omega_'+str(i)]=w
            if 'frequency_base_decimal' in solution:
                carriers.append({'point_index':i,**{k:v for k,v in solution.items() if not isinstance(v,np.ndarray)}})
            axes[0].plot(np.repeat(x,len(w)),w.real/scale,'.',markersize=2)
            axes[1].plot(np.repeat(x,len(w)),w.imag/scale,'.',markersize=2)
        axes[0].set(ylabel='Re omega / omega_ci' if model=='em' else 'Re omega (dimensionless)')
        axes[1].set(ylabel='Im omega / omega_ci' if model=='em' else 'Im omega (dimensionless)')
        for ax in axes:ax.set(xlabel=unit);ax.grid(True,alpha=.3)
    fig.savefig(root/'corrected-scientific-output.png',dpi=120);plt.close(fig)
    np.savez(root/'scientific-terminal.npz',**arrays)
    if carriers:(root/'complete-frequency-carriers.json').write_text(json.dumps(carriers,indent=2)+'\n')
    artifacts=[dict(name=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in sorted(root.iterdir())]
    metadata={'numeric_views':'binary64 rounded frequencies; complete decimal base+offset retained when present','frequency_units':'omega/omega_ci' if model=='em' else 'dimensionless omega','coordinate_units':'k c/omega_pi' if model=='em' else 'dimensionless k','generator_units':'dimensionless complex z and Z_J' if model=='generator' else None,'mode_classification':'per-point physical/canceled/infinite taxonomy in complete-frequency-carriers.json when applicable; auxiliary aliases not silently physical waves','visual_review':'PENDING'}
    manifest={'plot_metadata':metadata,'model':model,'status':'CORRECTED_SCIENTIFIC_PRESENTATION','human_visual_approval':'PENDING','original_PNG_identity':'NOT_CLAIMED','artifacts':artifacts}
    (root/'ARTIFACTS.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return {'result':result,'artifacts':manifest,'output_dir':str(root)}
