#!/bin/bash
# usage: tools/release_dl.sh <tag> <grep-pattern> <outdir>
R=silver666djon-netizen/explainer-factory
mkdir -p "$3"
gh api repos/$R/releases/tags/$1 -q '.assets[] | "\(.id) \(.name)"' | grep -E " ($2)" | while read id name; do
  gh api repos/$R/releases/assets/$id -H "Accept: application/octet-stream" > "$3/$name" && echo "got $name"
done
