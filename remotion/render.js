/**
 * Renders the cinematic documentary composition to out/cinematic_video.mp4.
 *
 * The scene list comes from data/scenes.json, so a new episode is data only.
 *
 *   node render.js                     # 1920x1080 long-form
 *   node render.js --vertical          # 1080x1920 shorts
 *   node render.js --out out/x.mp4     # custom destination
 */
const fs = require('node:fs');
const path = require('node:path');
const {bundle} = require('@remotion/bundler');
const {selectComposition, renderMedia} = require('@remotion/renderer');

const ROOT = __dirname;

const parseArgs = (argv) => {
  const args = {vertical: false, out: path.join(ROOT, 'out', 'cinematic_video.mp4')};
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--vertical') args.vertical = true;
    else if (arg === '--out') args.out = path.resolve(argv[++i]);
    else if (arg === '--fps') args.fps = Number(argv[++i]);
    else if (arg === '--scene-seconds') args.sceneSeconds = Number(argv[++i]);
    else if (arg === '--overlap-seconds') args.overlapSeconds = Number(argv[++i]);
  }
  return args;
};

/**
 * scenes.json is written by generate_video.py using the {image_url, text,
 * layout, durationInSeconds} schema. Older hand-written files use {image,
 * caption} and no layout, so accept both and hand the composition one canonical
 * shape. An unknown layout is a hard error: silently rendering the wrong framing
 * is worse than failing the render.
 */
const LAYOUTS = ['host_full', 'host_pip', 'broll_only'];

const normalizeScenes = (raw) => {
  if (!Array.isArray(raw) || raw.length === 0) {
    throw new Error('data/scenes.json has no "scenes" array');
  }
  return raw.map((scene, index) => {
    const layout = scene.layout || 'broll_only';
    const image = scene.image_url || scene.image || '';
    const caption = scene.text || scene.caption;
    if (!LAYOUTS.includes(layout)) {
      throw new Error(
        `scene ${index + 1} has unknown layout "${layout}" (expected ${LAYOUTS.join(', ')})`,
      );
    }
    // Only a full-frame presenter shot can do without a still.
    if (!image && layout !== 'host_full') {
      throw new Error(`scene ${index + 1} (${layout}) has no image_url/image`);
    }
    if (!caption) throw new Error(`scene ${index + 1} has no text/caption`);
    return {
      image,
      layout,
      caption,
      kicker: scene.kicker,
      durationInSeconds: scene.durationInSeconds,
    };
  });
};

const main = async () => {
  const args = parseArgs(process.argv.slice(2));
  const data = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'scenes.json'), 'utf8'));
  const scenes = normalizeScenes(data.scenes);
  const topic = data.topic || data._notes?.topic;

  // `data._notes.image_source` documents that the stills are placeholders; the
  // eventual AI image API feeds the same scene URLs, nothing else changes.
  if (data._notes?.image_source) {
    console.log(`Image source: ${data._notes.image_source.split('.')[0]}.`);
  }
  if (topic) console.log(`Episode: ${topic}`);

  const inputProps = {
    title: data.title || '12th Street',
    scenes,
    sceneDurationInSeconds: args.sceneSeconds ?? data.sceneDurationInSeconds ?? 6,
    overlapInSeconds: args.overlapSeconds ?? 1,
    fps: args.fps ?? 30,
    width: args.vertical ? 1080 : 1920,
    height: args.vertical ? 1920 : 1080,
  };

  console.log(`Bundling Remotion project (${scenes.length} scenes)...`);
  // publicDir is explicit: scene stills live in remotion/public/episodes/... and
  // are referenced as "/episodes/...". Without this, bundle() looks for a public
  // folder relative to the process cwd and every local still 404s.
  const serveUrl = await bundle({
    entryPoint: path.join(ROOT, 'src', 'index.ts'),
    publicDir: path.join(ROOT, 'public'),
  });

  const composition = await selectComposition({
    serveUrl,
    id: 'CinematicDoc',
    inputProps,
  });

  console.log(
    `Rendering ${composition.width}x${composition.height} @ ${composition.fps}fps, ` +
      `${composition.durationInFrames} frames (${(composition.durationInFrames / composition.fps).toFixed(1)}s)`,
  );

  fs.mkdirSync(path.dirname(args.out), {recursive: true});

  await renderMedia({
    composition,
    serveUrl,
    codec: 'h264',
    crf: 18,
    imageFormat: 'jpeg',
    inputProps,
    outputLocation: args.out,
    onProgress: ({progress}) => {
      const pct = Math.round(progress * 100);
      if (pct % 20 === 0) console.log(`  ${pct}%`);
    },
  });

  const {size} = fs.statSync(args.out);
  console.log(`Wrote ${args.out} (${(size / 1024 / 1024).toFixed(1)} MB)`);
};

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
