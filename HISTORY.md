# History

-----

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## 0.4.0 - 2023-06-21

***Added:***

- Upgrade PyApp to 0.9.0
- Build for PowerPC

## 0.3.1 - 2023-06-02

***Fixed:***

- Fix race condition when prematurely creating issues

## 0.3.0 - 2023-05-24

***Added:***

- Upgrade Textual to 0.20.1
- Upgrade PyApp to 0.7.0

## 0.2.0 - 2023-05-17

***Changed:***

- Remove vendored `pyperclip` dependency and the `--copy` flag of the `config find` command

***Fixed:***

- Changed the priority of member assignment to be based on the number of currently assigned issues followed by whether or not the member was a reviewer
- Properly handle Git SSH remote URLs

## 0.1.0 - 2023-04-15

This is the initial public release.
