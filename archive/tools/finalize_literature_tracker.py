"""Merge audited publication catalog into the evidence tracker, idempotently."""
from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parents[2]


def main():
    tracker = ROOT/'data/paper_tracker.csv'
    with tracker.open(encoding='utf-8-sig',newline='') as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames)
        rows = list(reader)
    aliases={'review_note':'review_note_file','paper_reported_results':'paper_reported_result',
             'paper_reported_results_source':'paper_reported_result_source'}
    for row in rows:
        for old,new in aliases.items():
            if row.get(old):
                row[new]=row[old]
            row.pop(old,None)
    fields=[f for f in fields if f not in aliases]
    extras = ['method_family','regime','direct_relevance','selection_role','drive_folder_match',
              'review_note_file','paper_reported_result','paper_reported_result_source','paper_reported_result_status']
    fields += [field for field in extras if field not in fields]
    catalog = json.loads((ROOT/'docs/references/literature_catalog_additions.json').read_text(encoding='utf-8'))
    existing = {r['paper_id'] for r in rows}
    for paper in catalog['papers']:
        if paper['paper_id'] in existing:
            continue
        row = {field:'' for field in fields}
        row.update({key:value for key,value in paper.items() if key in fields})
        row.update(code_public='yes',code_smoke_tested='no',
            paper_metadata_verified='yes',paper_metadata_source=paper['paper_url'],
            code_availability_verified='yes',code_availability_source=paper['code_url'],
            code_provenance=paper.get('code_provenance','author'),
            full_text_reviewed='no',original_dataset_download_verified='no',quartile_verified='no',
            dataset_public='yes' if paper.get('datasets') else 'unknown',
            dataset_scope_verified='yes' if paper.get('datasets') else 'no',
            verified_on=catalog['verified_on'],selection_role='contextual candidate; not executed',
            quartile_verification_note='Not applicable: conference paper' if paper['publication_type']=='conference'
                else 'Unknown: publisher confirms venue; no verified ranking-system/year/category evidence')
        rows.append(row)
    for row in rows:
        method = row['method']
        if method in ['DEC','IDEC','DECRA','DCSS']:
            row['selection_role'] = 'selected timeline; independent common-backbone adaptation executed'
            row['direct_relevance'] = 'high'
        if method == 'BRB':
            row['selection_role'] = 'literature comparison only in timeline experiment'
            row['notes'] = 'BRB plug-in; previous NumPy demo exists, main four-method timeline uses literature numbers only'
        if method == 'IDEC':
            row['full_text_reviewed'] = 'yes'
            row['review_note_file'] = 'docs/reading_notes/IDEC_2017.md'
            row['paper_reported_result'] = 'Table 2 ACC (%): DEC → IDEC; MNIST 86.55 → 88.06; USPS 74.08 → 76.05; REUTERS-10K 73.68 → 75.64'
            row['paper_reported_result_source'] = 'https://www.ijcai.org/proceedings/2017/0243.pdf'
            row['paper_reported_result_status'] = 'extracted_numeric'
        if method == 'DEC':
            row['full_text_reviewed'] = 'yes'
            row['review_note_file'] = 'docs/reading_notes/DEC_2016.md'
            row['paper_reported_result'] = 'Table 2 ACC (%), best of 9 settings: MNIST 84.30; STL-HOG 35.90; Reuters-10K 72.17; Reuters 75.63; not mean across seeds'
            row['paper_reported_result_source'] = 'https://proceedings.mlr.press/v48/xieb16.pdf'
            row['paper_reported_result_status'] = 'extracted_numeric'
        if method in ['DECRA','DCSS']:
            detail='common-backbone code adaptation executed; original author environment not executed; paper/code differences documented'
            if detail not in row['notes']:
                row['notes'] += '; '+detail
            row['notes']='; '.join(dict.fromkeys(part.strip() for part in row['notes'].split(';') if part.strip()))
        if method == 'BRB':
            row['paper_reported_result']='Table 13, 10 runs, ACC mean ± SE: IDEC+Pretrain → IDEC+BRB+Pretrain; MNIST 93.16 ± 2.20 → 94.19 ± 2.20; USPS 81.59 ± 0.28 → 81.87 ± 0.14; protocol differs from local Digits'
            row['paper_reported_result_source']='https://proceedings.iclr.cc/paper_files/paper/2025/file/f91685b940d5032f0f0c247edbd72edd-Paper-Conference.pdf'
            row['paper_reported_result_status']='extracted_numeric'
        if method == 'SANE':
            row['datasets']='CIFAR-10; CIFAR-100-20; STL-10; ImageNet-10; ImageNet-Dogs; non-image CNAE-9/Semeion/News20 in appendix'
            row['datasets_source']='https://proceedings.iclr.cc/paper_files/paper/2026/file/63ef323523f3be8b58ed9277cc747485-Paper-Conference.pdf'
            row['dataset_scope_verified']='yes'
            row['dataset_scope_status']='verified_names'
        if row.get('paper_reported_result'):
            row['paper_reported_result'] = row['paper_reported_result'].replace('94.4%?96.0%','94.4% → 96.0%').replace('0.10?0.74','0.10 → 0.74').replace('57%?66%','57% → 66%')
        if method == 'DCSS':
            row['paper_reported_result'] = row['paper_reported_result'].replace('section5.4','section 5.5').replace('of0.03-0.07','of 0.03–0.07').replace('and0.03-0.06','and 0.03–0.06').replace('Table2','Table 2').replace('over10runs','over 10 runs')
        if not row.get('method_family'):
            row['method_family'] = 'ae_centroid' if method in ['DEC','IDEC','DCN','DEC-DA','DECRA'] else 'image_contrastive' if method in ['SCAN','CC'] else 'reset_plugin'
        if not row.get('regime'):
            row['regime'] = 'single_view'
        row['verified_on'] = '2026-10-13'
    assert len(rows)==30 and len({r['paper_url'] for r in rows})==30
    with tracker.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f'Finalized {len(rows)} publication entries; full-text status remains evidence-based.')


if __name__=='__main__':
    main()
