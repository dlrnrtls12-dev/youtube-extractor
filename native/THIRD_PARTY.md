# Dependencies and source

- yt-dlp: https://github.com/yt-dlp/yt-dlp (Unlicense; bundled executable dependencies have their own licenses)
- Android yt-dlp wrapper and embedded Python/QuickJS/FFmpeg: https://github.com/yausername/youtubedl-android (MIT wrapper; see upstream build scripts and individual dependency licenses)
- FFmpeg: https://ffmpeg.org — Windows executable provided by imageio-ffmpeg 0.6.0. This build may be GPL; corresponding source/build provenance: https://github.com/imageio/imageio-ffmpeg/tree/v0.6.0 and https://github.com/BtbN/FFmpeg-Builds
- imageio-ffmpeg: https://github.com/imageio/imageio-ffmpeg (BSD-2-Clause)
- Node.js 22: https://github.com/nodejs/node/tree/v22.x (MIT and bundled dependency licenses)
- Python: https://www.python.org (PSF License)
- PyInstaller: https://pyinstaller.org (GPL with bootloader exception)
- Kotlin: https://github.com/JetBrains/kotlin (Apache-2.0)

The app does not call a hosted AI or extraction API. Engine updates access the yt-dlp official GitHub release.
