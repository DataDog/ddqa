# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
AUTHOR = "Datadog, Inc."
VERSION = VARS["version"]


def make_msi(target):
    if target == "x86_64-pc-windows-msvc":
        arch = "x64"
    elif target == "i686-pc-windows-msvc":
        arch = "x86"
    else:
        arch = "unknown"

    # https://gregoryszorc.com/docs/pyoxidizer/main/tugger_starlark_type_wix_msi_builder.html
    msi = WiXMSIBuilder(
        id_prefix="ddqa",
        product_name="Datadog QA",
        product_version=VERSION,
        product_manufacturer=AUTHOR,
        arch=arch,
    )
    msi.msi_filename = "ddqa-" + VERSION + "-" + arch + ".msi"
    msi.help_url = "https://datadoghq.dev/ddqa/"
    msi.license_path = CWD + "/LICENSE.txt"

    # https://gregoryszorc.com/docs/pyoxidizer/main/tugger_starlark_type_file_manifest.html
    m = FileManifest()

    exe_prefix = "targets/" + target + "/"
    m.add_path(
        path=exe_prefix + "ddqa.exe",
        strip_prefix=exe_prefix,
    )

    msi.add_program_files_manifest(m)

    return msi


def make_exe_installer():
    # https://gregoryszorc.com/docs/pyoxidizer/main/tugger_starlark_type_wix_bundle_builder.html
    bundle = WiXBundleBuilder(
        id_prefix="ddqa",
        name="Datadog QA",
        version=VERSION,
        manufacturer=AUTHOR,
    )

    bundle.add_vc_redistributable("x64")
    bundle.add_vc_redistributable("x86")

    bundle.add_wix_msi_builder(
        builder=make_msi("x86_64-pc-windows-msvc"),
        display_internal_ui=True,
        install_condition="VersionNT64",
    )
    bundle.add_wix_msi_builder(
        builder=make_msi("i686-pc-windows-msvc"),
        display_internal_ui=True,
        install_condition="Not VersionNT64",
    )

    return bundle


def make_macos_app_bundle():
    # https://gregoryszorc.com/docs/pyoxidizer/main/tugger_starlark_type_macos_application_bundle_builder.html
    bundle = MacOsApplicationBundleBuilder("Datadog QA")
    bundle.set_info_plist_required_keys(
        display_name="Datadog QA",
        identifier="com.datadoghq.ddqa",
        version=VERSION,
        signature="ddqa",
        executable="ddqa",
    )

    # https://gregoryszorc.com/docs/pyoxidizer/main/tugger_starlark_type_apple_universal_binary.html
    universal = AppleUniversalBinary("ddqa")

    for target in ["aarch64-apple-darwin", "x86_64-apple-darwin"]:
        universal.add_path("targets/" + target + "/ddqa")

    m = FileManifest()
    m.add_file(universal.to_file_content())
    bundle.add_macos_manifest(m)

    return bundle


register_target("windows_installers", make_exe_installer, default=True)
register_target("macos_app_bundle", make_macos_app_bundle)

resolve_targets()
