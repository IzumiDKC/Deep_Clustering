"""Summarize listed papers and evidence; a tracker row is not a full-text review.

Quartiles require a verified system/year/category and source. Public repositories
and successful original-code execution are separate. Uses the standard library.
"""
from pathlib import Path
from collections import Counter
import json
import argparse
import csv

ROOT = Path(__file__).resolve().parents[1]
QUARTILES = ("Q1", "Q2", "Q3", "Q4")
REQUIRED = ("paper_id", "year", "publication_type", "paper_url", "code_public",
            "code_smoke_tested", "dataset_public", "quartile", "ranking_system",
            "ranking_year", "ranking_category", "ranking_source", "full_text_reviewed")


def is_yes(row, key):
    return row.get(key, "").strip().lower() == "yes"


def percent(count, denominator):
    return 100.0 * count / denominator if denominator else None


def counts(rows, key):
    return dict(sorted(Counter(row.get(key, "").strip().lower() or "unknown"
                               for row in rows).items()))


def quartile_is_verified(row):
    return (row.get("quartile", "").strip().upper() in QUARTILES
            and is_yes(row, "quartile_verified")
            and all(row.get(key, "").strip() for key in
                    ("ranking_system", "ranking_year", "ranking_category", "ranking_source")))


def summarize(rows):
    for key in ("paper_id", "paper_url"):
        values = [row[key].strip().rstrip("/") for row in rows]
        if any(not value for value in values) or len(values) != len(set(values)):
            raise ValueError(f"Missing or duplicate {key}; check arXiv/published duplicates.")
    invalid_years = [row["paper_id"] for row in rows
                     if not row["year"].strip().isdigit() or len(row["year"].strip()) != 4]
    if invalid_years:
        raise ValueError(f"Publication year must have four digits: {invalid_years}")
    total = len(rows)
    journals = [row for row in rows if row["publication_type"].strip().lower() == "journal"]
    reviewed = [row for row in rows if is_yes(row, "full_text_reviewed")]
    verified_journals = [row for row in journals if quartile_is_verified(row)]
    q_counts = {q: sum(row["quartile"].strip().upper() == q for row in verified_journals)
                for q in QUARTILES}
    publication_types = counts(rows, "publication_type")
    return {
        "total_papers_in_tracker": total,
        "papers_listed": total,
        "paper_metadata_verified": sum(is_yes(row, "paper_metadata_verified") for row in rows),
        "publication_types": publication_types,
        "paper_kinds": counts(rows, "paper_kind"),
        "publication_type_percent": {key: percent(value, total)
                                     for key, value in publication_types.items()},
        "papers_by_year": dict(sorted(Counter(row["year"].strip() for row in rows).items())),
        "papers_from_2023_onward": sum(int(row["year"]) >= 2023 for row in rows),
        "method_families":counts(rows,"method_family"),
        "comparison_regimes":counts(rows,"regime"),
        "direct_relevance":counts(rows,"direct_relevance"),
        "sampling_protocol":"Purposive candidate catalog, prioritizing public code and relevance; not an estimate of field-wide public-code prevalence",
        "paper_reported_numeric_summaries":sum(row.get("paper_reported_result_status") in {"extracted_numeric", "verified_primary_table_excerpt"} for row in rows),
        "paper_result_extraction_pending":[row["paper_id"] for row in rows if not row.get("paper_reported_result")],
        "full_text_reviews_completed": len(reviewed),
        "full_text_review_percent": percent(len(reviewed), total),
        "reviewed_publication_types": counts(reviewed, "publication_type"),
        "journal_quartiles": q_counts,
        "journal_quartile_unknown": len(journals) - len(verified_journals),
        "quartile_denominator_journal_papers": len(journals),
        "quartile_verified_journal_papers": len(verified_journals),
        "journal_quartile_percent": {q: percent(value, len(journals)) for q, value in q_counts.items()},
        "journal_quartile_unknown_percent": percent(len(journals) - len(verified_journals), len(journals)),
        "quartile_claims_missing_evidence": [row["paper_id"] for row in journals
                                            if row["quartile"].strip() and not quartile_is_verified(row)],
        "journal_ranking_records": [{key: row.get(key, "") for key in
                                     ("paper_id", "year", "venue", "quartile", "ranking_system", "ranking_year",
                                      "ranking_category", "ranking_source", "quartile_verified",
                                      "quartile_verification_note")}
                                    for row in verified_journals],
        "journal_ranking_policy": "SCImago SJR best quartile across subject categories; common reference year2024, not necessarily publication year; primary indexed content, direct live access blocked403; conference papers excluded",
        "journal_ranking_reference_years": sorted({row["ranking_year"] for row in verified_journals}),
        "public_code_papers": sum(is_yes(row, "code_public") for row in rows),
        "public_code_verified": sum(is_yes(row, "code_public")
                                    and is_yes(row, "code_availability_verified") for row in rows),
        "public_code_method_papers": sum(is_yes(row, "code_public") and row.get("paper_kind") == "method" for row in rows),
        "public_resources_survey_papers": sum(is_yes(row, "code_public") and row.get("paper_kind") == "survey" for row in rows),
        "public_code_percent": percent(sum(is_yes(row, "code_public") for row in rows), total),
        "original_code_smoke_tested": sum(is_yes(row, "code_smoke_tested") for row in rows),
        "public_dataset_papers": sum(is_yes(row, "dataset_public") for row in rows),
        "dataset_scope_verified": sum(is_yes(row, "dataset_scope_verified") for row in rows),
        "original_dataset_download_verified": sum(is_yes(row, "original_dataset_download_verified")
                                                  for row in rows),
        "note": ("Tracker rows are listed candidates, not completed full-text reviews. "
                 "Quartile counts require quartile_verified=yes and system/year/category/source; "
                 "conference papers are excluded. Dataset_public is a tracker claim; "
                 "dataset_scope_verified confirms benchmark names only, not licenses or downloads. "
                 "Public code does not imply successful execution. The independent NumPy demo "
                 "is separate from original-code smoke tests and full paper reproduction."),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tracker", type=Path, default=ROOT/"data"/"paper_tracker.csv")
    parser.add_argument("--output", type=Path, default=ROOT/"results/timeline_20261013"/"survey_counts.json")
    args = parser.parse_args()
    with args.tracker.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(REQUIRED) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing tracker columns: {sorted(missing)}")
        rows = [{key: (value or "") for key, value in row.items()} for row in reader]
    summary = summarize(rows)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
