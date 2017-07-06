from setuptools import find_packages, setup

setup(
    name="regparser",
    version="4.3.1",
    packages=find_packages(),
    classifiers=[
        'License :: Public Domain',
        'License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication'
    ],
    install_requires=[
        "attrs",
        "cached-property",
        "click",
        "coloredLogs",
        "django",
        "dj-database-url",
        "django-click",
        "django_rq",
        "djangorestframework",
        "GitPython",
        "inflection",
        "ipdb",
        "json-delta",
        "lxml",
        "networkx",
        "pyparsing",
        "python-constraint",
        "requests",
        "requests-cache",
        "roman",
        "six",
        "stevedore"
    ],
    dependency_links=[
        "http://github.com/python-constraint/python-constraint/"
        "archive/1.3.1.tar.gz#egg=python-constraint",
    ],
    entry_points={
        "console_scripts": "eregs=regparser.web.management.runner:eregs",
        "eregs_ns.parser.amendment.content": [
            ("new_subpart = regparser.notice.amendments.subpart:"
             "content_for_new_subpart"),
            ("regtext = regparser.notice.amendments.section:"
             "content_for_regtext"),
            ("appendix = regparser.notice.amendments.appendix:"
             "content_for_appendix"),
        ],
        "eregs_ns.parser.layer.cfr": [
            "meta = regparser.layer.meta:Meta",
            ("internal-citations = regparser.layer.internal_citations:"
             "InternalCitationParser"),
            "toc = regparser.layer.table_of_contents:TableOfContentsLayer",
            "terms = regparser.layer.terms:Terms",
            ("paragraph-markers = regparser.layer.paragraph_markers:"
             "ParagraphMarkers"),
            "keyterms = regparser.layer.key_terms:KeyTerms",
            ("external-citations = regparser.layer.external_citations:"
             "ExternalCitationParser"),
            "formatting = regparser.layer.formatting:Formatting",
            "graphics = regparser.layer.graphics:Graphics",
        ],
        "eregs_ns.parser.layer.preamble": [
            "keyterms = regparser.layer.preamble.key_terms:KeyTerms",
            ("internal-citations = regparser.layer.preamble."
             "internal_citations:InternalCitations"),
            ("paragraph-markers = regparser.layer.preamble.paragraph_markers:"
             "ParagraphMarkers"),
            ("external-citations = regparser.layer.external_citations:"
             "ExternalCitationParser"),
            "formatting = regparser.layer.formatting:Formatting",
            "graphics = regparser.layer.graphics:Graphics",
        ],
        "eregs_ns.parser.preprocessors": [
            ("move-last-amdpar = regparser.tree.xml_parser.preprocessors:"
             "move_last_amdpar"),
            ("parentheses-cleanup = regparser.tree.xml_parser.preprocessors:"
             "parentheses_cleanup"),
            ("move-adjoining-chars = regparser.tree.xml_parser.preprocessors:"
             "move_adjoining_chars"),
            ("approvals-fp = regparser.tree.xml_parser.preprocessors:"
             "ApprovalsFP"),
            ("extract-tags = regparser.tree.xml_parser.preprocessors:"
             "ExtractTags"),
            "footnotes = regparser.tree.xml_parser.preprocessors:Footnotes",
            ("parse-amdpars = regparser.tree.xml_parser.preprocessors:"
             "preprocess_amdpars"),
            "atf-i-50032 = regparser.tree.xml_parser.preprocessors:atf_i50032",
            "atf-i-50031 = regparser.tree.xml_parser.preprocessors:atf_i50031",
            ("atf-import-categories = regparser.tree.xml_parser.preprocessors:"
             "ImportCategories"),
            ("promote-nested-subjgrp = regparser.tree.xml_parser."
             "preprocessors:promote_nested_subjgrp"),
            ("promote-nested-appendix = regparser.tree.xml_parser."
             "preprocessors:promote_nested_appendix"),
            ("move-subpart-into-contents = regparser.tree.xml_parser."
             "preprocessors:move_subpart_into_contents"),
        ],
        "eregs_ns.parser.xml_matchers.gpo_cfr.PART": [
            "empty-part = regparser.tree.gpo_cfr.section:ParseEmptyPart",
            "subpart = regparser.tree.gpo_cfr.subpart:parse_subpart",
            "subjgrp = regparser.tree.gpo_cfr.subpart:ParseSubjectGroup",
            "appendix = regparser.tree.gpo_cfr.appendices:parse_appendix",
        ]
    }
)
