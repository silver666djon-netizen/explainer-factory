#!/bin/bash
# Release helper that also sees DRAFT releases (gh's tag lookups only find published ones).
# Needs GH_TOKEN with contents:write (drafts are visible only to writers). Repo: $GITHUB_REPOSITORY or the default.
#   tools/rel.sh id <tag>                      -> release id (exit 1 if none)
#   tools/rel.sh url <tag>                     -> html url
#   tools/rel.sh download <tag> <dir> [glob…]  -> assets matching any glob (default: all)
#   tools/rel.sh upload <tag> <file…>          -> upload, replacing assets with the same name
#   tools/rel.sh delete <tag>                  -> delete the release (and its tag if one exists)
#   tools/rel.sh assets <tag>                  -> "id<TAB>name<TAB>download url" per asset (a draft's url works for the owner)
#   tools/rel.sh rename <tag> <old> <new>      -> rename one asset
set -euo pipefail
R="${GITHUB_REPOSITORY:-silver666djon-netizen/explainer-factory}"
cmd="$1"; tag="$2"; shift 2
rid() { gh api "repos/$R/releases?per_page=100" --paginate -q ".[] | select(.tag_name == \"$tag\") | .id" | head -1; }
id=$(rid)
case "$cmd" in
  id) [ -n "$id" ] && echo "$id" || exit 1 ;;
  url) [ -n "$id" ] || exit 1; gh api "repos/$R/releases/$id" -q .html_url ;;
  download)
    [ -n "$id" ] || { echo "no release $tag" >&2; exit 1; }
    dir="$1"; shift; mkdir -p "$dir"
    gh api "repos/$R/releases/$id/assets?per_page=100" --paginate -q '.[] | "\(.id) \(.name)"' | while read aid name; do
      ok=0; if [ $# -eq 0 ]; then ok=1; fi
      for g in "$@"; do case "$name" in $g) ok=1 ;; esac; done
      if [ $ok = 1 ]; then gh api "repos/$R/releases/assets/$aid" -H "Accept: application/octet-stream" > "$dir/$name"; fi
    done ;;
  upload)
    [ -n "$id" ] || { echo "no release $tag" >&2; exit 1; }
    for f in "$@"; do
      n=$(basename "$f")
      old=$(gh api "repos/$R/releases/$id/assets?per_page=100" --paginate -q ".[] | select(.name == \"$n\") | .id" | head -1)
      if [ -n "$old" ]; then gh api -X DELETE "repos/$R/releases/assets/$old" >/dev/null; fi
      gh api -X POST "https://uploads.github.com/repos/$R/releases/$id/assets?name=$n" --input "$f" -H "Content-Type: application/octet-stream" >/dev/null
    done ;;
  assets)
    [ -n "$id" ] || { echo "no release $tag" >&2; exit 1; }
    gh api "repos/$R/releases/$id/assets?per_page=100" --paginate -q '.[] | "\(.id)\t\(.name)\t\(.browser_download_url)"' ;;
  rename)
    [ -n "$id" ] || { echo "no release $tag" >&2; exit 1; }
    aid=$(gh api "repos/$R/releases/$id/assets?per_page=100" --paginate -q ".[] | select(.name == \"$1\") | .id" | head -1)
    [ -n "$aid" ] || { echo "no asset $1" >&2; exit 1; }
    gh api -X PATCH "repos/$R/releases/assets/$aid" -f name="$2" >/dev/null ;;
  delete)
    [ -n "$id" ] && gh api -X DELETE "repos/$R/releases/$id" >/dev/null || true
    gh api -X DELETE "repos/$R/git/refs/tags/$tag" >/dev/null 2>&1 || true ;;
esac
