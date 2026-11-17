/**
 * Renders the "Overlay" composition to a transparent VP8 WebM.
 *
 * Transparency needs codec vp8/vp9 + pixelFormat yuva420p; assemble.py decodes
 * the result back to RGBA PNG frames so the alpha channel survives compositing.
 */
const path = require('node:path');
const fs = require('node:fs');
const {bundle} = require('@remotion/bundler');
const {selectComposition, renderMedia} = require('@remotion/renderer');

const OUT_DIR = path.resolve(__dirname, 'out');
const OUT_FILE = path.join(OUT_DIR, 'overlay.webm');

const main = async () => {
  fs.mkdirSync(OUT_DIR, {recursive: true});

  console.log('Bundling Remotion project...');
  const serveUrl = await bundle({
    entryPoint: path.resolve(__dirname, 'src/index.ts'),
  });

  const composition = await selectComposition({serveUrl, id: 'Overlay'});
  console.log(
    `Rendering ${composition.width}x${composition.height} @ ${composition.fps}fps, ` +
      `${composition.durationInFrames} frames`,
  );

  await renderMedia({
    composition,
    serveUrl,
    codec: 'vp8',
    pixelFormat: 'yuva420p',
    imageFormat: 'png',
    muted: true,
    outputLocation: OUT_FILE,
  });

  const {size} = fs.statSync(OUT_FILE);
  console.log(`Wrote ${OUT_FILE} (${(size / 1024).toFixed(0)} kB)`);
};

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
