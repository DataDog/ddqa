from pathlib import Path


def main():
    # In order to cross-compile all dependencies must have wheels, see:
    # https://pyoxidizer.readthedocs.io/en/stable/pyoxidizer_packaging_python_files.html#choosing-which-packaging-method-to-call
    # https://github.com/Textualize/textual/pull/2025
    requirements_file = Path('requirements.txt')
    requirements = ['ddqa']

    for line in requirements_file.read_text(encoding='utf-8').splitlines():
        package = line.split('==')[0]
        if package != 'mkdocs-exclude==':
            requirements.append(package)

    requirements_file.write_text('\n'.join(requirements), encoding='utf-8')


if __name__ == '__main__':
    main()
