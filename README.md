# Unofficial iOS Chat — build scaffold

This private repository is a scaffold for an **unofficial** iOS messaging client based on the official [TelegramMessenger/Telegram-iOS](https://github.com/TelegramMessenger/Telegram-iOS) source. It does not contain a copy of Telegram's source tree; the Actions workflow fetches upstream at a recorded ref and includes its submodules.

The app must not be presented as the official Telegram app and must not use Telegram's standard paper-plane logo. The build scaffold replaces the default app icon with an original warm-ivory / brick-red chat mark and uses the display name `Unofficial Chat` by default. The visual direction is inspired by the supplied CF 助手 screenshot: warm neutral surfaces, restrained red accents, rounded cards and clear dark typography, while retaining Telegram's existing messaging UI and behavior. See [`docs/VISUAL_STYLE.md`](docs/VISUAL_STYLE.md).

## Current state

The repository contains the active Actions workflow, original icon asset, build/package scripts and an AI-auto-reply safety/design specification. **The runtime UI restyling and AI provider/chat-management code have not yet been merged into Telegram's source or build-verified.** No messages are sent to any AI service by this scaffold. The AI behavior and its required fail-closed consent rules are described in [`docs/AI_AUTOREPLY.md`](docs/AI_AUTOREPLY.md).

## Build an unsigned device IPA

The workflow is manually triggered from **Actions → Build unsigned IPA → Run workflow**. It checks out the official source recursively, selects the Xcode version declared by upstream `versions.json`, creates the configuration file only in the runner's temporary directory, and builds `release_arm64`. The runner-local patch exposes `--disableProvisioningProfiles` in `Make.py`, forwards the rules_apple feature `disable_legacy_signing`, and makes six iOS app/extension profile-embedding branches honor that feature. The pinned rules_apple fork otherwise rejects device bundles without profiles even when Telegram's no-profile flag is set. These narrow patches affect only the temporary checkout; normal signed builds retain their profile checks. The packaging script then strips/validates remaining signatures or profiles and uploads an `.ipa` artifact. No Apple signing certificate or provisioning profile is imported or stored.

Before a real build, add these GitHub Actions **repository secrets** (not repository files):

- `TG_API_ID` — the app's own Telegram API ID.
- `TG_API_HASH` — the matching API hash; treat it as sensitive.

Telegram's official instructions say to obtain these at [my.telegram.org → API development tools](https://core.telegram.org/api/obtaining_api_id). The API hash is compiled into the client binary as required by the upstream build, so a GitHub Secret protects it from source-control/log exposure but cannot make it secret from someone who receives and inspects the app.

The workflow inputs `app_display_name` and `app_bundle_id` are for the non-official app identity. Use a unique reverse-DNS bundle ID that you control before signing. The default `com.lin00700.unofficialchat` is a suggested personal identifier; replace it if you do not control or want to use that identifier.

The first GitHub-hosted macOS run passed credential preflight, recursive source checkout and Xcode selection, then failed during Bazel analysis because `IntentsExtension` still required a provisioning profile. The revised unsigned patch passes local pinned-source syntax/idempotence checks but still needs a successful macOS build. There is no verified IPA yet. Any resulting unsigned IPA cannot be installed until signed by the user.

## AI assistant configuration needed

The design supports multiple named assistant/provider profiles, assigning one or more profiles to one or more selected chats, and opening a chosen chat to manage its automation. **Selecting a chat does not enable automation.** Every chat/thread starts OFF and requires its own explicit consent before any message text is sent to the selected provider(s). There is no global “enable all chats” switch. Group and channel controls are permission-aware; read-only channels cannot be made to auto-post, and secret chats are excluded by default.

To implement and test the runtime AI feature, collect through a secure form:

1. For each assistant: display name, provider type, endpoint/base URL if applicable, model ID, and its API key/token (secret field). For a user-owned endpoint, provide the URL and authentication method instead of a third-party key.
2. Which chats or groups may be assigned; whether group replies should trigger only on a mention/reply (recommended), and whether generated replies may be sent automatically or should first be shown as drafts.
3. The context policy (for example, latest incoming text only versus a small recent-message window). Media/attachments remain excluded unless separately approved.

Provider credentials are intended for runtime entry and iOS Keychain storage, never source code or GitHub. The app must show the provider and data-sharing notice before recording per-chat consent; revoking consent or turning a chat OFF prevents future requests.

## Source/license and upstream notes

The official Telegram iOS README requires each developer to use their own API ID, avoid presenting the app as official or using Telegram's standard logo, follow Telegram's security guidance, and publish their code to comply with the applicable GNU GPL licenses. This repository is private at the user's request. **That privacy choice may not satisfy the upstream source-code publication requirement if the derived client is distributed.** Do not distribute a derived build until the source-publication/license implications have been reviewed and resolved.

The default workflow ref is pinned to upstream commit `fb0e62ba8a147f0821da6aa63c09da7d79a10111` for traceability. Upstream build and licensing documentation: [README](https://github.com/TelegramMessenger/Telegram-iOS/blob/master/README.md), [versions.json](https://github.com/TelegramMessenger/Telegram-iOS/blob/master/versions.json), [API ID instructions](https://core.telegram.org/api/obtaining_api_id).
