from django.db import models
from django.contrib.auth.models import User

# ## first draft!


'''
# temporary person model, to be exchanged with LinDA Workbench User System

class Interest(models.Model):
    name = models.CharField(max_length='512')


class Person(models.Model):
    first_name = models.CharField(max_length='512')
    last_name = models.CharField(max_length='512')
    interest = models.ForeignKey(Interest, verbose_name="user's field of interest, e.g. profession")

# end person model
'''

'''
class CSV(models.Model):
    rdf_subject = models.CharField(max_length='512', default=None, blank=True, null=True)
    # owner = models.ForeignKey(Person, verbose_name="Owner / creator of represented data model")
    def __str__(self):
        return "CSV #" + str(self.id)


class Column(models.Model):
    topic = models.CharField(max_length='512')
    rdf_predicate = models.CharField(max_length='512', default=None, blank=True, null=True)
    csv = models.ForeignKey(CSV, default=None, blank=True, null=True,
                            verbose_name="CSV representation this column belongs to")

    def __str__(self):
        return "CSV Column #" + str(self.id) + " (CSV #" + str(self.csv.id) + ")"


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
    column = models.ForeignKey(Column, default=None, blank=True, null=True,
                               verbose_name="table column this is a single field of")
    index = models.IntegerField()
    rdf_object = models.CharField(max_length='512', default=None, blank=True, null=True)
    data_type = models.IntegerField(default=0, choices=DATATYPES)

    def __str__(self):
        return "CSV Field #" + str(self.id) + " (CSV #" + str(self.column.csv.id) + ", Column #" + str(
            self.column.id) + ")"


class AdditionalTriple(models.Model):
    rdf_subject = models.CharField(max_length='512')
    rdf_object = models.CharField(max_length='512')
    csv = models.ForeignKey(CSV, default=None, blank=True, null=True,
                            verbose_name="CSV representation this additinal triple belongs to")

    def __str__(self):
        return "CSV Additional Triple #" + str(self.id) + " (CSV #" + str(self.csv.id) + ")"


# https://djangosnippets.org/snippets/1597/
# stores the raw csv data file
class CSVFile(models.Model):
    csv = models.ForeignKey(CSV, default=None, blank=True, null=True,
                            verbose_name="CSV representation this raw csv data belongs to")

    _data = models.TextField(
        db_column='data',
        blank=True)

    def set_data(self, data):
        #self._data = base64.encodestring(data)
        self._data = data

    def get_data(self):
        return data  #base64.decodestring(self._data)

    data = property(get_data, set_data)
    file_name = models.CharField(max_length='512', default=None, blank=True, null=True)

    def __str__(self):
        return "CSV CSV File #" + str(self.id) + " (CSV #" + str(self.csv.id) + ")"
'''
class Mapping(models.Model):
    user = models.ForeignKey(User)
    date = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    fileName = models.CharField(max_length='512', null=True)
    csvName = models.CharField(max_length='512', null=True)
    mappingFile = models.FileField(upload_to='transformation/mappings')
    
# ###############################################
#########       RDB                    ##########
# ###############################################

class DbMapping(models.Model):
    DATABASE_TYPES = (
        ('MY', 'MySQL'),
        ('PO', 'PostgreSQL'),
        ('SL', 'SQLite'),
        ('OR', 'Oracle'),
        ('MS', 'MS-SQL-Server'),
    )
    user = models.ForeignKey(User)
    name = models.CharField(max_length=50, blank=True, default='')
    date = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    host = models.CharField(max_length=50)
    port = models.CharField(max_length=6, blank=True)
    type = models.CharField(max_length=2, choices=DATABASE_TYPES)
    database = models.CharField(max_length=50)
    dbuser = models.CharField(max_length=50, default='')
    password = models.CharField(max_length=50)
    model = models.TextField(default='')
    fkeys = models.TextField(default='')
    current_page = models.IntegerField(default=1)

    def __str__(self):
        return "DbMapping #" + str(self.name)

# ###############################################
#########       END RDB                ##########
# ###############################################

