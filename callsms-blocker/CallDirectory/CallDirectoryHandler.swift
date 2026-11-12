import CallKit
import Foundation
import os

/// Offline Call Directory provider.
///
/// The system accepts only a de-duplicated, strictly ascending list of complete
/// phone numbers (E.164 digits, no "+"). There is no per-call callback and no
/// prefix, province, area-code, or country rule. This type only reads the
/// shared rules file.
final class CallDirectoryHandler: CXCallDirectoryProvider {
    override func beginRequest(with context: CXCallDirectoryExtensionContext) {
        context.delegate = self
        if context.isIncremental {
            context.removeAllBlockingEntries()
            context.removeAllIdentificationEntries()
        }

        let rules = RuleFile.loadFromAppGroup()
        let plan = CallListBuilder.plan(for: rules)
        if rules.callBlockingEnabled && !plan.overCap {
            CallListBuilder.enumerateBlocking(rules) { number in
                context.addBlockingEntry(withNextSequentialPhoneNumber: number)
            }
            CallListBuilder.enumerateLabels(rules) { number, label in
                context.addIdentificationEntry(withNextSequentialPhoneNumber: number, label: label)
            }
        } else if plan.overCap {
            Logger(subsystem: "callsms-blocker", category: "call-directory")
                .error("call directory list is over the hard cap; submitting nothing")
        }

        context.completeRequest()
    }
}

extension CallDirectoryHandler: CXCallDirectoryExtensionContextDelegate {
    func requestFailed(for extensionContext: CXCallDirectoryExtensionContext, withError error: Error) {
        let nsError = error as NSError
        Logger(subsystem: "callsms-blocker", category: "call-directory")
            .error("call directory reload failed: \(nsError.domain, privacy: .public) \(nsError.code, privacy: .public)")
    }
}
