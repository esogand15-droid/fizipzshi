#!/usr/bin/env bash
# Pushes a status marker + any pending results back to the session branch.
# Used by GitHub Actions jobs because Actions logs are not reachable from the
# agent sandbox (only git/API egress is allowed there).
set -u
BRANCH="${BRANCH:-arena/ff8acb52-fizipzshi}"
MSG="${1:-state}"
mkdir -p work/relay
echo "[$(date -u +%H:%M:%S)] $MSG" >> work/relay/status.log
git config user.email "agent@arena.ai" >/dev/null 2>&1 || true
git config user.name "HumsYar Agent Runner" >/dev/null 2>&1 || true

# stage results (videos/media never; heavy intermediates are skipped below)
for d in work/relay work/ocr work/transcripts work/pdftext work/relay/inventory.json \
         src INVENTORY.md tools frames images lock render fonts .gitignore .gitattributes; do
  git add -A "$d" 2>/dev/null || true
done
# never commit downloaded media or whisper wav dumps (they live in the release)
git rm -r -q --cached --ignore-unmatch work/media work/tmp_media >/dev/null 2>&1 || true
git rm -q --cached --ignore-unmatch render/pass1.pdf render/pass1.html render/pass2.html \
  render/HumsYar_MedPhysics_Jozve.pdf >/dev/null 2>&1 || true
find . -type f -size +20M -not -path './.git/*' -print0 2>/dev/null | xargs -0 -r git reset -q -- 2>/dev/null || true
git add -f "src/HumsYar_Master_Prompt_Physiology.md" 2>/dev/null || true
# the built book itself: keep the newest PDF at the repo root (deliverable)
[ -f HumsYar_MedPhysics_Jozve.pdf ] && git add -f HumsYar_MedPhysics_Jozve.pdf 2>/dev/null || true

if git diff --cached --quiet; then
  echo "[$(date -u +%H:%M:%S)] nothing staged for $MSG" >> work/relay/status.log
else
  git commit -q -m "relay: $MSG" || echo "(commit failed)" >> work/relay/status.log
fi

for i in 1 2 3 4 5; do
  if git push origin "HEAD:$BRANCH" >/dev/null 2>&1; then
    echo "[$(date -u +%H:%M:%S)] pushed: $MSG" >> work/relay/status.log
    break
  fi
  git fetch -q origin "$BRANCH" >/dev/null 2>&1 || true
  git merge -q -X ours --no-edit "origin/$BRANCH" >/dev/null 2>&1 || git checkout -q --theirs . 2>/dev/null || true
  git add -A work 2>/dev/null || true
  git commit -q -m "relay: $MSG (merge)" >/dev/null 2>&1 || true
  sleep 4
done
exit 0
