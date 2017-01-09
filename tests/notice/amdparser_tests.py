# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contextlib import contextmanager

import attr
import pytest
from lxml import etree

from regparser.grammar import tokens
from regparser.notice import amdparser
from regparser.notice.amdparser import Amendment
from regparser.test_utils.xml_builder import XMLBuilder
from regparser.tree.paragraph import hash_for_paragraph


def test_make_instructions():
    tokenized = [
        tokens.Paragraph.make(part='111'),
        tokens.Verb(tokens.Verb.PUT, active=True),
        tokens.Paragraph.make(part='222'),
        tokens.Paragraph.make(part='333'),
        tokens.Paragraph.make(part='444'),
        tokens.Verb(tokens.Verb.DELETE, active=True),
        tokens.Paragraph.make(part='555'),
        tokens.Verb(tokens.Verb.MOVE, active=True),
        tokens.Paragraph.make(part='666'),
        tokens.Paragraph.make(part='777')
    ]
    with XMLBuilder("EREGS_INSTRUCTIONS") as ctx:
        ctx.PUT(label=222)
        ctx.PUT(label=333)
        ctx.PUT(label=444)
        ctx.DELETE(label=555)
        ctx.MOVE(label=666, destination=777)
    assert ctx.xml_str == etree.tounicode(
        amdparser.make_instructions(tokenized))


def test_compress_context_simple():
    tokenized = [
        tokens.Verb(tokens.Verb.PUT, active=True),
        #  part 9876, subpart A
        tokens.Context(['9876', 'Subpart:A']),
        #  section 12
        tokens.Context([None, None, '12']),
        #  12(f)(4)
        tokens.Paragraph.make(paragraphs=['f', '4']),
        #  12(f)
        tokens.Context([None, None, None, 'g']),
        #  12(g)(1)
        tokens.Paragraph.make(paragraphs=[None, '1']),
    ]
    converted, final_ctx = amdparser.compress_context(tokenized, [])
    assert converted == [
        tokens.Verb(tokens.Verb.PUT, active=True),
        tokens.Paragraph.make(part='9876', subpart='A', section='12',
                              paragraphs=['f', '4']),
        tokens.Paragraph.make(part='9876', subpart='A', section='12',
                              paragraphs=['g', '1']),
    ]
    assert ['9876', 'Subpart:A', '12', 'g', '1'] == final_ctx


def test_compress_context_initial_context():
    tokenized = [tokens.Paragraph.make(paragraph='q')]
    converted, _ = amdparser.compress_context(
        tokenized, ['111', None, '12'])
    assert converted == [
        tokens.Paragraph.make(part='111', section='12', paragraph='q')]


def test_compress_context_interpretations():
    tokenized = [
        tokens.Context(['123', 'Interpretations']),
        tokens.Paragraph.make(section='12', paragraphs=['a', '2', 'iii']),
        tokens.Paragraph.make(is_interp=True, paragraphs=[None, '3', 'v']),
        tokens.Context([None, 'Appendix:R']),
        tokens.Paragraph.make(is_interp=True, paragraphs=[None, '5'])
    ]
    converted, _ = amdparser.compress_context(tokenized, [])
    assert converted == [
        tokens.Paragraph.make(part='123', is_interp=True, section='12',
                              paragraphs=['(a)(2)(iii)', '3', 'v']),
        #   None because we are missing a layer
        tokens.Paragraph.make(part='123', is_interp=True, section='Appendix:R',
                              paragraphs=[None, '5'])
    ]


def test_compress_context_in_tokenlists():
    tokenized = [
        tokens.Context(['123', 'Interpretations']),
        tokens.Paragraph.make(part='123', section='23', paragraph='a'),
        tokens.Verb(tokens.Verb.PUT, True),
        tokens.TokenList([
            tokens.Verb(tokens.Verb.POST, True),
            tokens.Paragraph.make(part='123', section='23',
                                  paragraphs=['a', '1']),
            tokens.Paragraph.make(paragraphs=[None, None, 'i']),
            tokens.Paragraph.make(section='23', paragraph='b')])]
    assert amdparser.compress_context_in_tokenlists(tokenized) == [
        tokens.Context(['123', 'Interpretations']),
        tokens.Paragraph.make(part='123', section='23', paragraph='a'),
        tokens.Verb(tokens.Verb.PUT, True),
        tokens.TokenList([
            tokens.Verb(tokens.Verb.POST, True),
            tokens.Paragraph.make(part='123', section='23',
                                  paragraphs=['a', '1']),
            tokens.Paragraph.make(part='123', section='23',
                                  paragraphs=['a', '1', 'i']),
            tokens.Paragraph.make(part='123', section='23', paragraph='b')])
    ]


def test_resolve_confused_context():
    tokenized = [tokens.Context([None, None, '12', 'a', '2', 'iii'])]
    converted = amdparser.resolve_confused_context(
        tokenized, ['123', 'Interpretations'])
    assert converted == [
        tokens.Context([None, 'Interpretations', '12', '(a)(2)(iii)'])]


def test_resolve_confused_context_appendix():
    tokenized = [tokens.Context([None, 'Appendix:A', '12'])]
    converted = amdparser.resolve_confused_context(
        tokenized, ['123', 'Interpretations'])
    assert converted == [
        tokens.Context([None, 'Interpretations', 'A', '(12)'])]


@pytest.mark.parametrize('left,right,expected', [
    ([1, 2, 3], [], [1, 2, 3]),
    ([1, 2, 3, 4, 5], [None, 6, None], [1, 6, 3]),
    ([1, 2], [2, None, 5, 6], [2, 2, 5, 6])
])
def test_compress(left, right, expected):
    assert amdparser.compress(left, right) == expected


def test_separate_tokenlist():
    tokenized = [
        tokens.Context(['1']),
        tokens.TokenList([
            tokens.Verb(tokens.Verb.MOVE, active=True),
            tokens.Context([None, '2'])
        ]),
        tokens.Paragraph.make(sub='3'),
        tokens.TokenList([tokens.Paragraph.make(section='b')])
    ]
    assert amdparser.separate_tokenlist(tokenized) == [
        tokens.Context(['1']),
        tokens.Verb(tokens.Verb.MOVE, active=True),
        tokens.Context([None, '2']),
        tokens.Paragraph.make(sub='3'),
        tokens.Paragraph.make(section='b')
    ]


def test_context_to_paragraph():
    tokenized = [
        tokens.Context(['1']),
        tokens.Verb(tokens.Verb.PUT, active=True),
        tokens.Context(['2']),
        tokens.Context(['3'], certain=True),
        tokens.Context(['4'])
    ]
    assert amdparser.context_to_paragraph(tokenized) == [
        tokens.Context(['1']),
        tokens.Verb(tokens.Verb.PUT, active=True),
        tokens.Paragraph.make(part='2'),
        tokens.Context(['3'], certain=True),
        tokens.Paragraph.make(part='4')
    ]


def test_context_to_paragraph_exceptions1():
    tokenized = [
        tokens.Verb(tokens.Verb.PUT, active=True),
        tokens.Context(['2']),
        tokens.Paragraph.make(part='3')
    ]
    assert tokenized == amdparser.context_to_paragraph(tokenized)


def test_context_to_paragraph_exceptions2():
    tokenized = [
        tokens.Verb(tokens.Verb.PUT, active=True),
        tokens.Context(['2']),
        tokens.TokenList([tokens.Paragraph.make(part='3')])
    ]
    assert tokenized == amdparser.context_to_paragraph(tokenized)


def test_switch_passive1():
    tokenized = [
        tokens.Context(['1']),
        tokens.Verb(tokens.Verb.PUT, active=True),
        tokens.Context(['2'])
    ]
    assert tokenized == amdparser.switch_passive(tokenized)


def test_switch_passive2():
    tokenized = [
        tokens.Context(['1']),
        tokens.Verb(tokens.Verb.PUT, active=False),
        tokens.Context(['2']),
        tokens.Context(['3']),
        tokens.Verb(tokens.Verb.MOVE, active=False),
    ]
    assert amdparser.switch_passive(tokenized) == [
        tokens.Verb(tokens.Verb.PUT, active=True),
        tokens.Context(['1']),
        tokens.Verb(tokens.Verb.MOVE, active=True),
        tokens.Context(['2']),
        tokens.Context(['3']),
    ]


def test_switch_passive3():
    tokenized = [
        tokens.Context(['1']),
        tokens.Verb(tokens.Verb.MOVE, active=False),
        tokens.Context(['2']),
        tokens.Context(['3']),
        tokens.Verb(tokens.Verb.PUT, active=False)]
    assert amdparser.switch_passive(tokenized) == [
        tokens.Verb(tokens.Verb.MOVE, active=True),
        tokens.Context(['1']),
        tokens.Context(['2']),
        tokens.Verb(tokens.Verb.PUT, active=True),
        tokens.Context(['3']),
    ]


def _paragraph_token_list():
    return tokens.TokenList([
        tokens.Paragraph.make(part='200', sub='1', section='a'),
        tokens.Paragraph.make(part='200', sub='1', section='b')
    ])


def test_subpart_designation():
    designate_token = tokens.Verb(tokens.Verb.DESIGNATE, True)
    token_list = _paragraph_token_list()
    context = tokens.Context(['Subpart', 'A'])

    tokenized = [designate_token, token_list, context]

    toks, subpart_added = amdparser.subpart_designation(tokenized)
    assert subpart_added

    paragraph_found = False
    for t in toks:
        assert not isinstance(t, tokens.Context)

        if isinstance(t, tokens.Paragraph):
            assert t.label == ['Subpart', 'A']
            paragraph_found = True

    assert paragraph_found


def test_subpart_designation_no_subpart():
    designate_token = tokens.Verb(tokens.Verb.DESIGNATE, True)
    token_list = _paragraph_token_list()
    tokenized = [designate_token, token_list]

    toks, subpart_added = amdparser.subpart_designation(tokenized)
    assert not subpart_added


def test_make_subpart_designation_instructions():
    token_list = _paragraph_token_list()
    subpart_token = tokens.Paragraph.make(subpart='J')
    tokenized = [token_list, subpart_token]
    with XMLBuilder('EREGS_INSTRUCTIONS') as ctx:
        ctx.MOVE_INTO_SUBPART(label='200-1-a', destination='200-Subpart:J')
        ctx.MOVE_INTO_SUBPART(label='200-1-b', destination='200-Subpart:J')

    assert ctx.xml_str == etree.tounicode(
        amdparser.make_subpart_designation_instructions(tokenized))


def test_get_destination_normal():
    subpart_token = tokens.Paragraph.make(part='205', subpart='A')
    tokenized = [subpart_token]

    assert amdparser.get_destination(tokenized, '205') == '205-Subpart:A'


def test_get_destination_no_reg_part():
    subpart_token = tokens.Paragraph.make(subpart='J')
    tokenized = [subpart_token]

    assert amdparser.get_destination(tokenized, '205') == '205-Subpart:J'


def test_switch_part_context():
    initial_context = ['105', '2']

    tokenized = [
        tokens.Paragraph.make(part='203', sub='2', section='x'),
        tokens.Verb(tokens.Verb.DESIGNATE, True)]

    assert amdparser.switch_part_context(tokenized, initial_context) == []

    tokenized = [
        tokens.Paragraph.make(part='105', sub='4', section='j',
                              paragraph='iv'),
        tokens.Verb(tokens.Verb.DESIGNATE, True)]

    assert initial_context == amdparser.switch_part_context(tokenized,
                                                            initial_context)

    tokenized = [
        tokens.Context(['', '4', 'j', 'iv']),
        tokens.Verb(tokens.Verb.DESIGNATE, True)]

    assert initial_context == amdparser.switch_part_context(tokenized,
                                                            initial_context)


def test_switch_level2_context():
    """The presence of certain types of context should apply throughout
    the amendment"""
    initial = ['105', None, '2']
    tokenized = [tokens.Paragraph(), tokens.Verb('verb', True)]
    transform = amdparser.switch_level2_context  # shorthand

    assert transform(tokenized, initial) == initial

    context = tokens.Context(['105', 'Subpart:G'], certain=False)
    tokenized.append(context)
    assert transform(tokenized, initial) == initial

    tokenized[-1] = attr.assoc(context, certain=True)
    assert transform(tokenized, initial) == ['105', 'Subpart:G', '2']

    # Don't try to proceed if multiple contexts are present
    tokenized.append(tokens.Context(['105', 'Appendix:Q'], certain=True))
    assert transform(tokenized, initial) == initial


def test_remove_false_deletes():
    tokenized = [
        tokens.Paragraph.make(part='444'),
        tokens.Verb(tokens.Verb.DELETE, active=True)]

    text = "Remove the semi-colong at the end of paragraph 444"
    new_tokenized = amdparser.remove_false_deletes(tokenized, text)
    assert new_tokenized == []


def test_multiple_moves_success():
    tokenized = [
        tokens.TokenList([tokens.Paragraph.make(part='444', sub='1'),
                          tokens.Paragraph.make(part='444', sub='2')]),
        tokens.Verb(tokens.Verb.MOVE, active=False),
        tokens.TokenList([tokens.Paragraph.make(part='444', sub='3'),
                          tokens.Paragraph.make(part='444', sub='4')])]
    tokenized = amdparser.multiple_moves(tokenized)
    assert tokenized == [
        tokens.Verb(tokens.Verb.MOVE, active=True),
        tokens.Paragraph.make(part='444', sub='1'),
        tokens.Paragraph.make(part='444', sub='3'),
        tokens.Verb(tokens.Verb.MOVE, active=True),
        tokens.Paragraph.make(part='444', sub='2'),
        tokens.Paragraph.make(part='444', sub='4')
    ]


def test_multiple_moved_not_even_number_of_elements_on_either_side():
    tokenized = [
        tokens.TokenList([tokens.Paragraph.make(part='444', sub='1'),
                          tokens.Paragraph.make(part='444', sub='2')]),
        tokens.Verb(tokens.Verb.MOVE, active=False),
        tokens.TokenList([tokens.Paragraph.make(part='444', sub='3')])]
    assert tokenized == amdparser.multiple_moves(tokenized)


def test_multiple_moves_paragraphs_on_either_side_of_a_move():
    tokenized = [tokens.Paragraph.make(part='444', sub='1'),
                 tokens.Verb(tokens.Verb.MOVE, active=False),
                 tokens.Paragraph.make(part='444', sub='3')]
    assert tokenized == amdparser.multiple_moves(tokenized)


@contextmanager
def assert_instruction_conversion(instruction_text, initial_label):
    """We have several tests that require creating an AMDPAR with the provided
    instruction_text, parsing, and comparing it to a built set of XML."""
    amdpar = etree.fromstring('<AMDPAR>{0}</AMDPAR>'.format(instruction_text))
    with XMLBuilder('EREGS_INSTRUCTIONS') as expected:
        yield expected
    instructions, _ = amdparser.parse_amdpar(amdpar, initial_label)
    assert etree.tounicode(instructions) == expected.xml_str


def test_parse_amdpar_newly_redesignated():
    text = ("Paragraphs 3.ii, 3.iii, 4 and newly redesignated paragraph "
            "10 are revised.")
    label = ['1111', 'Interpretations', '2', '(a)']
    with assert_instruction_conversion(text, label) as expected_ctx:
        expected_ctx.PUT(label='1111-Interpretations-2-(a)-3-ii')
        expected_ctx.PUT(label='1111-Interpretations-2-(a)-3-iii')
        expected_ctx.PUT(label='1111-Interpretations-2-(a)-4')
        expected_ctx.PUT(label='1111-Interpretations-2-(a)-10')


def test_parse_amdpar_interp_phrase():
    text = ('In Supplement I to part 999, under<E T="03">Section 999.3—Header'
            ',</E>under<E T="03">3(b) Subheader,</E>new paragraph 1.iv is '
            'added:')
    with assert_instruction_conversion(text, ['1111']) as expected_ctx:
        expected_ctx.POST(label='999-Interpretations-3-(b)-1-iv')


def test_parse_amdpar_interp_heading():
    text = "ii. The heading for 35(b) blah blah is revised."
    label = ['1111', 'Interpretations']
    with assert_instruction_conversion(text, label) as expected_ctx:
        expected_ctx.PUT(label='1111-Interpretations-35-(b)[title]')


def test_parse_amdpar_interp_context():
    text = "b. 35(b)(1) Some title and paragraphs 1, 2, and 3 are added."
    label = ['1111', 'Interpretations']
    with assert_instruction_conversion(text, label) as expected_ctx:
        expected_ctx.POST(label='1111-Interpretations-35-(b)(1)')
        expected_ctx.POST(label='1111-Interpretations-35-(b)(1)-1')
        expected_ctx.POST(label='1111-Interpretations-35-(b)(1)-2')
        expected_ctx.POST(label='1111-Interpretations-35-(b)(1)-3')


def test_parse_amdpar_interp_redesignated():
    text = ("Paragraph 1 under 51(b) is redesignated as paragraph 2 under "
            "subheading 51(b)(1) and revised")
    label = ['1111', 'Interpretations']
    with assert_instruction_conversion(text, label) as expected_ctx:
        expected_ctx.DELETE(label='1111-Interpretations-51-(b)-1')
        expected_ctx.POST(label='1111-Interpretations-51-(b)(1)-2')


def test_parse_amdpar_interp_entries():
    text = "Entries for 12(c)(3)(ix)(A) and (B) are added."
    label = ['1111', 'Interpretations']
    with assert_instruction_conversion(text, label) as expected_ctx:
        expected_ctx.POST(label='1111-Interpretations-12-(c)(3)(ix)(A)')
        expected_ctx.POST(label='1111-Interpretations-12-(c)(3)(ix)(B)')


def test_parse_amdpar_and_and():
    text = "12(a) 'Titles and Paragraphs' and paragraph 3 are added"
    label = ['1111', 'Interpretations']
    with assert_instruction_conversion(text, label) as expected_ctx:
        expected_ctx.POST(label='1111-Interpretations-12-(a)')
        expected_ctx.POST(label='1111-Interpretations-12-(a)-3')


def test_parse_amdpar_and_in_tags():
    text = ("Under <E>Appendix A - Some phrase and another</E>, paragraph "
            "3 is added")
    label = ['1111', 'Interpretations']
    with assert_instruction_conversion(text, label) as expected_ctx:
        expected_ctx.POST(label='1111-Interpretations-A-()-3')


def test_parse_amdpar_verbs_ands():
    text = ("Under 45(a)(1) Title, paragraphs 1 and 2 are removed, and "
            "45(a)(1)(i) Deeper Title and paragraphs 1 and 2 are added")
    label = ['1111', 'Interpretations']
    with assert_instruction_conversion(text, label) as expected_ctx:
        expected_ctx.DELETE(label='1111-Interpretations-45-(a)(1)-1')
        expected_ctx.DELETE(label='1111-Interpretations-45-(a)(1)-2')
        expected_ctx.POST(label='1111-Interpretations-45-(a)(1)(i)')
        expected_ctx.POST(label='1111-Interpretations-45-(a)(1)(i)-1')
        expected_ctx.POST(label='1111-Interpretations-45-(a)(1)(i)-2')


def test_parse_amdpar_add_field():
    text = "Adding introductory text to paragraph (c)"
    label = ['1111', None, '12']
    with assert_instruction_conversion(text, label) as expected_ctx:
        expected_ctx.PUT(label='1111-?-12-c[text]')


def test_parse_amdpar_moved_then_modified():
    text = ("Under Paragraph 22(a), paragraph 1 is revised, paragraph "
            "2 is redesignated as paragraph 3 and revised, and new "
            "paragraph 2 is added.")
    label = ['1111', 'Interpretations']
    with assert_instruction_conversion(text, label) as expected_ctx:
        expected_ctx.PUT(label='1111-Interpretations-22-(a)-1')
        expected_ctx.DELETE(label='1111-Interpretations-22-(a)-2')
        expected_ctx.POST(label='1111-Interpretations-22-(a)-3')
        expected_ctx.POST(label='1111-Interpretations-22-(a)-2')


def test_parse_amdpar_subject_group():
    text = ("<AMDPAR>8. Section 479.90a is added to "
            "[subject-group(Exemptions Relating to Transfers of Firearms)] "
            "to read as follows.</AMDPAR>")
    with assert_instruction_conversion(text, []) as expected_ctx:
        expected_ctx.POST(label='479-Subjgrp:ERtToF-90a')


def test_parse_amdpar_definition():
    """We should correctly deduce which paragraphs are being updated, even
    when they are identified by definition alone"""
    text = ("Section 478.11 is amended by adding a definition for the "
            "term “Nonimmigrant visa” in alphabetical order to read as "
            "follows:")
    with assert_instruction_conversion(text, []) as expected_ctx:
        expected_ctx.POST(label='478-?-11-p{0}'.format(hash_for_paragraph(
            "Nonimmigrant visa")))


@pytest.mark.parametrize('in_label,out_label', [
    ('1005-Interpretations', ['1005', 'Interp']),
    ('1005-Interpretations-31-(b)(1)-3',
     ['1005', '31', 'b', '1', 'Interp', '3']),
    ('1005-Interpretations-31-(b)(1)-3[title]',
     ['1005', '31', 'b', '1', 'Interp', '3']),
    ('1005-Interpretations-31-(c)-2-xi',
     ['1005', '31', 'c', 'Interp', '2', 'xi']),
    ('1005-Interpretations-31-()-2-xi', ['1005', '31', 'Interp', '2', 'xi']),
    ('1005-Interpretations-Appendix:A-2', ['1005', 'A', '2', 'Interp']),
    ('1005-Appendix:A-2', ['1005', 'A', '2']),
    ('1005-Subpart:A-2', ['1005', '2']),
    ('1005-Subjgrp:AbCd-2', ['1005', '2']),
])
def test_fix_label(in_label, out_label):
    """Fix label converts between the AMDPAR label format and the Node
    label format"""
    amd = Amendment('action', in_label)
    assert amd.label == out_label


def test_amendment_heading():
    amendment = Amendment('PUT', '100-2-a[heading]')
    assert amendment.action == 'PUT'
    assert amendment.label == ['100', '2', 'a']
    assert amendment.field == '[heading]'


@pytest.mark.parametrize('label,expected', [
    ('100', None),
    ('100-Interpretations', None),
    ('100-Subpart:A-105', ['100', 'Subpart', 'A']),
    ('100-Subjgrp:AbCdE', ['100', 'Subjgrp', 'AbCdE']),
    ('100-Appendix:R', ['100', 'R'])
])
def test_tree_format_level2(label, expected):
    assert Amendment('VERB', label).tree_format_level2() == expected
