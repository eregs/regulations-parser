from django.db import models


class DependencyNode(models.Model):
    label = models.CharField(max_length=512, primary_key=True)


class Dependency(models.Model):
    target = models.ForeignKey(DependencyNode, related_name='target_of')
    depender = models.ForeignKey(DependencyNode, related_name='depends_on')


class Entry(models.Model):
    label = models.OneToOneField(DependencyNode, primary_key=True)
    modified = models.DateTimeField(auto_now=True)
    contents = models.BinaryField()

    class Meta:
        ordering = ['label']
