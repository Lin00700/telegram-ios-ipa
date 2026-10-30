#!/usr/bin/env python3
"""Patch the pinned Telegram iOS checkout with a private, app-wide local wallpaper.

Selected Photos assets are stored only in Application Support. Static images and
small sampled GIF animations override chat wallpaper rendering for every chat.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def replace_exact(text: str, old: str, new: str, expected: int, label: str) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected} source occurrence(s), found {count}")
    return text.replace(old, new)


def write_once(path: Path, text: str) -> None:
    path.write_text(text)


def patch_picker(root: Path) -> None:
    path = root / "submodules/SettingsUI/Sources/Themes/CustomWallpaperPicker.swift"
    text = path.read_text()
    if "CUE_LOCAL_GLOBAL_WALLPAPER_V1" in text:
        return

    text = replace_exact(text, "import UIKit\n", "import UIKit\nimport Photos\nimport ImageIO\n", 1, "Photos/ImageIO imports")

    helper = r'''private let cueGlobalWallpaperPathKey = "CueGlobalWallpaperPath"

private func cueSaveGlobalWallpaperAsset(_ asset: PHAsset, completion: @escaping (Bool) -> Void) {
    let options = PHImageRequestOptions()
    options.version = .original
    options.deliveryMode = .highQualityFormat
    options.isNetworkAccessAllowed = true
    PHImageManager.default().requestImageDataAndOrientation(for: asset, options: options) { data, _, _, _ in
        guard let data, data.count <= 32 * 1024 * 1024,
              let source = CGImageSourceCreateWithData(data as CFData, nil),
              CGImageSourceGetCount(source) > 0 else {
            DispatchQueue.main.async {
                completion(false)
            }
            return
        }
        let frameCount = CGImageSourceGetCount(source)
        let fileName = frameCount > 1 ? "CueGlobalWallpaper.gif" : "CueGlobalWallpaper.image"
        let directory = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("Cue", isDirectory: true)
        do {
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true, attributes: nil)
            let url = directory.appendingPathComponent(fileName)
            try data.write(to: url, options: .atomic)
            DispatchQueue.main.async {
                UserDefaults.standard.set(url.path, forKey: cueGlobalWallpaperPathKey)
                NotificationCenter.default.post(name: Notification.Name("CueGlobalWallpaperChanged"), object: nil)
                completion(true)
            }
        } catch {
            DispatchQueue.main.async {
                completion(false)
            }
        }
    }
}

// CUE_LOCAL_GLOBAL_WALLPAPER_V1
'''
    text = replace_exact(text, "func presentCustomWallpaperPicker(", helper + "func presentCustomWallpaperPicker(", 1, "local asset saver insertion")

    old_selection = '''        controller.selectionBlock = { [weak legacyController] asset, _ in
            if let asset = asset {
                let controller = WallpaperGalleryController(context: context, source: .asset(asset.backingAsset))
                controller.apply = { [weak legacyController, weak controller] wallpaper, mode, editedImage, cropRect, brightness, _ in
                    if let legacyController = legacyController, let controller = controller {
                        uploadCustomWallpaper(context: context, wallpaper: wallpaper, mode: mode, editedImage: nil, cropRect: cropRect, brightness: brightness, completion: { [weak legacyController, weak controller] in
                            if let legacyController = legacyController, let controller = controller {
                                legacyController.dismiss()
                                controller.dismiss(forceAway: true)
                            }
                        })
                    }
                }
                push(controller)
            }
        }
'''
    new_selection = '''        controller.selectionBlock = { [weak legacyController, weak controller] asset, _ in
            guard let asset = asset else {
                return
            }
            cueSaveGlobalWallpaperAsset(asset.backingAsset) { saved in
                DispatchQueue.main.async { [weak legacyController, weak controller] in
                    guard let legacyController = legacyController, let controller = controller else {
                        return
                    }
                    if saved {
                        legacyController.dismiss()
                        controller.dismiss()
                    }
                }
            }
        }
'''
    text = replace_exact(text, old_selection, new_selection, 1, "local global wallpaper selection")
    write_once(path, text)


def patch_background_loader(root: Path) -> None:
    path = root / "submodules/TelegramPresentationData/Sources/ChatControllerBackgroundNode.swift"
    text = path.read_text()
    if "CUE_GLOBAL_WALLPAPER_IMAGE_LOADER_V1" in text:
        return
    text = replace_exact(text, "import UIKit\n", "import UIKit\nimport ImageIO\n", 1, "ImageIO import")
    helper = r'''private let cueGlobalWallpaperPathKey = "CueGlobalWallpaperPath"
public let cueGlobalWallpaperChangedNotification = Notification.Name("CueGlobalWallpaperChanged")

private enum CueGlobalWallpaperImageCache {
    static let lock = NSLock()
    static var cachedPath: String?
    static var cachedModificationDate: Date?
    static var cachedImage: UIImage?
}

private func decodeCueGlobalWallpaper(path: String) -> UIImage? {
    let url = URL(fileURLWithPath: path)
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil) else {
        return UIImage(contentsOfFile: path)
    }
    let sourceFrameCount = CGImageSourceGetCount(source)
    guard sourceFrameCount > 1 else {
        return UIImage(contentsOfFile: path)
    }

    let maximumFrames = 16
    let step = max(1, Int(ceil(Double(sourceFrameCount) / Double(maximumFrames))))
    let thumbnailOptions: CFDictionary = [
        kCGImageSourceCreateThumbnailFromImageAlways: true,
        kCGImageSourceThumbnailMaxPixelSize: 480,
        kCGImageSourceShouldCacheImmediately: true
    ] as CFDictionary
    var frames: [UIImage] = []
    var duration = 0.0
    var index = 0
    while index < sourceFrameCount && frames.count < maximumFrames {
        let cgImage = CGImageSourceCreateThumbnailAtIndex(source, index, thumbnailOptions)
            ?? CGImageSourceCreateImageAtIndex(source, index, nil)
        if let cgImage {
            frames.append(UIImage(cgImage: cgImage, scale: 1.0, orientation: .up))
            let properties = CGImageSourceCopyPropertiesAtIndex(source, index, nil) as? [CFString: Any]
            let gif = properties?[kCGImagePropertyGIFDictionary] as? [CFString: Any]
            let rawDelay = (gif?[kCGImagePropertyGIFUnclampedDelayTime] as? NSNumber)?.doubleValue
                ?? (gif?[kCGImagePropertyGIFDelayTime] as? NSNumber)?.doubleValue
                ?? 0.1
            duration += max(0.04, min(1.0, rawDelay)) * Double(step)
        }
        index += step
    }
    guard frames.count > 1 else {
        return UIImage(contentsOfFile: path)
    }
    return UIImage.animatedImage(with: frames, duration: max(0.8, min(6.0, duration)))
}

public func cueGlobalWallpaperImage() -> UIImage? {
    guard let path = UserDefaults.standard.string(forKey: cueGlobalWallpaperPathKey),
          FileManager.default.fileExists(atPath: path) else {
        return nil
    }
    let modificationDate = (try? FileManager.default.attributesOfItem(atPath: path)[.modificationDate]) as? Date
    CueGlobalWallpaperImageCache.lock.lock()
    if CueGlobalWallpaperImageCache.cachedPath == path,
       CueGlobalWallpaperImageCache.cachedModificationDate == modificationDate {
        let cached = CueGlobalWallpaperImageCache.cachedImage
        CueGlobalWallpaperImageCache.lock.unlock()
        return cached
    }
    CueGlobalWallpaperImageCache.lock.unlock()

    let image = decodeCueGlobalWallpaper(path: path)
    CueGlobalWallpaperImageCache.lock.lock()
    CueGlobalWallpaperImageCache.cachedPath = path
    CueGlobalWallpaperImageCache.cachedModificationDate = modificationDate
    CueGlobalWallpaperImageCache.cachedImage = image
    CueGlobalWallpaperImageCache.lock.unlock()
    return image
}

// CUE_GLOBAL_WALLPAPER_IMAGE_LOADER_V1
'''
    text = replace_exact(text, "private var backgroundImageForWallpaper:", helper + "private var backgroundImageForWallpaper:", 1, "global wallpaper image loader insertion")
    text = replace_exact(
        text,
        "    var backgroundImage: UIImage?\n    if cached && composed && wallpaper == backgroundImageForWallpaper?.0,",
        "    if let image = cueGlobalWallpaperImage() {\n        return image\n    }\n    var backgroundImage: UIImage?\n    if cached && composed && wallpaper == backgroundImageForWallpaper?.0,",
        1,
        "global wallpaper image rendering",
    )
    text = replace_exact(
        text,
        "public func chatControllerBackgroundImageSignal(wallpaper: TelegramWallpaper, mediaBox: MediaBox, accountMediaBox: MediaBox) -> Signal<(UIImage?, Bool)?, NoError> {\n    if wallpaper == signalBackgroundImageForWallpaper?.0,",
        "public func chatControllerBackgroundImageSignal(wallpaper: TelegramWallpaper, mediaBox: MediaBox, accountMediaBox: MediaBox) -> Signal<(UIImage?, Bool)?, NoError> {\n    if let image = cueGlobalWallpaperImage() {\n        return .single((image, true))\n    }\n    if wallpaper == signalBackgroundImageForWallpaper?.0,",
        1,
        "global wallpaper image signal",
    )
    write_once(path, text)


def patch_wallpaper_node(root: Path) -> None:
    path = root / "submodules/WallpaperBackgroundNode/Sources/WallpaperBackgroundNode.swift"
    text = path.read_text()
    if "CUE_GLOBAL_WALLPAPER_NODE_V1" in text:
        return

    text = replace_exact(
        text,
        "    let contentNode: ASDisplayNode\n",
        "    let contentNode: ASDisplayNode\n    private let cueGlobalWallpaperNode: ASDisplayNode\n",
        1,
        "global wallpaper image view property",
    )
    text = replace_exact(
        text,
        "    private var wallpaper: TelegramWallpaper?\n",
        "    private var wallpaper: TelegramWallpaper?\n\n    public override var frame: CGRect {\n        didSet {\n            if oldValue.size != self.bounds.size {\n                self.contentNode.frame = self.bounds\n                self.cueGlobalWallpaperNode.frame = self.bounds\n            }\n        }\n    }\n",
        1,
        "background view frame update",
    )
    text = replace_exact(
        text,
        "        self.contentNode = ASDisplayNode()\n        self.contentNode.contentMode = self.imageContentMode\n",
        "        self.cueGlobalWallpaperNode = ASDisplayNode(viewBlock: {\n            let imageView = UIImageView()\n            imageView.contentMode = .scaleAspectFit\n            imageView.clipsToBounds = true\n            imageView.isUserInteractionEnabled = false\n            return imageView\n        }, didLoad: nil)\n        self.cueGlobalWallpaperNode.isUserInteractionEnabled = false\n        self.cueGlobalWallpaperNode.isHidden = true\n\n        self.contentNode = ASDisplayNode()\n        self.contentNode.contentMode = self.imageContentMode\n",
        1,
        "animated image view construction",
    )
    text = replace_exact(
        text,
        "        self.dimLayer.backgroundColor = UIColor.black.cgColor\n        \n        super.init()\n        \n        if #available(iOS 12.0, *) {",
        "        self.dimLayer.backgroundColor = UIColor.black.cgColor\n        \n        super.init()\n        \n        NotificationCenter.default.addObserver(self, selector: #selector(cueGlobalWallpaperDidChange), name: cueGlobalWallpaperChangedNotification, object: nil)\n\n        if #available(iOS 12.0, *) {",
        1,
        "global wallpaper change observer",
    )
    text = replace_exact(
        text,
        "        self.clipsToBounds = true\n        self.contentNode.frame = self.bounds\n        self.addSubnode(self.contentNode)\n",
        "        self.clipsToBounds = true\n        self.cueGlobalWallpaperNode.frame = self.bounds\n        self.addSubnode(self.cueGlobalWallpaperNode)\n        self.contentNode.frame = self.bounds\n        self.addSubnode(self.contentNode)\n",
        1,
        "global wallpaper subnode insertion",
    )
    text = replace_exact(
        text,
        "    deinit {\n        self.patternImageDisposable.dispose()\n        self.wallpaperDisposable.dispose()\n        self.imageDisposable.dispose()\n    }\n    \n    private func updateDimming() {",
        "    deinit {\n        NotificationCenter.default.removeObserver(self)\n        self.patternImageDisposable.dispose()\n        self.wallpaperDisposable.dispose()\n        self.imageDisposable.dispose()\n    }\n\n    @objc private func cueGlobalWallpaperDidChange() {\n        guard let wallpaper = self.wallpaper else {\n            return\n        }\n        let starGift = self.starGift\n        self.wallpaper = nil\n        self.update(wallpaper: wallpaper, starGift: starGift, animated: false)\n    }\n    \n    private func updateDimming() {",
        1,
        "global wallpaper observer lifecycle",
    )
    text = replace_exact(
        text,
        "        if theme.overallDarkAppearance == true {\n            var intensity: Int32?\n",
        "        if theme.overallDarkAppearance == true {\n            if cueGlobalWallpaperImage() != nil {\n                dimAlpha = 0.46\n            }\n            var intensity: Int32?\n",
        1,
        "dark global wallpaper dimming",
    )
    text = replace_exact(
        text,
        "        let wallpaperDimColor: UIColor? = nil\n\n        if case let .color(color) = wallpaper {",
        "        let wallpaperDimColor: UIColor? = nil\n        let cueGlobalImage = cueGlobalWallpaperImage()\n\n        if case let .color(color) = wallpaper {",
        1,
        "global image selection state",
    )
    text = replace_exact(
        text,
        "        let cueGlobalImage = cueGlobalWallpaperImage()\n\n        if case let .color(color) = wallpaper {",
        "        let cueGlobalImage = cueGlobalWallpaperImage()\n        self.cueGlobalWallpaperNode.isHidden = true\n        if let imageView = self.cueGlobalWallpaperNode.view as? UIImageView {\n            imageView.stopAnimating()\n            imageView.image = nil\n        }\n\n        if case let .color(color) = wallpaper {",
        1,
        "reset stale GIF animation before wallpaper rendering",
    )
    text = replace_exact(
        text,
        "        } else if case let .file(file) = wallpaper, file.isPattern {\n            gradientColors = file.settings.colors\n            gradientAngle = file.settings.rotation ?? 0\n        }\n        \n        var scheduleLoopingEvent = false\n",
        "        } else if case let .file(file) = wallpaper, file.isPattern {\n            gradientColors = file.settings.colors\n            gradientAngle = file.settings.rotation ?? 0\n        }\n        if cueGlobalImage != nil {\n            gradientColors = []\n            gradientAngle = 0\n        }\n        \n        var scheduleLoopingEvent = false\n",
        1,
        "global image overrides gradient wallpapers",
    )
    text = replace_exact(
        text,
        "            self.motionEnabled = wallpaper.settings?.motion ?? false\n",
        "            self.motionEnabled = cueGlobalImage == nil ? (wallpaper.settings?.motion ?? false) : false\n",
        1,
        "global image disables parallax motion",
    )

    original_background_branch = '''            } else {
                self.contentNode.backgroundColor = .white
                if let image = chatControllerBackgroundImage(theme: nil, wallpaper: wallpaper, mediaBox: self.context.sharedContext.accountManager.mediaBox, knockoutMode: false) {
'''
    custom_background_branch = '''            } else {
                if let globalImage = cueGlobalImage {
                    self.contentNode.backgroundColor = .clear
                    self.contentNode.contentMode = .scaleAspectFit
                    if globalImage.images != nil {
                        self.contentNode.contents = nil
                        if let imageView = self.cueGlobalWallpaperNode.view as? UIImageView {
                            imageView.image = globalImage
                            imageView.startAnimating()
                        }
                        self.cueGlobalWallpaperNode.isHidden = false
                    } else {
                        self.cueGlobalWallpaperNode.isHidden = true
                        if let imageView = self.cueGlobalWallpaperNode.view as? UIImageView {
                            imageView.stopAnimating()
                            imageView.image = nil
                        }
                        self.contentNode.contents = globalImage.cgImage
                    }
                    self.blurredBackgroundContents = generateBlurredContents(image: globalImage, dimColor: wallpaperDimColor)
                    self.wallpaperDisposable.set(nil)
                    self.updateContentStats(WallpaperContentStats(isDark: calculateWallpaperBrightness(from: globalImage) <= 0.55, isSaturated: calculateWallpaperSaturation(from: globalImage) > 0.35))
                    Queue.mainQueue().justDispatch {
                        self._isReady.set(true)
                    }
                } else {
                    self.contentNode.contentMode = self.imageContentMode
                    self.cueGlobalWallpaperNode.isHidden = true
                    if let imageView = self.cueGlobalWallpaperNode.view as? UIImageView {
                        imageView.stopAnimating()
                        imageView.image = nil
                    }
                    self.contentNode.backgroundColor = .white
                    if let image = chatControllerBackgroundImage(theme: nil, wallpaper: wallpaper, mediaBox: self.context.sharedContext.accountManager.mediaBox, knockoutMode: false) {
'''
    text = replace_exact(text, original_background_branch, custom_background_branch, 1, "global image and GIF display")
    text = replace_exact(
        text,
        "                self.contentNode.isHidden = false\n            }\n        }\n",
        "                self.contentNode.isHidden = false\n                }\n            }\n        }\n",
        1,
        "global background branch closure",
    )
    text = text.replace("// CUE_GLOBAL_WALLPAPER_NODE_V1", "")
    text = text.replace(
        "public final class WallpaperBackgroundNodeImpl: ASDisplayNode, WallpaperBackgroundNode {",
        "// CUE_GLOBAL_WALLPAPER_NODE_V1: app-wide local image/GIF wallpapers use aspect-fit rendering.\npublic final class WallpaperBackgroundNodeImpl: ASDisplayNode, WallpaperBackgroundNode {",
        1,
    )
    write_once(path, text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", required=True, type=Path)
    args = parser.parse_args()
    root = args.upstream
    if not (root / ".gitmodules").exists():
        raise SystemExit(f"not a Telegram iOS checkout: {root}")
    patch_picker(root)
    patch_background_loader(root)
    patch_wallpaper_node(root)
    print("Applied app-wide local photo/GIF wallpaper support; selected assets remain on device.")


if __name__ == "__main__":
    main()
