Overview
========

Features
--------
* Split regulation into paragraph-level chunks
* Create a tree which defines the hierarchical relationship between these
  chunks
* Layer for external citations -- links to Acts, Public Law, etc.
* Layer for graphics -- converting image references into federal register
  URLs
* Layer for internal citations -- links between parts of this regulation
* Layer for interpretations -- connecting regulation text to the
  interpretations associated with it
* Layer for key terms -- pseudo headers for certain paragraphs
* Layer for meta info -- custom data (some pulled from federal notices)
* Layer for paragraph markers -- specifying where the initial paragraph
  marker begins and ends for each paragraph
* Layer for section-by-section analysis -- associated analyses (from FR
  notices) with the text they are analyzing
* Layer for table of contents -- a listing of headers
* Layer for terms -- defined terms, including their scope
* Layer for additional formatting, including tables, "notes", code blocks,
  and subscripts
* Build whole versions of the regulation from the changes found in final
  rules
* Create diffs between these versions of the regulations

Requirements
------------

* Python (2.7)
* lxml (3.2.0) - Used to parse out information XML from the federal register
* pyparsing (1.5.7) - Used to do generic parsing on the plain text
* inflection (0.1.2) - Helps determine pluralization (for terms layer)
* requests (1.2.3) - Client library for writing output to an API
* requests_cache (0.4.4) - *Optional* - Library for caching request results
  (speeds up rebuilding regulations)
* GitPython (0.3.2.RC1) - Allows the regulation to be written as a git repo
* python-constraint (1.2) - Used to determine paragraph depth

If running tests:

* nose (1.2.1) - A pluggable test runner
* mock (1.0.1) - Makes constructing mock objects/functions easy
* coverage (3.6) - Reports on test coverage
* cov-core (1.7) - Needed by coverage
* nose-cov (1.6) - Connects nose to coverage

