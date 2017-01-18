import logging
from itertools import chain

from regparser.grammar import unified as grammar
from regparser.tree.paragraph import p_levels
from regparser.tree.struct import Node

logger = logging.getLogger(__name__)


class Label(object):
    #   @TODO: subparts
    _p_markers = tuple('p{0}'.format(i) for i in range(1, 10))

    app_sect_schema = ('part', 'appendix', 'appendix_section') + _p_markers
    app_schema = ('part', 'appendix') + _p_markers
    regtext_schema = ('cfr_title', 'part', 'section') + _p_markers
    default_schema = regtext_schema

    comment_schema = ('comment', 'c1', 'c2', 'c3', 'c4')
    SCHEMA_FIELDS = set(app_sect_schema + app_schema + regtext_schema +
                        comment_schema)

    @classmethod
    def from_node(cls, node):
        """Convert between a struct.Node and a Label; use heuristics to
        determine which schema to follow. Node labels aren't as expressive as
        Label objects"""
        if (node.node_type == Node.APPENDIX or
                (node.node_type == Node.INTERP and len(node.label) > 2 and
                 node.label[1].isalpha())):
            if len(node.label) > 2 and node.label[2].isdigit():
                schema = cls.app_sect_schema
            else:
                schema = cls.app_schema
        else:
            schema = cls.regtext_schema[1:]   # Nodes don't track CFR title

        settings = {'comment': node.node_type == Node.INTERP}
        for idx, value in enumerate(node.label):
            if value == 'Interp':
                #   Add remaining bits as comment fields
                for cidx in range(idx + 1, len(node.label)):
                    comment_field = cls.comment_schema[cidx - idx]
                    settings[comment_field] = node.label[cidx]
                #   Stop processing the prefix fields
                break
            settings[schema[idx]] = value
        return cls(**settings)

    @staticmethod
    def determine_schema(settings):
        if 'appendix_section' in settings:
            return Label.app_sect_schema
        elif 'appendix' in settings:
            return Label.app_schema
        elif 'section' in settings or 'cfr_title' in settings:
            return Label.regtext_schema

    def __init__(self, schema=None, **kwargs):
        self.using_default_schema = False
        if schema is None:
            schema = Label.determine_schema(kwargs)
        if schema is None:
            self.using_default_schema = True
            schema = Label.default_schema
        self.settings = kwargs
        self.schema = schema
        self.comment = any(kwargs.get(field) for field in
                           Label.comment_schema)

    def copy(self, schema=None, **kwargs):
        """Keep any relevant prefix when copying"""
        kwschema = Label.determine_schema(kwargs)
        set_schema = bool(schema or kwschema or
                          not self.using_default_schema)

        if schema is None:
            if kwschema:
                schema = kwschema
            else:
                schema = self.schema

        if set_schema:
            new_settings = {'schema': schema}
        else:
            new_settings = {}

        found_start = False
        for field in schema + Label.comment_schema:
            if field in kwargs:
                found_start = True
                new_settings[field] = kwargs[field]
            if not found_start:
                new_settings[field] = self.settings.get(field)
        return Label(**new_settings)

    def to_list(self, for_node=True):
        """Convert a Label into a struct.Node style label list. Node labels
        don't contain CFR titles"""
        if for_node:
            lst = [self.settings.get(f) for f in self.schema
                   if f != 'cfr_title']
        else:
            lst = [self.settings.get(f) for f in self.schema]

        if self.comment:
            lst.append(Node.INTERP_MARK)
            lst.append(self.settings.get('c1'))
            lst.append(self.settings.get('c2'))
            lst.append(self.settings.get('c3'))
        return [l for l in lst if l]

    def __repr__(self):
        fields = ', '.join(
            '{0}={1}'.format(field, repr(self.settings.get(field)))
            for field in self.schema)
        return 'Label({0})'.format(fields)

    def __eq__(self, other):
        """Equality if types match and fields match"""
        return (isinstance(other, Label) and
                self.using_default_schema == other.using_default_schema and
                self.settings == other.settings and
                self.schema == other.schema and
                self.comment == other.comment)

    def __hash__(self):
        return hash(repr(self))

    def __lt__(self, other):
        self_list = tuple(self.to_list(for_node=False))
        other_list = tuple(other.to_list(for_node=False))
        return self_list < other_list

    def labels_until(self, other):
        """Given `self` as a starting point and `other` as an end point, yield
        a `Label` for paragraphs in between. For example, if `self` is
        something like 123.45(a)(2) and end is 123.45(a)(6), this should emit
        123.45(a)(3), (4), and (5)"""
        self_list = self.to_list(for_node=False)
        other_list = other.to_list(for_node=False)
        field = self.schema[len(self_list) - 1]
        start, end = self_list[-1], other_list[-1]
        level = [lvl for lvl in p_levels if start in lvl and end in lvl]
        if (self.schema != other.schema or len(self_list) != len(other_list) or
                self_list[:-1] != other_list[:-1] or not level):
            logger.warning("Bad use of 'through': %s - %s", self, other)
        else:
            level = level[0]
            start_idx, end_idx = level.index(start), level.index(end)
            for marker in level[start_idx + 1:end_idx]:
                yield self.copy(**{field: marker})


class ParagraphCitation(object):
    def __init__(self, start, end, label, full_start=None, full_end=None,
                 in_clause=False):
        if full_start is None:
            full_start = start
        if full_end is None:
            full_end = end

        self.start, self.end, self.label = start, end, label
        self.full_start, self.full_end = full_start, full_end
        self.in_clause = in_clause

    def __contains__(self, other):
        """Proper inclusion"""
        return (other.full_start >= self.full_start and
                other.full_end <= self.full_end and
                (other.full_end != self.full_end or
                 other.full_start != self.full_start))

    def __repr__(self):
        return "ParagraphCitation(start={0}, end={1}, label={2} )".format(
            repr(self.start), repr(self.end), repr(self.label))


def match_to_label(match, initial_label, comment=False):
    """Return the citation and offsets for this match"""
    if comment:
        field_map = {'comment': True}
    else:
        field_map = {}
    for field in Label.SCHEMA_FIELDS:
        value = getattr(match, field) or getattr(match, 'plaintext_' + field)
        if value:
            field_map[field] = value

    label = initial_label.copy(**field_map)
    return label


def single_citations(matches, initial_label, comment=False):
    """For each pyparsing match, yield the corresponding ParagraphCitation"""
    for match, start, end in matches:
        full_start = start
        if match.marker is not '':
            #   Remove the marker from the beginning of the string
            start = match.marker.pos[1]
        yield ParagraphCitation(
            start, end, match_to_label(match, initial_label, comment),
            full_start=full_start)


def multiple_citations(matches, initial_label, comment=False,
                       include_fill=False):
    """Similar to single_citations save that we have a compound citation, such
    as "paragraphs (b), (d), and (f). Yield a ParagraphCitation for each
    sub-citation. We refer to the first match as "head" and all following as
    "tail" """
    for outer_match, outer_start, outer_end in matches:
        label = initial_label   # Share context in between sub-citations
        for submatch in chain([outer_match.head], outer_match.tail):
            match = submatch.match or submatch     # might be wrapped
            new_label = match_to_label(match, label, comment)
            if include_fill and submatch.through:
                for fill_label in label.labels_until(new_label):
                    yield ParagraphCitation(
                        outer_start, outer_end, fill_label, in_clause=True)
            yield ParagraphCitation(
                match.pos.start, match.pos.end, new_label,
                full_start=outer_start, full_end=outer_end,
                in_clause=True)
            label = new_label   # update the label to keep context


def internal_citations(text, initial_label=None,
                       require_marker=False, title=None):
    """List of all internal citations in the text. require_marker helps by
    requiring text be prepended by 'comment'/'paragraphs'/etc. title
    represents the CFR title (e.g. 11 for FEC, 12 for CFPB regs) and is used
    to correctly parse citations of the the form 11 CFR 110.1 when
    11 CFR 110 is the regulation being parsed."""
    if not initial_label:
        initial_label = Label()
    citations = []

    def single(gram, comment):
        citations.extend(single_citations(gram.scanString(text),
                                          initial_label, comment))

    def multiple(gram, comment):
        citations.extend(multiple_citations(gram.scanString(text),
                                            initial_label, comment))

    single(grammar.marker_comment, True)

    multiple(grammar.multiple_non_comments, False)
    multiple(grammar.multiple_appendix_section, False)
    multiple(grammar.multiple_comments, True)
    multiple(grammar.multiple_appendices, False)
    multiple(grammar.multiple_period_sections, False)

    single(grammar.marker_appendix, False)
    single(grammar.appendix_with_section, False)
    single(grammar.marker_paragraph, False)
    single(grammar.mps_paragraph, False)
    single(grammar.m_section_paragraph, False)
    if not require_marker:
        single(grammar.section_paragraph, False)
        single(grammar.part_section_paragraph, False)
        multiple(grammar.multiple_section_paragraphs, False)

    # Some appendix citations are... complex
    for match, start, end in grammar.appendix_with_part.scanString(text):
        full_start = start
        if match.marker is not '':
            start = match.marker.pos[1]
        label_parts = filter(lambda l: l != '.', list(match)[3:])
        label = dict(zip(['p1', 'p2', 'p3'], label_parts))
        citations.append(ParagraphCitation(
            start, end, initial_label.copy(
                appendix=match.appendix, appendix_section=match.a1,
                **label), full_start=full_start))

    # Internal citations can sometimes be in the form XX CFR YY.ZZ
    # Check if this is a reference to the CFR title and part we are parsing
    for cit in cfr_citations(text):
        cit_title = cit.label.settings.get('cfr_title')
        cit_part = cit.label.settings.get('part')
        initial_part = initial_label.settings.get('part')
        if cit_title == title and cit_part == initial_part:
            citations.append(cit)

    return select_encompassing_citations(citations)


def select_encompassing_citations(citations):
    """The same citation might be found by multiple grammars; we take the
    most-encompassing of any overlaps"""
    encompassing = []
    for cit in citations:
        if not any(cit in other for other in citations):
            encompassing.append(cit)
    return encompassing


def remove_citation_overlaps(text, possible_markers):
    """Given a list of markers, remove any that overlap with citations"""
    return [(m, start, end) for m, start, end in possible_markers
            if not any((e.start <= start and e.end >= start) or
                       (e.start <= end and e.end >= end) or
                       (start <= e.start and end >= e.end)
                       for e in internal_citations(text))]


def cfr_citations(text, include_fill=False):
    """Find all citations which include CFR title and part"""
    citations = []
    initial_label = Label()
    citations.extend(single_citations(grammar.cfr.scanString(text),
                                      initial_label))
    citations.extend(single_citations(grammar.cfr_p.scanString(text),
                                      initial_label))
    citations.extend(multiple_citations(
        grammar.multiple_cfr_p.scanString(text), initial_label,
        include_fill=include_fill))

    return select_encompassing_citations(citations)
