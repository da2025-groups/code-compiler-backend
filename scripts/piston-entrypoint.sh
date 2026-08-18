#!/bin/bash
# Custom Piston entrypoint: starts the API then auto-installs required runtimes.
# Uses python3 for HTTP (curl is not present in the piston image).

CGROUP_FS="/sys/fs/cgroup"

(
  [ -e "$CGROUP_FS/cgroup.subtree_control" ] || { echo "cgroup v2 not found, skipping setup"; exit 0; }
  [ ! -e "$CGROUP_FS/unified" ] || { echo "Combined cgroup v1+v2 not supported, skipping"; exit 0; }
  cd "$CGROUP_FS" && \
  mkdir -p isolate/ && \
  echo 1 > isolate/cgroup.procs 2>/dev/null && \
  echo '+cpuset +cpu +io +memory +pids' > cgroup.subtree_control 2>/dev/null && \
  mkdir -p isolate/init && \
  echo 1 > isolate/init/cgroup.procs 2>/dev/null && \
  echo '+cpuset +memory' > isolate/cgroup.subtree_control 2>/dev/null && \
  echo "cgroup initialized"
) || echo "WARNING: cgroup setup incomplete — continuing anyway"

chown -R piston:piston /piston

# Start Piston API in background
su -- piston -c 'ulimit -n 65536 && node /piston_api/src' &
PISTON_PID=$!

# Wait for API (python3 is always available; curl is not)
echo "Waiting for Piston API..."
python3 - <<'PYEOF'
import urllib.request, time, sys
for _ in range(60):
    try:
        urllib.request.urlopen("http://localhost:2000/api/v2/runtimes", timeout=3)
        print("Piston API ready")
        sys.exit(0)
    except Exception:
        time.sleep(3)
print("ERROR: Piston API did not start", file=sys.stderr)
sys.exit(1)
PYEOF

[ $? -ne 0 ] && exit 1

# Install required runtimes — idempotent, skips already-installed ones
python3 - <<'PYEOF'
import urllib.request, json, sys

BASE = "http://localhost:2000/api/v2"

def get(path):
    with urllib.request.urlopen(f"{BASE}{path}", timeout=10) as r:
        return json.loads(r.read())

def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())

REQUIRED = [
    ("python",      "3.12.0"),
    ("javascript",  "18.15.0"),
    ("java",        "15.0.2"),
    ("gcc",         "10.2.0"),
    ("go",          "1.16.2"),
    ("rust",        "1.68.2"),
]

installed_langs = {r["language"] for r in get("/runtimes")}

for lang, ver in REQUIRED:
    if lang in installed_langs:
        print(f"  [ok] {lang} already installed")
    else:
        print(f"  [+]  Installing {lang}-{ver} ...")
        sys.stdout.flush()
        result = post("/packages", {"language": lang, "version": ver})
        print(f"       {result}")

print("All runtimes ready.")
PYEOF

wait $PISTON_PID
