# Remotion native scene pilot

`product-story-v1` is a registered React composition for a three-beat product video. It renders from a data manifest, with separate frame ranges, image crops, camera movement, type hierarchy and optional audio. The runner accepts only this registered component and verifies every asset checksum before rendering. It does not execute code from a plan or prompt.

From this directory:

```powershell
npm ci
npm run test:native-scene
```

The command builds a nine-second Café Aurora example using existing repository images. It writes `output/remotion-native-scene-pilot/manifest.json`, `sample-sound.wav`, `product-story.mp4`, and `render-receipt.json` at the repository root. The sound is a synthetic timing fixture, not licensed music or voiceover. To render a different manifest:

```powershell
node render-native-scene.mjs C:\path\manifest.json C:\path\video.mp4
```

The manifest uses schema `res.remotion-native-scene.v1`. It specifies canvas dimensions, frame rate, three contiguous beats, brand, colors, image IDs and optional audio ID. `assetFiles` maps IDs to local files, MIME types and SHA-256 checksums. The runner emits a JSON receipt with the manifest and video checksums.

This is an isolated creative and editing pilot. The existing Remotion contextual provider still uses the shared Motion Canvas projection, and the native scene is not offered as a commercial render job. A production integration must bind this scene contract to a versioned `CreativeDocument`, preserve the existing review and mix path, and satisfy the visual and license gates.
