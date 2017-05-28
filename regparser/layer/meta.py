import re

from regparser.layer.layer import Layer
from regparser.web.settings import parser as settings


class Meta(Layer):
    shorthand = 'meta'

    def __init__(self, tree, cfr_title, version, **context):
        super(Meta, self).__init__(tree, **context)
        self.cfr_title = cfr_title
        self.version = version

    def process(self, node):
        """If this is the root element, add some 'meta' information about
        this regulation, including its cfr title, effective date, and any
        configured info"""
        if len(node.label) != 1:
            return

        layer = {
            'cfr_title_number': self.cfr_title,
            'cfr_title_text': settings.CFR_TITLES[self.cfr_title]
        }

        if node.title:
            # up till the paren
            match = re.search(r'part \d+[^\w]*([^\(]*)', node.title, re.I)
            if match:
                layer['statutory_name'] = match.group(1).strip()
            match = re.search(r'\(regulation (\w+)\)', node.title, re.I)
            if match:
                layer['reg_letter'] = match.group(1)

        effective_date = self.effective_date()
        if effective_date:
            layer['effective_date'] = effective_date

        result = {}
        result.update(layer)
        result.update(settings.META)
        return [result]

    def effective_date(self):
        if self.version and self.version.effective:
            return self.version.effective.isoformat()
