$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force -Path bin | Out-Null
$version = '2026.08.19'
$release = "https://github.com/yt-dlp/yt-dlp/releases/download/$version"
Invoke-WebRequest "$release/yt-dlp.exe" -OutFile bin/yt-dlp.exe
$checksums = (Invoke-WebRequest "$release/SHA2-256SUMS").Content
$expected = (($checksums -split "`n" | Where-Object { $_ -match '\s+yt-dlp\.exe\s*$' }) -split '\s+')[0]
if (-not $expected -or (Get-FileHash bin/yt-dlp.exe -Algorithm SHA256).Hash.ToLower() -ne $expected.ToLower()) { throw 'yt-dlp checksum mismatch' }
$ffmpeg = python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"
Copy-Item -LiteralPath $ffmpeg -Destination bin/ffmpeg.exe
Copy-Item -LiteralPath (Get-Command node).Source -Destination bin/node.exe
New-Item -ItemType Directory -Force -Path licenses | Out-Null
Invoke-WebRequest 'https://raw.githubusercontent.com/yt-dlp/yt-dlp/2026.08.19/LICENSE' -OutFile licenses/yt-dlp.txt
Invoke-WebRequest 'https://raw.githubusercontent.com/nodejs/node/v22.x/LICENSE' -OutFile licenses/node.txt
Invoke-WebRequest 'https://raw.githubusercontent.com/imageio/imageio-ffmpeg/v0.6.0/LICENSE' -OutFile licenses/imageio-ffmpeg.txt
Invoke-WebRequest 'https://raw.githubusercontent.com/FFmpeg/FFmpeg/master/COPYING.GPLv3' -OutFile licenses/ffmpeg-gplv3.txt
python -m PyInstaller --noconfirm --clean --windowed --onedir --name YouTubeExtractor --add-binary 'bin/yt-dlp.exe;bin' --add-binary 'bin/ffmpeg.exe;bin' --add-binary 'bin/node.exe;bin' --add-data 'licenses;licenses' desktop.py
if ($LASTEXITCODE -ne 0) { throw 'Windows build failed' }
$test = Start-Process -FilePath dist/YouTubeExtractor/YouTubeExtractor.exe -ArgumentList '--self-test' -PassThru -Wait -WindowStyle Hidden
if ($test.ExitCode -ne 0) { throw 'Packaged app self-test failed' }
Copy-Item ../README.md dist/YouTubeExtractor/README.md
Copy-Item ../THIRD_PARTY.md dist/YouTubeExtractor/THIRD_PARTY.md
Compress-Archive -Path dist/YouTubeExtractor -DestinationPath YouTubeExtractor-Windows.zip -Force
