#!/usr/bin/env bash
# Pushes a status marker + any pending changes back to the session branch.
# Used by the GitHub Actions relay because Actions logs are not reachable
# from the agent sandbox (only git/API egress is allowed there).
set -u
BRANCH="${BRANCH:-arena/01a0f6eb-fizipzshi}"
MSG="${1:-state}"
mkdir -p work/relay
echo "[$(date -u +%H:%M:%S)] $MSG" >> work/relay/status.log
git config user.email "agent@arena.ai" >/dev/null 2>&1 || true
git config user.name "HumsYar Agent Runner" >/dev/null 2>&1 || true
git add -A work/relay src INVENTORY.md tools .gitignore .gitattributes 2>/dev/null || true
find src -type f -size +45M -print0 2>/dev/null | xargs -0 -r git reset -q -- 2>/dev/null || true
git commit -q -m "relay: $MSG" >/dev/null 2>&1 || echo "(no changes for $MSG)" >> work/relay/status.log
for i in 1 2 3; do
  if git push origin "HEAD:$BRANCH" >/dev/null 2>&1; then
    echo "[$(date -u +%H:%M:%S)] pushed: $MSG" >> work/relay/status.log
    break
  fi
  git pull --no-rebase -X ours -q origin "$BRANCH" >/dev/null 2>&1 || true
  git commit -q -m "relay: $MSG (merge)" >/dev/null 2>&1 || true
  sleep 5
done
exit 0
