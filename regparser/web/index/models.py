from enum import Enum

from django.db import models
from lxml import etree


class DependencyNode(models.Model):
    label = models.CharField(max_length=512, primary_key=True)


class Dependency(models.Model):
    target = models.ForeignKey(DependencyNode, related_name='target_of')
    depender = models.ForeignKey(DependencyNode, related_name='depends_on')


class SerializedManager(models.Manager):
    """We usually don't intend to deserialize the binary (often quite large)
    "contents" field, so defer its inclusion by default"""
    def get_queryset(self):
        return super(SerializedManager, self).get_queryset().defer('contents')


class Serialized(models.Model):
    contents = models.BinaryField()

    objects = SerializedManager()

    class Meta:
        abstract = True


class Entry(Serialized):
    label = models.OneToOneField(DependencyNode, primary_key=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['label']


class SourceCollection(Enum):
    notice = '{0}'
    annual = '{2} Annual {0} CFR {1}'

    def __init__(self, format_str):
        self.format = format_str.format


class DocCollection(Enum):
    notice = 'notice'
    gpo_cfr = 'gpo_cfr'


class SourceFile(Serialized):
    collection = models.CharField(
        max_length=32, choices=[(c.name, c.name) for c in SourceCollection])
    file_name = models.CharField(max_length=128)

    def xml(self):
        return etree.fromstring(bytes(self.contents))

    class Meta:
        unique_together = ('collection', 'file_name')
        index_together = unique_together


class CFRVersion(models.Model):
    identifier = models.CharField(max_length=64)
    source = models.ForeignKey(
        SourceFile, models.CASCADE, related_name='versions',
        blank=True, null=True)
    delaying_source = models.ForeignKey(
        SourceFile, models.CASCADE, related_name='delays',
        blank=True, null=True)
    effective = models.DateField(blank=True, null=True)
    fr_volume = models.IntegerField()
    fr_page = models.IntegerField()
    cfr_title = models.IntegerField()
    cfr_part = models.IntegerField()

    class Meta:
        unique_together = ('identifier', 'cfr_title', 'cfr_part')
        index_together = unique_together

    @property
    def is_final(self):
        return bool(self.effective)

    @property
    def is_proposal(self):
        return not self.is_final

    def has_doc(self):
        """We can't access self.doc directly, as that will raise an exception
        if the doc does not exist"""
        return Document.objects.filter(version=self).exists()

    def __lt__(self, other):
        """Linearizing versions requires knowing not only relevant dates and
        identifiers, but also which versions are from final rules and which
        are just proposals"""
        sort_fields = ('cfr_title', 'cfr_part', 'fr_volume', 'fr_page',
                       'identifier')
        if self.is_final and other.is_final:
            sort_fields = sort_fields[:2] + ('effective',) + sort_fields[2:]

        left = tuple(getattr(self, field) for field in sort_fields)
        right = tuple(getattr(other, field) for field in sort_fields)
        return left < right

    @staticmethod
    def parents_of(versions):
        """A "parent" of a version is the version which it builds atop.
        Versions can only build on final versions. Assume the versions are
        already sorted"""
        current_parent = None
        for version in versions:
            yield current_parent
            if version.is_final:
                current_parent = version


class Document(Serialized):
    collection = models.CharField(
        max_length=32, choices=[(c.name, c.value) for c in DocCollection])
    label = models.CharField(max_length=128)
    source = models.ForeignKey(SourceFile, models.CASCADE, related_name='docs')
    version = models.OneToOneField(
        CFRVersion, models.CASCADE, related_name='doc', blank=True, null=True)
    previous_document = models.ForeignKey(
        'self', models.CASCADE, related_name='docs', blank=True, null=True)

    class Meta:
        unique_together = ('collection', 'label', 'version')
        index_together = unique_together


class Layer(Serialized):
    document = models.ForeignKey(
        Document, models.CASCADE, related_name='layers')


class Diff(Serialized):
    left_document = models.ForeignKey(
        Document, models.CASCADE, related_name='+')
    right_document = models.ForeignKey(
        Document, models.CASCADE, related_name='+')
