Command Line Usage
==================

Assuming you have installed ``regparser`` via ``pip`` (either directly or
indirectly via the requirements file), you should have access to the ``eregs``
program from the command line. If, for whatever reason, you do not, you can
still access its functionality by using ``python eregs.py`` in place of
``eregs`` in all of the following commands.

This interface is a wrapper around our various subcommands. For a list of all
available commands, simply execute ``eregs`` without any parameters. This will
also provide a brief description of the subcommand's purpose. To learn more,
about each command's usage, run::

  eregs <subcommand> --help

The Shared Index
----------------

Most of the subcommands make use of a shared index, or database, of partial
computations. For example, rather than downloading and transforming XML files
representing annual editions of a regulation with each run, the computation
will be performed once and then stored within the index. All of these files
are stored in the ``.eregs_index`` directory and can be safely deleted.

Further, these partial computations can depend on each other in the sense that
one may be an essential input into another. When an "earlier" file (i.e. a
dependency) is updated, it invalidates all of the partial computations which
depended on it, which must now be re-built. The ``eregs`` command has logic to
resolve missing or out-of-date dependencies automatically, by executing the
appropriate subcommand which will update the necessary files.

The shared index allows computations to be built incrementally, as new data
(e.g. a new final rule or annual edition) does not force all other versions of
the regulation to be rebuilt. Moreover, by using this sort of shared database,
we make no direct dependencies between commands. The command to generate
"layer" data need not be aware if the depending regulation trees were
generated from annual editions of the regulation, final rules, or something
else.

The major caveat to this approach is that, if you are looking to change how
the parser works, you will likely want it to re-compute specific data rather
than relying on previous runs. This means you will need to ``clear`` the
appropriate data to trigger rebuilds.

Shared Index Data
-----------------

Here we document some of the file types within the shared index, so you know
what needs to be cleared when editing the parser.

* ``annual`` - Transformed XML corresponding to the annual edition of
  regulations. This might need to be cleared if working on the XML transforms
  in ``regparser.notice.preprocessors``
* ``diff`` - Structures representing Diffs between regulation trees. This
  most likely needs to be cleared if working on diff-computing code
  (``regparser.diff``)
* ``layer`` - These represent Layer data, with one file per regulation +
  version + layer type combination. These can be surgically removed depending
  on which ``regparser.layer`` has been edited
* ``notice_xml`` - Transformed XML corresponding to notices/final rules. These
  may need to be removed if working on the XML transforms in
  ``regparser.notice.preprocessors``
* ``rule_changes`` - These structures are derived from the final rules in
  ``notice_xml`` and represent the set of amendments made for a regulation in
  that notice. These might need to be cleared if modifying any of the
  tree-building code (``regparser.tree``) or any amendment processing
  functions (in ``regparser.notice``)
* ``sxs`` - A specific data representation for section-by-section analyses.
  These might need to be removed if modifying how SxS or notices more broadly
  are built (``regparser.notice``)
* ``tree`` - These represent the (whole) regulation at each version. Edits to
  tree-building code (notably ``regparser.tree``) should lead you to remove
  these files.
* ``version`` - Each file here represents the dates and version identifier
  associated with each version of a regulation. These may need to be removed
  if working on the code which determines the order of regulation versions,
  delays between versions, etc. (mostly in ``regparser.notice``)
