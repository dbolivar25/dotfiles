# UV: A Modern Python Package Manager

## Overview

UV is a high-performance Python package manager and project tool written in
Rust, designed as a modern alternative to traditional tools in the Python
ecosystem. Developed by Astral (the same team behind the popular Ruff linter),
UV serves as a drop-in replacement for traditional Python package management
tools like pip, offering significant improvements in speed, reliability, and
dependency resolution. UV aims to be "a single tool to replace pip, pip-tools,
pipx, poetry, pyenv, twine, virtualenv, and more."

## Key Features

### Performance

UV's most notable feature is its speed - benchmarks show it's 10-100 times
faster than traditional package managers like pip. The significant performance
improvements come from efficient cache design, smart downloading of package
metadata, and other optimizations.

### Virtual Environment Management

UV includes built-in virtual environment management that's compatible with other
tools. When you run `uv add` for the first time in a project, it automatically
creates a virtual environment and manages it for you. This creates a streamlined
workflow for Python development compared to using separate tools.

### Python Version Management

UV can manage Python installations directly, allowing you to install specific
Python versions on demand. Support for this feature is currently in preview, but
allows for automatic downloading of Python versions when required. You can pin
specific Python versions for projects with commands like `uv python pin 3.11`.

### Dependency Management

UV supports everything expected from a modern Python packaging tool: editable
installs, Git dependencies, URL dependencies, local dependencies, constraint
files, source distributions, custom indexes, and more. It also offers advanced
features like alternate resolution strategies (including `--resolution=lowest`
for testing against lowest-compatible dependency versions) and the ability to
resolve dependencies against arbitrary target Python versions with the
`--python-version` parameter.

## Command Usage

### Basic Commands

- **Create a virtual environment**: `uv venv`
- **Install a package**: `uv pip install <package>`
- **Install from requirements.txt**: `uv pip install -r requirements.txt`
- **Compile dependencies**: `uv pip compile`
- **Sync dependencies**: `uv pip sync requirements.txt`
- **Specify Python version**: `uv venv --python 3.12.0`
- **Pin Python version**: `uv python pin 3.11`

### Project Initialization

You can initialize a new project with UV by running a command that creates the
necessary structure to manage Python dependencies, including a pyproject.toml
configuration file.

## Compatibility

UV is designed as a drop-in replacement for pip and pip-tools, providing
compatibility with existing workflows while delivering significant performance
improvements. However, it does not support some legacy features like .egg
distributions, and its requirements.txt files may not be portable across all
platforms and Python versions (unlike poetry.lock or pdm.lock files which are
platform-agnostic).

## Comparison with Other Tools

### vs. pip

Compared to pip, UV is significantly faster and addresses issues like dependency
smells and low success rates of inference when restoring runtime environments.

### vs. Poetry

Both UV and Poetry handle package dependencies, project structure, lock files,
and package publishing effectively. However, UV's main advantage is its
blazing-fast speed due to its Rust implementation.

### vs. Conda

While Conda excels at managing non-Python packages, UV provides better
performance and compatibility with the Python ecosystem.

## Current Status and Future

UV represents an intermediary milestone in Astral's pursuit of a "Cargo for
Python": a unified Python package and project manager that is extremely fast,
reliable, and easy to use. The developers are working on standardizing parts of
UV via PEPs (Python Enhancement Proposals).

## Installation

UV is available for Linux, Windows, and macOS. For detailed installation
instructions, visit the [official documentation](https://docs.astral.sh/uv/).
