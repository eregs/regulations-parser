from setuptools import find_packages, setup

setup(
    name='interpparser',
    version="0.0.1",
    packages=find_packages(),
    classifiers=[
        'License :: Public Domain',
        'License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication'
    ],
    entry_points={
        'eregs_ns.parser.amendment.content':
            ('interpretations = '
             'interpparser.amendments:content_for_interpretations'),
        'eregs_ns.parser.layer.cfr':
            'interpretations = interpparser.layers:Interpretations',
        'eregs_ns.parser.preprocessors': [
            'supplement-amdpar = interpparser.preprocessors:supplement_amdpar',
            ('appendix-to-interp = interpparser.preprocessors:'
             'appendix_to_interp'),
            ],
        "eregs_ns.parser.xml_matchers.gpo_cfr.PART": [
            "interpretations = interpparser.gpo_cfr:parse_interp",
            ]
    }
)
