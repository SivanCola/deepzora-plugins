"""Generate the unreviewed channel; never execute code from a tagged repo."""
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.request
from catalog import build


def api(path):
    headers = {"User-Agent":"deepzora-plugin-index","Accept":"application/vnd.github+json"}
    if os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request("https://api.github.com/"+path,headers=headers),timeout=30) as r:
        return json.load(r)


def main(inspector, dest):
    rows=[]
    for page in range(1,11):
        repos=api(f"search/repositories?q=topic:deepzora-plugin+archived:false+fork:false&per_page=100&page={page}")["items"]
        for repo in repos:
            name=repo["full_name"]
            sha=api("repos/"+name+"/commits/"+repo["default_branch"])["sha"]
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp); out=root/"out.json"
                label=repo.get("description") or name
                entry=dict(id=name.lower(),name=repo["name"],repo=name,commit=sha,summary={"zh":label,"en":label})
                (root/"registry.json").write_text(json.dumps(dict(schemaVersion=1,plugins=[entry])))
                try:
                    build(root,out,inspector,None)
                except (ValueError,KeyError, __import__("subprocess").SubprocessError) as err:
                    print(f"skipping {name}: {err}",file=sys.stderr)
                    continue
                rows.extend(json.loads(out.read_text())["releases"])
        if len(repos)<100:
            break
    Path(dest).write_text(json.dumps(dict(schemaVersion=1,releases=rows),ensure_ascii=False,indent=2)+"\n")


if __name__=="__main__":
    main(*sys.argv[1:])

