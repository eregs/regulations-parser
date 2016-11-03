==================
Additional Details
==================

Here, we dive a bit deeper into some of the topics around the parser, so
that you may use it in a production setting. We apologize in advance for
somewhat out-of-date documentation.

Parsing Workflow
================

The parser first reads the file passed to it as a parameter and attempts to
parse that into a structured tree of subparts, sections, paragraphs, etc.
Following this, it will make a call to the Federal Register's API,
retrieving a list of final rules (i.e. changes) that apply to this
regulation. It then writes/saves parsed versions of those notices.

If this all worked well, we save the the parsed regulation and then generate
and save all of the layers associated with its version. We then generate
additional whole regulation trees and their associated layers for each
final rule (i.e. each alteration to the regulation).

At the very end, we take all versions of the regulation we've built and
compare each pair (both going forwards and backwards). These diffs are
generated and then written to the API/filesystem/Git.

Output
======

The parser has three options for what it does with the parsed documents it
creates, depending on the protocol it's give in ``write_to``/``pipeline``,
etc.

When no protocol is given (or the ``file://`` protocol is used), all of the
created objects will be pretty-printed as JSON files and stored in subfolders
of the provided path. Spitting out JSON files this way is a good way to track
how tweaks to the parser might have unexpected effects on the output -- just
diff two such directories.

If the protocol is ``http://`` or ``https://``, the output will be written to
an API (running ``regulations-core``) rather than the file system. The same
JSON files are sent to the API as in the above method. This would be the
method used once you are comfortable with the results (by testing the
filesystem output).

A final method, a bit divergent from the other two, is to write the results as
a git repository. To try this, use the ``git://`` protocol, telling the parser
to write the versions of the regulation (*only*; layers, notices, etc. are not
written) as a git history. Each node in the parse tree will be written as a
markdown file, with hierarchical information encoded in directories. This is
an experimental feature, but has a great deal of potential.

Modifying Data
==============

Our sources of data, through human and technical error, often contain
problems for our parser. Over the parser's development, we've created
several not-always-exclusive solutions. We have found that, in most cases,
the easiest fix is to download and edit a *local* version of the problematic
XML. Only if there's some complication in that method should you progress to
the more complex strategies.

All of the paths listed in ``LOCAL_XML_PATHS`` are checked when fetching
regulation notices. The file/directory names in these folders should mirror
those found on federalregister.gov, (e.g. ``articles/xml/201/131/725.xml``).
Any changes you make to these documents (such as correcting XML tags,
rewording amendment paragraphs, etc.) will be used as if they came from the
Federal Register.

In addition, certain notices have `multiple` effective dates, meaning that
different parts of the notice go into effect at different times. This
complication is not handled automatically by the parser. Instead, you must
manually copy the notice into two (or more) versions, such that 503.xml
becomes 503-1.xml, 503-2.xml, etc. Each file must then be *manually*
modified to change the effective date and remove sections that are not
relevant to this date. We sometimes refer to this as "splitting" the notice.

Appendix Parsing
================

The most complicated segments of a regulation are their appendices, at least
from a structural parsing perspective. This is because appendices are
free-form, often with unique variations on sub-sections, headings, paragraph
marker hierarchy, etc. Given all this, the parser does its best to
determine *an* ordering and *a* hierarchy for the subsections/paragraphs
contained within an appendix.

In general, if the parser can find a unique identifier or paragraph marker,
it will note the paragraph/section accordingly. So "Part I: Blah Blah"
becomes 1111-A-I, and "a. Some text" and "(a) Some text)" might become
1111-A-I-a. When the citable value of a paragraph cannot be determined (i.e.
it has no paragraph marker), the paragraph will be assigned a number and
prefaced with "p" (e.g. p1, p2). Similarly, headers become h1, h2, ...

This works out, but had numerous downsides. Most notably, as the citation
for such paragraphs is arbitrary, determining changes to appendices is quite
difficult (often requiring patches). Further, without guidance from
paragraph markers/headers, the parser must make assumptions about the
hierarchy of paragraphs. It currently uses some heuristics, such as headers
indicating a new depth level, but is not always accurate.

Markdown/Plaintext-ifying
=========================

With some exceptions, we treat a plain-text version of the regulation as
canon. By this, we mean that the *words* of the regulation count for much
more than their presentation in the source documents. This allows us to
build better tables of content, export data in more formats, and the other
niceties associated with separating data from presentation.

At points, however, we need to encode non-plain text concepts into the
plain-text regulation. These include displaying images, tables, offsetting
blocks of text, and subscripting. To encode these concepts, we use a
variation of Markdown. 

Images become::

  ![Appendix A9](ER27DE11.000)

Tables become::

  | Header 1 | Header 2|
  ---
  | Cell 1, 1 | Cell 1, 2 |

Subscripts become::

  P_{0}

etc.

Runtime
=======

A quick note of warning: the parser was not optimized for speed. It performs
many actions over and over, which can be **very** slow on very large
regulations (such as CFPB's regulation Z). Further, regulations that have
been amended a great deal cause further slow down, particularly when
generating diffs (currently an n:super:`2` operation). Generally, parsing will
take less than ten minutes, but in the extreme example of reg Z, it currently
requires several hours.

Parsing Error Example
=====================

Let's say you are already in a good steady state, that you can parse the
known versions of a regulation without problem. A new final rule is
published in the federal register affecting your regulation. To make this
concrete, we will use CFPB's regulation Z (12 CFR 1026), final rule
2014-18838.

The first step is to run the parser as we have before. We should configure
it to send output to a local directory (see above). Once it runs, it will
hit the federal register's API and should find the new notice. As described
above, the parser first parses the file you give it, then it heads over to
the federal register API, parses notices and rules found there, and then
proceeds to compile additional versions of the regulation from them. So, as
the parser is running (Z takes a long time), we can check its partial
output. Notably, we can check the ``notice/2014-18838`` JSON file for
accuracy.

In a browser, open https://www.federalregister.gov and search for the notice
in question (you can do this by using the 2014-18838 identifier). Scroll
through the
`page <https://www.federalregister.gov/articles/2014/08/15/2014-18838/truth-in-lending-regulation-z-annual-threshold-adjustments-card-act-hoepa-and-atrqm>`_
to find the list of changes -- they will generally begin with "PART ..." and
be offset from the rest of the text. In a text editor, look at the JSON file
mentioned before.

The JSON file that describes our parsed notice has two relevant fields.
The ``amendments`` field lists what `types` of changes are being made; it
corresponds to AMDPAR tags (for reference). Looking at the web page, you
should be able to map sentences like "Paragraph (b)(1)(ii)(A) and (B) are
revised" to an appropriate PUT/POST/DELETE/etc. entry in the ``amendments``
field. If these do not match up, you know that there's an error parsing the
AMDPARs. You will need to alter the XML for this notice to read how the
parser can understand it. If the logic behind the change is too complicated,
e.g. "remove the third semicolon and replace the fourth sentence", you will
need to add a "patch" (see above).

In this case, the amendment parsing was correct, so we can continue to the
second relevant field. The ``changes`` field includes the ``content`` of
changes made (when adding or editing a paragraph). If all went well you should
be able to relate all of the PUT/POST entries in the ``amendments`` section
with an entry in the ``changes`` field, and the content of that entry should
match the content from the federal register. Note that a single ``amendment``
may include multiple ``changes`` if the amendment is about a paragraph with
children (sub-paragraphs).

Here we hit a problem, and have a few tip-offs. One of the entries in
``amendments`` was not present in the ``changes`` field. Further, one of the
``changes`` entries was something like  "i. \* \* \*". In addition, the
"child_labels" of one of the entries doesn't make sense -- it contains
children which should not be contained. The parser must have skipped over some
relevant information; we could try to deduce further but let's treat the
parser as a black box and see if we can't spot a problem in the web-hosted
rule, first. You see, federalregister.gov uses XSLTs to take the raw XML
(which we parse) to convert it into XHTML. If `we` have a problem, they might
also.

We'll zero in on where we know our problem begins (based on the information
investigating `changes`). We might notice that the text of the problem
section is in italics, while those arround it (other sections which *do*
parse correctly) are not. We might not. In any event, we need to look at the
XML. On the federal register's site, there is a 'DEV' icon in the right
sidebar and an 'XML' link in the modal. We're going to download this XML and
put it where our parser knows to look (see the ``LOCAL_XML_PATHS`` setting).
For example, if this setting is

.. code-block:: python

  LOCAL_XML_PATHS = ['fr-notices/']

we would need to save the XML file to
``fr-notices/articles/xml/201/418/838.xml``, duplicating the directory
structure found on the federal register. I recommend using a git repository
and committing this "clean" version of the notice.

Now, edit the saved XML and jump to our problematic section. Does the XML
structure here match sections we know work? It does not. Our "italic" tip
off above was accurate. The problematic paragraphs are wrapped in ``E`` tags,
which should not be present. Delete them and re-run the parser. You will see
that this fixes our notice.

Generally, this will be the workflow. Something doesn't parse correctly and
you must investigate. Most often, the problems will reside in unexpected XML
structure. AMDPARs, which contain the list of changes may also need to be
simplified. If the same type of change needs to be made for multiple
documents, consider adding a corresponding rule to the parser -- just test
existing docs first.

Integration with regulations-core and regulations-site
======================================================

*TODO* This section is rather out-of-date.

With the above examples, you should have been able to run the parser and
generate some output. "But where's the website?" you ask. The parser was
written to be as generic as possible, but integrating with
``regulations-core`` and ``regulations-site`` is likely where you'll want to
end up. Here, we'll show one way to connect these applications up; see the
individual repos for more configuration detail.

Let's set up ``regulations-core`` first. This is an API which will be used to
both store and query the regulation data.

.. code-block:: bash

  git clone https://github.com/18F/regulations-core.git
  cd regulations-core
  pip install -r requirements.txt  # pulls in python dependencies
  ./bin/django syncdb --migrate
  ./bin/django runserver 127.0.0.1:8888 &   # Starts the API

Then, we can configure the parser to write to this API and run it, here using
the FEC example above

.. code-block:: bash

 cd /path/to/regulations-parser
 echo "API_BASE = 'http://localhost:8888/'" >> local_settings.py
 eregs build_from fec_docs/1997CFR/CFR-1997-title11-vol1-part110.xml 11

Next up, we set up ``regulations-site`` to provide a webapp.

.. code-block:: bash

  git clone https://github.com/18f/regulations-site.git
  cd regulations-site
  pip install -r requirements.txt
  echo "API_BASE = 'http://127.0.0.1:8888/'" >> regulations/settings/local_settings.py
  ./run_server.sh

Then, navigate to http://localhost:8000/ in your browser to see the FEC reg.
