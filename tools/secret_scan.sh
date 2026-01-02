#!/usr/bin/env bash
set -euo pipefail

git secrets --scan > secret_scan_report.txt
