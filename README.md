# Video Downloader

A simple command-line application for downloading videos and playlists from websites supported by [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Features

- Download videos and playlists.
- Choose the preferred video format.
- Configure the download directory.
- Automatically retry failed downloads.
- View and clear download history.
- Save application settings between sessions.
- Use FFmpeg bundled with the Windows release.
- Use system-installed FFmpeg on Linux.

## Installation

### Windows

1. Extract the entire archive to a folder of your choice.
2. Run the provided installer or launcher, if included in the release.
3. Follow the on-screen instructions.

**Important:** Keep the `ffmpeg` directory alongside the application files. It contains the FFmpeg executable required by the Windows release.

Do not extract or move individual application files separately.

### Linux

1. Install Python 3 and FFmpeg using your distribution's package manager.
2. Open a terminal in the extracted directory.
3. Run the provided Linux installer or launcher, if included in the release.

For Debian and Ubuntu:

```bash
sudo apt update
sudo apt install python3 ffmpeg
```

If the release includes an installation script, follow the instructions provided with that release.

## Usage

1. Start the application.
2. Enter the video or playlist URL when prompted.
3. Select the desired options.
4. Wait for the download to finish.
5. Find the downloaded files in the configured download directory.

The application uses an interactive terminal menu to manage downloads and settings.

## Settings

The application allows you to configure:

| Setting            | Description                                   |
| ------------------ | --------------------------------------------- |
| Download directory | Location where downloaded files are saved.    |
| Format preference  | Preferred video and audio quality.            |
| Retry attempts     | Number of retries after a failed download.    |
| Fragment retries   | Number of retries for failed media fragments. |
| Socket timeout     | Maximum wait time for network operations.     |
| Overwrite files    | Whether existing files can be overwritten.    |
| Progress display   | Whether download progress is displayed.       |

Settings are saved locally and reused when you start the application again.

## Download History

The application stores download history locally. You can view previous entries or clear the history through the application menu.

## Troubleshooting

### Downloads fail

- Check your internet connection.
- Make sure the URL is valid.
- Update the application if a newer release is available.
- Try again later if the website is temporarily unavailable.

### FFmpeg is missing

**Windows:** Make sure the `ffmpeg` directory and its contents remain in the extracted application folder.

**Linux:** Install FFmpeg using your distribution's package manager and verify that it is available in your terminal.

### Python or dependency errors

If the application reports a missing dependency or a Python error, follow the installation instructions included with your release. Avoid deleting application files to resolve dependency problems.

### Downloads are slow or unavailable

Some websites impose temporary restrictions, rate limits, or other download limitations. Repeated requests may result in temporary access restrictions. Follow the website's terms and applicable laws.

## VPN and Privacy

A VPN may improve privacy on public networks, but it does not guarantee anonymity or prevent a website from restricting downloads.

Use the application responsibly and respect copyright, website terms, and applicable laws.

## Application Data

The application stores its configuration and download history in:

```text
~/.video_downloader/
```

On Windows, `~` refers to your user profile directory. On Linux, it refers to your home directory.

## Third-Party Software

This application uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) to handle supported downloads.

The Windows release includes FFmpeg. Linux users should install FFmpeg separately.

Third-party components are subject to their respective licenses.

## License

This project is distributed under the MIT License. See [LICENCE](LICENCE) for details.
