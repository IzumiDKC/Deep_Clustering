"""Post-run label-free RBF-width ablation; keep the main experiment intact.

The hypothesis was formed after inspecting the main results and initialization
diagnostics. Widths use only X and initial K-means assignments, never y. This is
an exploratory ablation, not a replacement of preregistered source defaults.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys
import time
from itertools import combinations

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score
from threadpoolctl import threadpool_limits
from src.models import Autoencoder, squared_distances
from src.dcss import train_dcss
from src.evaluation import evaluate
from run_demo import plot_results, write_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'results/timeline_20261013')
    parser.add_argument('--output',type=Path,default=ROOT/'results/dcss_width_ablation_20261013')
    args = parser.parse_args()
    source,out = args.source.resolve(),args.output.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error('Choose a new output folder.')
    for child in ['', 'traces','models','predictions']:
        (out/child).mkdir(parents=True,exist_ok=True)
    config = json.loads((source/'config.json').read_text(encoding='utf-8'))
    config.update(methods=['DCSS'],output=str(out),
        executed_notebook='', ablation='post-run unsupervised per-cluster RMS RBF-width initialization',
        hypothesis_timing='after main results and label-free diagnostics; exploratory, no grid search',
        dcss_width_initialization='sqrt(mean within-initial-KMeans squared distance), each cluster; X only')
    config['method_registry'] = {'DCSS':dict(config['method_registry']['DCSS'])}
    config['method_registry']['DCSS']['implementation_scope'] += '; exploratory per-cluster RMS sigma initialization'
    config['source_sha256'][str(Path(__file__).relative_to(ROOT))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (out/'config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    shutil.copy2(source/'environment.json',out/'environment.json')
    shutil.copy2(source/'sample_indices.npy',out/'sample_indices.npy')
    indices = np.load(out/'sample_indices.npy',allow_pickle=False)
    with np.load(config['data'],allow_pickle=False) as bundle:
        x = bundle['X'][indices].astype(np.float64)
        # Evaluation labels are isolated below; initialization/trainer accept only X.
        y_evaluation = bundle['y'][indices]
    source_runs = pd.read_csv(source/'runs.csv').set_index(['method','seed'])
    records,partitions,representatives,width_records = [],[],{},[]
    with threadpool_limits(limits=1):
        for seed in config['seeds']:
            model = Autoencoder(x.shape[1],config['latent_dim'],seed)
            with np.load(source/'models'/f'pretrain_seed{seed}.npz',allow_pickle=False) as saved:
                model.params = {key:saved[key].copy() for key in model.params}
            with np.load(source/'models'/f'initialization_seed{seed}.npz',allow_pickle=False) as saved:
                centers = saved['centers'].copy()
            for filename in [f'pretrain_seed{seed}.npz',f'initialization_seed{seed}.npz']:
                shutil.copy2(source/'models'/filename,out/'models'/filename)
            shutil.copy2(source/'traces'/f'pretrain_seed{seed}.csv',out/'traces'/f'pretrain_seed{seed}.csv')
            start = time.perf_counter()
            distances = squared_distances(model.encode(x),centers)
            initial_labels = distances.argmin(1)
            within = distances[np.arange(len(x)),initial_labels]
            global_width = np.sqrt(within.mean())
            widths = np.array([np.sqrt(within[initial_labels==c].mean())
                if np.any(initial_labels==c) else global_width for c in range(len(centers))])
            widths = np.maximum(widths,1e-12)
            model.params['log_sigmas'] = np.log(widths)
            width_seconds = time.perf_counter()-start
            width_records.append({'seed':seed,'sigmas':widths.tolist(),'width_seconds':width_seconds,'uses_y':False})
            start = time.perf_counter()
            labels,z,centers,trace = train_dcss(model,x,centers,
                epochs=config['cluster_epochs'],batch_size=config['batch_size'],learning_rate=config['learning_rate'],
                seed=seed,silhouette_weight=config['dcss_silhouette_weight'],entropy_weight=config['dcss_entropy_weight'],
                temperature=config['dcss_temperature'],distance_normalization=config['dcss_distance_normalization'])
            fitting = time.perf_counter()-start
            original = source_runs.loc[('DCSS',seed)]
            initialization = float(original.initialization_seconds)+width_seconds
            pretraining = float(original.pretrain_seconds)
            scores = evaluate(y_evaluation,labels)
            records.append({'method':'DCSS','seed':seed,**scores,'pretrain_seconds':pretraining,
                'initialization_seconds':initialization,'fit_seconds':fitting,
                'standalone_seconds':pretraining+initialization+fitting,
                'nonempty_clusters':len(np.unique(labels)),'samples':len(x),'sha256_training_X':config['sha256_training_X']})
            partitions.append((seed,labels.copy()))
            if seed == config['seeds'][0]:
                representatives['DCSS'] = (z.copy(),labels.copy())
            pd.DataFrame({'sample_id':indices,'label_evaluation_only':y_evaluation,'cluster':labels}).to_csv(
                out/'predictions'/f'DCSS_seed{seed}.csv',index=False)
            np.savez_compressed(out/'models'/f'DCSS_seed{seed}.npz',**model.params,centers=centers)
            write_rows(out/'traces'/f'DCSS_seed{seed}.csv',trace)
            print(f'Seed {seed}: calibrated DCSS ACC={scores["acc"]:.4f}; fit={fitting:.2f}s',flush=True)
    runs = pd.DataFrame(records)
    runs.to_csv(out/'runs.csv',index=False)
    row = {'method':'DCSS','n_runs':len(runs)}
    for metric in ['acc','nmi','ari','standalone_seconds']:
        row[metric+'_mean'] = float(runs[metric].mean())
        row[metric+'_std'] = float(runs[metric].std(ddof=1))
    pairs = [{'method':'DCSS','seed_a':a,'seed_b':b,'pairwise_ari':adjusted_rand_score(la,lb)}
        for (a,la),(b,lb) in combinations(partitions,2)]
    values = [p['pairwise_ari'] for p in pairs]
    row.update(pairwise_ari_mean=float(np.mean(values)),pairwise_ari_std=float(np.std(values,ddof=1)),n_pairs=len(pairs))
    summary = pd.DataFrame([row])
    summary.to_csv(out/'summary.csv',index=False)
    write_rows(out/'pairwise_ari.csv',pairs)
    (out/'width_initializations.json').write_text(json.dumps(width_records,indent=2),encoding='utf-8')
    plot_results(out,runs,summary,representatives,x,y_evaluation,config['seeds'],
                 'Digits | exploratory RMS-width ablation',digit_images=True)
    print(summary.to_string(index=False))


if __name__ == '__main__':
    main()
