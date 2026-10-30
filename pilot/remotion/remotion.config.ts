import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('png'); // lossless frames into the encoder (text edges stay clean)
Config.setPixelFormat('yuv420p');
Config.setCodec('h264');
Config.setCrf(16);
