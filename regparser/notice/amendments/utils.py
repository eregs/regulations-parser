def label_amdpar_from(instruction_xml):
    label_parts = instruction_xml.get('label', '').split('-')
    # <AMDPAR><EREGS_INSTRUCTIONS><INSTRUCTION>...
    amdpar = instruction_xml.getparent().getparent()
    return label_parts, amdpar
