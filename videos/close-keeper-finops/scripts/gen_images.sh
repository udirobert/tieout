#!/bin/bash
K="$ELEVENLABS_API_KEY"; OUT=assets/img; mkdir -p $OUT
STYLE="Editorial risograph illustration, strictly text-free - no letters, numbers, logos or readable characters anywhere. Single object or figure isolated on a flat near-black #0e1013 background so it cuts out cleanly. Ink-black and paper-cream only, one small burnt-orange accent, heavy grain, hard rim light, high contrast, printmaking texture."
gen() { curl -s -X POST -H "xi-api-key: $K" -H "Content-Type: application/json" \
  -d "{\"model_id\":\"gemini-3-pro-image\",\"prompt\":\"$2 $STYLE\",\"aspect_ratio\":\"$3\",\"resolution\":\"2K\"}" \
  https://api.elevenlabs.io/v1/flows/image | python3 -c 'import json,sys;print(json.load(sys.stdin).get("id",""))'; }
declare -a NAMES=(night-close paper-stack hands-receipt stamp mcp-plug lantern)
declare -a PROMPTS=(
"A lone person hunched at a small kitchen table at midnight, laptop screen lighting their face from below, paperwork fanned across the table, a cold cup of coffee, tired and unglamorous, three-quarter view"
"A tall slightly-toppling stack of paper receipts and printed sheets held by one binder clip, side view, a few sheets fanning loose at the top"
"Two hands holding up a single torn paper receipt against the light to examine it, jagged torn edge on top, everything else falling into shadow"
"A heavy wooden-handled rubber stamp resting face-up on an ink pad, a wet smear of orange ink beside it, low three-quarter angle"
"A hand plugging a thick braided cable with a chunky industrial connector into a wall socket, faint warm glow at the contact point"
"A small closed metal lantern hanging from one hook, lit from inside, casting a tight cone of warm light down onto empty floor, nothing else")
declare -a RATIOS=("3:4" "1:1" "4:3" "1:1" "1:1" "3:4")
IDS=()
for i in "${!NAMES[@]}"; do IDS+=("$(gen x "${PROMPTS[$i]}" "${RATIOS[$i]}")"); echo "queued ${NAMES[$i]} -> ${IDS[$i]}"; done
END=$((SECONDS+400))
while [ $SECONDS -lt $END ]; do
  left=0
  for i in "${!NAMES[@]}"; do
    [ -f "$OUT/${NAMES[$i]}.png" ] && continue
    [ -z "${IDS[$i]}" ] && continue
    left=$((left+1))
    J=$(curl -s -H "xi-api-key: $K" "https://api.elevenlabs.io/v1/flows/image/${IDS[$i]}")
    S=$(echo "$J" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("status",""))')
    if [ "$S" = "completed" ]; then
      U=$(echo "$J" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("content_url") or (d.get("asset_images") or [{}])[0].get("content_url",""))')
      curl -s -o "$OUT/${NAMES[$i]}.png" "$U" && echo "DONE ${NAMES[$i]} $(du -h "$OUT/${NAMES[$i]}.png" | cut -f1)"
    elif [ "$S" = "failed" ]; then echo "FAILED ${NAMES[$i]}: $J"; IDS[$i]=""; fi
  done
  [ $left -eq 0 ] && break
  sleep 5
done
echo "remaining without file: $(ls $OUT | wc -l) of 6"
