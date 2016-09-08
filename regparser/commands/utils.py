def relevant_paths(root_dir, only_title, only_part):
    """We may want to filter the paths we search in to those relevant to a
    particular cfr title/part. Most index entries encode this as their first
    two path components"""
    prefix_path = root_dir.path
    for sub_entry in root_dir.sub_entries():
        suffix_path = sub_entry.path[len(prefix_path):]
        if only_title and suffix_path[0] != str(only_title):
            continue
        if only_part and suffix_path[1] != str(only_part):
            continue
        yield sub_entry
