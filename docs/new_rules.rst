=================
Parsing New Rules
=================
Regulations are published, in full, annually; we rely on these annual editions
to "synchronize" entire CFR parts. This works well when looking at the history
of a regulation assuming that it has at most one change per year. When
multiple final rules affect a single CFR part in a single year and when a
`new` final rule has been issued, we don't have access to a canonical, entire
regulation. To account for these situations, we have a parser for final rules,
which attempts to figure out what section/paragraphs/etc. are changing and
apply those changes to the previous version of the regulation to derive a new
version.

Unfortunately, the changes are not encoded in a machine readable format, so
the parser makes a best-effort, but tends to fall a bit short. In this
document, we'll discuss what to expect from the parser and how to resolve
common difficulties.

Fetching the Rule
=================
Running the ``pipeline`` command will generally pull down and attempt to parse
the relevant annual editions and final rules. It caches its results for a few
days, so if a rule has only recently hit the Federal Register, you may need to
run::

  eregs clear

After running ``pipeline``, you should see a version associated with the new
rule in your output. If not, verify that the final rule is present on the
`Federal Register <https://www.federalregister.gov/>`_ (our source of final
rules). Looking in the right-hand column, you should find meta data associated
with the final rule's publication date, effective date, entry type (must be
"Rule"), and CFR references. If one of those fields is not present and you
believe this to be in error, file a ticket on federalregister.gov's
`support <http://federalregister.tenderapp.com/>`_ page.

It's possible that running the ``pipeline`` causes an error. If you are
familiar with Python, try running ``eregs --debug pipeline`` with the same
parameters to get additional debugging output and to drop into a debugger at
the point of error. Please
`file an issue <https://github.com/18F/regulations-parser/issues/new>`_ and we
will see if we can recreate the problem.

Viewing the Diff
================
Generally, eRegs will be able to create an appropriate version, but `won't`
have found all of the appropriate changes. To make the verification process a
bit easier, send the output to an instance of eRegs' UI. You can navigate to
the "diff" view and compare the new rule to the previous version; the UI will
highlight sections with changed text and tell you where `it` thinks changes
have occurred. Open this view in conjunction with the text of the final rule
and verify that the appropriate changes have been made.

We can also view more raw output representing the changes by investigating the
output associated with ``notices``. Run ``pipeline`` and send the results to a
part of the file system, e.g.::

  eregs pipeline 11 222 /tmp/eregs-output

and then inspect the ``/tmp/eregs-output/notice`` directory for a JSON file
corresponding to the new rule. This data structure will contain keys
associated with ``amendments`` (describing `how` the regulation is changing)
and ``changes`` (describing the `content` of those changes).

Editing the Rule
================
Odds are that the parser did `not` pick up all of the changes present in the
final rule. We can tweak the text of the rule to match align with the parser's
expectations.

File Location
-------------
For initial edits, it'll make sense to modify the files directly within the
index. These edits will trigger a rebuild on successive ``pipeline`` runs, but
will be erased should the ``clear`` command ever be executed. To test out
minor edits, modify the appropriate file in ``.eregs_index/notice_xml``.

Once you would like to make those changes more permanent, we recommend you
fork and checkout our shared notice-xml
`repository <https://github.com/eregs/fr-notices>`_. Copy the final rule's XML
(attainable via the "Dev" link from the Federal Register's UI) into a
directory matching the structure.

For example, final rule
`2014-18842
<https://www.federalregister.gov/articles/2014/08/11/2014-18842/technical-amendments-to-regulations>`_ is represented by this XML: https://www.federalregister.gov/articles/xml/201/418/842.xml. To modify that, we'd save that XML file into ``fr-notices/articles/xml/201/418/842.xml``.

We recommend committing this file in its original form to make it easy for
future developers to understand what's changed. In any event, you'll need to
inform the parser to look for your new file. To do so,

.. code-block:: bash

  eregs clear   # remove the downloaded reference
  echo 'LOCAL_XML_PATHS = ["path/to/fr-notices/"]' >> local_settings.py

Then re-run pipeline. This will alert the parser of the file's presence. You
will only need to re-run the ``pipeline`` command on successive edits.

When all is said and done, we request you make a pull request to the shared
``fr-notices`` repository, which gets downloaded automatically by the parser.

Amendments
----------
The complications around final rules arise largely from the amendment
instructions (indicated by the ``AMDPAR`` tags in the XML). Unfortunately, we
must attempt to parse these instructions, lest we will not know if paragraphs
have been deleted, moved, etc. The ``AMDParsing`` logic attempts to find
appropriate verbs ("revise", "correct", "add", "remove", "reserve",
"designate", etc.) and the paragraphs associated with those actions. So, the
parser would understand an amendment like::

  Section 1026.35 is amended by revising paragraph (b) introductory text,
  adding new paragraph (b)(2), and removing paragraph (c).

In particular, it'd parse out as something like::

  Context: 1026.35
  Verb(PUT): amended, revising
  Paragraph: 1026.35(b) introductory text
  Verb(POST): adding
  Paragraph: 1026.35(b)(2)
  Verb(DELETE): removing
  Paragraph: 1026.35(c)

We do not currently recognize concepts such as distinct sentences or specific
words within a paragraph, so amendment instructions to "amend the fifth
sentence" or "remove the last semicolon" cannot be understood. In these
situations, it makes more sense to replace the text with something along the
likes of "revise paragraph (b)" and include the entirety of the paragraph
(rather than the single sentence, etc.).

We have also constructed two "artificial" amendment instructions to make
this process easier.

* ``[insert-in-order]`` acts as a verb, indicating that the paragraph should
  be inserted in `textual` order (rather than by looking at the paragraph
  marker). This is particularly useful for modifications to definitions (which
  often do not contain paragraph markers).
* ``[label:111-22-c]`` acts as a very well defined paragraph. We can
  specifically target `any` paragraph this way for modification. Certain
  paragraphs are best defined by a specific keyterm or definition associated
  with them (rather than a paragraph marker). In these scenarios, we have a
  special syntax: ``[label:111-22-keyterm(Special Term Here)]``
