================
Extension Points
================

The parser has several available extension points, with more added as the need
arises. Take a look at 
`our outline <https://github.com/18F/atf-eregs/blob/master/eregs_extensions/extensions-outline.rst>`_
of the process for more information about the plugin system in general. Here
we document specific extension points an example uses.


eregs_ns.parser.layers (deprecated)
===================================

List of strings referencing layer classes (generally implementing the 
abstract base class ``regparser.layer.layer:Layer``).

Examples:

* `ATF <https://github.com/18F/atf-eregs/blob/c398e553164cd456d6606a78c7762ad5f9ed665b/eregs_extensions/setup.py#L6-L8>`_

This has been deprecated in favor of layers applicable to specific document
types (see below).


eregs_ns.parser.layer.cfr
=========================

Layer classes (implementing the abstract base class
``regparser.layer.layer:Layer``) which should apply the CFR documents.


eregs_ns.parser.layer.preamble
==============================

Layer classes (implementing the abstract base class
``regparser.layer.layer:Layer``) which should apply the "preamble" documents
(i.e.  proposed rules).


eregs_ns.parser.preprocessors
=============================

List of strings referencing preprocessing classes (generally implementing the
abstract base class
``regparser.tree.xml_parser.preprocessors:PreProcessorBase``).

Examples:

* `ATF <https://github.com/18F/atf-eregs/blob/c398e553164cd456d6606a78c7762ad5f9ed665b/eregs_extensions/setup.py#L9-L11>`_
* `FEC <https://github.com/18F/fec-eregs/blob/88c4d7b0b0ff1aafefd68d393fdbf5f3a5be6f89/eregs_extensions/setup.py#L15-L17>`_

Preprocessors may have a ``plugin_order`` attribute, an integer which defines
the order in which the plugins are executed. Defaults to zero. Sorts
ascending.


eregs_ns.parser.term_definitions
================================

``dict: string->[(string,string)]``: List of phrases which *should* trigger a
definition. Pair is of the form (term, context), where "context" refers to a
substring match for a specific paragraph. e.g.  ("bob", "text noting that it
defines bob").

Examples:

* `ATF <https://github.com/18F/atf-eregs/blob/c398e553164cd456d6606a78c7762ad5f9ed665b/eregs_extensions/setup.py#L15-L17>`_
* `EPA <https://github.com/18F/epa-notice/blob/124c8089cd915394cc9f19074af0e2f3d9daf8b9/eregs_extensions/setup.py#L6-L8>`_
* `FEC <https://github.com/18F/fec-eregs/blob/88c4d7b0b0ff1aafefd68d393fdbf5f3a5be6f89/eregs_extensions/setup.py#L6-L8>`_


eregs_ns.parser.term_ignores
============================

``dict: string->[string]``: List of phrases which shouldn't contain defined
terms. Keyed by CFR part or ``ALL``.

Examples:

* `ATF <https://github.com/18F/atf-eregs/blob/c398e553164cd456d6606a78c7762ad5f9ed665b/eregs_extensions/setup.py#L18-L20>`_
* `FEC <https://github.com/18F/fec-eregs/blob/88c4d7b0b0ff1aafefd68d393fdbf5f3a5be6f89/eregs_extensions/setup.py#L18-L20>`_


eregs_ns.parser.test_suite
==========================

Extra modules to test with the ``eregs full_tests`` command.

Examples:

* `ATF <https://github.com/18F/atf-eregs/blob/c398e553164cd456d6606a78c7762ad5f9ed665b/eregs_extensions/setup.py#L12-L14>`_
* `FEC <https://github.com/18F/fec-eregs/blob/88c4d7b0b0ff1aafefd68d393fdbf5f3a5be6f89/eregs_extensions/setup.py#L12-L14>`_
