Command Line Usage
==================

Assuming you have installed ``regparser`` via ``pip`` (either directly or
indirectly via the requirements file), you should have access to the ``eregs``
program from the command line.

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

Pipeline and its Components
---------------------------

The primary interface to the parser is the ``pipeline`` command, which pulls
down all of the information needed to process a single regulation, parses it,
and outputs the result in the requested format. The ``pipeline`` command gets
its name from its operation -- it effectively pulls in data and sends it
through a "pipeline" of other commands, executing each in sequence. Each of
these other commands can be executed independently, particularly useful if you
are modifying the parser's workings.

* ``versions`` - Pull down and process a list of "versions" for a regulation,
  i.e. identifiers for when the regulation changed over time. This is a
  critical step as almost every other command uses this list of versions as a
  starting point for determining what work needs to be done. Each version has
  a specific identifier (referred to as the ``version_id`` or
  ``document_number``) and effective date. These versions are generally
  associated with a Final Rule from the Federal Register. The process takes
  into account modifications to the effective dates by later rules. Output is
  in the index's ``version`` directory.
* ``annual_editions`` - Regulations are published once a year (technically, in
  batches, with a quarter published every three months). This command pulls
  down those annual editions of the regulation and associates the parsed
  output with the most recent version id. If multiple versions are effective
  in a single year, the last will be used (mod details around quarters.)
  Output is in the index's ``tree`` directory.
* ``fill_with_rules`` - If multiple versions of a regulation are effective in
  a single year, or if the annual edition has not been published yet, the
  parser will attempt to derive the changes from the Final Rules. Though
  fraught with error, this process is attempted for any versions which do not
  have an associated annual edition. The term "fill" comes from "filling" the
  gaps in the history of the regulation tree. Output is in the index's
  ``tree`` directory.
* ``layers`` - Now that the regulation's core content has been parsed, attempt
  to derive "layers" of additional data, such as internal citations,
  definitions, etc. Output is in the index's ``layer`` directory.
* ``diffs`` - The completed trees also allow the parser to compute the
  differences between trees. These data structures are created with this
  command, which saves its output in the index's ``diff`` directory.
* ``write_to`` - Once everything has been processed, we will want to send our
  results somewhere. If the final parameter begins with ``http://`` or
  ``https://``, the parser will send the results as JSON to an HTTP API. If
  the final parameter begins with ``git://``, the results will be serialized
  into a ``git`` repository and saved to the provided location. All other
  values are interpreted as a directory on disk; the output will be serialized
  to disk as JSON.

Many of the above commands depend on more fundamental commands, particularly
commands to pull down and preprocess XML from the Federal Register and GPO.
These commands are automatically called to fulfill dependencies generated by
the above commands, but can also be executed separately. This is particularly
useful if you need to re-import modified data.

* ``preprocess_notice`` - Given a final rule's document number, find the
  relevant XML (on disk or from the Federal Register), run it through a few
  preprocessing steps and save the results into the index's ``notice_xml``
  directory.
* ``fetch_annual_edition`` - Given identifiers for which regulation and year,
  pull down the relevant XML, run it through the same preprocessing steps, and
  store the result into the index's ``annual`` directory.
* ``parse_rule_changes`` - Given a final rule's document number, convert the
  relevant XML file into a representation of the amendments, i.e. the
  instructions describing how the regulations is changing. Output stored in
  the index's ``rule_changes`` directory.
* ``fetch_sxs`` - Find and parse the "Section-by-Section Analyses" which are
  present in final rule associated with the provided document number. These
  are used to generate the SxS layer. Results stored in the index's ``sxs``
  directory.

Tools
-----

* ``clear`` - Removes content from the index. Useful if you have tweaked the
  parser's workings. Additional parameters can describe specific directories
  you would like to remove.
* ``compare_to`` - This command compares a set of local JSON files with a
  known copy, as stored in an instance of ``regulations-core`` (the API). The
  command will compare the requested JSON files and provide an interface for
  seeing the differences, if present.
