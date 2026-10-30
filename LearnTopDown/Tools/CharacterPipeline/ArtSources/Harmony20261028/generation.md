# Sparrow harmony artwork, 2026-10-28

Built-in image generation produced transparent RGBA source artwork. The four user supplied crow bow images and the previously accepted structural direction were used for the bow. These are new generated assets, not extracted game weapon meshes. Existing third-party source packs remain unchanged.

## Bow

Output: `bow-relief.png`. Original generated output: `exec-365d1ce0-906d-4990-a008-294501496746.png`.

Prompt:

Create a production transparent RGBA texture asset of ONE elaborately carved fantasy recurve bow, orthographic FRONT view horizontally laid out. Use references 1-4 for the exact HARD WEAPON STRUCTURE, not their characters: narrow sharply bent connecting arms, two inward hooked spike clusters next to the grip, at the two ends a broad fan of 4-5 long angular rigid crow-feather BLADES with deeply cut negative spaces. Use reference 5 as the accepted structural direction, and substantially improve its ornamentation and material depth. Palette aged dark bronze and warm gold, ivory only on narrow bevels; dark inset plate centers, fine engraved ridges and hooked barbs, sharp tips. Make the inner two hook clusters ornate 3-pronged interlocking talons, clearly distinct from the small center grip. Stagger 4-5 blade lengths and angles at each tip, not uniform leaf petals. Intricate layered raised metal ridges and dark cut channels, actual sculptural depth in painted shading, razor edge highlights, very restrained golden energy only along seams. Large transparent gaps, thin connecting limbs. Avoid a continuous fluffy wing, smooth leaf silhouettes, flat beige fill, big central crest, broad bloom. Grip UV(.5,.735), string tips near(.073,.035)/(.927,.035), complete bow in 2.75:1 frame. No string, arrow, character, background, text, red annotation. One full bow on genuinely transparent background.

## Arrow

Output: `arrow-relief.png`. Original generated output: `exec-8b518eec-5020-4e75-acdf-2689cca2912b.png`.

Prompt:

One SINGLE exquisitely crafted fantasy arrow / light lance VFX texture asset, full orthographic SIDE silhouette, horizontal points RIGHT, transparent RGBA, ultra wide about 4:1. Design quality of a high-end fantasy MMO weapon. Full length is about three character heights. A razor spear-like arrowhead about 23 percent length with a long needle point, a pair of swept sharply hooked secondary blades, sculpted dark bronze inset recesses and narrow raised ivory/gold bevel ridges. NO plain triangular broadhead. Slender long shaft about 48 percent length with small engraved collars and narrow golden energy seams. Tail about 20 percent length has three sharply swept carved feather vanes with separated barbs and deep negative gaps, clearly a real ARROW tail. Aged dark bronze / gold, tiny ivory ridges, dark visible facet faces, restrained gold light moving through seams. The silhouette must be crisp, tapered, elegant and intricate at small game scale. No huge flat white or beige triangles, no ordinary pole with an attached triangle, no leaves, no broad bloom, no trail or particles, no bow, no character, no words or grid. Entire one arrow visible with transparent margins, exact left-right flight axis, genuinely transparent background.

## Native integration

The source pixels are unchanged. `prepare-relief.py` in the associated QA output reads alpha and luminance to build front/back relief and boundary geometry, exported as `bow-relief.json` and `arrow-relief.json`. `sparrow_harmony_author.py` imports these as SM_ReferenceBow and SM_CarvedArrow with matching artwork materials under /Game/TopDown/Characters/Sparrow/FX/Harmony20261028. The bow spans 480 cm and the arrow 320 cm before per-skill scaling. Artwork is a painted relief, not a fully modeled production weapon asset; oblique/back views are limited.

Actual runtime captures, not the source artwork, are the review basis. See Saved/QA/CharacterPipeline/sparrow-harmony-rework-20261028/preview.html and game-manifest.json.
