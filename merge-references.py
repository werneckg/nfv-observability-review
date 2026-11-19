#!/usr/bin/env python3
"""
Description:
- Reads CSV and BibTeX files recursively from a source directory
- Removes duplicated works based on title (case-insensitive)
- Exports a unified CSV file
- Generates a summary.log report with statistics
"""

import argparse
import os
from pathlib import Path
from collections import defaultdict
import csv
import bibtexparser
from pylatexenc.latex2text import LatexNodes2Text
import html2text

OUTPUT_FILE = "merged-output.csv"
SUMMARY_FILE = "summary.log"

def parse_arguments():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Merge CSV and BibTeX references removing duplicated titles."
    )

    parser.add_argument(
        "--source-dir",
        default="Sources",
        help="Source directory containing CSV and BibTeX files"
    )

    return parser.parse_args()


def normalize_title(title):
    """
    Normalize title for duplicate comparison.
    """
    if not title:
        return ""

    title = str(title)

    # Convert HTML escaped characters
    title = html2text.HTML2Text().handle(title)

    # Convert LaTeX escaped characters
    title = LatexNodes2Text().latex_to_text(title)
    
    return " ".join(title.strip().title().split())


def find_source_files(source_dir):
    """
    Recursively find CSV and BibTeX files.
    """
    supported_extensions = {".csv", ".bib"}
    source_files = []

    for root, _, files in os.walk(source_dir):
        print(root)        
        for file_name in files:
            file_path = Path(root) / file_name

            if file_path.suffix.lower() in supported_extensions:
                source_files.append(file_path)

    return source_files


def read_csv_file(file_path):
    """
    Read records from a CSV file.
    """
    records = []

    with open(file_path, mode="r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            records.append(dict(row))

    return records


def read_bibtex_file(file_path):
    """
    Read records from a BibTeX file.
    """
    records = []

    with open(file_path, mode="r", encoding="utf-8") as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)

        for entry in bib_database.entries:
            records.append(dict(entry))

    return records


def load_records(source_files):
    """
    Load all records from supported files.
    """
    all_records = []

    for file_path in source_files:
        if file_path.suffix.lower() == ".csv":
            records = read_csv_file(file_path)

        elif file_path.suffix.lower() == ".bib":
            records = read_bibtex_file(file_path)

        else:
            continue

        for record in records:
            record["source_file"] = file_path.name
            all_records.append(record)

    return all_records


def extract_title(record):
    """
    Extract title from a record using flexible field matching.
    """
    possible_title_fields = {
        "title",
        "document title",
        "item title"
    }

    normalized_record = {
        key.strip().lower(): value
        for key, value in record.items()
    }

    for field in possible_title_fields:
        if field in normalized_record:
            return str(normalized_record[field]).strip()

    return ""

def extract_authors(record):
    """
    Extract authors from a record using flexible field matching.
    """
    possible_authors_fields = {
        "author",
        "authors"
    }

    normalized_record = {
        key.strip().lower(): value
        for key, value in record.items()
    }

    for field in possible_authors_fields:
        if field in normalized_record:
            return str(normalized_record[field]).strip()

    return ""

def extract_year(record):
    """
    Extract year from a record using flexible field matching.
    """
    possible_year_fields = {
        "year",
        "publication year"
    }

    normalized_record = {
        key.strip().lower(): value
        for key, value in record.items()
    }

    for field in possible_year_fields:
        if field in normalized_record:
            return str(normalized_record[field]).strip()

    return ""

def extract_doi(record):
    """
    Extract DOI from a record using flexible field matching.
    """
    possible_doi_fields = {
        "doi",
        "item doi"
    }

    normalized_record = {
        key.strip().lower(): value
        for key, value in record.items()
    }

    for field in possible_doi_fields:
        if field in normalized_record:
            return str(normalized_record[field]).strip()

    return ""

def extract_local(record):
    """
    Extract local from a record using flexible field matching.
    """
    possible_local_fields = {
        "publication title",
        "booktitle",
        "journal",
        "source title"
    }

    normalized_record = {
        key.strip().lower(): value
        for key, value in record.items()
    }

    for field in possible_local_fields:
        if field in normalized_record:
            return str(normalized_record[field]).strip()

    return ""

def extract_link(record):
    """
    Extract link from a record using flexible field matching.
    """
    possible_link_fields = {
        "url",
        "link",
        "pdf link"
    }

    normalized_record = {
        key.strip().lower(): value
        for key, value in record.items()
    }

    for field in possible_link_fields:
        if field in normalized_record:
            return str(normalized_record[field]).strip()

    return ""


def remove_duplicates(records):
    """
    Remove duplicated records using title comparison.
    """
    unique_records = []
    duplicate_records = []

    seen_titles = {}
    duplicate_map = defaultdict(list)

    for record in records:
        title = extract_title(record)
        authors = extract_authors(record)
        year = extract_year(record)
        doi = extract_doi(record)
        local = extract_local(record)
        link = extract_link(record)

        record["title"] = title
        record["author"] = authors
        record["year"] = year
        record["doi"] = doi
        record["journal"] = local
        record["url"] = link

        if not title:
            continue

        normalized_title = normalize_title(title)

        if normalized_title not in seen_titles:
            record["title"] = normalized_title
            seen_titles[normalized_title] = record
            unique_records.append(record)

        else:
            original_record = seen_titles[normalized_title]

            duplicate_info = {
                "title": title,
                "doi": doi,
                "source_file": record["source_file"],
                "original_source_file": original_record["source_file"]
            }

            duplicate_records.append(duplicate_info)
            duplicate_map[normalized_title].append(duplicate_info)

    return unique_records, duplicate_records


def collect_all_columns(records):
    """
    Collect all available columns from records.
    """
    columns = set()

    for record in records:
        columns.update(record.keys())

    columns.discard("source_file")

    return sorted(columns)


def write_output_csv(records, output_file):
    """
    Write unified CSV output using a fixed column order.
    """
    if not records:
        return

    columns = [
        "Title",
        #"Authors",
        "Year",
        "In",
        "DOI",
        "URL",
        "SourceFile"
    ]

    with open(output_file, mode="w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames = columns,
            extrasaction = "ignore",
            quoting = csv.QUOTE_ALL
        )

        writer.writeheader()

        for record in records:
            # entry_type = str(
            #    record.get("ENTRYTYPE", "")
            # ).strip().lower()

            # if entry_type == "incollection":
            #    continue

            cleaned_record = {
                "Title": record.get("title", ""),
                "Authors": record.get("author", ""),
                "Year": record.get("year", ""),
                "In": record.get("journal", ""),
                "DOI": record.get("doi", ""),
                "URL": record.get("url", ""),
                "SourceFile": record.get("source_file", "")
            }

            writer.writerow(cleaned_record)


def write_summary_log(
    total_records,
    duplicate_records,
    unique_records,
    summary_file
):
    """
    Write summary statistics log.
    """
    with open(summary_file, mode="w", encoding="utf-8") as log_file:
        log_file.write("=== MERGE SUMMARY ===\n\n")

        log_file.write(f"Total works: {total_records}\n")
        log_file.write(f"Duplicated works: {len(duplicate_records)}\n")
        log_file.write(f"Unique works: {len(unique_records)}\n\n")

        log_file.write("=== DUPLICATED WORKS ===\n\n")

        if not duplicate_records:
            log_file.write("No duplicated works found.\n")
            return

        for index, duplicate in enumerate(duplicate_records, start=1):
            log_file.write(f"{index}. Title: {duplicate['title']}\n")
            log_file.write(f"   DOI: {duplicate['doi']}\n")
            log_file.write(
                f"   Source File: {duplicate['source_file']}\n"
            )
            log_file.write(
                f"   Original File: "
                f"{duplicate['original_source_file']}\n\n"
            )


def main():
    """
    Main execution flow.
    """
    args = parse_arguments()

    source_dir = args.source_dir

    if not os.path.exists(source_dir):
        print(f"Source directory does not exist: {source_dir}")
        return

    source_files = find_source_files(source_dir)

    if not source_files:
        print("No CSV or BibTeX files found.")
        return

    print(f"Found {len(source_files)} source files.")
    
    records = load_records(source_files)

    print(f"Loaded {len(records)} records.")

    unique_records, duplicate_records = remove_duplicates(records)

    write_output_csv(unique_records, OUTPUT_FILE)

    write_summary_log(
        total_records=len(records),
        duplicate_records=duplicate_records,
        unique_records=unique_records,
        summary_file=SUMMARY_FILE
    )

    print(f"Generated output file: {OUTPUT_FILE}")
    print(f"Generated summary file: {SUMMARY_FILE}")


if __name__ == "__main__":
    main()
