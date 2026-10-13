# Clicko authentication gallery

These two original editorial assets were generated with the built-in image-generation tool on 2026-09-06. They are decorative content inside independent CSS 3D panels, not a flattened UI background. Optimized JPEGs total approximately 169 KiB. Full-resolution originals remain in the local generated_images directory.

## Generation prompts

**clicko-leaves.jpg** — Portrait 2:3 editorial studio photograph of sculptural tropical leaves. Graphite black and silver-gray satin textures, fine veins, true black background, tiny controlled coral #FF7F50 rim light and subtle tangerine reflection. Mostly monochromatic, softly lit contours. No lettering, UI, panels, logos, orange wash or blue.

**clicko-mountain.jpg** — Landscape editorial photography of a sculptural dark mountain above soft low fog. Silver-gray rock, gray mist, near-black sky, delicate coral sunrise rim on the right. Deep shadow and fine texture; no blue, neon, text, frame, logo or stars.

## Implementation

- AuthAtmosphere.tsx and AuthAtmosphere.css own the decorative scene; no account data or API calls.
- Perspective and distinct translateZ depths, damped pointer camera and route interpolation. LoginView stays mounted during its existing Login/Signup mode change.
- Nine lightweight panels; four on small/coarse-pointer layouts. CSS fallback when perspective is unavailable.
- 30 Hz camera updates, 20 Hz on compact/low-core devices. No React state updates per animation frame. Hidden tabs pause the loop and ambient animation. Reduced motion disables camera and ambient movement.
- Decorative content is aria-hidden and pointer-events:none; forms retain their auth handlers, labels and validation.

## Visual QA

Login and Signup inspected at 1280px and 390px widths. No horizontal overflow; image loading and mode transition verified. No browser warning/error logs during these checks. Auth API logic is unchanged; visual QA does not imply testing email delivery or external integrations.
