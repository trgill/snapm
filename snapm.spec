%global summary A set of tools for managing snapshots
%global sphinx_docs 1

Name:		snapm
Version:	0.3.0
Release:	1%{?dist}
Summary:	%{summary}

License:	GPL-2.0-only
URL:		https://github.com/snapshotmanager/snapm
Source0:	%{url}/archive/v%{version}/%{name}-%{version}.tar.gz

BuildArch:	noarch

BuildRequires:	make
BuildRequires:	python3-setuptools
BuildRequires:	python3-devel
%if 0%{?sphinx_docs}
BuildRequires:	python3-sphinx
BuildRequires:  boom-boot
%endif

Requires: python3-snapm = %{version}-%{release}
Requires: python3-boom

%package -n python3-snapm
Summary: %{summary}
%{?python_provide:%python_provide python3-snapm}
Requires: %{__python3}

%description
Snapshot manager (snapm) is a tool for managing sets of snapshots on Linux
systems.  The snapm tool allows snapshots of multiple volumes to be captured at
the same time, representing the system state at the time the set was created.

%description -n python3-snapm
Snapshot manager (snapm) is a tool for managing sets of snapshots on Linux
systems.  The snapm tool allows snapshots of multiple volumes to be captured at
the same time, representing the system state at the time the set was created.

This package provides the python3 snapm module.

%prep
%autosetup -p1 -n snapm-%{version}

%build
%if 0%{?sphinx_docs}
make %{?_smp_mflags} -C doc html
rm doc/_build/html/.buildinfo
mv doc/_build/html doc/html
rm -r doc/_build
%endif

%py3_build

%install
%py3_install

mkdir -p ${RPM_BUILD_ROOT}/%{_mandir}/man8
install -m 644 man/man8/snapm.8 ${RPM_BUILD_ROOT}/%{_mandir}/man8

rm doc/Makefile
rm doc/conf.py

# Test suite currently does not operate in rpmbuild environment
#%%check
#%%{__python3} setup.py test

%files
%license COPYING
%doc README.md
%{_bindir}/snapm
%doc %{_mandir}/man*/snapm.*

%files -n python3-snapm
%license COPYING
%doc README.md
%{python3_sitelib}/%{name}/*
%{python3_sitelib}/%{name}-*.egg-info/
%doc doc
%doc tests

%changelog
* Thu Jun 20 2023 Bryn M. Reeves <bmr@redhat.com> - 0.3.0
- snapm: forbid revert if snapset status is SnapStatus.INVALID
- dist: add pyproject.toml
- tests: fix boot path in tests/boot/boom/boom.conf
- snapm: check for boom configuration and create if missing
- dist: add dependency on boom-boot >= 1.6.4
- docs: update list of Packit build targets in README.md
- doc: add JSON output options to snapm.8
- doc: add and update command output examples to README.md
- dist: add requirements.txt
- doc: add boom requirement to installation instructions
- snapm: fix plugin list command formatting (black)
- tests: add JSON report output test
- report: fix setting of ReportOpts.json in ReportOpts()
- report: allow sort keys to use optional prefix
- report: handle $PREFIX_all when parsing field list
- tests: fix ReportTests::test_ReportOpts_str() for JSON output
- snapm: add support for JSON reports to list commands
- report: add support for JSON output
- snapm: add snapset_name as a default field for snapshot reports
- report: add title argument to Report()
- report: remove unused 'private' Report argument
- report: fix field prefix handling and drop hardcoded snapshot_ prefix
- report: fix comment typos
- dist: add BuildRequires for boom-boot to snapm.spec
- snapm: don't use match statement for compatibility with py3.9
- dist: build for epel and centos-stream in .packit.yaml
- lvm2: fix unpacking of snapshot name fields in Lvm2Cow
- snapm: add 'plugin' subcommand to display info on available plugins
- snapm: rename snapshot cmd handler fns to better match command line
- doc: describe size policy for non-fixed sized snapshot types in snapm.8
- doc: add default --size-policy to README.md
- doc: describe size checks for non-fixed sized snapshots in README.md
- tests: add command-level size policy tests
- tests: add integration tests with default and per-mount size policy
- lvm2: apply SizePolicy checks to thin volumes
- doc: provide a better description of --nameprefixes in snapm.8
- lvm2: apply name length checks separately for Lvm2Cow/Lvm2Thin
- snapm: check for in-progress revert when creation snapshot sets
- snapm: add Bootable property to sets to indicate if boot configured
- snapm: add missing autoactivate state to SnapshotSet.__str__ and json
- snapm: use Manager.revert_snapset() for 'snapm snapset revert'
- snapm: split Manager.revert_snapset() out from revert_snapsets()
- snapm: warn user to reboot when reverting with an in-use origin
- snapm: add SnapshotSet.origin_mounted and Snapshot.origin_mounted
- snapm: rename local in Manager.rename_snapshot_set() revert->rollback
- snapm: include timestamp in SnapshotSet and Snapshot json
- snapm: handle zero values in snapm.size_fmt()
- snapm: use constants for properties and report fields
- tests: add json property to MockArgs
- snapm: use lists rather than discrete JSON blobs for multi-item output
- snapm: add --json option to snapset and snapshot show commands
- snapm: add .as_dict() and .json() methods to SnapshotSet and Snapshot
- snapm: use constants for SnapshotSet and Snapshot property names
- snapm: improve formatting of Snapset boot entries
- snapm: include kernel version in boot entry titles
- snapm: rename "rollback" to "revert"
- Fix test_auto_profile_create_boot_entry
- snapm: imrpove snapset delete log message
- lvm2: limit maximum name length to max lvm name - 4 (123) for CoW
- snapm: improve error logging in Manager.create_snapshot_set()
- lvm2: check lvm name limits in Lvm2Thin.check_create_snapshot()
- snapm: improve rollback command log message
- snapm: refresh boot cache after operations that may invalidate it
- snapm: delete snapshot boot entry when rolling back snapset
- boot: force root fs to be rw when creating snapshot boot entry
- tests: set correct initramfs and kernel patterns for Ubuntu boom profile
- boot: ensure boom image cache is cleaned when deleting entries
- boot: enable boom image caching when creating boot entries
- doc: update man page date in snapm.8
- doc: add description of booting and rolling back sets to snapm.8
- doc: update examples in snapm.8
- doc: add missing snapset report fields to snapm.8
- doc: fix description of -o|--options in snapm.8
- doc: add break after size policy example in snapm.8
- doc: describe default size policy in snapm.8
- doc: fix create command description in snapm.8
- doc: fix typos in snapm.8 SNAPSHOT SETS AND SNAPSHOTS
- doc: Update valid characters for snapset names in snapm.8
- snapm: use rsplit() to parse size policy from mount spec
- snapm: raise SnapmPluginError in more Manager methods
- snapm: add SnapmPluginError and improve error message on set create
- plugins: escape invalid characters in mount point path
- doc: add size and free snapshot fields to snapm.8
- doc: add autoactivate, bootentry and rollback to report field list
- doc: document --members option in snapm.8 man page
- snapm: fix formatting of _DEFAULT_SNAPSHOT_FIELDS
- snapm: uncouple display snapset members from --verbose
- snapm: don't display extra fields in --verbose reports
- snapm: fix whitespace in snapset/snapshot show subcommands
- snapm: change default snapshot report fields
- doc: add size policies to snapm.8 man page
- snapm: add size and free to string representation of snapshots
- snapm: move size_fmt() from snapm.report to snapm
- snapm: add report fields for size_bytes and free_bytes
- snapm: add Snapshot.free to reflect free space available to snapshots
- snapm.SizePolicy: always return a multiple of sector size
- snapm: improve formatting of capped percentage size policy checks
- snapm: add size field to the snapshot report
- report: add REP_SIZE field type for human readable size strings
- snapm: add a size property to Snapshot
- snapm.SnapshotSet: remove useless class variables
- snapm.Snapshot: remove useless class variables
- snapm: command line support for default size policy
- snapm: support default size policy in Manager.create_snapshot_set()
- snapm: also cap FREE size policies to <=100
- tests: test snapm.is_size_policy()
- lvm2: fix free space accounting for multiple VGs
- tests: add basic tests for SizePolicy class
- doc: add basic documentation for size policies to README.md
- tests: fix ManagerTests::test_create_snapshot_set_no_space_raises
- lvm2: fix free space accounting in Lvm2Cow._check_free_space()
- snapm: cap PERCENT_SIZE policy to 100 of device size
- snapm: fix FREE space accounting
- Add Plugin.{start,end}_transaction()
- Make default SizePolicy 200USED
- snapm: implement size control policies in manager and plugins
- snapm: add size control policy infrastructure
- lvm2: improve error message when snapshot creation fails

* Thu May 30 2024 Bryn M. Reeves <bmr@redhat.com> - 0.2.1
- tests: set boom /boot path explicitly in test_boot
- tests: skip privileged tests if running as non-root user
- tests: use mock /boot directory for command and manager tests
- tests: replace zero-length find targets with dummy files
- Update snapm.spec source to use URL with name and version macros
- Change interpreter to /usr/bin/python3
- Use _smp_mflags make flags in snapm.spec docs build
- Fix use of python3_sitelib wildcard in snapm.spec
- Fix license and classifiers in setup.cfg
- Set boom optional keys defaults if enabled in profile
- Use v4 of checkout action in GitHub workflow

* Mon May 20 2024 Bryn M. Reeves <bmr@redhat.com> - 0.2.0
- Bump release and update .packit.yaml
- Require python3-boom
- Set default boom profile options from /proc/cmdline
- Only pass no_fstab=True if command line mounts are defined
- Set lvm_root_lv when calling boom.create_entry() for LVM volumes
- Broaden exception handling in 'snapm snapset create'
- Set and verify autoactivate when creating bootable snapshot set
- Move autoactivation status change into SnapshotSet class
- tests: skip profile auto-creation test on Ubuntu
- Ignore bandit B101, "assert used"
- tests: add boot integration regression tests
- Add test support to allow users of LvmLoopBacked to create snapshots
- Add LvmLoopBacked.dump_vgs() to assist debugging LVM tests
- Update README.md for --bootable and --rollback
- Document -b|--bootable and -r|--rollback options in man page
- Add boot integration using the boom boot manager
- Add -m to coverage report command to report missing statements
- Combine regular and coverage test runs into a single step
- Add azure boom OsProfile for CI testing hosts
- tests: extend test workflow to install boom
- Fix comment in tests/_util.py
- Add test to assert that SnapmNoSpaceError is raised when VG out of space
- Increase the test loop device size to 12GiB
- Propagate exceptions from Manager.create_snapshot_set()
- Add snapset rollback command to man page and README.md
- Add test for "snapm snapset rollback" command
- Add test for Manager.rollback_snapshot_sets()
- Add infrastructure for roll back tests
- Add snapm snapset rollback command
- Add rollback support to Manager, Snapshot and Plugins
- Move snapm.command._expand_fields()
- Split coverate reporting into a separate task step
- Try to exclude python-dbus modules from CI coverage runs
- Redefine Snapshot.origin and add Snapshot.origin_options property
- Properly calculate minimum unique SHA prefix in reports
- doc: fix man page typo ("columnes")
- manager: add ' ' to the list of forbidden characters for snapset names
- dist: use packages = find: in setup.cfg

* Fri Nov 17 2023 Bryn M. Reeves <bmr@redhat.com> - 0.1.0
- Initial spec file for packaging
