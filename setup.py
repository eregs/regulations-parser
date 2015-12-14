from setuptools import setup, find_packages

setup(
    name="regparser",
    version="2.0.0",
    packages=find_packages(),
    classifiers=[
        'License :: Public Domain',
        'License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication'
    ],
    install_requires=[
        "click",
        "dagger",
        "GitPython",
        "inflection",
        "ipdb",
        "json-delta",
        "lxml",
        "pyparsing",
        "python-constraint",
        "requests",
        "requests-cache"
    ],
    entry_points={"console_scripts": ["eregs=eregs:main"]}
)
