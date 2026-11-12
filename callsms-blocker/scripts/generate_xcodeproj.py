#!/usr/bin/env python3
"""Write CallSMSBlocker.xcodeproj. Run this after adding or removing source files."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "CallSMSBlocker.xcodeproj"

SHARED = [
    "AppIdentity.swift",
    "CRC32.swift",
    "FilterRules.swift",
    "PhoneNumber.swift",
    "GeoDatabase.swift",
    "KeywordPresets.swift",
    "SMSClassifier.swift",
    "CallListBuilder.swift",
    "RuleFile.swift",
]
APP_SWIFT = [
    "App/CallSMSBlockerApp.swift",
    "App/RuleStore.swift",
    "App/SettingsOpener.swift",
    "Views/RootView.swift",
    "Views/Editors.swift",
    "Views/SMSFilterView.swift",
    "Views/CallBlockView.swift",
    "Views/SimulatorView.swift",
    "Views/OnboardingView.swift",
]


def xid(key: str) -> str:
    return hashlib.sha1(key.encode()).hexdigest()[:24].upper()


def q(value: str) -> str:
    if value == "":
        return '""'
    if all(ch.isalnum() or ch in "._/$" for ch in value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


class Project:
    def __init__(self) -> None:
        self.objects: list[tuple[str, str, list[str]]] = []

    def add(self, isa: str, key: str, body: list[str]) -> str:
        identifier = xid(f"{isa}:{key}")
        self.objects.append((identifier, isa, body))
        return identifier

    def render(self) -> str:
        lines = [
            "// !$*UTF8*$!",
            "{",
            "\tarchiveVersion = 1;",
            "\tclasses = {};",
            "\tobjectVersion = 56;",
            "\tobjects = {",
        ]
        for identifier, isa, body in self.objects:
            lines.append(f"\t\t{identifier} /* {isa} */ = {{")
            lines.append(f"\t\t\tisa = {isa};")
            lines.extend(body)
            lines.append("\t\t};")
        lines.extend([
            "\t};",
            f"\trootObject = {xid('PBXProject:CallSMSBlocker')};",
            "}",
            "",
        ])
        return "\n".join(lines)


def file_type(path: str) -> str:
    if path.endswith(".swift"):
        return "sourcecode.swift"
    if path.endswith(".entitlements"):
        return "text.plist.entitlements"
    if path.endswith(".plist"):
        return "text.plist.xml"
    if path.endswith(".xcconfig"):
        return "text.xcconfig"
    if path.endswith(".xcassets"):
        return "folder.assetcatalog"
    if path.endswith(".png"):
        return "image.png"
    if path.endswith(".json"):
        return "text.json"
    if path.endswith(".txt"):
        return "text"
    if path.endswith(".dat"):
        return "file"
    raise SystemExit(f"unknown file type: {path}")


def main() -> None:
    for relative in SHARED:
        if not (ROOT / "Shared" / relative).is_file():
            raise SystemExit(f"missing Shared/{relative}")
    for relative in APP_SWIFT:
        if not (ROOT / "CallSMSBlocker" / relative).is_file():
            raise SystemExit(f"missing {relative}")

    project = Project()

    def file_ref(key: str, path: str, name: str | None = None) -> str:
        body = [f"\t\t\tlastKnownFileType = {file_type(path)};"]
        if name:
            body.append(f"\t\t\tname = {q(name)};")
        body.append(f"\t\t\tpath = {q(path)};")
        body.append('\t\t\tsourceTree = "<group>";')
        return project.add("PBXFileReference", key, body)

    def product_ref(name: str, explicit: str) -> str:
        return project.add("PBXFileReference", f"product:{name}", [
            "\t\t\texplicitFileType = " + explicit + ";",
            "\t\t\tincludeInIndex = 0;",
            f"\t\t\tpath = {q(name)};",
            "\t\t\tsourceTree = BUILT_PRODUCTS_DIR;",
        ])

    def framework_ref(name: str) -> str:
        return project.add("PBXFileReference", f"framework:{name}", [
            "\t\t\tlastKnownFileType = wrapper.framework;",
            f"\t\t\tname = {q(name)};",
            f"\t\t\tpath = {q('System/Library/Frameworks/' + name)};",
            "\t\t\tsourceTree = SDKROOT;",
        ])

    shared_refs = {name: file_ref(f"shared:{name}", name) for name in SHARED}
    app_refs = {name: file_ref(f"app:{name}", Path(name).name) for name in APP_SWIFT}
    message_ref = file_ref("message:swift", "MessageFilterExtension.swift")
    call_ref = file_ref("call:swift", "CallDirectoryHandler.swift")
    test_ref = file_ref("test:swift", "LogicTests.swift")
    info_refs = {
        "app": file_ref("info:app", "Info.plist"),
        "message": file_ref("info:message", "Info.plist"),
        "call": file_ref("info:call", "Info.plist"),
        "test": file_ref("info:test", "Info.plist"),
    }
    entitlement_refs = {
        "app": file_ref("ent:app", "CallSMSBlocker.entitlements"),
        "message": file_ref("ent:message", "MessageFilter.entitlements"),
        "call": file_ref("ent:call", "CallDirectory.entitlements"),
    }
    asset_ref = file_ref("asset", "Assets.xcassets")
    prefix_ref = file_ref("res:prefix", "prefix_ranges.dat")
    virtual_ref = file_ref("res:virtual", "virtual_prefixes.txt")
    source_ref = file_ref("res:source", "SOURCE.json")
    config_ref = file_ref("config", "Shared.xcconfig")

    app_product = product_ref("CallSMSBlocker.app", "wrapper.application")
    message_product = product_ref("MessageFilter.appex", "wrapper.app-extension")
    call_product = product_ref("CallDirectory.appex", "wrapper.app-extension")
    test_product = product_ref("CallSMSLogicTests.xctest", "wrapper.cfbundle")

    swiftui = framework_ref("SwiftUI.framework")
    uikit = framework_ref("UIKit.framework")
    callkit = framework_ref("CallKit.framework")
    identity = framework_ref("IdentityLookup.framework")
    xctest = framework_ref("XCTest.framework")

    def build_file(key: str, ref: str, attributes: list[str] | None = None) -> str:
        body = [f"\t\t\tfileRef = {ref};"]
        if attributes:
            joined = ", ".join(attributes)
            body.append(f"\t\t\tsettings = {{ATTRIBUTES = ({joined}, ); }};")
        return project.add("PBXBuildFile", key, body)

    def sources_phase(key: str, refs: list[tuple[str, str]]) -> str:
        files = [build_file(f"src:{key}:{name}", ref) for name, ref in refs]
        return project.add("PBXSourcesBuildPhase", key, [
            "\t\t\tbuildActionMask = 2147483647;",
            "\t\t\tfiles = (",
            *[f"\t\t\t\t{item}," for item in files],
            "\t\t\t);",
            "\t\t\trunOnlyForDeploymentPostprocessing = 0;",
        ])

    def resource_phase(key: str, refs: list[tuple[str, str]]) -> str:
        files = [build_file(f"res:{key}:{name}", ref) for name, ref in refs]
        return project.add("PBXResourcesBuildPhase", key, [
            "\t\t\tbuildActionMask = 2147483647;",
            "\t\t\tfiles = (",
            *[f"\t\t\t\t{item}," for item in files],
            "\t\t\t);",
            "\t\t\trunOnlyForDeploymentPostprocessing = 0;",
        ])

    def framework_phase(key: str, refs: list[tuple[str, str]]) -> str:
        files = [build_file(f"fw:{key}:{name}", ref) for name, ref in refs]
        return project.add("PBXFrameworksBuildPhase", key, [
            "\t\t\tbuildActionMask = 2147483647;",
            "\t\t\tfiles = (",
            *[f"\t\t\t\t{item}," for item in files],
            "\t\t\t);",
            "\t\t\trunOnlyForDeploymentPostprocessing = 0;",
        ])

    shared_pairs = [(name, shared_refs[name]) for name in SHARED]
    app_pairs = [(name, app_refs[name]) for name in APP_SWIFT] + shared_pairs
    message_pairs = [("MessageFilterExtension.swift", message_ref)] + shared_pairs
    call_pairs = [("CallDirectoryHandler.swift", call_ref)] + shared_pairs
    test_pairs = [("LogicTests.swift", test_ref)] + shared_pairs

    app_sources = sources_phase("app", app_pairs)
    message_sources = sources_phase("message", message_pairs)
    call_sources = sources_phase("call", call_pairs)
    test_sources = sources_phase("test", test_pairs)

    app_resources = resource_phase("app", [
        ("Assets.xcassets", asset_ref),
        ("prefix_ranges.dat", prefix_ref),
        ("virtual_prefixes.txt", virtual_ref),
        ("SOURCE.json", source_ref),
    ])
    message_resources = resource_phase("message", [("prefix_ranges.dat", prefix_ref)])
    test_resources = resource_phase("test", [("prefix_ranges.dat", prefix_ref)])
    call_resources = resource_phase("call", [])

    app_frameworks = framework_phase("app", [
        ("SwiftUI.framework", swiftui),
        ("UIKit.framework", uikit),
        ("CallKit.framework", callkit),
    ])
    message_frameworks = framework_phase("message", [("IdentityLookup.framework", identity)])
    call_frameworks = framework_phase("call", [("CallKit.framework", callkit)])
    test_frameworks = framework_phase("test", [("XCTest.framework", xctest)])

    message_embed = build_file("embed:message", message_product, ["RemoveHeadersOnCopy"])
    call_embed = build_file("embed:call", call_product, ["RemoveHeadersOnCopy"])
    embed_phase = project.add("PBXCopyFilesBuildPhase", "embed", [
        "\t\t\tbuildActionMask = 2147483647;",
        '\t\t\tdstPath = "";',
        "\t\t\tdstSubfolderSpec = 13;",
        "\t\t\tfiles = (",
        f"\t\t\t\t{message_embed},",
        f"\t\t\t\t{call_embed},",
        "\t\t\t);",
        '\t\t\tname = "Embed App Extensions";',
        "\t\t\trunOnlyForDeploymentPostprocessing = 0;",
    ])

    def group(key: str, name: str, children: list[str], path: str | None = None) -> str:
        body = [
            "\t\t\tchildren = (",
            *[f"\t\t\t\t{child}," for child in children],
            "\t\t\t);",
        ]
        if path:
            body.append(f"\t\t\tpath = {q(path)};")
        else:
            body.append(f"\t\t\tname = {q(name)};")
        body.append('\t\t\tsourceTree = "<group>";')
        return project.add("PBXGroup", key, body)

    app_group_folder = group("app-root", "CallSMSBlocker", [
        group("app-app", "App", [app_refs[name] for name in APP_SWIFT if name.startswith("App/")], "App"),
        group("app-views", "Views", [app_refs[name] for name in APP_SWIFT if name.startswith("Views/")], "Views"),
        asset_ref,
        info_refs["app"],
        entitlement_refs["app"],
    ], "CallSMSBlocker")
    message_group = group("message", "MessageFilter", [message_ref, info_refs["message"], entitlement_refs["message"]], "MessageFilter")
    call_group = group("call", "CallDirectory", [call_ref, info_refs["call"], entitlement_refs["call"]], "CallDirectory")
    shared_group = group("shared", "Shared", [shared_refs[name] for name in SHARED], "Shared")
    resource_group = group("resources", "Resources", [prefix_ref, virtual_ref, source_ref], "Resources")
    test_group = group("tests", "LogicTests", [test_ref, info_refs["test"]], "LogicTests")
    config_group = group("config", "Config", [config_ref], "Config")
    products = group("products", "Products", [app_product, message_product, call_product, test_product])
    frameworks = group("frameworks", "Frameworks", [swiftui, uikit, callkit, identity, xctest])
    main_group = group("main", "CallSMSBlocker", [
        app_group_folder, message_group, call_group, shared_group, resource_group, test_group, config_group, frameworks, products,
    ])

    def settings(extra: dict[str, str], debug: bool) -> list[str]:
        values = {
            "ALWAYS_SEARCH_USER_PATHS": "NO",
            "CLANG_ENABLE_MODULES": "YES",
            "CLANG_ENABLE_OBJC_ARC": "YES",
            "CODE_SIGN_IDENTITY": "",
            "CODE_SIGN_STYLE": "Manual",
            "CODE_SIGNING_ALLOWED": "NO",
            "CODE_SIGNING_REQUIRED": "NO",
            "COPY_PHASE_STRIP": "NO",
            "DEBUG_INFORMATION_FORMAT": "dwarf" if debug else "dwarf-with-dsym",
            "DEVELOPMENT_TEAM": "",
            "ENABLE_NS_ASSERTIONS": "YES" if debug else "NO",
            "ENABLE_USER_SCRIPT_SANDBOXING": "NO",
            "GCC_OPTIMIZATION_LEVEL": "0" if debug else "s",
            "ONLY_ACTIVE_ARCH": "YES" if debug else "NO",
            "PROVISIONING_PROFILE_SPECIFIER": "",
            "SWIFT_ACTIVE_COMPILATION_CONDITIONS": "DEBUG" if debug else "",
            "SWIFT_OPTIMIZATION_LEVEL": "-Onone" if debug else "-O",
            "SWIFT_VERSION": "5.0",
            "VALIDATE_PRODUCT": "NO",
        }
        values.update(extra)
        if not debug:
            values.pop("SWIFT_ACTIVE_COMPILATION_CONDITIONS", None)
        lines = ["\t\t\tbuildSettings = {"]
        for key in sorted(values):
            lines.append(f"\t\t\t\t{key} = {q(values[key])};")
        lines.append("\t\t\t};")
        return lines

    ios_common = {
        "ASSETCATALOG_COMPILER_GENERATE_SWIFT_ASSET_SYMBOL_EXTENSIONS": "YES",
        "IPHONEOS_DEPLOYMENT_TARGET": "16.0",
        "SDKROOT": "iphoneos",
        "SUPPORTED_PLATFORMS": "iphoneos iphonesimulator",
        "SUPPORTS_MACCATALYST": "NO",
        "SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD": "NO",
        "SUPPORTS_XR_DESIGNED_FOR_IPHONE_IPAD": "NO",
        "TARGETED_DEVICE_FAMILY": "1",
        "GENERATE_INFOPLIST_FILE": "NO",
    }

    def config_pair(key: str, extra: dict[str, str]) -> str:
        debug = project.add("XCBuildConfiguration", f"{key}:Debug", [
            f"\t\t\tbaseConfigurationReference = {config_ref};",
            *settings(extra, True),
            "\t\t\tname = Debug;",
        ])
        release = project.add("XCBuildConfiguration", f"{key}:Release", [
            f"\t\t\tbaseConfigurationReference = {config_ref};",
            *settings(extra, False),
            "\t\t\tname = Release;",
        ])
        return project.add("XCConfigurationList", key, [
            "\t\t\tbuildConfigurations = (",
            f"\t\t\t\t{debug},",
            f"\t\t\t\t{release},",
            "\t\t\t);",
            "\t\t\tdefaultConfigurationIsVisible = 0;",
            "\t\t\tdefaultConfigurationName = Release;",
        ])

    app_config = config_pair("cfg:app", {
        **ios_common,
        "ASSETCATALOG_COMPILER_APPICON_NAME": "AppIcon",
        "ASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME": "AccentColor",
        "CODE_SIGN_ENTITLEMENTS": "CallSMSBlocker/CallSMSBlocker.entitlements",
        "INFOPLIST_FILE": "CallSMSBlocker/Info.plist",
        "LD_RUNPATH_SEARCH_PATHS": "$(inherited) @executable_path/Frameworks",
        "PRODUCT_BUNDLE_IDENTIFIER": "$(APP_BUNDLE_ID)",
        "PRODUCT_NAME": "CallSMSBlocker",
        "SKIP_INSTALL": "NO",
    })
    message_config = config_pair("cfg:message", {
        **ios_common,
        "APPLICATION_EXTENSION_API_ONLY": "YES",
        "CODE_SIGN_ENTITLEMENTS": "MessageFilter/MessageFilter.entitlements",
        "INFOPLIST_FILE": "MessageFilter/Info.plist",
        "LD_RUNPATH_SEARCH_PATHS": "$(inherited) @executable_path/Frameworks @executable_path/../../Frameworks",
        "PRODUCT_BUNDLE_IDENTIFIER": "$(APP_BUNDLE_ID).MessageFilter",
        "PRODUCT_NAME": "MessageFilter",
        "SKIP_INSTALL": "YES",
    })
    call_config = config_pair("cfg:call", {
        **ios_common,
        "APPLICATION_EXTENSION_API_ONLY": "YES",
        "CODE_SIGN_ENTITLEMENTS": "CallDirectory/CallDirectory.entitlements",
        "INFOPLIST_FILE": "CallDirectory/Info.plist",
        "LD_RUNPATH_SEARCH_PATHS": "$(inherited) @executable_path/Frameworks @executable_path/../../Frameworks",
        "PRODUCT_BUNDLE_IDENTIFIER": "$(APP_BUNDLE_ID).CallDirectory",
        "PRODUCT_NAME": "CallDirectory",
        "SKIP_INSTALL": "YES",
    })
    test_config = config_pair("cfg:test", {
        "BUNDLE_LOADER": "",
        "GENERATE_INFOPLIST_FILE": "NO",
        "INFOPLIST_FILE": "LogicTests/Info.plist",
        "LD_RUNPATH_SEARCH_PATHS": "$(inherited) @executable_path/../Frameworks @loader_path/../Frameworks",
        "MACOSX_DEPLOYMENT_TARGET": "13.0",
        "PRODUCT_BUNDLE_IDENTIFIER": "$(APP_BUNDLE_ID).logic-tests",
        "PRODUCT_NAME": "CallSMSLogicTests",
        "SDKROOT": "macosx",
        "SUPPORTED_PLATFORMS": "macosx",
        "TEST_HOST": "",
    })
    project_config = config_pair("cfg:project", {
        "ALWAYS_SEARCH_USER_PATHS": "NO",
        "CLANG_ANALYZER_NONNULL": "YES",
        "CLANG_WARN_DOCUMENTATION_COMMENTS": "YES",
        "CLANG_WARN_UNGUARDED_AVAILABILITY": "YES_AGGRESSIVE",
        "SDKROOT": "iphoneos",
    })

    def proxy(key: str, remote: str, remote_name: str) -> str:
        return project.add("PBXContainerItemProxy", key, [
            f"\t\t\tcontainerPortal = {xid('PBXProject:CallSMSBlocker')};",
            "\t\t\tproxyType = 1;",
            f"\t\t\tremoteGlobalIDString = {remote};",
            f"\t\t\tremoteInfo = {q(remote_name)};",
        ])

    def dependency(key: str, target: str, remote_name: str) -> str:
        item = proxy(f"proxy:{key}", target, remote_name)
        return project.add("PBXTargetDependency", key, [
            f"\t\t\ttarget = {target};",
            f"\t\t\ttargetProxy = {item};",
        ])

    message_target = project.add("PBXNativeTarget", "MessageFilter", [
        f"\t\t\tbuildConfigurationList = {message_config};",
        "\t\t\tbuildPhases = (",
        f"\t\t\t\t{message_sources},",
        f"\t\t\t\t{message_frameworks},",
        f"\t\t\t\t{message_resources},",
        "\t\t\t);",
        "\t\t\tbuildRules = (",
        "\t\t\t);",
        "\t\t\tdependencies = (",
        "\t\t\t);",
        '\t\t\tname = "MessageFilter";',
        f"\t\t\tproductName = {q('MessageFilter')};",
        f"\t\t\tproductReference = {message_product};",
        '\t\t\tproductType = "com.apple.product-type.app-extension";',
    ])
    call_target = project.add("PBXNativeTarget", "CallDirectory", [
        f"\t\t\tbuildConfigurationList = {call_config};",
        "\t\t\tbuildPhases = (",
        f"\t\t\t\t{call_sources},",
        f"\t\t\t\t{call_frameworks},",
        f"\t\t\t\t{call_resources},",
        "\t\t\t);",
        "\t\t\tbuildRules = (",
        "\t\t\t);",
        "\t\t\tdependencies = (",
        "\t\t\t);",
        '\t\t\tname = "CallDirectory";',
        f"\t\t\tproductName = {q('CallDirectory')};",
        f"\t\t\tproductReference = {call_product};",
        '\t\t\tproductType = "com.apple.product-type.app-extension";',
    ])
    message_dep = dependency("dep:message", message_target, "MessageFilter")
    call_dep = dependency("dep:call", call_target, "CallDirectory")
    app_target = project.add("PBXNativeTarget", "CallSMSBlocker", [
        f"\t\t\tbuildConfigurationList = {app_config};",
        "\t\t\tbuildPhases = (",
        f"\t\t\t\t{app_sources},",
        f"\t\t\t\t{app_frameworks},",
        f"\t\t\t\t{app_resources},",
        f"\t\t\t\t{embed_phase},",
        "\t\t\t);",
        "\t\t\tbuildRules = (",
        "\t\t\t);",
        "\t\t\tdependencies = (",
        f"\t\t\t\t{message_dep},",
        f"\t\t\t\t{call_dep},",
        "\t\t\t);",
        '\t\t\tname = "CallSMSBlocker";',
        f"\t\t\tproductName = {q('CallSMSBlocker')};",
        f"\t\t\tproductReference = {app_product};",
        '\t\t\tproductType = "com.apple.product-type.application";',
    ])
    test_target = project.add("PBXNativeTarget", "CallSMSLogicTests", [
        f"\t\t\tbuildConfigurationList = {test_config};",
        "\t\t\tbuildPhases = (",
        f"\t\t\t\t{test_sources},",
        f"\t\t\t\t{test_frameworks},",
        f"\t\t\t\t{test_resources},",
        "\t\t\t);",
        "\t\t\tbuildRules = (",
        "\t\t\t);",
        "\t\t\tdependencies = (",
        "\t\t\t);",
        '\t\t\tname = "CallSMSLogicTests";',
        f"\t\t\tproductName = {q('CallSMSLogicTests')};",
        f"\t\t\tproductReference = {test_product};",
        '\t\t\tproductType = "com.apple.product-type.bundle.unit-test";',
    ])

    project.add("PBXProject", "CallSMSBlocker", [
        "\t\t\tattributes = {",
        "\t\t\t\tBuildIndependentTargetsInParallel = 1;",
        "\t\t\t\tLastUpgradeCheck = 1600;",
        "\t\t\t\tTargetAttributes = {",
        f"\t\t\t\t\t{app_target} = {{CreatedOnToolsVersion = 16.0; }};",
        f"\t\t\t\t\t{message_target} = {{CreatedOnToolsVersion = 16.0; }};",
        f"\t\t\t\t\t{call_target} = {{CreatedOnToolsVersion = 16.0; }};",
        f"\t\t\t\t\t{test_target} = {{CreatedOnToolsVersion = 16.0; }};",
        "\t\t\t\t};",
        "\t\t\t};",
        f"\t\t\tbuildConfigurationList = {project_config};",
        '\t\t\tcompatibilityVersion = "Xcode 14.0";',
        '\t\t\tdevelopmentRegion = "zh-Hans";',
        "\t\t\thasScannedForEncodings = 0;",
        "\t\t\tknownRegions = (",
        "\t\t\t\tzh-Hans,",
        "\t\t\t\tBase,",
        "\t\t\t);",
        f"\t\t\tmainGroup = {main_group};",
        f"\t\t\tproductRefGroup = {products};",
        '\t\t\tprojectDirPath = "";',
        '\t\t\tprojectRoot = "";',
        "\t\t\ttargets = (",
        f"\t\t\t\t{app_target},",
        f"\t\t\t\t{message_target},",
        f"\t\t\t\t{call_target},",
        f"\t\t\t\t{test_target},",
        "\t\t\t);",
    ])

    text = project.render()
    defined = set(re.findall(r"^\t\t([0-9A-F]{24}) ", text, re.M))
    used = set(re.findall(r"\b([0-9A-F]{24})\b", text))
    missing = used - defined
    if missing:
        raise SystemExit(f"project references unknown ids: {sorted(missing)[:8]}")
    if text.count("{") != text.count("}"):
        raise SystemExit("project braces are unbalanced")
    PROJECT.mkdir(parents=True, exist_ok=True)
    (PROJECT / "project.pbxproj").write_text(text, encoding="utf-8")
    write_schemes(app_target, message_target, call_target, test_target)
    print(PROJECT / "project.pbxproj")


def write_schemes(app: str, message: str, call: str, tests: str) -> None:
    schemes = PROJECT / "xcshareddata" / "xcschemes"
    schemes.mkdir(parents=True, exist_ok=True)
    (schemes / "CallSMSBlocker.xcscheme").write_text(scheme(
        "CallSMSBlocker", "CallSMSBlocker.app", app,
        extra_builds=[
            ("MessageFilter", "MessageFilter.appex", message),
            ("CallDirectory", "CallDirectory.appex", call),
        ],
        tests=None,
    ), encoding="utf-8")
    (schemes / "CallSMSLogicTests.xcscheme").write_text(scheme(
        "CallSMSLogicTests", "CallSMSLogicTests.xctest", tests,
        extra_builds=[],
        tests=("CallSMSLogicTests", "CallSMSLogicTests.xctest", tests),
    ), encoding="utf-8")


def scheme(name: str, product: str, identifier: str, extra_builds: list[tuple[str, str, str]], tests) -> str:
    def ref(blueprint_name: str, buildable: str, blueprint: str) -> str:
        return f"""
               <BuildableReference
                  BuildableIdentifier = "primary"
                  BlueprintIdentifier = "{blueprint}"
                  BuildableName = "{buildable}"
                  BlueprintName = "{blueprint_name}"
                  ReferencedContainer = "container:CallSMSBlocker.xcodeproj">
               </BuildableReference>"""

    entries = [f"""
         <BuildActionEntry
            buildForTesting = "YES"
            buildForRunning = "YES"
            buildForProfiling = "YES"
            buildForArchiving = "YES"
            buildForAnalyzing = "YES">
            <BuildableReference
               BuildableIdentifier = "primary"
               BlueprintIdentifier = "{identifier}"
               BuildableName = "{product}"
               BlueprintName = "{name}"
               ReferencedContainer = "container:CallSMSBlocker.xcodeproj">
            </BuildableReference>
         </BuildActionEntry>"""]
    for blueprint_name, buildable, blueprint in extra_builds:
        entries.append(f"""
         <BuildActionEntry
            buildForTesting = "YES"
            buildForRunning = "YES"
            buildForProfiling = "YES"
            buildForArchiving = "YES"
            buildForAnalyzing = "YES">{ref(blueprint_name, buildable, blueprint)}
         </BuildActionEntry>""")
    testables = ""
    if tests:
        test_name, test_product, test_id = tests
        testables = f"""
         <Testables>
            <TestableReference
               skipped = "NO">
               <BuildableReference
                  BuildableIdentifier = "primary"
                  BlueprintIdentifier = "{test_id}"
                  BuildableName = "{test_product}"
                  BlueprintName = "{test_name}"
                  ReferencedContainer = "container:CallSMSBlocker.xcodeproj">
               </BuildableReference>
            </TestableReference>
         </Testables>"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Scheme
   LastUpgradeVersion = "1600"
   version = "1.7">
   <BuildAction
      parallelizeBuildables = "YES"
      buildImplicitDependencies = "YES">
      <BuildActionEntries>{''.join(entries)}
      </BuildActionEntries>
   </BuildAction>
   <TestAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      shouldUseLaunchSchemeArgsEnv = "YES">{testables}
   </TestAction>
   <LaunchAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      launchStyle = "0"
      useCustomWorkingDirectory = "NO"
      ignoresPersistentStateOnLaunch = "NO"
      debugDocumentVersioning = "YES"
      debugServiceExtension = "internal"
      allowLocationSimulation = "YES">
   </LaunchAction>
   <ProfileAction
      buildConfiguration = "Release"
      shouldUseLaunchSchemeArgsEnv = "YES"
      savedToolIdentifier = ""
      useCustomWorkingDirectory = "NO"
      debugDocumentVersioning = "YES">
   </ProfileAction>
   <AnalyzeAction
      buildConfiguration = "Debug">
   </AnalyzeAction>
   <ArchiveAction
      buildConfiguration = "Release"
      revealArchiveInOrganizer = "YES">
   </ArchiveAction>
</Scheme>
"""


if __name__ == "__main__":
    main()
