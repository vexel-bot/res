# Clicko autonomous video-editing benchmark

`video-edit-planner-pt-br-policy.v1.json` freezes the first provider-neutral evaluation of a
multimodal editing planner. Canonical digest:

- `1e07d491e5ad6850e6bb9fcd76ea861e1bdf3f40c53bcb6b5f4440109c20a8ed`.

The suite compares Qwen3-VL 4B and 8B only after their exact model bytes and serving runtime are
pinned. A hosted Gemini video implementation is the planned baseline, but hosted APIs do not
pretend to be open-source artifacts and therefore are not recorded in an artifact inventory.

The planner may emit typed proposals with evidence/timecodes. It may not directly mutate a
`CreativeDocument`, approve its own output, or act as the only quality judge. Missing evidence,
invalid operations, unpinned weights, or an incomplete runtime keep the decision fail-closed.

Motion Canvas, OpenTimelineIO and PySceneDetect are supporting tools rather than planning
models. Their separate inventories let the team evaluate a deterministic motion projection,
timeline interchange and shot-boundary evidence without copying any of them into the domain.
