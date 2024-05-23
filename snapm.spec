%global summary A set of tools for managing snapshots
%global sphinx_docs 1

Name:		snapm
Version:	0.2.0
Release:	1%{?dist}
Summary:	%{summary}

License:	GPL-2.0-only
URL:		https://github.com/snapshotmanager/snapm
Source0:	snapm-%{version}.tar.gz

BuildArch:	noarch

BuildRequires:	make
BuildRequires:	python3-setuptools
BuildRequires:	python3-devel
%if 0%{?sphinx_docs}
BuildRequires:	python3-sphinx
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
* Thu May 23 2024 Bryn M. Reeves <bmr@redhat.com>
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
