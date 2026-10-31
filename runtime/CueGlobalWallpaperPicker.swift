import Foundation
import ImageIO
import PhotosUI
import UniformTypeIdentifiers
import UIKit

public enum CueGlobalWallpaperSettingsUI {
    private static let storageQueue = DispatchQueue(label: "CueGlobalWallpaper.storage", qos: .utility)
    private static var coordinators: [UUID: WallpaperPickerCoordinator] = [:]
    private static let pathKey = "CueGlobalWallpaperPath"
    private static let changed = Notification.Name("CueGlobalWallpaperChanged")
    private static let maximumFileSize = 32 * 1024 * 1024

    public static func present(from viewController: UIViewController) {
        let presentPicker = {
            let coordinator = WallpaperPickerCoordinator()
            coordinators[coordinator.id] = coordinator
            coordinator.present(from: viewController)
        }
        if Thread.isMainThread {
            presentPicker()
        } else {
            DispatchQueue.main.async(execute: presentPicker)
        }
    }

    public static func clearCurrentWallpaper() {
        storageQueue.sync {
            UserDefaults.standard.removeObject(forKey: pathKey)
            if let directory = cueDirectory(create: false) {
                for name in ["CueGlobalWallpaper.gif", "CueGlobalWallpaper.image"] {
                    try? FileManager.default.removeItem(at: directory.appendingPathComponent(name))
                }
            }
            postChangedNotification()
        }
    }

    fileprivate static func finish(_ coordinator: WallpaperPickerCoordinator) {
        coordinators.removeValue(forKey: coordinator.id)
    }

    fileprivate static func loadAndSave(_ provider: NSItemProvider, completion: @escaping (Result<Void, Error>) -> Void) {
        loadImageData(from: provider) { result in
            switch result {
            case let .success((data, frameCount)):
                storageQueue.async {
                    do {
                        guard let directory = cueDirectory(create: true) else {
                            throw WallpaperError.storageUnavailable
                        }
                        let fileName = frameCount > 1 ? "CueGlobalWallpaper.gif" : "CueGlobalWallpaper.image"
                        let otherName = frameCount > 1 ? "CueGlobalWallpaper.image" : "CueGlobalWallpaper.gif"
                        let destination = directory.appendingPathComponent(fileName)
                        try data.write(to: destination, options: .atomic)
                        var values = URLResourceValues()
                        values.isExcludedFromBackup = true
                        try? destination.setResourceValues(values)
                        let obsolete = directory.appendingPathComponent(otherName)
                        if FileManager.default.fileExists(atPath: obsolete.path) {
                            try FileManager.default.removeItem(at: obsolete)
                        }
                        UserDefaults.standard.set(destination.path, forKey: pathKey)
                        postChangedNotification()
                        DispatchQueue.main.async { completion(.success(())) }
                    } catch {
                        DispatchQueue.main.async { completion(.failure(error)) }
                    }
                }
            case let .failure(error):
                DispatchQueue.main.async { completion(.failure(error)) }
            }
        }
    }

    private static func loadImageData(from provider: NSItemProvider, completion: @escaping (Result<(Data, Int), Error>) -> Void) {
        func tryRepresentation(_ typeIdentifier: String, fallback: (() -> Void)?) {
            provider.loadDataRepresentation(forTypeIdentifier: typeIdentifier) { data, error in
                guard let data, let frameCount = validatedFrameCount(in: data) else {
                    if let fallback {
                        fallback()
                    } else {
                        completion(.failure(error ?? WallpaperError.invalidImage))
                    }
                    return
                }
                completion(.success((data, frameCount)))
            }
        }
        tryRepresentation(UTType.gif.identifier) {
            tryRepresentation(UTType.image.identifier, fallback: nil)
        }
    }

    private static func validatedFrameCount(in data: Data) -> Int? {
        guard data.count <= maximumFileSize,
              let source = CGImageSourceCreateWithData(data as CFData, nil) else { return nil }
        let count = CGImageSourceGetCount(source)
        guard count > 0 else { return nil }
        for index in 0..<count {
            guard CGImageSourceCreateImageAtIndex(source, index, nil) != nil else { return nil }
        }
        return count
    }

    private static func cueDirectory(create: Bool) -> URL? {
        guard let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first else { return nil }
        let directory = support.appendingPathComponent("Cue", isDirectory: true)
        if create {
            do {
                try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
                var values = URLResourceValues()
                values.isExcludedFromBackup = true
                try? directory.setResourceValues(values)
            } catch {
                return nil
            }
        }
        return directory
    }

    private static func postChangedNotification() {
        DispatchQueue.main.async {
            NotificationCenter.default.post(name: changed, object: nil)
        }
    }

    private enum WallpaperError: LocalizedError {
        case invalidImage
        case storageUnavailable

        var errorDescription: String? {
            switch self {
            case .invalidImage:
                return "所选文件不是可解码的图片，或文件超过 32 MiB。请另选一张图片。"
            case .storageUnavailable:
                return "无法访问应用本地存储空间。请稍后重试。"
            }
        }
    }
}

private final class WallpaperPickerCoordinator: NSObject, PHPickerViewControllerDelegate {
    let id = UUID()
    private weak var presenter: UIViewController?

    func present(from viewController: UIViewController) {
        dispatchPrecondition(condition: .onQueue(.main))
        presenter = viewController
        var configuration = PHPickerConfiguration(photoLibrary: .shared())
        configuration.filter = .images
        configuration.selectionLimit = 1
        configuration.preferredAssetRepresentationMode = .current
        let picker = PHPickerViewController(configuration: configuration)
        picker.delegate = self
        viewController.present(picker, animated: true)
    }

    func picker(_ picker: PHPickerViewController, didFinishPicking results: [PHPickerResult]) {
        guard let result = results.first else {
            picker.dismiss(animated: true) {
                CueGlobalWallpaperSettingsUI.finish(self)
            }
            return
        }
        picker.dismiss(animated: true) {
            CueGlobalWallpaperSettingsUI.loadAndSave(result.itemProvider) { [weak self] outcome in
                guard let self else { return }
                CueGlobalWallpaperSettingsUI.finish(self)
                if case let .failure(error) = outcome {
                    self.showFailure(error.localizedDescription)
                }
            }
        }
    }

    private func showFailure(_ message: String) {
        guard let presenter, presenter.viewIfLoaded?.window != nil else { return }
        let alert = UIAlertController(title: "无法设置壁纸", message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "好", style: .default))
        presenter.present(alert, animated: true)
    }
}
