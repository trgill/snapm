![Snapm CI](https://github.com/snapshotmanager/snapm/actions/workflows/snapm.yml/badge.svg) [![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/snapshotmanager/snapm)

# Snapm

Snapshot manager (snapm) manages named snapshot sets on Linux systems. Each
snapshot set captures coordinated snapshots across multiple volumes,
representing a consistent point-in-time system state that can be referenced and
managed as a single unit.

## Features

- **Coordinated snapshot sets**: Create coordinated snapshots across
  multiple volumes
- **Bootable snapshots**: Generate boot entries for snapshot boot and
  failsafe revert
- **Multiple backends**: Support for LVM2 (Copy-on-Write and Thin) and
  Stratis
- **Flexible scheduling**: Integration with systemd timers for automated
  snapshot creation with retention policies
- **Size policies**: Flexible snapshot sizing with multiple strategies
- **Plugin architecture**: Extensible design for additional storage
  backends

## Quick Start

### Installation

#### From RPM (Fedora/CentOS/RHEL)

Install from distribution repositories (when available):

```bash
dnf install snapm boom-boot
```

#### Manual Installation

1. Create and activate a virtual environment:

```bash
python3 -m venv --system-site-packages .venv && source .venv/bin/activate
```

2. If ``boom-boot`` is not installed from your distribution's packages, clone
   and install it with ``pip``:

```bash
git clone https://github.com/snapshotmanager/boom-boot.git
cd boom-boot
python3 -m pip install .
```

3. Repeat the process with the ``snapm`` repository:

```bash
git clone https://github.com/snapshotmanager/snapm.git
cd snapm
python3 -m pip install .
```

### Basic Usage

#### Create a bootable snapshot set

Create a snapshot set named "before-upgrade" of root and home,
with snapshot boot and revert boot entries:

```bash
snapm snapset create --bootable --revert before-upgrade / /home
```

#### List snapshot sets

```bash
snapm snapset list
```

Show detailed information:

```bash
snapm snapset show before-upgrade
```

#### Boot into a snapshot

- Reboot and select the snapshot boot entry from the GRUB menu
- Entry will be named: "Snapshot before-upgrade YYYY-MM-DD HH:MM:SS
(version)"
- Optionally run ``grub2-reboot <title>`` to pre-select snapshot boot
  entry, e.g.:
```bash

grub2-reboot "Snapshot before-upgrade YYYY-MM-DD HH:MM:SS (version)"
```

- Use ``grub-reboot`` instead of ``grub2-reboot`` on Debian and Ubuntu
  systems.

#### Revert to snapshot state

```bash
snapm snapset revert before-upgrade
```

Then reboot into the Revert boot entry.

Note: Reverting destroys the snapshot set (snapshots are merged back into the
origin volumes).

#### Clean up

Delete snapshot set when no longer needed:

```bash
snapm snapset delete before-upgrade
```

### Common Workflows

#### System Updates

Before major system updates:

```bash
snapm snapset create --bootable --revert pre-update / /var
```

If update goes wrong, revert:

```bash
snapm snapset revert pre-update
```

When satisfied with update, clean up:

```bash
snapm snapset delete pre-update
```

#### Development Snapshots

Quick development checkpoint:

```bash
snapm snapset create dev-checkpoint /home /var
```

Continue working...

If needed, revert specific volumes by splitting them into a dedicated snapshot
set first:

```bash
snapm snapset split dev-checkpoint dev-checkpoint-home /home
```

Example output:

```text
SnapsetName:      dev-checkpoint-home
Sources:          /home
NrSnapshots:      1
Time:             2025-08-30 12:44:00
UUID:             ee82269f-8c78-5814-b47a-b9be31bcebb5
Status:           Inactive
Autoactivate:     no
Bootable:         no
```

```bash
snapm snapset revert dev-checkpoint-home
```

Alternatively revert the entire snapshot set:

```bash
snapm snapset revert dev-checkpoint
```

## Documentation

- **[User Guide](https://snapm.readthedocs.io/en/latest/user_guide.html)** -
  Comprehensive usage documentation
- **[API Documentation](https://snapm.readthedocs.io/en/latest/snapm.html)** -
  Auto-generated API docs
- **[Manual Pages](man/)** - System manual pages

## Requirements

- Linux system with LVM2 or Stratis volumes
- [boom-boot](https://github.com/snapshotmanager/boom-boot)
- Root privileges for performing storage operations
- Python 3.9+

## Supported Storage Backends

| Backend | Type | Snapshots | Thin Provisioning | Status |
|---------|------|-----------|-------------------|--------|
| LVM2 | Copy-on-Write | ✓ | ✗ | Stable |
| LVM2 Thin | Thin Pools | ✓ | ✓ | Stable |
| Stratis | Thin Pools | ✓ | ✓ | Stable |

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md)
for guidelines.

## Support

- [GitHub Issue Tracker](https://github.com/snapshotmanager/snapm/issues)
- [User Guide](https://snapm.readthedocs.io/en/latest/user_guide.html)
- [API Docs](https://snapm.readthedocs.io/en/latest/snapm.html)

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

## Related Projects

- [boom](https://github.com/snapshotmanager/boom) - Boot manager for
  Linux snapshot boot
- [stratis-cli](https://github.com/stratis-storage/stratis-cli) -
  Command-line tool for Stratis storage
- [lvm2](https://gitlab.com/lvmteam/lvm2) - The LVM2 logical volume manager
