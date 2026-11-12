# Deepzora community plugins

Submit a pull request editing `registry.json`. Include bilingual summaries, a license, README, and a package containing a Deepzora v2, Codex or Claude manifest. A local package lives in `packages/<name>/`; alternatively specify a public GitHub repo, package path and full commit. The release version comes from the manifest. Do not reuse a released version for different code. To withdraw a release add its version to the entry's `yanked` array; do not delete its history.

Example listing (repository defaults to this one):

```json
{"id":"community/review-kit","name":"Review Kit","path":"packages/review-kit","summary":{"en":"Review a change","zh":"审阅改动"}}
```

PR CI reads the exact source tree with Deepzora's parser, lists its inventory and compatibility diagnostics and uploads a candidate index. Review the source, license, host commands and capability changes. Maintainers merge only after review. The publish workflow runs on main, preserves existing releases and publishes `dist/index-v1.json`. Catalog clients install the recorded Git commit; no npm account or package proxy is required. Changes in another repository cannot change an existing release.

Independent authors can add the GitHub topic **deepzora-plugin** to a public non-fork repository with a root manifest. A scheduled workflow publishes a separate unreviewed `dist/tagged.json`. A topic never grants community review. Browse both sources with `deepzora plugin search --all`.

Local reproduction: build the inspector using `scripts/inspector.sh /path/to/deepzora /tmp/plugin-inspect` in a clean Deepzora checkout, then run `python3 scripts/catalog.py . /tmp/index-v1.json --inspector /tmp/plugin-inspect`. The inspector only parses files; no install, hook, login or runtime startup occurs.

