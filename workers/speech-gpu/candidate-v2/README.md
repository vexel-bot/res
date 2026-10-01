# Speech GPU PT-BR minimal v2

This directory is a parallel, unpromoted dependency-minimization revision. It never
replaces `candidate/` evidence in place.

- Chatterbox and Perth remain pinned to the v1 source revisions, but both wheels
  must be built and installed with `--no-deps`. The PT-BR environment omits
  `pykakasi`; Chatterbox already handles that optional Japanese import lazily.
- `openvoice-tone-color-only.patch` preserves the upstream base-speaker path with a
  lazy text import while preventing English/Mandarin cleaners from loading when the
  worker imports only `ToneColorConverter`.
- `kokoro-lazy-language-g2p.patch` postpones annotations and imports the English G2P
  only for language codes `a`/`b`; the PT-BR `p` path keeps `misaki.espeak`.
- Patched OpenVoice and Kokoro wheels must be built from their pinned revisions and
  installed with `--no-deps`. Misaki remains pinned without the `en` extra.

The Linux dependency stages now pass clean patch application, static import proof,
source-wheel builds with `--no-deps`, frozen uv installs and offline import smokes.
They explicitly prove that `pykakasi`, `praat-parselmouth`, `Unidecode`,
`eng_to_ipa`, `cn2an`, `jieba`, `pypinyin`, `inflect`, `num2words` and the Misaki
English extra do not return. The OpenVoice stage also replaces the bytes bundled by
`espeakng-loader` with the separately built, manifested eSpeak runtime using a
stdlib-only installer. No final v2 image, benchmark result or provider is approved
by this evidence. The next gates are final isolated-image smoke, complete SBOM and
notices review.

The Kokoro source audit distinguishes the canonical Git blob digest of `LICENSE`
(`c71d239d...`) from the normalized Apache-2.0 text digest (`1eb85fc9...`) already
used by earlier inventories. Linux source builds verify the canonical blob bytes.
