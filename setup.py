from setuptools import setup, find_packages

setup(
    name="regparser",
    version="4.1.0",
    packages=find_packages(),
    classifiers=[
        'License :: Public Domain',
        'License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication'
    ],
    install_requires=[
        "cached-property",
        "click",
        "coloredLogs",
        "Django==1.9.*",
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
    entry_points={"console_scripts": ["eregs=eregs:main"]}
)
