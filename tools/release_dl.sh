#!/bin/bash
# usage: tools/release_dl.sh <tag> <grep-pattern> <outdir>   (works for draft releases too: they have no public tag URL)
R=silver666djon-netizen/explainer-factory
mkdir -p "$3"
id=$(gh api "repos/$R/releases?per_page=100" --paginate -q ".[] | select(.tag_name == \"$1\") | .id" | head -1)
[ -n "$id" ] || { echo "no release $1" >&2; exit 1; }
gh api "repos/$R/releases/$id/assets?per_page=100" --paginate -q '.[] | "\(.id) \(.name)"' | grep -E " ($2)" | while read aid name; do
  gh api "repos/$R/releases/assets/$aid" -H "Accept: application/octet-stream" > "$3/$name" && echo "got $name"
done
