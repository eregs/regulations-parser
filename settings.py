from regparser import plugins

META = {}

#   All current, US CFR titles
CFR_TITLES = [
    None,
    "General Provisions",
    "Grants and Agreements",
    "The President",
    "Accounts",
    "Administrative Personnel",
    "Domestic Security",
    "Agriculture",
    "Aliens and Nationality",
    "Animals and Animal Products",
    "Energy",
    "Federal Elections",
    "Banks and Banking",
    "Business Credit and Assistance",
    "Aeronautics and Space",
    "Commerce and Foreign Trade",
    "Commercial Practices",
    "Commodity and Securities Exchanges",
    "Conservation of Power and Water Resources",
    "Customs Duties",
    "Employees' Benefits",
    "Food and Drugs",
    "Foreign Relations",
    "Highways",
    "Housing and Urban Development",
    "Indians",
    "Internal Revenue",
    "Alcohol, Tobacco Products and Firearms",
    "Judicial Administration",
    "Labor",
    "Mineral Resources",
    "Money and Finance: Treasury",
    "National Defense",
    "Navigation and Navigable Waters",
    "Education",
    "Panama Canal [Reserved]",
    "Parks, Forests, and Public Property",
    "Patents, Trademarks, and Copyrights",
    "Pensions, Bonuses, and Veterans' Relief",
    "Postal Service",
    "Protection of Environment",
    "Public Contracts and Property Management",
    "Public Health",
    "Public Lands: Interior",
    "Emergency Management and Assistance",
    "Public Welfare",
    "Shipping",
    "Telecommunication",
    "Federal Acquisition Regulations System",
    "Transportation",
    "Wildlife and Fisheries",
]

DEFAULT_IMAGE_URL = (
    'https://s3.amazonaws.com/images.federalregister.gov/' +
    '%s/original.gif')

# dict: string->[string]: List of phrases which shouldn't contain defined
# terms. Keyed by CFR part or 'ALL'.
IGNORE_DEFINITIONS_IN = plugins.update_dictionary(
    "eregs_ns.parser.term_ignores", {'ALL': []})

# dict: string->[(string,string)]: List of phrases which *should* trigger a
# definition. Pair is of the form (term, context), where "context" refers to a
# substring match for a specific paragraph. e.g.
# ("bob", "text noting that it defines bob")
INCLUDE_DEFINITIONS_IN = plugins.update_dictionary(
    "eregs_ns.parser.term_definitions", {'ALL': []})

# list of modules implementing the __contains__ and __getitem__ methods
OVERRIDES_SOURCES = [
    'regcontent.overrides'
]

# list of iterable[(xpath, replacement-xml)] modules, which will be loaded
# in regparser.content.Macros
MACROS_SOURCES = [
    'regcontent.macros'
]

# In some cases, it is beneficial to tweak the XML the Federal Register
# provides. This setting specifies file paths to look through for local
# versions of their XML. See also XML_REPO below, which is effectively tacked
# on to the end of this list
LOCAL_XML_PATHS = []


# Sometimes appendices provide examples or model forms that include
# labels that we would otherwise recognize as structural to the appendix
# text itself. This specifies those labels to ignore by regulation
# number, appendix, and label.
APPENDIX_IGNORE_SUBHEADER_LABEL = {}

# Refer to a shared collection of modified FR notices
XML_REPO_PREFIX = 'https://raw.githubusercontent.com/eregs/fr-notices/master/'

# A dictionary of agency-specific external citations
# @todo - move ATF citations to an extension
CUSTOM_CITATIONS = {
    "ATF I 5300.1": "https://atf-eregs.apps.cloud.gov/static/atf_eregs/5300_1.pdf",
    "ATF I 5300.2": "https://www.atf.gov/file/58806/download"}

# Regulations.gov settings. The demo key is rate limited by IP; sign up for
# your own key at
# http://regulationsgov.github.io/developers/key/
REGS_GOV_API = 'https://api.data.gov/regulations/v3/'
REGS_GOV_KEY = 'DEMO_KEY'

# These are the host and port for the regparser Django server running the
# administrative UI.
# It's apparently necessary to include the hostname and post in settings
# because the information in the HTTP request can be spoofed.
# For development, override these in ``local_settings.py``.
CANONICAL_HOSTNAME = "https://example.com"
CANONICAL_PORT = ""

# The URL for the regulations-site API that parser commands invoked from the
# web API/UI should run against:
EREGS_SITE_API_URL = "http://localhost:1234/api/"

try:
    from local_settings import *
except ImportError:
    pass
