import {Config} from '@remotion/cli/config';

// 1080p long-form by default; the composition also accepts vertical shorts
// (1080x1920) through input props.
Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setCodec('h264');
Config.setCrf(18);
