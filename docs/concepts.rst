Concepts
========

- **Diff**: a structure representing the changes between two regulation trees, describing which nodes were modified, deleted, or added.
- **Layer**: a grouping of extra information about the regulation, generally tied to specific text. For example, citations are a layer which refers to the text in a specific paragraph. There are also layers which apply to the entire tree, for example, the regulation letter. These are more or less a catch all for information which doesn't directly fit in the tree.
- **Rule**: a representation of the 
  `same concept as issued by the Federal Register <https://www.federalregister.gov/articles/search?conditions%5Bpublication_date%5D%5Bis%5D=11%2F02%2F2015&conditions%5Btype%5D=RULE>`_. Sometimes called a **notice**. Rules change regulations, and have a great deal of meta data. Rules contain the contents, effective dates, and the authors of those changes. They can also potentially contain detailed analyses of each of the sections that changed.
- **Tree**: a representation of the regulation content. It's a recursive structure, where each component (part, subpart, section, paragraph, sub-sub-sub paragraph, etc.) is also a tree
