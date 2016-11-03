def title_body(text):
    """Split text into its first line (the title) and the rest of the text."""
    newline = text.find("\n")
    if newline < 0:
        return text, ""
    return text[:newline], text[newline:]
