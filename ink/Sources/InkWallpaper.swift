import Foundation
import PhotosUI
import UIKit
import UniformTypeIdentifiers

public enum InkWallpaperStore {
    public static let globalPathKey = "CueGlobalWallpaperPath"
    public static let changed = Notification.Name("CueGlobalWallpaperChanged")

    public static func save(data: Data, scope: String, peerId: Int64) -> Bool {
        guard data.count > 32, data.count <= 32 * 1024 * 1024 else {
            return false
        }
        let directory = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("Cue", isDirectory: true)
        do {
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            let gif = data.starts(with: Data([0x47, 0x49, 0x46]))
            let name: String
            if scope == "chat" {
                name = gif ? "chat-\(peerId).gif" : "chat-\(peerId).image"
            } else {
                name = gif ? "CueGlobalWallpaper.gif" : "CueGlobalWallpaper.image"
            }
            let url = directory.appendingPathComponent(name)
            try data.write(to: url, options: .atomic)
            if scope == "chat" {
                UserDefaults.standard.set(url.path, forKey: "ink.wallpaper.chat.\(peerId)")
                UserDefaults.standard.set(true, forKey: InkPreferences.chatWallpaperKey)
            } else {
                UserDefaults.standard.set(url.path, forKey: globalPathKey)
                UserDefaults.standard.set(true, forKey: InkPreferences.globalWallpaperKey)
            }
            NotificationCenter.default.post(name: changed, object: nil)
            return true
        } catch {
            return false
        }
    }
}

public final class InkWallpaperPicker: NSObject, PHPickerViewControllerDelegate {
    public static let shared = InkWallpaperPicker()
    private var scope = "global"
    private var peerId: Int64 = 0

    public func present(from controller: UIViewController, scope: String, peerId: Int64) {
        self.scope = scope
        self.peerId = peerId
        var configuration = PHPickerConfiguration()
        configuration.filter = .images
        configuration.selectionLimit = 1
        configuration.preferredAssetRepresentationMode = .current
        let picker = PHPickerViewController(configuration: configuration)
        picker.delegate = self
        controller.present(picker, animated: true)
    }

    public func picker(_ picker: PHPickerViewController, didFinishPicking results: [PHPickerResult]) {
        picker.dismiss(animated: true)
        guard let provider = results.first?.itemProvider else {
            return
        }
        let identifier = provider.hasItemConformingToTypeIdentifier(UTType.gif.identifier) ? UTType.gif.identifier : UTType.image.identifier
        let scope = self.scope
        let peerId = self.peerId
        provider.loadDataRepresentation(forTypeIdentifier: identifier) { data, _ in
            guard let data else {
                return
            }
            _ = InkWallpaperStore.save(data: data, scope: scope, peerId: peerId)
        }
    }
}
