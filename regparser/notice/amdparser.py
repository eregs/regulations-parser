# -*- coding: utf-8 -*-
import logging
from itertools import takewhile

import attr
from lxml import etree

from regparser.grammar import amdpar, tokens
from regparser.tree.struct import Node
from regparser.tree.xml_parser.tree_utils import get_node_text

logger = logging.getLogger(__name__)


def parse_amdpar(par, initial_context):
    """ Parse the <AMDPAR> tags into a list of paragraphs that have changed.
    """

    #   Replace and "and"s in titles; they will throw off and_token_resolution
    for e in filter(lambda e: e.text, par.xpath('./E')):
        e.text = e.text.replace(' and ', ' ')
    text = get_node_text(par, add_spaces=True)
    auth = par.getnext()    # potential authority info
    if auth is not None and auth.tag != 'AUTH':
        auth = None

    tokenized = [t[0] for t, _, _ in amdpar.token_patterns.scanString(text)]

    tokenized = compress_context_in_tokenlists(tokenized)
    tokenized = resolve_confused_context(tokenized, initial_context)
    tokenized = paragraph_in_context_moved(tokenized, initial_context)
    tokenized = remove_false_deletes(tokenized, text)
    tokenized = multiple_moves(tokenized)
    tokenized = switch_passive(tokenized)
    tokenized = and_token_resolution(tokenized)
    tokenized, designated_subpart = subpart_designation(tokenized)
    tokenized = context_to_paragraph(tokenized)
    tokenized = move_then_modify(tokenized)
    if not designated_subpart:
        tokenized = separate_tokenlist(tokenized)
    initial_context = switch_part_context(tokenized, initial_context)
    initial_context = switch_level2_context(tokenized, initial_context)
    tokenized, final_context = compress_context(tokenized, initial_context)
    if designated_subpart:
        return make_subpart_designation_instructions(tokenized), final_context
    elif auth is not None:
        cfr_part = final_context[0]
        return make_authority_instructions(auth, cfr_part), final_context
    else:
        return make_instructions(tokenized), final_context


def matching(token_list, *types, **fields):
    """We have a recurring need to find all elements in a list that "match".
    This shorthand method helps"""
    return [t for t in token_list if t.match(*types, **fields)]


def compress(lhs_label, rhs_label):
    """Combine two labels where the rhs replaces the lhs. If the rhs is
    empty, assume the lhs takes precedent."""
    if not rhs_label:
        return lhs_label

    label = list(lhs_label)
    label.extend([None] * len(rhs_label))
    label = label[:len(rhs_label)]

    for idx, rhs_part in enumerate(rhs_label):
        label[idx] = rhs_part or label[idx]
    return label


def compress_context_in_tokenlists(tokenized):
    """Use compress (above) on elements within a tokenlist."""
    final = []
    for token in tokenized:
        if token.match(tokens.TokenList):
            subtokens = []
            label_so_far = []
            for subtoken in token.tokens:
                if hasattr(subtoken, 'label'):
                    label_so_far = compress(label_so_far, subtoken.label)
                    subtokens.append(
                        attr.assoc(subtoken, label=label_so_far))
                else:
                    subtokens.append(subtoken)
            final.append(
                attr.assoc(token, tokens=subtokens))
        else:
            final.append(token)
    return final


def resolve_confused_context(tokenized, initial_context):
    """Resolve situation where a Context thinks it is regtext, but it
    *should* be an interpretation"""
    if initial_context[1:2] == ['Interpretations']:
        final_tokens = []
        for token in tokenized:
            par_with_label = (
                token.match(tokens.Context, tokens.Paragraph) and
                len(token.label) > 1
            )
            if par_with_label and token.label[1] is None:
                final_tokens.append(attr.assoc(
                    token,
                    label=[token.label[0], 'Interpretations', token.label[2],
                           '(' + ')('.join(l for l in token.label[3:] if l) +
                           ')']
                ))
            elif par_with_label and token.label[1].startswith('Appendix:'):
                final_tokens.append(attr.assoc(
                    token,
                    label=[token.label[0], 'Interpretations',
                           token.label[1][len('Appendix:'):],
                           '(' + ')('.join(l for l in token.label[2:] if l) +
                           ')']
                ))
            elif token.match(tokens.TokenList):
                sub_tokens = resolve_confused_context(token.tokens,
                                                      initial_context)
                final_tokens.append(attr.assoc(token, tokens=sub_tokens))
            else:
                final_tokens.append(token)
        return final_tokens
    else:
        return tokenized


def paragraph_in_context_moved(tokenized, initial_context):
    """Catches this situation: "Paragraph 1 under subheading 51(b)(1) is
    redesignated as paragraph 7 under subheading 51(b)", i.e. a Paragraph
    within a Context moved to another Paragraph within a Context. The
    contexts and paragraphs in this situation need to be swapped."""
    final_tokens = []
    idx = 0
    while idx < len(tokenized) - 4:
        par1 = tokenized[idx].match(tokens.Paragraph)
        cont1 = tokenized[idx + 1].match(tokens.Context)
        verb = tokenized[idx + 2].match(tokens.Verb, verb=tokens.Verb.MOVE,
                                        active=False)
        par2 = tokenized[idx + 3].match(tokens.Paragraph)
        cont2 = tokenized[idx + 4].match(tokens.Context)
        if (all([par1, cont1, verb, par2, cont2]) and
                all(tok.label[1:2] == ['Interpretations']
                    for tok in (par1, cont1, par2, cont2))):
            batch, initial_context = compress_context(
                [cont1, par1, verb, cont2, par2], initial_context)
            final_tokens.extend(batch)
            idx += 5
        else:
            final_tokens.append(tokenized[idx])
            idx += 1
    final_tokens.extend(tokenized[idx:])
    return final_tokens


def remove_false_deletes(tokenized, text):
    """ Sometimes a statement like 'Removing the 'x' from the end of
    paragraph can be confused as removing the paragraph. Ensure that
    doesn't happen here. Likely this method needs a little more work. """
    contains_delete = bool(matching(tokenized, tokens.Verb, verb='DELETE'))
    contains_one_par = len(matching(tokenized, tokens.Paragraph)) == 1

    if contains_delete and contains_one_par and 'end of paragraph' in text:
        return []
    return tokenized


def multiple_moves(tokenized):
    """Phrases like paragraphs 1 and 2 are redesignated paragraphs 3 and 4
    are replaced with Move(active), paragraph 1, paragraph 3, Move(active)
    paragraph 2, paragraph 4"""
    converted = []
    skip = 0
    for idx, el0 in enumerate(tokenized):
        if skip:
            skip -= 1
        elif idx < len(tokenized) - 2:
            el1, el2 = tokenized[idx + 1:idx + 3]
            if (el0.match(tokens.TokenList)
                    and el2.match(tokens.TokenList)
                    and el1.match(tokens.Verb, verb=tokens.Verb.MOVE,
                                  active=False)
                    and len(el0.tokens) == len(el2.tokens)):
                skip = 2
                for tidx in range(len(el0.tokens)):
                    converted.append(attr.assoc(el1, active=True))
                    converted.append(el0.tokens[tidx])
                    converted.append(el2.tokens[tidx])
            else:
                converted.append(el0)
        else:
            converted.append(el0)
    return converted


def switch_passive(tokenized):
    """Passive verbs are modifying the phrase before them rather than the
    phrase following. For consistency, we flip the order of such verbs"""
    if all(not t.match(tokens.Verb, active=False) for t in tokenized):
        return tokenized
    converted, remaining = [], tokenized
    while remaining:
        to_add = list(takewhile(
            lambda t: not isinstance(t, tokens.Verb), remaining))
        if len(to_add) < len(remaining):
            #   also take the verb
            verb = remaining[len(to_add)]
            #   switch verb to the beginning
            if not verb.active:
                verb = attr.assoc(verb, active=True)
                to_add.append(verb)
                to_add = to_add[-1:] + to_add[:-1]
                #   may need to grab one more if the verb is move
                if (verb.verb == tokens.Verb.MOVE and
                        len(to_add) < len(remaining)):
                    to_add.append(remaining[len(to_add)])
            else:
                to_add.append(verb)
        converted.extend(to_add)
        remaining = remaining[len(to_add):]
    return converted


def and_token_resolution(tokenized):
    """Troublesome case where a Context should be a Paragraph, but the only
    indicator is the presence of an "and" token afterwards. We'll likely
    want to expand this step in the future, but for now, we only catch a few
    cases"""
    # compress "and" tokens
    tokenized = zip(tokenized, tokenized[1:] + [None])
    tokenized = [l for l, r in tokenized
                 if l != r or not l.match(tokens.AndToken)]

    # we'll strip out all "and" tokens in just a moment, but as a first
    # pass, remove all those preceded by a verb (which makes the following
    # logic simpler).
    tokenized = list(reversed(tokenized))
    tokenized = zip(tokenized, tokenized[1:] + [None])
    tokenized = list(reversed([l for l, r in tokenized
                               if not l.match(tokens.AndToken) or not r or
                               not r.match(tokens.Verb)]))

    # check for the pattern in question
    final_tokens = []
    idx = 0
    while idx < len(tokenized) - 3:
        t1, t2, t3, t4 = tokenized[idx:idx + 4]
        if (t1.match(tokens.Verb)
                and t2.match(tokens.Context)
                and t3.match(tokens.AndToken)
                and t4.match(tokens.Paragraph, tokens.TokenList)):
            final_tokens.append(t1)
            final_tokens.append(tokens.Paragraph.make(t2.label))
            final_tokens.append(t4)
            idx += 3    # not 4 as one will appear below
        elif t1 != tokens.AndToken:
            final_tokens.append(t1)
        idx += 1

    final_tokens.extend(tokenized[idx:])
    return final_tokens


def subpart_designation(tokenized):
    u"""If we have a designate verb, and a token list, we're going to
    change the context to a Paragraph. Because it's not a context, it's
    part of the manipulation.
    e.g. Designate §§ 1005.1 through 1005.20 as subpart A under the heading
    set forth above."""

    # Ensure that we only have one of each: designate verb, a token list and
    # a context
    verb_exists = len(matching(tokenized, tokens.Verb,
                               verb=tokens.Verb.DESIGNATE)) == 1
    list_exists = len(matching(tokenized, tokens.TokenList)) == 1
    context_exists = len(matching(tokenized, tokens.Context)) == 1

    if verb_exists and list_exists and context_exists:
        token_list = []
        for token in tokenized:
            if isinstance(token, tokens.Context):
                token_list.append(tokens.Paragraph.make(token.label))
            else:
                token_list.append(token)
        return token_list, True
    else:
        return tokenized, False


def context_to_paragraph(tokenized):
    """Generally, section numbers, subparts, etc. are good contextual clues,
    but sometimes they are the object of manipulation."""

    #   Don't modify anything if there are already paragraphs or no verbs
    for token in tokenized:
        if isinstance(token, tokens.Paragraph):
            return tokenized
        elif (isinstance(token, tokens.TokenList) and
              any(isinstance(t, tokens.Paragraph) for t in token.tokens)):
            return tokenized
    # copy
    converted = list(tokenized)
    verb_seen = False
    for idx, token in enumerate(converted):
        if isinstance(token, tokens.Verb):
            verb_seen = True
        elif verb_seen and token.match(tokens.Context, certain=False):
            converted[idx] = tokens.Paragraph.make(token.label)
    return converted


def move_then_modify(tokenized):
    """The subject of modification may be implicit in the preceding move
    operation: A is redesignated B and changed. Replace the operation with a
    DELETE and a POST so it's easier to compile later."""
    final_tokens = []
    idx = 0
    while idx < len(tokenized) - 3:
        move, p1, p2, edit = tokenized[idx:idx + 4]
        if (move.match(tokens.Verb, verb=tokens.Verb.MOVE, active=True)
                and p1.match(tokens.Paragraph)
                and p2.match(tokens.Paragraph)
                and edit.match(tokens.Verb, verb=tokens.Verb.PUT, active=True,
                               and_prefix=True)):
            final_tokens.append(tokens.Verb(tokens.Verb.DELETE, active=True))
            final_tokens.append(p1)
            final_tokens.append(tokens.Verb(tokens.Verb.POST, active=True))
            final_tokens.append(p2)
            idx += 4
        else:
            final_tokens.append(tokenized[idx])
            idx += 1
    final_tokens.extend(tokenized[idx:])
    return final_tokens


def separate_tokenlist(tokenized):
    """When we come across a token list, separate it out into individual
    tokens"""

    converted = []
    for token in tokenized:
        if isinstance(token, tokens.TokenList):
            converted.extend(token.tokens)
        else:
            converted.append(token)
    return converted


def switch_part_context(token_list, carried_context):
    """ Notices can refer to multiple regulations (CFR parts). If the
    CFR part changes, empty out the context that we carry forward. """

    def is_valid_label(label):
        return label and label[0] is not None

    if carried_context and carried_context[0] is not None:
        token_list = [t for t in token_list if hasattr(t, 'label')]
        reg_parts = [t.label[0] for t in token_list if is_valid_label(t.label)]

        if len(reg_parts) > 0:
            reg_part = reg_parts[0]
            if reg_part != carried_context[0]:
                return []
    return carried_context


def switch_level2_context(token_list, carried_context):
    """If an amendment mentions a subpart/subject group/appendix and we're
    sure that that mention is contextual, the fact that we're working in that
    subpart/etc. should apply to the whole AMDPAR"""
    level2_markers = ('Subpart', 'Subjgrp', 'Appendix')
    level2s = [token.label[1] for token in token_list
               if token.match(tokens.Context, certain=True) and
               any(marker in str(token.label) for marker in level2_markers)]
    if len(level2s) == 1 and carried_context:
        return carried_context[:1] + level2s + carried_context[2:]
    elif len(level2s) == 1:
        return [None] + level2s
    elif len(level2s) > 1:
        logger.warning("Multiple subpart contexts in amendment: %s",
                       token_list)
    return carried_context


def compress_context(tokenized, initial_context):
    """Add context to each of the paragraphs (removing context)"""
    # copy
    context = list(initial_context)
    converted = []
    for token in tokenized:
        if isinstance(token, tokens.Context):
            # Interpretations of appendices
            if (len(context) > 1 and len(token.label) > 1
                    and context[1] == 'Interpretations'
                    and (token.label[1] or '').startswith('Appendix')):
                context = compress(
                    context,
                    [token.label[0], None, token.label[1]] + token.label[2:])
            else:
                context = compress(context, token.label)
            continue
        #   Another corner case: a "paragraph" is indicates interp context
        elif (isinstance(token, tokens.Paragraph) and len(context) > 1 and
              len(token.label) > 3 and context[1] == 'Interpretations' and
              token.label[1] != 'Interpretations'):
            context = compress(
                context,
                [token.label[0], None, token.label[2], '(' + ')('.join(
                    p for p in token.label[3:] if p) + ')'])
            continue
        elif isinstance(token, tokens.Paragraph):
            context = compress(context, token.label)
            token = attr.assoc(token, label=context)
        converted.append(token)
    return converted, context


def get_destination(tokenized, reg_part):
    """ In a designate scenario, get the destination label.  """

    paragraphs = [t for t in tokenized if isinstance(t, tokens.Paragraph)]
    destination = paragraphs[0]

    if destination.label[0] is None:
        # Sometimes the destination label doesn't know the reg part.
        destination.label[0] = reg_part

    destination = destination.label_text()
    return destination


def make_subpart_designation_instructions(tokenized):
    u"""Convert tokens into an `EREGS_INSTRUCTIONS` xml element specifically
    for subpart designations, like Designate §§ 1005.1 through 1005.20 as
    subpart A"""
    instructions = etree.Element('EREGS_INSTRUCTIONS')
    token_lists = matching(tokenized, tokens.TokenList)

    # There's only one token list of paragraphs, sections to be designated
    reg_part = token_lists[0].tokens[0].label[0]
    subpart = get_destination(tokenized, reg_part)

    for token in token_lists[0]:
        etree.SubElement(instructions, 'MOVE_INTO_SUBPART',
                         label=token.label_text(), destination=subpart)
    return instructions


def make_authority_instructions(auth_xml, cfr_part):
    """Creates an `EREGS_INSTRUCTIONS` element specific to the authority
    information"""
    instructions = etree.Element('EREGS_INSTRUCTIONS')
    authority = etree.SubElement(instructions, 'AUTHORITY', label=cfr_part)
    authority.text = '\n'.join(get_node_text(p, add_spaces=True)
                               for p in auth_xml.xpath('./P'))
    return instructions


def make_instructions(tokenized):
    """Convert the tokens into an `EREGS_INSTRUCTIONS` xml element. Does not
    handle subpart designations"""
    instructions = etree.Element('EREGS_INSTRUCTIONS')
    verb = None
    for idx, token in enumerate(tokenized):
        if token.match(tokens.Verb):
            assert token.active
            verb = token.verb
        # MOVEs must have _two_ paragraphs
        elif (verb == tokens.Verb.MOVE and
              not tokenized[idx - 1].match(tokens.Paragraph)):
            continue
        elif verb == tokens.Verb.MOVE and token.match(tokens.Paragraph):
            origin = tokenized[idx - 1].label_text()
            etree.SubElement(instructions, verb, label=origin,
                             destination=token.label_text())
        elif verb and token.match(tokens.Paragraph):
            label = token.label_text()
            # Edits to intro text should always be PUTs
            if label.endswith('[text]') and verb == tokens.Verb.POST:
                etree.SubElement(instructions, tokens.Verb.PUT, label=label)
            else:
                etree.SubElement(instructions, verb, label=label)
    return instructions


def convert_label(label_str):
    """The labels that come back from parsing the list of amendments are not
    the same type we use in the rest of parsing. Convert between the two here
    (removing subpart markers, converting to interp format, etc.)"""
    fields_removed = label_str
    for field in (Amendment.TITLE, Amendment.TEXT, Amendment.HEADING):
        fields_removed = fields_removed.replace(field, '')

    label = fields_removed.split('-')
    if len(label) > 1:
        sub_type = label[1]
        uses_subpart = any(m in sub_type for m in ('?', 'Subpart', 'Subjgrp'))
        if sub_type == 'Interpretations':
            label = convert_interp_label(label)
        elif 'Appendix:' in sub_type:
            label = label[:1] + [sub_type[len('Appendix:'):]] + label[2:]
        elif uses_subpart and len(label) == 2:   # Subpart/Subject Group
            # 111-Subpart:A -> 111-Subpart-A
            label = label[:1] + sub_type.split(':')
        elif uses_subpart:   # Subpart info is skipped
            label = label[:1] + label[2:]
    return label


def convert_interp_label(label):
    """Convert between the interp format of amendments and the normal,
    node label format
    :param list[str] label:"""
    new_style = label[:1]
    if len(label) == 2:
        return new_style + [Node.INTERP_MARK]
    # Convert appendix format
    new_style.append(label[2].replace('Appendix:', ''))
    # Add paragraphs
    if len(label) > 3:
        paragraphs = [p.strip('()') for p in label[3].split(')(')]
        paragraphs = filter(bool, paragraphs)
        new_style.extend(paragraphs)
    new_style.append(Node.INTERP_MARK)
    # Add any paragraphs of the comment
    new_style.extend(label[4:])
    return new_style


class Amendment(object):
    """ An Amendment object contains all the information necessary for
    an amendment. """

    TITLE = '[title]'
    TEXT = '[text]'
    HEADING = '[heading]'

    def __init__(self, action, label, destination=None, amdpar_xml=None):
        self.destination = None
        self.field = None

        self.action = action
        self.original_label = label
        self.amdpar_xml = amdpar_xml
        self.label = convert_label(self.original_label)

        if destination:
            self.destination = convert_label(destination)

        if self.TITLE in self.original_label:
            self.field = self.TITLE
        elif self.TEXT in self.original_label:
            self.field = self.TEXT
        elif self.HEADING in self.original_label:
            self.field = self.HEADING

    def label_id(self):
        """ Return the label id (dash delimited) for this label. """
        return '-'.join(self.label)

    def __repr__(self):
        if self.destination:
            return '({0}, {1}, {2})'.format(self.action, self.label,
                                            self.destination)
        else:
            return '({0}, {1})'.format(self.action, self.label)

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
                self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def tree_format_level2(self):
        """The label we use in amendments contains more information than is
        present in regtree Nodes (see also regparser.citations.Label). This
        converts the second level (i.e. one below the root) to a format usable
        in Nodes."""
        parts = self.original_label.split('-')
        if len(parts) >= 2:
            if 'Subpart' in parts[1]:
                return [parts[0], 'Subpart', parts[1][len('Subpart:'):]]
            elif 'Subjgrp' in parts[1]:
                return [parts[0], 'Subjgrp', parts[1][len('Subjgrp:'):]]
            elif 'Appendix' in parts[1]:
                return [parts[0], parts[1][len('Appendix:'):]]
            # this does not account for interpretations


def amendment_from_xml(xml):
    """Deserialize amendments"""
    return Amendment(xml.tag, xml.get('label'),
                     xml.get('destination') or None,
                     amdpar_xml=xml.getparent().getparent())
