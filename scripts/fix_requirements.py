from pathlib import Path


def main():
    with Path('requirements.txt').open('a', encoding='utf-8') as f:
        f.write('\nddqa\n')


if __name__ == '__main__':
    main()
