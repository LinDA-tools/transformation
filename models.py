from django.db import models

### first draft!



# temporary person model, to be exchanged with LinDA Workbench User System

class Interest(models.Model):
    name = models.CharField(max_length='512')

class Person(models.Model):
    first_name = models.CharField(max_length='512')
    last_name = models.CharField(max_length='512')
    interest = models.ForeignKey(Interest, verbose_name="user's field of interest")

# end person model

class Field(models.Model):
    DATATYPES = (
        (0, 'none'),
        (1, 'reconciliated'),
        (2, 'Integer'),
        (3, 'Date'),
        (4, 'Text'),
        (4, 'Currency'),
        # more?
    )
    content = models.CharField(max_length='512')
    index = models.IntegerField()
    rdf_object = models.CharField(max_length='512')
    data_type = models.IntegerField(default=0, choices=DATATYPES)

class Column(models.Model):
    fields = models.ForeignKey(Field, verbose_name="single db fields")
    topic = models.CharField(max_length='512')
    rdf_predicate = models.CharField(max_length='512')

class AdditionalTriple(models.Model):
    rdf_subject = models.CharField(max_length='512')
    rdf_object = models.CharField(max_length='512')

class CSV(models.Model):
    rdf_subject = models.CharField(max_length='512')
    colums = models.ForeignKey(Column, verbose_name="one column of the CSV")
    additional_triples = models.ForeignKey(AdditionalTriple, verbose_name="additional triples")
    owner = models.ForeignKey(Person, verbose_name="Owner / creator of represented data model")


