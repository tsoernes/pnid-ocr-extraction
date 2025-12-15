#!/bin/bash
# Demo script showing different types of P&ID comparisons
# Note: Position/coordinate differences are IGNORED by default

BASE="data/output/pnid_dexpi_final.json"

echo "============================================"
echo "P&ID Comparison Demo"
echo "============================================"
echo ""
echo "NOTE: Position differences are IGNORED by default"
echo "      Use --include-positions flag to compare them"
echo ""

echo "1. Components Removed (var_001):"
echo "--------------------------------"
python src/compare_pnid_jsonld.py "$BASE" \
  data/variations/pnid_c01_var_001_remove_components_medium.json | \
  grep -A 20 "Summary:"

echo ""
echo "2. Names Modified (var_003):"
echo "----------------------------"
python src/compare_pnid_jsonld.py "$BASE" \
  data/variations/pnid_c01_var_003_modify_names_medium.json | \
  grep -A 20 "Summary:"

echo ""
echo "3. Positions Perturbed (var_009) - NO DIFFERENCES (positions ignored):"
echo "----------------------------------------------------------------------"
python src/compare_pnid_jsonld.py "$BASE" \
  data/variations/pnid_c01_var_009_perturb_positions_medium.json

echo ""
echo "3b. Same with --include-positions flag:"
echo "---------------------------------------"
python src/compare_pnid_jsonld.py "$BASE" \
  data/variations/pnid_c01_var_009_perturb_positions_medium.json --include-positions | \
  grep -A 20 "Summary:"

echo ""
echo "4. Combined Heavy Changes (var_006):"
echo "------------------------------------"
python src/compare_pnid_jsonld.py "$BASE" \
  data/variations/pnid_c01_var_006_combined_heavy_medium.json | \
  grep -A 20 "Summary:"

echo ""
echo "============================================"
echo "JSON Output Example (var_001):"
echo "============================================"
python src/compare_pnid_jsonld.py "$BASE" \
  data/variations/pnid_c01_var_001_remove_components_medium.json --json | \
  jq '.summary'
