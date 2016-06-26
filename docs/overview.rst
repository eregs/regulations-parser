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

Python 2.7, 3.3, 3.4, 3.5. See ``requirements.txt`` and similar for specific
library versions.
