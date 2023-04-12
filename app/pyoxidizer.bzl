# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
VERSION = VARS["version"]

def make_exe():
    # https://gregoryszorc.com/docs/pyoxidizer/main/pyoxidizer_config_type_python_distribution.html#starlark_pyoxidizer.default_python_distribution
    dist = default_python_distribution(python_version = "3.10", flavor="standalone")

    # https://gregoryszorc.com/docs/pyoxidizer/main/pyoxidizer_config_type_python_packaging_policy.html#starlark_pyoxidizer.PythonPackagingPolicy
    policy = dist.make_python_packaging_policy()
    policy.set_resource_handling_mode("files")
    policy.resources_location = "filesystem-relative:lib"
    policy.include_distribution_resources = True

    # https://gregoryszorc.com/docs/pyoxidizer/main/pyoxidizer_config_type_python_interpreter_config.html#starlark_pyoxidizer.PythonInterpreterConfig
    python_config = dist.make_python_interpreter_config()
    python_config.sys_frozen = True
    python_config.run_module = "ddqa"

    if "apple" in BUILD_TARGET_TRIPLE:
        module_search_paths = ["$ORIGIN/lib", "$ORIGIN../Resources/lib"]
    else:
        module_search_paths = ["$ORIGIN/lib"]
    python_config.module_search_paths = module_search_paths

    # https://gregoryszorc.com/docs/pyoxidizer/main/pyoxidizer_config_type_python_executable.html#starlark_pyoxidizer.PythonExecutable
    exe = dist.to_python_executable(
        name="ddqa",
        packaging_policy=policy,
        config=python_config,
    )
    exe.add_python_resources(exe.pip_download(["ddqa==" + VERSION]))
    exe.packed_resources_load_mode = "none"

    return exe

def make_embedded_resources(exe):
    return exe.to_embedded_resources()

def make_install(exe):
    # https://gregoryszorc.com/docs/pyoxidizer/main/tugger_starlark_type_file_manifest.html#starlark_tugger.FileManifest
    files = FileManifest()

    # https://gregoryszorc.com/docs/pyoxidizer/main/pyoxidizer_config_tugger_extensions.html#filemanifest-add-python-resource
    files.add_python_resource(".", exe)

    return files

def make_msi(exe):
    version = VERSION.replace(".dev", ".")

    # https://gregoryszorc.com/docs/pyoxidizer/main/tugger_starlark_type_wix_msi_builder.html#starlark_tugger.WiXMSIBuilder
    msi = exe.to_wix_msi_builder(
        "ddqa",
        "Datadog QA",
        version,
        "Datadog, Inc.",
    )
    msi.msi_filename = "ddqa-" + version + "-x64.msi"
    msi.help_url = "https://datadoghq.dev/ddqa/"
    msi.license_path = CWD + "/../LICENSE.txt"

    return msi

def make_macos_app_bundle(exe):
    if BUILD_TARGET_TRIPLE == "aarch64-apple-darwin":
        arch = "-arm"
    else:
        arch = "-intel"

    bundle = MacOsApplicationBundleBuilder("ddqa-" + VERSION + arch)
    bundle.set_info_plist_required_keys(
        display_name="Datadog QA",
        identifier="com.datadoghq.ddqa",
        version=VERSION,
        signature="ddqa",
        executable="ddqa",
    )

    manifest = exe.to_file_manifest(".")
    bundle.add_macos_file(manifest.get_file("ddqa"))
    manifest.remove("ddqa")
    bundle.add_resources_manifest(manifest)

    return bundle

register_target("exe", make_exe)
register_target("resources", make_embedded_resources, depends=["exe"], default_build_script=True)
register_target("install", make_install, depends=["exe"], default=True)
register_target("msi", make_msi, depends=["exe"])
register_target("macos_app_bundle", make_macos_app_bundle, depends=["exe"])

resolve_targets()
