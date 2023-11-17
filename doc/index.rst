Snapm documentation
===================

Snapshot manager (snapm) is a tool for managing sets of snapshots on Linux
systems.  The snapm tool allows snapshots of multiple volumes to be captured at
the same time, representing the system state at the time the set was created.

The tool has a modular plugin architecture allowing different snapshot backends
to be used together. Currently snapshots using LVM2 copy-on-write and thinly
provisioned snapshots are supported.

Contents:

.. toctree::
   :maxdepth: 2

   snapm
   modules


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

