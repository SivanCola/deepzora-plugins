#!/bin/sh
set -eu
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
core=$(cd "$1" && pwd)
dest=$2
tmp=$(mktemp -d "$core/cmd/catalog-inspect-XXXXXX")
trap 'rm -rf "$tmp"' EXIT
cp "$here/inspect.go" "$tmp/main.go"
(cd "$core" && go build -o "$dest" "./cmd/$(basename "$tmp")")

