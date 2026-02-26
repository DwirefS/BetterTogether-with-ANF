#!/usr/bin/env bash
set -euo pipefail

# Validate local prerequisites for the AlphaAgent demo.
RED='\033[0;31m'; GREEN='\033[0;32m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅${NC} $1"; }
fail() { echo -e "${RED}❌${NC} $1"; MISSING=1; }

MISSING=0

command -v az      >/dev/null 2>&1 && ok "az CLI"    || fail "az CLI not found (https://aka.ms/installazurecli)"
command -v make    >/dev/null 2>&1 && ok "make"       || fail "make not found"
command -v bash    >/dev/null 2>&1 && ok "bash"       || fail "bash not found"
command -v ssh     >/dev/null 2>&1 && ok "ssh"        || fail "ssh not found"
command -v rsync   >/dev/null 2>&1 && ok "rsync"      || fail "rsync not found"
command -v jq      >/dev/null 2>&1 && ok "jq"         || fail "jq not found (brew install jq)"

# Check az login status
if az account show >/dev/null 2>&1; then
  ACCT=$(az account show --query name -o tsv)
  ok "az authenticated ($ACCT)"
else
  fail "Not logged in to Azure. Run: az login"
fi

if [[ "$MISSING" -ne 0 ]]; then
  echo ""
  echo "Install missing prerequisites before continuing."
  exit 1
fi

echo ""
echo "All prerequisites satisfied."
