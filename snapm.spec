%global summary A set of tools for managing snapshots
%global sphinx_docs 1

Name:		snapm
Version:	0.1.0
Release:	1
Summary:	%{summary}

License:	GPL-2.0-only
URL:		https://github.com/snapshotmanager/snapm
Source0:	snapm-0.1.0.tar.gz

BuildArch:	noarch

BuildRequires:	make
BuildRequires:	python3-setuptools
BuildRequires:	python3-devel
%if 0%{?sphinx_docs}
BuildRequires:	python3-sphinx
%endif

Requires: python3-snapm = %{version}-%{release}

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
%autosetup -p1 -n snapm-0.1.0

%build
%if 0%{?sphinx_docs}
make -C doc html
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
%{python3_sitelib}/*
%doc doc
%doc tests

%changelog
* Fri Nov 17 2023 Bryn M. Reeves <bmr@redhat.com> - 0.1.0
- Initial spec file for packaging
