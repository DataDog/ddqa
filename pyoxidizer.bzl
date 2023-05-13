# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
AUTHOR = "Datadog, Inc."
VERSION = VARS["version"].replace(".dev", ".")


def make_msi(target_triple):
    if target_triple == "x86_64-pc-windows-msvc":
        arch = "x64"
    elif target_triple == "i686-pc-windows-msvc":
        arch = "x86"
    else:
        arch = "unknown"

    # https://gregoryszorc.com/docs/pyoxidizer/main/tugger_starlark_type_wix_msi_builder.html#starlark_tugger.WiXMSIBuilder
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

    # https://gregoryszorc.com/docs/pyoxidizer/main/tugger_starlark_type_file_manifest.html#starlark_tugger.FileManifest
    m = FileManifest()

    exe_prefix = "targets/" + target_triple + "/"
    m.add_path(
        path=exe_prefix + "ddqa.exe",
        strip_prefix=exe_prefix,
    )

    msi.add_program_files_manifest(m)

    return msi


def make_exe_installer():
    # https://gregoryszorc.com/docs/pyoxidizer/main/tugger_starlark_type_wix_bundle_builder.html#starlark_tugger.WiXBundleBuilder
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


register_target("windows_installers", make_exe_installer, default=True)

resolve_targets()
