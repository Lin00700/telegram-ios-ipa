import SwiftUI

@main
struct CallSMSBlockerApp: App {
    @StateObject private var store = RuleStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(store)
        }
    }
}
