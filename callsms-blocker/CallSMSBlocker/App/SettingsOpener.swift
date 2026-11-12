import UIKit

@MainActor
enum SettingsOpener {
    /// Tries the private Settings URL, then leaves the caller to show the manual steps.
    /// Silence Unknown Callers has no public deep link.
    static func openSilenceUnknownCallers() async -> Bool {
        await openFirst([
            "App-Prefs:root=Phone",
            "App-Prefs:Phone",
            "prefs:root=Phone",
            "App-Prefs:root=PHONE"
        ])
    }

    static func openMessagesSettings() async -> Bool {
        await openFirst([
            "App-Prefs:root=MESSAGES",
            "App-Prefs:MESSAGES",
            "prefs:root=MESSAGES"
        ])
    }

    private static func openFirst(_ candidates: [String]) async -> Bool {
        for candidate in candidates {
            guard let url = URL(string: candidate) else { continue }
            if await UIApplication.shared.open(url, options: [:]) {
                return true
            }
        }
        return false
    }
}
