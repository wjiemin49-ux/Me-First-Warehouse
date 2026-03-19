# MiniMax Music Batch

Generate a small batch of short-video-friendly songs with MiniMax Music.

## Usage

In PowerShell:

```powershell
$env:MINIMAX_API_KEY='your-key'
python .\generate_trending_batch.py
```

Optional flags:

```powershell
python .\generate_trending_batch.py --count 3 --model music-2.5 --continue-on-error
```

Files are saved to `D:\me\音乐\AI音乐尝试存放处` by default:

- `*.mp3`
- `*.lyrics.txt`
- `*.json`
- `run_summary.json`

If `mutagen` is installed, the script also embeds the title and lyrics into MP3 metadata.
