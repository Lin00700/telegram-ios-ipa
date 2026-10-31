# Unofficial iOS Chat — build scaffold

This repository is a scaffold for an **unofficial** iOS messaging client based on the official [TelegramMessenger/Telegram-iOS](https://github.com/TelegramMessenger/Telegram-iOS) source. It does not contain a copy of Telegram's source tree; the Actions workflow fetches upstream at a recorded ref and includes its submodules.

The app must not be presented as the official Telegram app and must not use Telegram's standard paper-plane logo. The build scaffold replaces the default app icon with an original warm-ivory / brick-red chat mark and uses the display name `Unofficial Chat` by default. See [`docs/VISUAL_STYLE.md`](docs/VISUAL_STYLE.md).

## Current state

Applied to the pinned upstream checkout at build time (each patch is exact-match guarded and fails the build if upstream drifts):

- **Global ink-wash UI** — extends the paper / ink / cinnabar / muted-jade palette across shared light and dark themes, including navigation, lists, chat bubbles, input panels and menus. Settings now have Chinese section headings, spaced paper-card groups, ink glyphs with cinnabar seals; the root tab bar uses a paper capsule and a distinct seal-like selected state. The chat list distinguishes warm-paper rows from its background. The default bundled chat wallpaper remains local to the client (`scripts/apply_inkwash_theme.py`, `scripts/apply_inkwash_components.py`).
- **Global photo/GIF wallpaper** — reachable from a chat's automation menu, picked from Photos and stored only in Application Support; aspect-fit (no stretching), dimmed in dark mode, and GIFs sampled to at most 16 frames (`runtime/CueGlobalWallpaperPicker.swift`, `scripts/apply_global_wallpaper.py`).
- **Purchase-entry hiding** — Premium, Business, Stars, gifts, subscription prompts, wallet rows and StoreKit contexts are hidden locally. Server-side entitlements are not touched and nothing is unlocked.
- **Per-chat local translation** — off by default, enabled per conversation, only for messages received after enabling; original text is kept and Simplified Chinese is shown below it. Uses on-device ML Kit plus bundled OpenCC `t2s`; no chat text is uploaded and Telegram Premium is not required. Minimum iOS is 15.5.
- **AI providers and per-chat auto-reply** — the provider manager is exposed from the main Settings page and the chat automation menu. Choose OpenAI, native Anthropic Claude Messages, native Google Gemini `generateContent`, or a custom OpenAI-compatible HTTPS service. Each provider has an editable endpoint, model ID and API key; keys stay in the device Keychain (`ThisDeviceOnly`). Add providers first, then assign them per chat and explicitly enable auto-reply; translation remains separate and OFF by default. Replies go through Telegram's normal send path and respect send permission. Bots and Secret Chats are blocked; broadcast-channel posting requires native Telegram posting permission and a separate explicit consent.

Verification: `python3 -m unittest discover -s tests -v` runs in the workflow preflight (34 static/package tests pass). New UI overlays were also exercised against copies of the pinned upstream sources and checked for idempotence. This does not replace an Xcode build or real-device visual/interaction verification; both remain pending for this redesign branch.

Known gaps: the CF Assistant reference screenshot was not available in this build session, so the implementation follows the documented palette rather than a pixel-perfect copy; APIs with proprietary formats beyond OpenAI Chat Completions, Anthropic Messages and Gemini `generateContent` need their own adapter; broadcast-channel replies require native Telegram posting permission and a separate explicit public-posting consent; full UI and privacy behavior still need real-device testing.

## Build an unsigned device IPA

The workflow is manually triggered from **Actions → Build unsigned IPA → Run workflow**. It checks out the official source recursively, selects the Xcode version declared by upstream `versions.json`, creates the configuration file only in the runner's temporary directory, and builds `release_arm64` with provisioning profiles and code signing disabled. The packaging script then strips/validates remaining signatures or profiles and uploads an `.ipa` artifact. No Apple signing certificate or provisioning profile is imported or stored. The unsigned build runs on the `xcode-27` runner and takes roughly an hour. Sign the resulting IPA with your own identity before installing.

Before a real build, add these GitHub Actions **repository secrets** (not repository files):

- `TG_API_ID` — the app's own Telegram API ID.
- `TG_API_HASH` — the matching API hash; treat it as sensitive.

Telegram's official instructions say to obtain these at [my.telegram.org → API development tools](https://core.telegram.org/api/obtaining_api_id). The API hash is compiled into the client binary as required by the upstream build, so a GitHub Secret protects it from source-control/log exposure but cannot make it secret from someone who receives and inspects the app.

The workflow inputs `app_display_name` and `app_bundle_id` set the non-official app identity. Use a unique reverse-DNS bundle ID that you control before signing.

## AI assistant

The design supports multiple named assistant/provider profiles, assigning one or more profiles to selected chats, and managing each chat's automation. **Selecting a chat does not enable automation.** Every chat/thread starts OFF and requires its own explicit consent before any message text is sent to a provider. There is no global "enable all chats" switch. Group controls are permission-aware; secret chats are excluded. Provider credentials are entered at runtime and stored in the iOS Keychain, never in source code or GitHub. See [`docs/AI_AUTOREPLY.md`](docs/AI_AUTOREPLY.md).

## Source/license and upstream notes

The upstream Telegram iOS README asks each developer to use their own API ID, avoid presenting the app as official or using Telegram's standard logo, follow Telegram's security guidance, and publish their code to comply with the applicable GNU GPL licenses. This repository is public, which helps with source availability, but it only holds the overlay: the patched upstream source is produced on the runner. If you distribute a built IPA, also make the corresponding patched source available and review the GPL terms yourself.

The default workflow ref is pinned to upstream commit `fb0e62ba8a147f0821da6aa63c09da7d79a10111` for traceability. See [`UPSTREAM.md`](UPSTREAM.md).
