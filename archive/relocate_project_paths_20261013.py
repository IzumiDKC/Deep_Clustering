"""One-time path migration following the user-authorized folder cleanup."""
from pathlib import Path
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
MAPPING={
    'results_timeline_20261013':'results/timeline_20261013',
    'results_dcss_width_ablation_20261013':'results/dcss_width_ablation_20261013',
    'results_verified_20261012':'archive/results_verified_20261012',
    'docs/primary_papers':'docs/references/primary_papers',
    'docs/author_sources':'docs/references/author_sources',
    'checks/build_timeline_notebook.py':'scripts/build_timeline_notebook.py',
    'checks/diagnose_dcss_initialization.py':'scripts/diagnose_dcss_initialization.py',
    'checks/run_dcss_calibration.py':'scripts/run_dcss_calibration.py',
}


def replace_paths(text):
    for old,new in MAPPING.items():
        text=text.replace(old,new)
    return text


def update(path, transform):
    text=path.read_text(encoding='utf-8-sig')
    path.write_text(transform(text),encoding='utf-8')


def main():
    # Source snapshots/config originals are never rewritten.
    for relative in ['scripts/build_review_report.py','scripts/prepare_data.py','scripts/summarize_survey.py']:
        update(ROOT/relative,lambda text:replace_paths(text).replace(
            'ROOT = Path(__file__).resolve().parent','ROOT = Path(__file__).resolve().parents[1]'))
    for relative in ['scripts/build_timeline_notebook.py','scripts/diagnose_dcss_initialization.py',
                     'scripts/run_dcss_calibration.py','checks/verify_experiment.py']:
        update(ROOT/relative,replace_paths)
    report=ROOT/'scripts/build_review_report.py'
    update(report,lambda text:text.replace('ROOT / "results" / "summary.csv"',
        'ROOT / "archive" / "reference_results" / "summary.csv"').replace(
        'out != ROOT / "results"','out != ROOT / "archive" / "reference_results"').replace(
        'default=ROOT / "archive/results_verified_20261012"','default=ROOT / "results/timeline_20261013"').replace(
        'ROOT.parent / "Bao_cao_Survey_Deep_Clustering_va_Demo_5_Phuong_phap.docx"',
        'ROOT / "docs/original/Bao_cao_Survey_Deep_Clustering_va_Demo_5_Phuong_phap.docx"'))
    update(ROOT/'scripts/summarize_survey.py',lambda text:text.replace(
        'default=ROOT/"results"/"survey_counts.json"','default=ROOT/"results/timeline_20261013"/"survey_counts.json"'))
    update(ROOT/'checks/verify_experiment.py',lambda text:text.replace(
        'default=ROOT/"results"','default=ROOT/"archive/reference_results"'))
    update(ROOT/'scripts/build_timeline_notebook.py',lambda text:text.replace(
        "ROOT / ('results_timeline_' + datetime.now().strftime('%Y%m%d_%H%M%S'))",
        "ROOT / 'results' / ('timeline_' + datetime.now().strftime('%Y%m%d_%H%M%S'))").replace(
        "[sys.executable,'-m','ipykernel_launcher'","[sys.executable,'-B','-m','ipykernel_launcher'"))
    update(ROOT/'run_demo.py',lambda text:text.replace('default=ROOT/"results_local"','default=ROOT/"results"/"local"').replace(
        'Run python prepare_data.py first.','Run python scripts/prepare_data.py first.'))
    update(ROOT/'run_windows.bat',lambda text:text.replace('cd /d "%~dp0"',
        'cd /d "%~dp0"\nset PYTHONDONTWRITEBYTECODE=1').replace(
        '"results_windows_%RANDOM%"','"results\\windows_%RANDOM%"').replace(
        'See the results_windows folder','See the results\\windows folder'))
    update(ROOT/'requirements/report.txt',lambda text:text.replace('-r requirements.txt','-r ../requirements.txt'))
    update(ROOT/'requirements/notebook.txt',lambda text:text.replace('-r requirements_report.txt','-r report.txt'))

    for relative in ['docs/literature_timeline.md','docs/model_audit.md','docs/survey_audit.md',
                     'docs/reading_notes/DEC_2016.md','data/README_DATA.md']:
        update(ROOT/relative,replace_paths)
    update(ROOT/'data/README_DATA.md',lambda text:text.replace('python prepare_data.py','python scripts/prepare_data.py'))
    # Notes paths are prose; fix Windows command samples as well.
    update(ROOT/'docs/survey_audit.md',lambda text:text.replace('python.exe summarize_survey.py','python.exe scripts/summarize_survey.py'))

    for relative in ['results/timeline_20261013','results/dcss_width_ablation_20261013']:
        path=ROOT/relative/'config.json'
        config=json.loads(path.read_text(encoding='utf-8'))
        config['output_before_cleanup']=config['output']
        config['output']=str((ROOT/relative).resolve())
        config['relocated_on']='2026-10-13'
        locations={'run_demo.py':'archive/source_snapshots/20261013/run_demo.py'}
        if 'checks/run_dcss_calibration.py' in config.get('source_sha256',{}):
            locations['checks/run_dcss_calibration.py']='archive/source_snapshots/20261013/checks/run_dcss_calibration.py'
        config['source_locations']=locations
        config['relocation_note']='Only filesystem paths changed; original training source/config snapshots retained; metrics and checkpoints untouched.'
        path.write_text(json.dumps(config,indent=2,ensure_ascii=False),encoding='utf-8')

    # Keep archived reports usable after relocation; these are historical pages.
    report_mapping={
        '../results_verified_20261012/':'../results_verified_20261012/',
        '../data/':'../../data/', '../notebooks/':'../notebooks/', '../src/':'../../src/',
        '../checks/':'../../checks/', 'href="survey_audit.md"':'href="../../docs/survey_audit.md"',
        'href="model_audit.md"':'href="../../docs/model_audit.md"',
        'href="Bao_cao_timeline_20261013.html"':'href="../../docs/Bao_cao_timeline_20261013.html"',
        '(survey_audit.md)':'(../../docs/survey_audit.md)', '(model_audit.md)':'(../../docs/model_audit.md)',
    }
    for path in (ROOT/'archive/reports').glob('*'):
        if path.suffix in ['.md','.html']:
            update(path,lambda text:apply_map(text,report_mapping))
    for path in (ROOT/'archive/notebooks').glob('*.ipynb'):
        document=json.loads(path.read_text(encoding='utf-8'))
        for cell in document['cells']:
            source=''.join(cell['source']) if isinstance(cell['source'],list) else cell['source']
            cell['source']=replace_paths(source)
        path.write_text(json.dumps(document,indent=1,ensure_ascii=False),encoding='utf-8')
    for relative in ['archive/tools/execute_review_notebook.py','archive/tools/finalize_literature_tracker.py']:
        update(ROOT/relative,lambda text:replace_paths(text).replace('resolve().parents[1]','resolve().parents[2]').replace(
            'ROOT/"notebooks"','ROOT/"archive/notebooks"').replace(
            "ROOT/'docs/literature_catalog_additions.json'","ROOT/'docs/references/literature_catalog_additions.json'"))
    shutil.copy2(ROOT/'README.md',ROOT/'archive/README_before_cleanup.md')
    print('Paths updated; original training snapshots and measured results preserved.')


def apply_map(text,mapping):
    for old,new in mapping.items():
        text=text.replace(old,new)
    return text


if __name__=='__main__':
    main()
