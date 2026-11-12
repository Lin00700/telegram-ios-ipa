import SwiftUI

struct RootView: View {
    @EnvironmentObject private var store: RuleStore
    @AppStorage("hasSeenOnboarding") private var hasSeenOnboarding = false

    var body: some View {
        TabView {
            NavigationStack {
                SMSFilterView()
            }
            .tabItem { Label("短信", systemImage: "message") }

            NavigationStack {
                CallBlockView()
            }
            .tabItem { Label("来电", systemImage: "phone") }

            NavigationStack {
                SimulatorView()
            }
            .tabItem { Label("模拟", systemImage: "text.magnifyingglass") }

            NavigationStack {
                OnboardingView()
            }
            .tabItem { Label("说明", systemImage: "book") }
        }
        .sheet(isPresented: onboardingPresented) {
            NavigationStack {
                OnboardingView(showsDone: true) {
                    hasSeenOnboarding = true
                }
            }
        }
        .alert("提示", isPresented: alertPresented) {
            Button("好", role: .cancel) {}
        } message: {
            Text(store.alertMessage ?? "")
        }
    }

    private var onboardingPresented: Binding<Bool> {
        Binding(
            get: { !hasSeenOnboarding },
            set: { if !$0 { hasSeenOnboarding = true } }
        )
    }

    private var alertPresented: Binding<Bool> {
        Binding(
            get: { store.alertMessage != nil },
            set: { if !$0 { store.alertMessage = nil } }
        )
    }
}
