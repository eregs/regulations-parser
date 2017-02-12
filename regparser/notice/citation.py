import attr


@attr.attrs(slots=True, frozen=True)
class Citation(object):
    volume = attr.attrib(convert=int)
    page = attr.attrib(convert=int)

    def formatted(self):
        return '{0} FR {1}'.format(self.volume, self.page)

    def asdict(self):
        return attr.asdict(self)
