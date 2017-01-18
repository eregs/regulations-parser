""" Set of Tokens to be used when parsing.
    @label is a list describing the depth of a paragraph/context. It follows:
    [ Part, Subpart/Appendix/Interpretations, Section, p-level-1, p-level-2,
    p-level-3, p-level4, p-level5 ]
"""
import attr
import six


def uncertain_label(label_parts):
    """Convert a list of strings/Nones to a '-'-separated string with question
    markers to replace the Nones. We use this format to indicate
    uncertainty"""
    return '-'.join(p or '?' for p in label_parts)


def _none_str(value):
    """Shorthand for displaying a variable as a string or the text None"""
    if value is None:
        return 'None'
    else:
        return "'{0}'".format(value)


@attr.attrs(frozen=True)
class Token(object):
    """Base class for all tokens. Provides methods for pattern matching and
    copying this token"""
    def match(self, *types, **fields):
        """Pattern match. self must be one of the types provided (if they
        were provided) and all of the fields must match (if fields were
        provided). If a successful match, returns self"""
        type_match = not types or any(isinstance(self, typ) for typ in types)
        has_fields = not fields or all(hasattr(self, f) for f in fields)
        fields_match = not has_fields or all(
            getattr(self, f) == v for f, v in fields.items())
        return type_match and has_fields and fields_match and self


@attr.attrs(slots=True, frozen=True)
class Verb(Token):
    """Represents what action is taking place to the paragraphs"""
    verb = attr.attrib()
    active = attr.attrib()
    and_prefix = attr.attrib(default=False)

    PUT = 'PUT'
    POST = 'POST'
    MOVE = 'MOVE'
    DELETE = 'DELETE'
    DESIGNATE = 'DESIGNATE'
    RESERVE = 'RESERVE'
    KEEP = 'KEEP'
    INSERT = 'INSERT'


@attr.attrs(slots=True, frozen=True)
class Context(Token):
    """Represents a bit of context for the paragraphs. This gets compressed
    with the paragraph tokens to define the full scope of a paragraph. To
    complicate matters, sometimes what looks like a Context is actually the
    entity which is being modified (i.e. a paragraph). If we are certain
    that this is only context, (e.g. "In Subpart A"), use 'certain'"""
    # replace with Nones
    label = attr.attrib(convert=lambda label: [p or None for p in label])
    certain = attr.attrib(default=False)


@attr.attrs(slots=True, frozen=True)
class Paragraph(Token):
    """Represents an entity which is being modified by the amendment. Label
    is a way to locate this paragraph (though see the above note). We might
    be modifying a field of a paragraph (e.g. intro text only, or title
    only;) if so, set the `field` parameter."""
    label = attr.attrib(default=attr.Factory(list))
    field = attr.attrib(default=None)

    TEXT_FIELD = 'text'
    HEADING_FIELD = 'title'
    KEYTERM_FIELD = 'heading'

    @classmethod
    def make(cls, label=None, field=None, part=None, sub=None, section=None,
             paragraphs=None, paragraph=None, subpart=None, is_interp=None,
             appendix=None):
        """label and field are the only "materialized" fields. Everything
        other field becomes part of the label, offering a more legible API.
        Particularly useful for writing tests"""
        if sub is None and subpart:
            if isinstance(subpart, six.string_types):
                sub = 'Subpart:{0}'.format(subpart)
            else:
                sub = 'Subpart'
        if sub is None and is_interp:
            sub = 'Interpretations'
        if sub is None and appendix:
            sub = 'Appendix:' + appendix
        if paragraph:
            paragraphs = [paragraph]
        if label is None:
            label = [part, sub, section] + (paragraphs or [])
        # replace with Nones
        label = [p or None for p in label]
        # Trim the right side of the list
        while label and not label[-1]:
            label.pop()
        return cls(label, field)

    def label_text(self):
        """Converts self.label into a string"""
        label = uncertain_label(self.label)
        if self.field:
            label += '[{0}]'.format(self.field)
        return label


@attr.attrs(slots=True, frozen=True)
class TokenList(Token):
    """Represents a sequence of other tokens, e.g. comma separated of
    created via "through" """
    tokens = attr.attrib()

    def __iter__(self):
        return iter(self.tokens)


@attr.attrs(slots=True, frozen=True)
class AndToken(Token):
    """The word 'and' can help us determine if a Context token should be a
    Paragraph token. Note that 'and' might also trigger the creation of a
    TokenList, which takes precedent"""
