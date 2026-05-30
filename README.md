Hivemind Manager

Hivemind Manager ("hm") is a developer-focused process manager built on top of Hivemind.

It provides service discovery, dependency management, supervision, automatic restarts, log management, and project-aware workflows for local development environments.

Instead of manually managing multiple Hivemind processes, "hm" treats your workspace as a collection of services and provides a unified CLI for operating them.

---

Features

- Automatic discovery of "*.hm" service definitions
- Project-aware workspace detection
- Dependency resolution via "# depends_on:"
- Supervisor process with automatic restart backoff
- PID tracking and process lifecycle management
- Orphaned process cleanup
- Multi-service log management
- Execution-based log rotation
- Project-local configuration via "pyproject.toml"
- Works from any subdirectory inside a project
- Lightweight and Hivemind-compatible

---

Installation

From PyPI

pip install hivemind-manager==0.1.0

From Source

git clone git@github.com:dhruv13x/hivemind-manager.git

cd hivemind-manager

pip install -e .

---

Requirements

- Python 3.8+
- Hivemind installed and available on PATH

Verify installation:

hivemind --version

---

Quick Start

Inside your project:

hm init

This creates a project configuration:

[tool.hm]
home_dir = "hm"
preserve_logs = true
max_log_history = 5
max_log_size_mb = 0

Then start services:

hm up

Check status:

hm ps

Stop everything:

hm down

---

Service Definitions

Services are defined using standard Hivemind files.

Example:

infra.hm

api: uvicorn app.main:app --host 0.0.0.0 --port 8000
worker: python -m app.worker

transfer.hm

# depends_on: infra

transfer_bot: python -m services.transfer_bot.main

---

Dependency Management

Dependencies are declared using comments:

# depends_on: infra

Example:

# depends_on: infra

transfer_bot: python -m services.transfer_bot.main

When starting:

hm start transfer

"hm" automatically starts:

infra
└── transfer

if the dependency is not already running.

---

Project Discovery

"hm" automatically discovers project roots using:

1. "HM_PROJECT_ROOT"
2. "pyproject.toml" containing "[tool.hm]"
3. ".hm" service definitions
4. Current working directory

This means commands work from anywhere inside the project:

cd scripts/dev

hm ps
hm start infra
hm logs transfer

---

Commands

Initialize Project

hm init

Create project configuration and HM workspace.

---

List Services

hm list

Example:

Detected services:

✓ infra
✓ transfer
✓ bypass
✓ uab

---

Show Status

hm ps

Example:

SERVICE         STATUS
----------------------
infra           running
transfer        running
uab             stopped

---

Start Service

hm start infra

Without log following:

hm start infra --no-follow

---

Stop Service

hm stop infra

---

Restart Service

hm restart infra

---

View Logs

hm logs infra

Multiple services:

hm logs infra transfer uab

---

Start All Services

hm up

---

Stop All Services

hm down

---

Diagnostics

hm doctor

Example:

Project Root : /workspace/bot_platform
HM Home      : /workspace/bot_platform/hm
Config File  : /workspace/bot_platform/pyproject.toml
Hivemind Bin : /usr/local/bin/hivemind

---

Log Management

Each service receives:

hm/
├── infra.log
├── infra.log.1
├── infra.log.2
├── infra.pid

Execution-based rotation preserves previous runs:

infra.log      current execution
infra.log.1    previous execution
infra.log.2    older execution

This makes debugging service restarts straightforward.

---

Configuration

Project configuration lives in:

[tool.hm]
home_dir = "hm"
preserve_logs = true
max_log_history = 5
max_log_size_mb = 0

Options

Option| Description
"home_dir"| Directory used for logs and PID files
"preserve_logs"| Preserve previous execution logs
"max_log_history"| Number of historical logs to keep
"max_log_size_mb"| Size-based rotation threshold (0 disables)

---

Environment Variables

Override configuration:

HM_PROJECT_ROOT=/workspace/project
HM_HOME_DIR=/tmp/hm
HM_HIVEMIND_BIN=/usr/local/bin/hivemind

---

Why Hivemind Manager?

Hivemind excels at running processes.

Hivemind Manager adds:

- Service-level supervision
- Dependency resolution
- Project discovery
- Log history
- Process cleanup
- Workspace-aware workflows

without replacing Hivemind itself.

---

License

MIT License

Copyright (c) dhruv13x
