# Youtube Converter

Convert yt videos to audio or video again easily!

## Updates

- The app reads version.txt to determine its version.
- Built-in updater can pull:
  - Nightly (tag: nightly)
  - Prerelease (drafts)
  - Release (latest stable)
- Configure channel in settings (release | prerelease | nightly).

## CI/CD

- Nightly build on every push to main (pre-release with stable nightly tag).
- Draft release generated automatically with categorized changes (Release Drafter).
- Optional: auto-tag on published release.

#### FAQ

- The app seems like it hasn't been updated in a while, will it still work?
  - The app should work 90%, unless ytdlp or ffmpeg changes significantly it will fetch from the repo itself and auto update! So it should still work nonetheless.
- Help! The app has a bug!
  - Report it! Go to the issues tab

...more to come
