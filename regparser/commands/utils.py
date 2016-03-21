def relevant_paths(root_dir, only_title, only_part):
    """We may want to filter the paths we search in to those relevant to a
    particular cfr title/part. Most index entries encode this as their first
    two path components"""
    title_dirs = [(root_dir / title) for title in root_dir
                  if not only_title or str(only_title) == title]
    part_dirs = [(title_dir / part)
                 for title_dir in title_dirs for part in title_dir
                 if not only_part or str(only_part) == part]
    return [(part_dir / child)
            for part_dir in part_dirs for child in part_dir]
