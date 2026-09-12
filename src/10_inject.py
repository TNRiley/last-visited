#!/usr/bin/env python3
"""Splice payload.json and app.js into template.html, then finish the page.

wrap_for_pages.py and add_catalog_link.py run as the last two steps: regenerating
the page without them silently drops the doctype and the breadcrumb back to the
catalog, and the page then looks fine locally and wrong on Pages.

    python 10_inject.py
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)

def workspace_root(p):
    while True:
        if os.path.isdir(os.path.join(p, "projects")):
            return p
        nxt = os.path.dirname(p)
        if nxt == p:
            raise SystemExit("could not find the workspace root")
        p = nxt

def read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return fh.read()

tpl, data, app = read("template.html"), read("payload.json"), read("app.js")
for token in ("__DATA__", "__APP__"):
    if token not in tpl:
        raise SystemExit("template has no %s placeholder" % token)

out = tpl.replace("__DATA__", data).replace("__APP__", app)
dest = os.path.join(PROJ, "index.html")
with open(dest, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(out)
print("wrote %s  (%.2f MB)" % (dest, os.path.getsize(dest) / 1e6))

tools = os.path.join(workspace_root(HERE), "catalog", "tools")
for script in ("wrap_for_pages.py", "add_catalog_link.py"):
    r = subprocess.run([sys.executable, os.path.join(tools, script), dest],
                       capture_output=True, text=True)
    msg = (r.stdout or r.stderr).strip().splitlines()
    print("  %-22s %s" % (script, msg[-1] if msg else "ok"))
    if r.returncode:
        raise SystemExit(r.returncode)
