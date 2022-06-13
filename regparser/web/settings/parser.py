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
LOCAL_XML_PATHS = [
    # 'fr-notices'
]


# Sometimes appendices provide examples or model forms that include
# labels that we would otherwise recognize as structural to the appendix
# text itself. This specifies those labels to ignore by regulation
# number, appendix, and label.
APPENDIX_IGNORE_SUBHEADER_LABEL = {}

# Refer to a shared collection of modified FR notices
XML_REPO_PREFIX = 'https://raw.githubusercontent.com/TimothyAndry/fr-notices/master/'

# A dictionary of agency-specific external citations
# @todo - move ATF citations to an extension
CUSTOM_CITATIONS = {
    "ATF I 5300.1": "https://atf-eregs.apps.cloud.gov/static/atf_eregs/5300_1.pdf",
    "ATF I 5300.2": "https://www.atf.gov/file/58806/download",
    "F 3210.12": "https://www.atf.gov/firearms/docs/form/certification-qualifying-state-relief-atf-e-form-321012",
    "F 3310.11": "https://www.atf.gov/firearms/docs/form/federal-firearms-licensee-theftloss-report-atf-form-331011",
    "F 3310.11A": "https://www.atf.gov/firearms/docs/form/federal-firearms-licensee-firearms-inventory-theftloss-continuation-sheet-atf",
    "F 3310.12": "https://www.atf.gov/firearms/docs/form/report-multiple-sale-or-other-disposition-certain-rifles-atf-form-331012",
    "F 3310.4": "https://www.atf.gov/firearms/docs/form/report-multiple-sale-or-other-disposition-pistols-and-revolvers-atf-form-33104",
    "F 3310.6": "https://www.atf.gov/firearms/docs/form/interstate%C2%A0firearms-shipment-theftloss-report-atf-form-33106",
    "F 3311.4": "https://www.atf.gov/firearms/docs/form/application-alternate-means-identification-firearms-marking-variance-atf-form",
    "F 3312.1": "https://www.atf.gov/firearms/docs/form/national-tracing-center-trace-request-atf-form-33121",
    "F 3312.1 (ES)": "https://www.atf.gov/resource-center/docs/form/solicitud-de-rastreo-del-centro-nacional-de-rastreos-formulario-33121s",
    "F 4590": "https://www.atf.gov/firearms/docs/form/factoring-criteria-weapons-atf-form-4590",
    "F 5000.29": "https://www.atf.gov/resource-center/docs/form/environmental-information-atf-form-500029",
    "F 5000.30": "https://www.atf.gov/resource-center/docs/atf-f-5000-30pdf",
    "F 5070.1": "https://www.atf.gov/alcohol-tobacco/docs/form/prevent-all-cigarette-trafficking-pact-act-registration-form-atf-form",
    "F 5070.1A": "https://www.atf.gov/alcohol-tobacco/docs/form/prevent-all-cigarette-trafficking-pact-act-registration-form-continuation",
    "F 5300.11": "https://www.atf.gov/firearms/docs/form/annual-firearms-manufacturing-and-exportation-report-afmer-atf-form-530011",
    "F 5300.38": "https://www.atf.gov/firearms/docs/form/application-amended-federal-firearms-license-atf-form-530038",
    "F 5300.5": "https://www.atf.gov/firearms/docs/form/report-firearms-transactions-atf-form-53005",
    "F 5300.9": "https://www.atf.gov/firearms/docs/4473-part-1-firearms-transaction-record-over-counter-atf-form-53009",
    "F 5300.9 (ES)": "https://www.atf.gov/firearms/docs/form/4473-registro-de-transacci%C3%B3n-de-armas-de-fuego-formulario-53009-de-la-atf",
    "F 5310.12/F 5310.16": "https://www.atf.gov/firearms/docs/form/form-7-7-cr-application-federal-firearms-license-atf-form-531012531016",
    "Form 7": "https://www.atf.gov/firearms/docs/form/form-7-7-cr-application-federal-firearms-license-atf-form-531012531016",
    "F 5310.12A": "https://www.atf.gov/firearms/docs/form/form-7531012a-7cr531016-responsible-person-questionnaire-supplement-use",
    "F 5320.1": "https://www.atf.gov/firearms/docs/form/form-1-application-make-and-register-firearm-atf-form-53201",
    "Form 1": "https://www.atf.gov/firearms/docs/form/form-1-application-make-and-register-firearm-atf-form-53201",
    "Form 1 (5320.1)": "https://www.atf.gov/firearms/docs/form/form-1-application-make-and-register-firearm-atf-form-53201",
    "F 5320.10": "https://www.atf.gov/firearms/docs/form/form-10-application-registration-firearms-acquired-certain-governmental-entities",
    "Form 10": "https://www.atf.gov/firearms/docs/form/form-10-application-registration-firearms-acquired-certain-governmental-entities",
    "F 5320.2": "https://www.atf.gov/firearms/docs/form/form-2-notice-firearms-manufactured-or-imported-atf-form-53202",
    "Form 2": "https://www.atf.gov/firearms/docs/form/form-2-notice-firearms-manufactured-or-imported-atf-form-53202",
    "F 5320.20": "https://www.atf.gov/firearms/docs/form/application-transport-interstate-or-temporarily-export-certain-nfa-firearms-atf",
    "F 5320.23": "https://www.atf.gov/firearms/docs/form/national-firearms-act-nfa-responsible-person-questionnaire-532023",
    "F 5320.3": "https://www.atf.gov/firearms/docs/form/form-3-application-tax-exempt-transfer-firearm-and-registration-special",
    "Form 3": "https://www.atf.gov/firearms/docs/form/form-3-application-tax-exempt-transfer-firearm-and-registration-special",
    "F 5320.4": "https://www.atf.gov/firearms/docs/form/form-4-application-tax-paid-transfer-and-registration-firearm-atf-form-53204",
    "Form 4": "https://www.atf.gov/firearms/docs/form/form-4-application-tax-paid-transfer-and-registration-firearm-atf-form-53204",
    "F 5320.5": "https://www.atf.gov/firearms/docs/form/form-5-application-tax-exempt-transfer-and-registration-firearm-atf-form-53205",
    "Form 5": "https://www.atf.gov/firearms/docs/form/form-5-application-tax-exempt-transfer-and-registration-firearm-atf-form-53205",
    "F 5320.9": "https://www.atf.gov/firearms/docs/form/form-9-application-and-permit-permanent-exportation-firearms-atf-form-53209",
    "Form 9": "https://www.atf.gov/firearms/docs/form/form-9-application-and-permit-permanent-exportation-firearms-atf-form-53209",
    "F 5330.3A": "https://www.atf.gov/firearms/docs/form/form-6-part-1-application-and-permit-importation-firearms-ammunition-and",
    "Form 6": "https://www.atf.gov/firearms/docs/form/form-6-part-1-application-and-permit-importation-firearms-ammunition-and",
    "F 5330.3B": "https://www.atf.gov/firearms/docs/form/form-6-part-2-application-and-permit-importation-firearms-ammunition-and",
    "F 5330.3C": "https://www.atf.gov/firearms/docs/form/form-6a-release-and-receipt-imported-firearms-ammunition-and-implements-war-atf",
    "Form 6A": "https://www.atf.gov/firearms/docs/form/form-6a-release-and-receipt-imported-firearms-ammunition-and-implements-war-atf",
    "F 5330.3D": "https://www.atf.gov/firearms/docs/form/form-6nia-applicationpermit-temporary-importation-firearms-and-ammunition",
    "Form 6NIA": "https://www.atf.gov/firearms/docs/form/form-6nia-applicationpermit-temporary-importation-firearms-and-ammunition",
    "F 5330.4": "https://www.atf.gov/firearms/docs/form/form-4587-application-register-importer-us-munitions-import-list-articles-atf",
    "F 5400.13" : "https://www.atf.gov/explosives/docs/form/application-explosives-license-or-permit-atf-form-540013540016",
    "F 5400.16": "https://www.atf.gov/explosives/docs/form/application-explosives-license-or-permit-atf-form-540013540016",
    "F 5400.28": "https://www.atf.gov/explosives/docs/form/employee-possessor-questionnaire-atf-form-540028",
    "F 5400.29": "https://www.atf.gov/explosives/docs/form/application-restoration-explosives-privileges-atf-form-540029",
    "F 5400.4": "https://www.atf.gov/explosives/docs/form/limited-permittee-transaction-report-atf-form-54004",
    "F 5400.5": "https://www.atf.gov/explosives/docs/form/report-theftloss-explosive-materials-atf-form-54005",
    "F 5630.7": "https://www.atf.gov/firearms/docs/form/special-tax-registration-and-return-national-firearms-act-atf-form-56307",
    "F 6310.1": "https://www.atf.gov/resource-center/docs/form/arson-and-explosives-training-requests-non-atf-employees-atf-form-63101",
    "F 6330.1": "https://www.atf.gov/resource-center/docs/form/application-national-firearms-examiner-academy-atf-form-63301",
    "F 6400.1": "https://www.atf.gov/resource-center/docs/form/state-and-local-training-registration-request-atf-form-64001",
    "F 7110.15": "https://www.atf.gov/resource-center/docs/form/forensic-firearm-training-request-non-atf-employees-atf-form-711015",
    "F 8620. 42": "https://www.atf.gov/resource-center/docs/form/police-check-inquiry-atf-form-862042",
    "F 8620.65": "https://www.atf.gov/resource-center/docs/form/request-atf-background-investigation-information-atf-form-862065",
    "FD-258": "https://www.fbi.gov/file-repository/identity-history-summary-request-fd-258-110120/view",
    "Form 4473": "https://www.atf.gov/firearms/docs/4473-part-1-firearms-transaction-record-over-counter-atf-form-53009",
    "Department of Defense Form 214": "https://www.archives.gov/veterans/military-service-records",
    "IRS Form SS-4": "https://www.irs.gov/forms-pubs/about-form-ss-4",
    "Department of Defense Form 458": "https://www.esd.whs.mil/directives/forms/",
    "Form 3210.12": "https://www.atf.gov/firearms/docs/form/certification-qualifying-state-relief-atf-e-form-321012",
    "Form 3310.11": "https://www.atf.gov/firearms/docs/form/federal-firearms-licensee-theftloss-report-atf-form-331011",
    "Form 3310.11A": "https://www.atf.gov/firearms/docs/form/federal-firearms-licensee-firearms-inventory-theftloss-continuation-sheet-atf",
    "Form 3310.12": "https://www.atf.gov/firearms/docs/form/report-multiple-sale-or-other-disposition-certain-rifles-atf-form-331012",
    "Form 3310.4": "https://www.atf.gov/firearms/docs/form/report-multiple-sale-or-other-disposition-pistols-and-revolvers-atf-form-33104",
    "Form 3310.6": "https://www.atf.gov/firearms/docs/form/interstate%C2%A0firearms-shipment-theftloss-report-atf-form-33106",
    "Form 3311.4": "https://www.atf.gov/firearms/docs/form/application-alternate-means-identification-firearms-marking-variance-atf-form",
    "Form 3312.1": "https://www.atf.gov/firearms/docs/form/national-tracing-center-trace-request-atf-form-33121",
    "Form 3312.1 (ES)": "https://www.atf.gov/resource-center/docs/form/solicitud-de-rastreo-del-centro-nacional-de-rastreos-formulario-33121s",
    "Form 4590": "https://www.atf.gov/firearms/docs/form/factoring-criteria-weapons-atf-form-4590",
    "Form 5000.29": "https://www.atf.gov/resource-center/docs/form/environmental-information-atf-form-500029",
    "Form 5000.30": "https://www.atf.gov/resource-center/docs/atf-f-5000-30pdf",
    "Form 5070.1": "https://www.atf.gov/alcohol-tobacco/docs/form/prevent-all-cigarette-trafficking-pact-act-registration-form-atf-form",
    "Form 5070.1A": "https://www.atf.gov/alcohol-tobacco/docs/form/prevent-all-cigarette-trafficking-pact-act-registration-form-continuation",
    "Form 5300.11": "https://www.atf.gov/firearms/docs/form/annual-firearms-manufacturing-and-exportation-report-afmer-atf-form-530011",
    "Form 5300.38": "https://www.atf.gov/firearms/docs/form/application-amended-federal-firearms-license-atf-form-530038",
    "Form 5300.5": "https://www.atf.gov/firearms/docs/form/report-firearms-transactions-atf-form-53005",
    "Form 5300.9": "https://www.atf.gov/firearms/docs/4473-part-1-firearms-transaction-record-over-counter-atf-form-53009",
    "Form 4473": "https://www.atf.gov/firearms/docs/4473-part-1-firearms-transaction-record-over-counter-atf-form-53009",
    "Form 5300.9 (ES)": "https://www.atf.gov/firearms/docs/form/4473-registro-de-transacci%C3%B3n-de-armas-de-fuego-formulario-53009-de-la-atf",
    "Form 5310.12": "https://www.atf.gov/firearms/docs/form/form-7-7-cr-application-federal-firearms-license-atf-form-531012531016",
    "Form 5310.16": "https://www.atf.gov/firearms/docs/form/form-7-7-cr-application-federal-firearms-license-atf-form-531012531016",
    "Form 5310.12A": "https://www.atf.gov/firearms/docs/form/form-7531012a-7cr531016-responsible-person-questionnaire-supplement-use",
    "Form 5320.1": "https://www.atf.gov/firearms/docs/form/form-1-application-make-and-register-firearm-atf-form-53201",
    "Form 5320.10": "https://www.atf.gov/firearms/docs/form/form-10-application-registration-firearms-acquired-certain-governmental-entities",
    "Form 5320.2": "https://www.atf.gov/firearms/docs/form/form-2-notice-firearms-manufactured-or-imported-atf-form-53202",
    "Form 5320.20": "https://www.atf.gov/firearms/docs/form/application-transport-interstate-or-temporarily-export-certain-nfa-firearms-atf",
    "Form 5320.23": "https://www.atf.gov/firearms/docs/form/national-firearms-act-nfa-responsible-person-questionnaire-532023",
    "Form 5320.3": "https://www.atf.gov/firearms/docs/form/form-3-application-tax-exempt-transfer-firearm-and-registration-special",
    "Form 5320.4": "https://www.atf.gov/firearms/docs/form/form-4-application-tax-paid-transfer-and-registration-firearm-atf-form-53204",
    "Form 5320.5": "https://www.atf.gov/firearms/docs/form/form-5-application-tax-exempt-transfer-and-registration-firearm-atf-form-53205",
    "Form 5320.9": "https://www.atf.gov/firearms/docs/form/form-9-application-and-permit-permanent-exportation-firearms-atf-form-53209",
    "Form 5330.3A": "https://www.atf.gov/firearms/docs/form/form-6-part-1-application-and-permit-importation-firearms-ammunition-and",
    "Form 5330.3B": "https://www.atf.gov/firearms/docs/form/form-6-part-2-application-and-permit-importation-firearms-ammunition-and",
    "Form 5330.3C": "https://www.atf.gov/firearms/docs/form/form-6a-release-and-receipt-imported-firearms-ammunition-and-implements-war-atf",
    "Form 5330.3D": "https://www.atf.gov/firearms/docs/form/form-6nia-applicationpermit-temporary-importation-firearms-and-ammunition",
    "Form 5330.4": "https://www.atf.gov/firearms/docs/form/form-4587-application-register-importer-us-munitions-import-list-articles-atf",
    "Form 5400.13" : "https://www.atf.gov/explosives/docs/form/application-explosives-license-or-permit-atf-form-540013540016",
    "Form 5400.16": "https://www.atf.gov/explosives/docs/form/application-explosives-license-or-permit-atf-form-540013540016",
    "Form 5400.28": "https://www.atf.gov/explosives/docs/form/employee-possessor-questionnaire-atf-form-540028",
    "Form 5400.29": "https://www.atf.gov/explosives/docs/form/application-restoration-explosives-privileges-atf-form-540029",
    "Form 5400.4": "https://www.atf.gov/explosives/docs/form/limited-permittee-transaction-report-atf-form-54004",
    "Form 5400.5": "https://www.atf.gov/explosives/docs/form/report-theftloss-explosive-materials-atf-form-54005",
    "Form 5630.7": "https://www.atf.gov/firearms/docs/form/special-tax-registration-and-return-national-firearms-act-atf-form-56307",
    "Form 6310.1": "https://www.atf.gov/resource-center/docs/form/arson-and-explosives-training-requests-non-atf-employees-atf-form-63101",
    "Form 6330.1": "https://www.atf.gov/resource-center/docs/form/application-national-firearms-examiner-academy-atf-form-63301",
    "Form 6400.1": "https://www.atf.gov/resource-center/docs/form/state-and-local-training-registration-request-atf-form-64001",
    "Form 7110.15": "https://www.atf.gov/resource-center/docs/form/forensic-firearm-training-request-non-atf-employees-atf-form-711015",
    "Form 8620. 42": "https://www.atf.gov/resource-center/docs/form/police-check-inquiry-atf-form-862042",
    "Form 8620.65": "https://www.atf.gov/resource-center/docs/form/request-atf-background-investigation-information-atf-form-862065",
}

# Regulations.gov settings. The demo key is rate limited by IP; sign up for
# your own key at
# http://regulationsgov.github.io/developers/key/
REGS_GOV_API = 'https://api.regulations.gov/v4/documents'
REGS_GOV_KEY = 'gpPfSsRlg4We153fby1C9gnWC4Pfmdeja5NKlS6j'

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
