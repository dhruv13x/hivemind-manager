# Hivemind Manager (hm) CLI

`hm` is a developer process manager and supervisor built around `hivemind` for development environments. It dynamically scans, starts, stops, and manages service configurations (`*.hm` files) with automatic dependency resolution.

## Installation

Install in editable mode in your virtual environment:

```bash
pip install -e ~/workspace/tools/hivemind_manager
```

## Dynamic Dependencies

Declare dependencies inside your `*.hm` files using comments:

```bash
# depends_on: infra
```
