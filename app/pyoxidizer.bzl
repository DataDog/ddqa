# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
def make_exe():
    # https://gregoryszorc.com/docs/pyoxidizer/main/pyoxidizer_config_type_python_distribution.html#starlark_pyoxidizer.default_python_distribution
    dist = default_python_distribution(python_version = "3.10", flavor="standalone")

    # https://gregoryszorc.com/docs/pyoxidizer/main/pyoxidizer_config_type_python_packaging_policy.html#starlark_pyoxidizer.PythonPackagingPolicy
    policy = dist.make_python_packaging_policy()
    policy.resources_location = "in-memory"
    policy.resources_location_fallback = "filesystem-relative:site-packages"

    # https://gregoryszorc.com/docs/pyoxidizer/main/pyoxidizer_config_type_python_interpreter_config.html#starlark_pyoxidizer.PythonInterpreterConfig
    python_config = dist.make_python_interpreter_config()
    python_config.run_module = "ddqa"
    python_config.sys_frozen = True

    # https://gregoryszorc.com/docs/pyoxidizer/main/pyoxidizer_config_type_python_executable.html#starlark_pyoxidizer.PythonExecutable
    exe = dist.to_python_executable(
        name="ddqa",
        packaging_policy=policy,
        config=python_config,
    )
    exe.add_python_resources(exe.pip_download(["-r", "requirements.txt", "--no-deps"]))

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
    # https://gregoryszorc.com/docs/pyoxidizer/main/tugger_starlark_type_wix_msi_builder.html#starlark_tugger.WiXMSIBuilder
    return exe.to_wix_msi_builder(
        "ddqa",
        "Datadog QA",
        "1.0",
        "Datadog, Inc.",
    )

register_target("exe", make_exe)
register_target("resources", make_embedded_resources, depends=["exe"], default_build_script=True)
register_target("install", make_install, depends=["exe"], default=True)
register_target("msi_installer", make_msi, depends=["exe"])

resolve_targets()
