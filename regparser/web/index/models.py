from django.db import models


class DependencyNode(models.Model):
    label = models.CharField(max_length=512, primary_key=True)


class Dependency(models.Model):
    target = models.ForeignKey(DependencyNode, related_name='target_of',
        null=True, on_delete=models.SET_NULL)
    depender = models.ForeignKey(DependencyNode, related_name='depends_on',
        null=True, on_delete=models.SET_NULL)


class EntryManager(models.Manager):
    """We usually don't intend to deserialize the binary (often quite large)
    "contents" field, so defer its inclusion by default"""
    def get_queryset(self):
        return super(EntryManager, self).get_queryset().defer('contents')


class Entry(models.Model):
    # label = models.OneToOneField(DependencyNode, primary_key=True,
    #     null=True, on_delete=models.SET_NULL)
    label = models.OneToOneField(DependencyNode, default='', primary_key=True, null=False, on_delete=models.SET_DEFAULT)
    modified = models.DateTimeField(auto_now=True)
    contents = models.BinaryField()

    objects = EntryManager()

    class Meta:
        ordering = ['label']
