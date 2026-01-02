#!/usr/bin/env bash
set -euo pipefail

git ls-files --others --exclude-standard > untracked_files.txt
