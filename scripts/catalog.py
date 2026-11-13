"""Build a catalog using trusted code and data from a candidate checkout."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

PAIR = r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*"
# Exactly what the client accepts (canonical SemVer 2.0, no build metadata): a
# row the client rejects would be dropped there after passing here.
IDENT = r"(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
VERSION = rf"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-{IDENT}(?:\.{IDENT})*)?"
SEGMENT = r"[A-Za-z0-9][A-Za-z0-9_.-]*"
KINDS = ("deepzora", "codex", "claude")
SELF = "SivanCola/deepzora-plugins"


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True, timeout=120).strip()


def build(root, output, inspector, previous):
    if (root / "registry.json").is_symlink():
        raise ValueError("registry must be a file")
    manifest = json.loads((root / "registry.json").read_text())
    if manifest["schemaVersion"] != 1:
        raise ValueError("unsupported registry")
    history = json.loads(previous.read_text())["releases"] if previous and previous.exists() else []
    releases = {(v["id"], v["version"]): v for v in history}
    origins, ids = {}, set()
    for item in manifest["plugins"]:
        key, sub = item["id"], item.get("path", "")
        repo = item.get("repo", SELF)
        if not re.fullmatch(PAIR, key) or key != key.lower() or not re.fullmatch(PAIR, repo):
            raise ValueError("invalid id or repo")
        if sub and not all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", s) for s in sub.split("/")):
            raise ValueError("invalid subdirectory")
        if not item["name"].strip() or not all(item["summary"][k].strip() for k in ("en","zh")):
            raise ValueError("missing display metadata")
        if key in ids or (repo.lower(),sub) in origins:
            raise ValueError("duplicate listing")
        ids.add(key)
        origins[(repo.lower(), sub)] = key
        minimum = item.get("minDeepzora")
        if minimum is not None and not re.fullmatch(VERSION, minimum):
            raise ValueError("invalid minimum Deepzora version")
        platforms = item.get("platforms", [])
        if not isinstance(platforms, list) or any(p not in ("darwin","linux","windows") for p in platforms):
            raise ValueError("invalid platforms")
        with tempfile.TemporaryDirectory() as tmp:
            if "commit" in item:
                sha = item["commit"]
                if not re.fullmatch("[a-f0-9]{40}", sha):
                    raise ValueError("a full commit is required")
                tree = Path(tmp)
                git(tree, "init", "-q")
                git(tree, "fetch", "--no-tags", "--depth=1", f"https://github.com/{repo}.git", sha)
                git(tree, "checkout", "-q", "--detach", sha)
            else:
                if repo != SELF or not sub.startswith("packages/"):
                    raise ValueError("only local packages can omit the commit")
                tree = root
                sha = git(root, "log", "-1", "--format=%H", "--", sub)
            package = tree / sub
            if not package.is_dir() or package.resolve()!=package.absolute():
                raise ValueError("invalid package root")
            for parent, dirs, files in os.walk(package):
                if ".git" in dirs:
                    dirs.remove(".git")
                if any((Path(parent) / f).is_symlink() for f in dirs+files):
                    raise ValueError("catalog packages cannot contain symlinks")
            report = json.loads(subprocess.check_output([inspector, str(package)], timeout=30))
            version = report["version"]
            if not isinstance(version, str) or not re.fullmatch(VERSION, version):
                raise ValueError("manifest must declare a semantic version")
            if not re.fullmatch(SEGMENT, str(report["manifestName"])) or report["manifestKind"] not in KINDS:
                raise ValueError("unsupported manifest name or kind")
            caps = [k for k,v in report["counts"].items() if v]
            if not caps and report["manifestKind"] != "deepzora":
                raise ValueError("no compatible capabilities")
            row = dict(id=key, repo=repo, path=sub, commit=sha, name=item["name"],
                       summary=item["summary"], capabilities=caps, platforms=item.get("platforms", []),
                       **{k: report[k] for k in ("version","manifestName","manifestKind")})
            if minimum:
                row["minDeepzora"] = minimum
            old_versions = [r for (rid, _), r in releases.items() if rid == key]
            for prior in old_versions:
                if prior["commit"] != sha:
                    print(json.dumps({"compare":f"https://github.com/{repo}/compare/{prior['commit']}...{sha}",
                                      "previousVersion":prior["version"],"candidateVersion":version,
                                      "addedCapabilities": sorted(set(caps)-set(prior["capabilities"])),
                                      "removedCapabilities": sorted(set(prior["capabilities"])-set(caps))}))
            old = releases.get((key,version))
            if old and (old["commit"],old["repo"],old["path"]) != (sha,repo,sub):
                raise ValueError(f"{key}@{version}: released source is immutable; bump version")
            releases[key,version] = row
            for (rid,v),existing in releases.items():
                if rid==key:
                    if (existing["repo"],existing["path"])!=(repo,sub):
                        raise ValueError("source changed; use a new ID")
                    existing["yanked"] = v in item.get("yanked", [])
            print(json.dumps(dict(release=row, verification=report), ensure_ascii=False))
    if set(v["id"] for v in history)-ids:
        raise ValueError("mark a release yanked instead of removing a listing")
    output.write_text(json.dumps(dict(schemaVersion=1,releases=[releases[k] for k in sorted(releases)]),ensure_ascii=False,indent=2)+"\n")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("root",type=Path)
    p.add_argument("output",type=Path)
    p.add_argument("--inspector",required=True)
    p.add_argument("--previous",type=Path)
    a=p.parse_args()
    build(a.root.resolve(),a.output,a.inspector,a.previous)

