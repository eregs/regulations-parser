# vim: set fileencoding=utf-8
from regparser.layer.terms import ParentStack, Terms
from regparser.layer.def_finders import Ref
from regparser.tree.struct import Node
import settings
from unittest import TestCase


class LayerTermTest(TestCase):
    def setUp(self):
        self.original_ignores = settings.IGNORE_DEFINITIONS_IN
        settings.IGNORE_DEFINITIONS_IN = {'ALL': {}}

    def tearDown(self):
        settings.IGNORE_DEFINITIONS_IN = self.original_ignores

    def test_is_exclusion(self):
        t = Terms(None)
        n = Node('ex ex ex', label=['1111', '2'])
        self.assertFalse(t.is_exclusion('ex', n))

        t.scoped_terms = {('1111',): [Ref('abc', '1', 0)]}
        self.assertFalse(t.is_exclusion('ex', n))

        t.scoped_terms = {('1111',): [Ref('ex', '1', 0)]}
        self.assertFalse(t.is_exclusion('ex', n))
        n.text = u'Something something the term “ex” does not include potato'
        self.assertTrue(t.is_exclusion('ex', n))

        t.scoped_terms = {('1111',): [Ref('abc', '1', 0)]}
        self.assertFalse(t.is_exclusion('ex', n))

    def test_node_definitions_no_def(self):
        """Verify that none of the matchers match certain strings"""
        t = Terms(None)
        stack = ParentStack()
        stack.add(0, Node(label=['999']))
        stack.add(1, Node('Definitions', label=['999', '1']))

        no_defs = ['This has no defs',
                   'Also has no terms',
                   'Still no terms, but',
                   'the next one does']

        for txt in no_defs:
            defs, exc = t.node_definitions(Node(txt), stack)
            self.assertEqual([], defs)
            self.assertEqual([], exc)

    def test_node_defintions_act(self):
        t = Terms(None)
        stack = ParentStack()
        stack.add(0, Node('Definitions', label=['9999']))

        node = Node(u'“Act” means something else entirely')
        included, excluded = t.node_definitions(node, stack)
        self.assertEqual(1, len(included))
        self.assertEqual([], excluded)

    def test_node_definitions_needs_term(self):
        t = Terms(None)
        stack = ParentStack()
        stack.add(0, Node('Definitions', label=['9999']))
        node = Node(u"However, for purposes of rescission under §§ 1111.15 "
                    + u"and 1111.13, and for purposes of §§ 1111.12(a)(1), "
                    + u"and 1111.46(d)(4), the term means all calendar "
                    + u"days...")
        self.assertEqual(([], []), t.node_definitions(node, stack))

    def test_node_definitions_exclusion(self):
        n1 = Node(u'“Bologna” is a type of deli meat', label=['111', '1'])
        n2 = Node(u'Let us not forget that the term “bologna” does not ' +
                  'include turtle meat', label=['111', '1', 'a'])
        t = Terms(Node(label=['111'], children=[n1, n2]))
        t.pre_process()

        stack = ParentStack()
        stack.add(1, Node('Definitions'))

        included, excluded = t.node_definitions(n1, stack)
        self.assertEqual([Ref('bologna', '111-1', 1)], included)
        self.assertEqual([], excluded)
        t.scoped_terms[('111', '1')] = included

        included, excluded = t.node_definitions(n2, stack)
        self.assertEqual([], included)
        self.assertEqual([Ref('bologna', '111-1-a', 33)], excluded)

    def test_node_definitions_multiple_xml(self):
        """Find xml definitions which are separated by `and`"""
        stack = ParentStack().add(0, Node(label=['9999']))
        winter = Node("(4) Cold and dreary mean winter.", label=['9999', '4'])
        winter.tagged_text = ('(4) <E T="03">Cold</E> and '
                              '<E T="03">dreary</E> mean winter.')
        inc, _ = Terms(None).node_definitions(winter, stack)
        self.assertEqual(len(inc), 2)
        cold, dreary = inc
        self.assertEqual(cold, Ref('cold', '9999-4', 4))
        self.assertEqual(dreary, Ref('dreary', '9999-4', 13))

    def test_node_definitions_xml_commas(self):
        """Find xml definitions which have commas separating them"""
        stack = ParentStack().add(0, Node(label=['9999']))
        summer = Node("(i) Hot, humid, or dry means summer.",
                      label=['9999', '4'])
        summer.tagged_text = ('(i) <E T="03">Hot</E>, <E T="03">humid</E>, '
                              'or <E T="03">dry</E> means summer.')
        inc, _ = Terms(None).node_definitions(summer, stack)
        self.assertEqual(len(inc), 3)
        hot, humid, dry = inc
        self.assertEqual(hot, Ref('hot', '9999-4', 4))
        self.assertEqual(humid, Ref('humid', '9999-4', 9))
        self.assertEqual(dry, Ref('dry', '9999-4', 19))

    def test_node_definitions_xml_or(self):
        """Find xml definitions which are separated by `or`"""
        stack = ParentStack().add(0, Node(label=['9999']))
        tamale = Node("(i) Hot tamale or tamale means nom nom",
                      label=['9999', '4'])
        tamale.tagged_text = ('(i) <E T="03">Hot tamale</E> or <E T="03"> '
                              'tamale</E> means nom nom ')
        inc, _ = Terms(None).node_definitions(tamale, stack)
        self.assertEqual(len(inc), 2)
        hot, tamale = inc
        self.assertEqual(hot, Ref('hot tamale', '9999-4', 4))
        self.assertEqual(tamale, Ref('tamale', '9999-4', 18))

    def test_pre_process(self):
        noname_subpart = Node(
            '',
            label=['88', 'Subpart'],
            node_type=Node.EMPTYPART,
            children=[
                Node(u"Definition. For the purposes of this part, "
                     + u"“abcd” is an alphabet", label=['88', '1'])])
        xqxq_subpart = Node(
            '',
            title='Subpart XQXQ: The unreadable',
            label=['88', 'Subpart', 'XQXQ'], node_type=Node.SUBPART,
            children=[
                Node(label=['88', '2'], children=[
                    Node(label=['88', '2', 'a'],
                         text="Definitions come later for the purposes of "
                              + "this section ",
                         children=[
                             Node(u"“AXAX” means axe-cop",
                                  label=['88', '2', 'a', '1'])]),
                    Node(label=['88', '2', 'b'], children=[
                        Node(label=['88', '2', 'b', 'i'], children=[
                            Node(label=['88', '2', 'b', 'i', 'A'],
                                 text=u"Definition. “Awesome sauce” means "
                                      + "great for the purposes of this "
                                      + "paragraph",)])])])])
        tree = Node(label=['88'], children=[noname_subpart, xqxq_subpart])
        t = Terms(tree)
        t.pre_process()

        self.assertTrue(('88',) in t.scoped_terms)
        self.assertEqual([Ref('abcd', '88-1', 44)],
                         t.scoped_terms[('88',)])
        self.assertTrue(('88', '2') in t.scoped_terms)
        self.assertEqual([Ref('axax', '88-2-a-1', 1)],
                         t.scoped_terms[('88', '2')])
        self.assertTrue(('88', '2', 'b', 'i', 'A') in t.scoped_terms)
        self.assertEqual([Ref('awesome sauce', '88-2-b-i-A', 13)],
                         t.scoped_terms[('88', '2', 'b', 'i', 'A')])

        #   Check subparts are correct
        self.assertEqual({None: ['1'], 'XQXQ': ['2']},
                         dict(t.scope_finder.subpart_map))

        # Finally, make sure the references are added
        referenced = t.layer['referenced']
        self.assertTrue('abcd:88-1' in referenced)
        self.assertEqual('abcd', referenced['abcd:88-1']['term'])
        self.assertEqual('88-1', referenced['abcd:88-1']['reference'])
        self.assertEqual((44, 48), referenced['abcd:88-1']['position'])

        self.assertTrue('axax:88-2-a-1' in referenced)
        self.assertEqual('axax', referenced['axax:88-2-a-1']['term'])
        self.assertEqual('88-2-a-1', referenced['axax:88-2-a-1']['reference'])
        self.assertEqual((1, 5), referenced['axax:88-2-a-1']['position'])

        self.assertTrue('awesome sauce:88-2-b-i-A' in referenced)
        self.assertEqual('awesome sauce',
                         referenced['awesome sauce:88-2-b-i-A']['term'])
        self.assertEqual('88-2-b-i-A',
                         referenced['awesome sauce:88-2-b-i-A']['reference'])
        self.assertEqual((13, 26),
                         referenced['awesome sauce:88-2-b-i-A']['position'])

    def test_pre_process_defined_twice(self):
        tree = Node(u"The term “lol” means laugh out loud. "
                    + u"How do you pronounce “lol”, though?",
                    label=['1212', '5'])
        t = Terms(tree)
        t.pre_process()

        self.assertEqual(t.layer['referenced']['lol:1212-5']['position'],
                         (10, 13))

    def test_pre_process_subpart(self):
        root = Node(label=['1212'])
        subpartA = Node(label=['1212', 'Subpart', 'A'], title='Subpart A')
        section2 = Node(label=['1212', '2'], title='1212.2')
        def1 = Node(u"“totes” means in total", label=['1212', '2', 'a'])
        subpartB = Node(label=['1212', 'Subpart', 'B'], title='Subpart B')
        section22 = Node("\nFor the purposes of this subpart",
                         label=['1212', '22'], title='1212.22')
        def2 = Node(u"“totes” means in extremely", label=['1212', '22', 'a'])

        root.children = [subpartA, subpartB]
        subpartA.children, subpartB.children = [section2], [section22]
        section2.children, section22.children = [def1], [def2]

        t = Terms(root)
        t.pre_process()
        self.assertTrue(('1212',) in t.scoped_terms)
        self.assertEqual(len(t.scoped_terms[('1212',)]), 1)
        self.assertEqual('1212-2-a', t.scoped_terms[('1212',)][0].label)

        self.assertTrue(('1212', '22') in t.scoped_terms)
        self.assertEqual(len(t.scoped_terms[('1212', '22')]), 1)
        self.assertEqual('1212-22-a', t.scoped_terms[('1212', '22')][0].label)

    def test_excluded_offsets(self):
        t = Terms(None)
        t.scoped_terms['_'] = [
            Ref('term', 'lablab', 4), Ref('other', 'lablab', 8),
            Ref('more', 'nonnon', 1)
        ]
        self.assertEqual([(4, 8), (8, 13)],
                         t.excluded_offsets('lablab', 'Some text'))
        self.assertEqual([(1, 5)], t.excluded_offsets('nonnon', 'Other'))
        self.assertEqual([], t.excluded_offsets('ababab', 'Ab ab ab'))

    def test_excluded_offsets_blacklist(self):
        t = Terms(None)
        t.scoped_terms['_'] = [Ref('bourgeois', '12-Q-2', 0)]
        settings.IGNORE_DEFINITIONS_IN['ALL'] = ['bourgeois pig']
        excluded = t.excluded_offsets('12-3', 'You are a bourgeois pig!')
        self.assertEqual([(10, 23)], excluded)

    def test_excluded_offsets_blacklist_per_reg(self):
        t = Terms(None)

        t.scoped_terms['_'] = [
            Ref('bourgeois', '12-Q-2', 0),
            Ref('consumer', '12-Q-3', 0)]

        settings.IGNORE_DEFINITIONS_IN['ALL'] = ['bourgeois pig']
        settings.IGNORE_DEFINITIONS_IN['12'] = ['consumer price index']
        exclusions = [(0, 4)]
        excluded = t.per_regulation_ignores(
            exclusions, ['12', '2'], 'There is a consumer price index')
        self.assertEqual([(0, 4), (11, 31)], excluded)

    def test_excluded_offsets_blacklist_word_boundaries(self):
        t = Terms(None)
        t.scoped_terms['_'] = [Ref('act', '28-6-d', 0)]
        settings.IGNORE_DEFINITIONS_IN['ALL'] = ['shed act']
        excluded = t.excluded_offsets('28-9', "That's a watershed act")
        self.assertEqual([], excluded)

    def test_calculate_offsets(self):
        applicable_terms = [('rock band', 'a'), ('band', 'b'), ('drum', 'c'),
                            ('other thing', 'd')]
        text = "I am in a rock band. That's a band with a drum, a rock drum."
        t = Terms(None)
        matches = t.calculate_offsets(text, applicable_terms)
        self.assertEqual(3, len(matches))
        found = [False, False, False]
        for _, ref, offsets in matches:
            if ref == 'a' and offsets == [(10, 19)]:
                found[0] = True
            if ref == 'b' and offsets == [(30, 34)]:
                found[1] = True
            if ref == 'c' and offsets == [(42, 46), (55, 59)]:
                found[2] = True
        self.assertEqual([True, True, True], found)

    def test_calculate_offsets_pluralized1(self):
        applicable_terms = [('rock band', 'a'), ('band', 'b'), ('drum', 'c'),
                            ('other thing', 'd')]
        text = "I am in a rock band. That's a band with a drum, a rock drum."
        text += " Many bands. "
        t = Terms(None)
        matches = t.calculate_offsets(text, applicable_terms)
        self.assertEqual(4, len(matches))
        found = [False, False, False, False]
        for _, ref, offsets in matches:
            if ref == 'a' and offsets == [(10, 19)]:
                found[0] = True
            if ref == 'b' and offsets == [(66, 71)]:
                found[1] = True
            if ref == 'b' and offsets == [(30, 34)]:
                found[2] = True
            if ref == 'c' and offsets == [(42, 46), (55, 59)]:
                found[3] = True
        self.assertEqual([True, True, True, True], found)

    def test_calculate_offsets_pluralized2(self):
        applicable_terms = [('activity', 'a'), ('other thing', 'd')]
        text = "activity, activities."
        t = Terms(None)
        matches = t.calculate_offsets(text, applicable_terms)
        self.assertEqual(2, len(matches))

    def test_calculate_offsets_lexical_container(self):
        applicable_terms = [('access device', 'a'), ('device', 'd')]
        text = "This access device is fantastic!"
        t = Terms(None)
        matches = t.calculate_offsets(text, applicable_terms)
        self.assertEqual(1, len(matches))
        _, ref, offsets = matches[0]
        self.assertEqual('a', ref)
        self.assertEqual([(5, 18)], offsets)

    def test_calculate_offsets_overlap(self):
        applicable_terms = [('mad cow disease', 'mc'), ('goes mad', 'gm')]
        text = 'There goes mad cow disease'
        t = Terms(None)
        matches = t.calculate_offsets(text, applicable_terms)
        self.assertEqual(1, len(matches))
        _, ref, offsets = matches[0]
        self.assertEqual('mc', ref)
        self.assertEqual('mad cow disease', text[offsets[0][0]:offsets[0][1]])

    def test_calculate_offsets_word_part(self):
        """If a defined term is part of another word, don't include it"""
        applicable_terms = [('act', 'a')]
        text = "I am about to act on this transaction."
        t = Terms(None)
        matches = t.calculate_offsets(text, applicable_terms)
        self.assertEqual(1, len(matches))
        self.assertEqual(1, len(matches[0][2]))

    def test_calculate_offsets_exclusions(self):
        applicable_terms = [('act', 'a')]
        text = "This text defines the 'fudge act'"
        t = Terms(None)
        self.assertEqual(
            [], t.calculate_offsets(text, applicable_terms, [(23, 32)]))
        self.assertEqual(
            [('act', 'a', [(29, 32)])],
            t.calculate_offsets(text, applicable_terms, [(1, 5)]))

    def test_process(self):
        t = Terms(Node(children=[
            Node("ABC5", children=[Node("child")], label=['ref1']),
            Node("AABBCC5", label=['ref2']),
            Node("ABC3", label=['ref3']),
            Node("AAA3", label=['ref4']),
            Node("ABCABC3", label=['ref5']),
            Node("ABCOTHER", label=['ref6']),
            Node("ZZZOTHER", label=['ref7']),
        ]))
        t.scoped_terms = {
            ("101", "22", "b", "2", "ii"): [
                Ref("abc", "ref1", 1),
                Ref("aabbcc", "ref2", 2)],
            ("101", "22", "b"): [
                Ref("abc", "ref3", 3),
                Ref("aaa", "ref4", 4),
                Ref("abcabc", "ref5", 5)],
            ("101", "22", "b", "2", "iii"): [
                Ref("abc", "ref6", 6),
                Ref("zzz", "ref7", 7)]}
        #   Check that the return value is correct
        layer_el = t.process(Node(
            "This has abc, aabbcc, aaa, abcabc, and zzz",
            label=["101", "22", "b", "2", "ii"]))
        self.assertEqual(4, len(layer_el))
        found = [False, False, False, False]
        for ref_obj in layer_el:
            if ref_obj['ref'] == 'abc:ref1':
                found[0] = True
            if ref_obj['ref'] == 'aabbcc:ref2':
                found[1] = True
            if ref_obj['ref'] == 'aaa:ref4':
                found[2] = True
            if ref_obj['ref'] == 'abcabc:ref5':
                found[3] = True
        self.assertEqual([True, True, True, True], found)

    def test_process_label_in_node(self):
        """Make sure we don't highlight definitions that are being defined
        in this paragraph."""
        tree = Node(children=[
            Node("Defining secret phrase.", label=['AB', 'a']),
            Node("Has secret phrase. Then some other content",
                 label=['AB', 'b'])
        ], label=['AB'])
        t = Terms(tree)
        t.scoped_terms = {
            ('AB',): [Ref("secret phrase", "AB-a", 9)]
        }
        #   Term is defined in the first child
        self.assertEqual([], t.process(tree.children[0]))
        self.assertEqual(1, len(t.process(tree.children[1])))
