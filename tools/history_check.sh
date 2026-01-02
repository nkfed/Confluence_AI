#!/usr/bin/env bash
set -euo pipefail

git rev-list --objects --all | sort -k 2 > allfiles.txt
grep -E "(\.log|\.txt|\.json|\.csv)$" allfiles.txt > suspect_files.txt
