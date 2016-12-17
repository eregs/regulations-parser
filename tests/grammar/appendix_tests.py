from regparser.grammar import appendix


def test_par():
    match = appendix.headers.parseString("3(c)(4) Pandas")
    assert match.section == '3'
    assert match.p1 == 'c'
    assert match.p2 == '4'


def test_section():
    match = appendix.headers.parseString("Section 105.11")
    assert match.part == '105'
    assert match.section == '11'


def test_newline():
    starts = [start for _, start, _ in
              appendix.headers.scanString("\nSection 100.22")]
    assert starts[0] == 1
    starts = [start for _, start, _ in
              appendix.headers.scanString("\nParagraph 2(b)(2)")]
    assert starts[0] == 1


def test_marker_par():
    match = appendix.headers.parseString("Paragraph 3(b)")
    assert match.section == '3'
    assert match.p1 == 'b'


def test_appendix():
    match = appendix.headers.parseString("Appendix M - More Info")
    assert match.appendix == 'M'
