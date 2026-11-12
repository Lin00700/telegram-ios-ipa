import Foundation

struct GeoHit: Equatable {
    var province: String
    var areaCode: String
    var city: String

    var summary: String {
        "\(province) · \(city) · \(areaCode)"
    }
}

enum GeoDatabaseError: Error, Equatable {
    case truncated
    case magic
    case version
    case crc
    case inconsistent
}

final class GeoDatabase {
    struct Area {
        var code: String
        var city: String
        var provinceIndex: Int
    }

    let provinces: [String]
    let areas: [Area]
    let areaCodes: Set<String>
    private let storage: Data
    private let rangeOffset: Int
    private let rangeCount: Int
    private let areaIndexByCode: [String: Int]

    convenience init(contentsOf url: URL) throws {
        let data = try Data(contentsOf: url, options: [.mappedIfSafe])
        try self.init(data: data)
    }

    init(data: Data) throws {
        guard data.count >= 12 else { throw GeoDatabaseError.truncated }
        guard data.prefix(4) == Data("P7R1".utf8) else { throw GeoDatabaseError.magic }
        var cursor = 4
        let version = Self.readUInt16(data, &cursor)
        guard version == 1 else { throw GeoDatabaseError.version }
        let provinceCount = Int(Self.readUInt16(data, &cursor))
        var provinces: [String] = []
        provinces.reserveCapacity(provinceCount)
        for _ in 0..<provinceCount {
            provinces.append(try Self.readString(data, &cursor))
        }
        let areaCount = Int(Self.readUInt16(data, &cursor))
        var areas: [Area] = []
        areas.reserveCapacity(areaCount)
        var areaIndexByCode: [String: Int] = [:]
        for index in 0..<areaCount {
            let code = try Self.readString(data, &cursor)
            let city = try Self.readString(data, &cursor)
            let provinceIndex = Int(Self.readUInt16(data, &cursor))
            guard provinceIndex < provinces.count else { throw GeoDatabaseError.inconsistent }
            areas.append(Area(code: code, city: city, provinceIndex: provinceIndex))
            areaIndexByCode[code] = index
        }
        let rangeCount = Int(Self.readUInt32(data, &cursor))
        let tableBytes = rangeCount * 8
        guard cursor + tableBytes + 4 == data.count else { throw GeoDatabaseError.truncated }
        let stored = Self.readUInt32(data, data.count - 4)
        let computed = CRC32.ieee(data.prefix(data.count - 4))
        guard stored == computed else { throw GeoDatabaseError.crc }
        self.storage = data
        self.rangeOffset = cursor
        self.rangeCount = rangeCount
        self.provinces = provinces
        self.areas = areas
        self.areaCodes = Set(areaIndexByCode.keys)
        self.areaIndexByCode = areaIndexByCode
        guard rangesAreOrdered() else { throw GeoDatabaseError.inconsistent }
    }

    static func bundled(in bundle: Bundle = .main) -> GeoDatabase? {
        guard let url = bundle.url(forResource: "prefix_ranges", withExtension: "dat") else { return nil }
        return try? GeoDatabase(contentsOf: url)
    }

    func lookup(prefix7: Int) -> GeoHit? {
        var low = 0
        var high = rangeCount - 1
        while low <= high {
            let mid = (low + high) / 2
            let start = rangeStart(mid)
            let length = rangeLength(mid)
            let end = start + length - 1
            if prefix7 < start {
                high = mid - 1
            } else if prefix7 > end {
                low = mid + 1
            } else {
                return hit(areaIndex: rangeArea(mid))
            }
        }
        return nil
    }

    func lookup(areaCode: String) -> GeoHit? {
        guard let index = areaIndexByCode[areaCode] else { return nil }
        return hit(areaIndex: index)
    }

    func firstPrefix(whereProvince predicate: (String) -> Bool) -> Int? {
        for index in 0..<rangeCount {
            let area = rangeArea(index)
            guard area < areas.count else { continue }
            let province = provinces[areas[area].provinceIndex]
            if predicate(province) {
                return rangeStart(index)
            }
        }
        return nil
    }

    var sortedAreaCodes: [String] {
        areas.map(\.code)
    }

    private func hit(areaIndex: Int) -> GeoHit? {
        guard areaIndex < areas.count else { return nil }
        let area = areas[areaIndex]
        guard area.provinceIndex < provinces.count else { return nil }
        return GeoHit(province: provinces[area.provinceIndex], areaCode: area.code, city: area.city)
    }

    private func rangesAreOrdered() -> Bool {
        var previousEnd = -1
        for index in 0..<rangeCount {
            let start = rangeStart(index)
            let length = rangeLength(index)
            let area = rangeArea(index)
            guard length > 0, area < areas.count, start > previousEnd else { return false }
            previousEnd = start + length - 1
        }
        return true
    }

    private func rangeStart(_ index: Int) -> Int {
        Int(Self.readUInt32(storage, rangeOffset + index * 8))
    }

    private func rangeLength(_ index: Int) -> Int {
        Int(Self.readUInt16(storage, rangeOffset + index * 8 + 4))
    }

    private func rangeArea(_ index: Int) -> Int {
        Int(Self.readUInt16(storage, rangeOffset + index * 8 + 6))
    }

    private static func readString(_ data: Data, _ cursor: inout Int) throws -> String {
        guard cursor < data.count else { throw GeoDatabaseError.truncated }
        let length = Int(data[cursor])
        cursor += 1
        guard cursor + length <= data.count else { throw GeoDatabaseError.truncated }
        let bytes = data.subdata(in: cursor..<(cursor + length))
        cursor += length
        guard let text = String(data: bytes, encoding: .utf8), !text.isEmpty else {
            throw GeoDatabaseError.inconsistent
        }
        return text
    }

    private static func readUInt16(_ data: Data, _ cursor: inout Int) -> UInt16 {
        let value = readUInt16(data, cursor)
        cursor += 2
        return value
    }

    private static func readUInt32(_ data: Data, _ cursor: inout Int) -> UInt32 {
        let value = readUInt32(data, cursor)
        cursor += 4
        return value
    }

    private static func readUInt16(_ data: Data, _ offset: Int) -> UInt16 {
        UInt16(data[offset]) | (UInt16(data[offset + 1]) << 8)
    }

    private static func readUInt32(_ data: Data, _ offset: Int) -> UInt32 {
        UInt32(data[offset])
            | (UInt32(data[offset + 1]) << 8)
            | (UInt32(data[offset + 2]) << 16)
            | (UInt32(data[offset + 3]) << 24)
    }
}
