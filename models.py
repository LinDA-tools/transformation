from django.db import models

### first draft!


class CSV(models.Model):
    rdf_subject = models.CharField()
    colums = models.ForeignKey(Column, verbose_name="one column of the CSV")
    additional_triples = models.ForeignKey(AdditinalTriple, verbose_name="additional triples")

class Column(models.Model):
    fields = models.ForeignKey(Field, verbose_name="single db fields")
    topic = models.CharField()
    rdf_predicate = models.CharField()

class Field(models.Model):
    content = models.CharField()
    index = models.IntegerField()
    rdf_object = models.CharField()

class AdditinalTriple(models.Model):
    rdf_subject = models.CharField()
    rdf_object = models.CharField()

