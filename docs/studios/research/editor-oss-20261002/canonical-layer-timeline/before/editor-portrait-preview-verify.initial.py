"""Compare retained real browser frames against exact original-size MP4 decoding."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAPTURES = ROOT / 'docs/studios/research/editor-oss-20261002/directed-native14-portrait-ui'
OUT = ROOT / 'docs/studios/research/editor-oss-20261002/canonical-layer-timeline/portrait-pixels.json'
assert not OUT.exists(), 'Preserve certified evidence'
state = json.loads((ROOT / 'output/visual-directed-native14-20261004/execution.json').read_text(encoding='utf-8'))
receipt = []
decoded = {}
for path in sorted(CAPTURES.glob('*.json')):
    observed = json.loads(path.read_text(encoding='utf-8'))['data']['result']
    key = next(key for key in state['variants'] if path.name.startswith(key + '-'))
    video = ROOT / 'output/visual-directed-native14-20261004' / (key + '.mp4')
    assert hashlib.sha256(video.read_bytes()).hexdigest() == observed['video']['sha256']
    assert observed['overlayCount'] == 0 and observed['video']['objectFit'] == 'contain'
    assert observed['computedAspect'] == '0.5625 / 1'
    assert abs(observed['frameRect']['width'] - observed['frameRect']['height'] * 9 / 16) <= 1 / 64
    frame = round(observed['video']['currentTime'] * 30)
    cache_key = (key, frame)
    if cache_key not in decoded:
        decoded[cache_key] = subprocess.check_output(['ffmpeg', '-v', 'error', '-threads', '1', '-i', str(video),
            '-vf', f'select=eq(n\\,{frame})', '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
        assert len(decoded[cache_key]) == 1080 * 1920 * 3
    maximum = 0
    for point in observed['pixels']:
        offset = (point['y'] * 1080 + point['x']) * 3
        expected = decoded[cache_key][offset:offset + 3]
        maximum = max(maximum, *(abs(a-b) for a,b in zip(point['rgb'], expected)))
    assert maximum <= 4, (path.name, maximum, 'Do not widen the declared channel tolerance')
    if '-timeline-' in path.name:
        timeline = observed['canonicalTimeline']
        assert timeline['maximum'] == '449' and int(timeline['frame']) == frame
        assert timeline['legacyClips'] == timeline['trimControls'] == 0
        assert int(observed['compositionFrame']) == frame
        assert observed['inspectorVideo']['src'] == observed['video']['src']
        assert abs(observed['inspectorVideo']['currentTime'] - frame/30) <= .000002
    receipt.append({'capture':path.name,'frame':frame,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'points':len(observed['pixels']),'maxChannelError':maximum})
    print(path.name, frame, maximum, flush=True)
OUT.write_text(json.dumps({'scope':'sparse browser-to-independent-original-size-MP4 pixels; no human quality verdict',
    'declaredMaxChannelError':4,'captures':receipt},indent=2),encoding='utf-8')
