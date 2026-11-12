import Foundation

struct CallPlan: Equatable {
    static let cap = 1_000_000
    static let numbersPerSegment = 10_000

    var segmentCount: Int
    var blockingCount: Int
    var labelCount: Int
    var totalEntries: Int
    var overCap: Bool

    var remainingEntries: Int {
        max(0, Self.cap - totalEntries)
    }

    var remainingSegments: Int {
        remainingEntries / Self.numbersPerSegment
    }
}

enum CallListBuilder {
    struct NumberRange: Equatable {
        var lower: Int64
        var upper: Int64

        var count: Int { Int(upper - lower + 1) }
    }

    static func plan(for rules: FilterRules) -> CallPlan {
        let ranges = activeRanges(rules)
        let manuals = blockingNumbers(rules)
        var blocking = ranges.reduce(0) { $0 + $1.count }
        for number in manuals where rangeIndex(of: number, in: ranges) == nil {
            blocking += 1
        }
        let labels = labelMap(rules).count
        let total = blocking + labels
        return CallPlan(
            segmentCount: ranges.count,
            blockingCount: blocking,
            labelCount: labels,
            totalEntries: total,
            overCap: total > CallPlan.cap
        )
    }

    static func enumerateBlocking(_ rules: FilterRules, emit: (Int64) -> Void) {
        let snapshot = plan(for: rules)
        guard rules.callBlockingEnabled, !snapshot.overCap else { return }
        let ranges = activeRanges(rules)
        let manuals = blockingNumbers(rules)
        var manualIndex = 0
        var last: Int64 = 0

        func emitOne(_ number: Int64) {
            guard number > last else { return }
            emit(number)
            last = number
        }

        for range in ranges {
            while manualIndex < manuals.count && manuals[manualIndex] < range.lower {
                emitOne(manuals[manualIndex])
                manualIndex += 1
            }
            var number = range.lower
            while number <= range.upper {
                emitOne(number)
                if number == Int64.max { break }
                number += 1
            }
            while manualIndex < manuals.count && manuals[manualIndex] <= range.upper {
                manualIndex += 1
            }
        }
        while manualIndex < manuals.count {
            emitOne(manuals[manualIndex])
            manualIndex += 1
        }
    }

    static func enumerateLabels(_ rules: FilterRules, emit: (Int64, String) -> Void) {
        let snapshot = plan(for: rules)
        guard rules.callBlockingEnabled, !snapshot.overCap else { return }
        let labels = labelMap(rules)
        for number in labels.keys.sorted() {
            if let label = labels[number] {
                emit(number, label)
            }
        }
    }

    static func range(for prefix7: String) -> NumberRange? {
        guard PhoneNumber.isPrefix7(prefix7), let value = Int64(prefix7) else { return nil }
        let lower = Int64(86) * 100_000_000_000 + value * Int64(CallPlan.numbersPerSegment)
        return NumberRange(lower: lower, upper: lower + Int64(CallPlan.numbersPerSegment) - 1)
    }

    private static func activeRanges(_ rules: FilterRules) -> [NumberRange] {
        var prefixes: [String] = []
        if rules.segmentBlockEnabled {
            prefixes.append(contentsOf: rules.blockedSegments)
        }
        if rules.expandVirtualSegments {
            prefixes.append(contentsOf: rules.virtualSegments)
        }
        var seen = Set<String>()
        var ranges: [NumberRange] = []
        for prefix in prefixes where seen.insert(prefix).inserted {
            guard let range = range(for: prefix) else { continue }
            ranges.append(range)
        }
        ranges.sort { $0.lower < $1.lower }
        return ranges
    }

    private static func blockingNumbers(_ rules: FilterRules) -> [Int64] {
        var seen = Set<Int64>()
        for item in rules.blockedNumbers {
            guard let number = Int64(item.e164), number > 0 else { continue }
            seen.insert(number)
        }
        return seen.sorted()
    }

    private static func labelMap(_ rules: FilterRules) -> [Int64: String] {
        var map: [Int64: String] = [:]
        for item in rules.labeledNumbers {
            guard let number = Int64(item.e164), number > 0 else { continue }
            let label = item.label.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !label.isEmpty else { continue }
            map[number] = String(label.prefix(24))
        }
        return map
    }

    private static func rangeIndex(of number: Int64, in ranges: [NumberRange]) -> Int? {
        var low = 0
        var high = ranges.count - 1
        while low <= high {
            let mid = (low + high) / 2
            let range = ranges[mid]
            if number < range.lower {
                high = mid - 1
            } else if number > range.upper {
                low = mid + 1
            } else {
                return mid
            }
        }
        return nil
    }
}
