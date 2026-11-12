import Foundation
import IdentityLookup

/// Local SMS/MMS filter. The system only delivers messages from senders who are
/// not in Contacts. This type never opens a network connection and never writes
/// the shared container; Apple does not allow either.
final class MessageFilterExtension: ILMessageFilterExtension {}

extension MessageFilterExtension: ILMessageFilterQueryHandling {
    func handle(
        _ queryRequest: ILMessageFilterQueryRequest,
        context: ILMessageFilterExtensionContext,
        completion: @escaping (ILMessageFilterQueryResponse) -> Void
    ) {
        let response = ILMessageFilterQueryResponse()
        let rules = RuleFile.loadFromAppGroup()
        let classification = SMSClassifier(rules: rules, geo: GeoDatabase.bundled()).classify(
            sender: queryRequest.sender,
            body: queryRequest.messageBody
        )
        apply(classification, to: response)
        completion(response)
    }

    private func apply(_ classification: SMSClassification, to response: ILMessageFilterQueryResponse) {
        switch classification.action {
        case .none:
            response.action = .none
        case .allow:
            response.action = .allow
        case .junk:
            response.action = .junk
        case .transaction:
            response.action = .transaction
            switch classification.topic {
            case .orders:
                response.subAction = .transactionalOrders
            case .finance:
                response.subAction = .transactionalFinance
            default:
                response.subAction = .transactionalOthers
            }
        case .promotion:
            response.action = .promotion
            response.subAction = .promotionalOffers
        }
    }
}

extension MessageFilterExtension: ILMessageFilterCapabilitiesQueryHandling {
    func handle(
        _ capabilitiesQueryRequest: ILMessageFilterCapabilitiesQueryRequest,
        context: ILMessageFilterExtensionContext,
        completion: @escaping (ILMessageFilterCapabilitiesQueryResponse) -> Void
    ) {
        let response = ILMessageFilterCapabilitiesQueryResponse()
        // At most five subcategories. Declaring them does not upload anything.
        response.transactionalSubActions = [.transactionalFinance, .transactionalOrders, .transactionalOthers]
        response.promotionalSubActions = [.promotionalOffers, .promotionalOthers]
        completion(response)
    }
}
