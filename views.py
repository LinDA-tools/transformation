from django.http import HttpResponseRedirect
from django.shortcuts import render, render_to_response, redirect
from django.template import RequestContext
from .forms import *
from django.core.urlresolvers import reverse
import csv
import xlrd
from io import TextIOWrapper
from io import StringIO
from transformation.models import *
from django.db import transaction



# ###############################################
#  MODELS 
# ###############################################


def index(request):
    print("CSV")
    if request.method == 'POST':
        # handle the uploaded file here
        raise






def csv_upload(request):
    if request.method == 'POST':
        csv_raw = None
        csv_rows = None
        csv_dialect = None
        uploadFileName = 'no file selected'
        
        # if page was loaded without a selecting a file in html form    
        if not request.FILES:
            form = UploadFileForm(request.POST)
            if request.POST and form.is_valid() and form != None:
                print("PATH 1.1")
                # print(str(form.cleaned_data))
                # content  is passed on via hidden html input fields
                if form.cleaned_data['hidden_csv_raw_field']:
                    csv_raw = form.cleaned_data['hidden_csv_raw_field']
                    csv_rows, csv_dialect = process_csv(StringIO(form.cleaned_data['hidden_csv_raw_field']), form)
                else:
                    print('no raw csv')

                uploadFileName = form.cleaned_data['hidden_filename_field']


            # if page is loaded without POST
            else: 
                print("PATH 1.2")

        # when an upload file was selected in html form
        else:
            print("PATH 3")

            form = UploadFileForm(request.POST, request.FILES)
            uploadFileName = request.FILES['upload_file'].name

            if form.is_valid():
                csv_rows = []
                csvLines = []
                rows = []
                csv_dialect = {}
                csv_raw = ""

                # https://docs.python.org/2/library/csv.html#
                with TextIOWrapper(request.FILES['upload_file'].file, encoding=request.encoding) as csvfile:
                #with TextIOWrapper(request.FILES['upload_file'].file, encoding='utf-8') as csvfile:
                    # the file is also provided in raw formatting, so users can appy changes (choose csv params) without reloading file 
                    csv_raw = csvfile.read()
                    csv_rows, csv_dialect = process_csv(csvfile, form)

                # which button was pressed?
                # http://stackoverflow.com/questions/866272/how-can-i-build-multiple-submit-buttons-django-form
        if 'button_upload' in request.POST:
            csv_rows = csv_rows[:11] if csv_rows else None
            html_post_data = {'form': form, 'csvContent': csv_rows, 'csvRaw': csv_raw, 'csvDialect': csv_dialect, 'filename': uploadFileName}
            return render(request, 'transformation/csv_upload.html', html_post_data)
        elif 'button_next' in request.POST:
            #html_post_data = {'form': form, 'csvContent': csv_rows, 'csvDialect': csv_dialect, 'filename': uploadFileName}
            csv_db_id = store_csv_in_model(csv_rows=csv_rows, csv_raw=csv_raw, file_name=uploadFileName)
            request.session['csv_db_id'] = csv_db_id
            return redirect(reverse('csv-column-choice-view'))
            #return render(request, 'transformation/csv_column_choice.html', html_post_data)
    # html GET
    else:

        print("PATH 4")
        print('HTML GET!')
        form = UploadFileForm()
        #return render_to_response('transformation/csv_upload.html', {'form': form}, context_instance=RequestContext(request))
        return render(request, 'transformation/csv_upload.html', {'form': form})





def csv_column_choice(request):
    if request.method == 'POST':
        pass
    else:
        m_csv = CSV.objects.filter(id=request.session['csv_db_id'])[0]
        print(m_csv)
    return render(request, 'transformation/csv_column_choice.html', {'id':request.session['csv_db_id']})





def data_choice(request):
    if request.method == 'POST':
        form = DataChoiceForm(request.POST, request.FILES)
        if form.is_valid():
            print('  --  data choice: POST  --  ')
            return render_to_response('transformation/data_choice.html', {'form': form}, context_instance=RequestContext(request))
        else:
            print('form not valid')
            print(form.errors)
    else:
        print('Form not valid!')
        form = DataChoiceForm()
    return render_to_response('transformation/data_choice.html', {'form': form}, context_instance=RequestContext(request))





# ###############################################
#  OTHER FUNCTIONS 
# ###############################################


def csv_model_2_array(m_id):
    m_csv = CSV.objects.filter(id=m_id)[0]
    m_columns = Column.objects.filter(csv=m_csv.id)
    m_fields = []
    for col in m_columns:
        m_fields.append(Field.objects.filter(column=col.id))
# TODO WIP hier weitermachen, db model nach array struktur wie 'csvContent': csv_rows
# oder einfach JSON object speichern?? einfacher?



def process_csv(csvfile, form):
    '''
    Processes the CSV File and converts it to a 2dim array.
    Uses either the CSV Paramaters specified in the HTML form if those exist
    or the autodetected params instead.
    '''
    csv_dialect = {}
    csv_rows = []
    csvfile.seek(0)
    # Sniffer guesses CSV parameters / dialect
    # when error 'could not determine delimiter' -> raise bytes to sniff
    dialect = csv.Sniffer().sniff(csvfile.read(10240))
    csvfile.seek(0)
    # ['delimiter', 'doublequote', 'escapechar', 'lineterminator', 'quotechar', 'quoting', 'skipinitialspace']
    csv_dialect['delimiter']=dialect.delimiter
    csv_dialect['escape']=dialect.escapechar
    csv_dialect['quotechar']=dialect.quotechar
    csv_dialect['line_end']=dialect.lineterminator.replace('\r', 'cr').replace('\n', 'lf')

    # use csv params / dialect chosen by user if specified 
    # to avoid '"delimiter" must be an 1-character string' error, I encoded to utf-8
    # http://stackoverflow.com/questions/11174790/convert-unicode-string-to-byte-string
    if form.cleaned_data['delimiter'] != "":
        dialect.delimiter = form.cleaned_data['delimiter'].encode('utf-8')
    if form.cleaned_data['escape'] != "":
        dialect.escapechar = form.cleaned_data['escape'].encode('utf-8')
    if form.cleaned_data['quotechar'] != "":
        dialect.quotechar = form.cleaned_data['quotechar'].encode('utf-8')
    if form.cleaned_data['line_end'] != "":
        dialect.lineterminator = form.cleaned_data['line_end'].encode('utf-8')

    #print(dir(dialect))
    #print(dialect.delimiter)
    csvreader = unicode_csv_reader(csvfile, dialect)
    for row in csvreader:
        csv_rows.append(row)

    return [csv_rows, csv_dialect]

# http://stackoverflow.com/questions/1136106/what-is-an-efficent-way-of-inserting-thousands-of-records-into-an-sqlite-table-u
@transaction.commit_manually
def store_csv_in_model(csv_rows, csv_id=None, csv_raw=None, file_name=None):
    '''
    Stores the 2dim array representation of the CSV file in the database.
    '''
    num_columns = len(csv_rows[0])
    # http://stackoverflow.com/questions/17037566/transpose-a-matrix-in-python
    csv_transpose = list(zip(*csv_rows))
    if csv_id==None:
        m_csv = CSV()
        m_csv.save()
        if csv_raw and file_name:
            m_csv_file = CSVFile(data=csv_raw, file_name=file_name, csv=m_csv)
            m_csv_file.save()
        for row in csv_transpose:
            m_column = None
            for num_field, field in enumerate(row):
                if num_field == 0: # csv row topic
                    m_column = Column(csv=m_csv)
                    m_column.topic = row
                    m_column.save()
                    print("column "+str(m_column.id))
                else:
                    m_field = Field(content=field, index=num_field, data_type=0, column=m_column)
                    m_field.save()
        m_csv.save()
        print("CSV #"+str(m_csv.id)+" stored in DB.")
    else:
        m_csv = CSV.objects.filter(id=csv_id)[0]
    #if m_csv == None
    # TODO catch
    transaction.commit()
    return m_csv.id



def Excel2CSV(ExcelFile, CSVFile):
    '''
    Converts an MS Excel file to a CSV file.
    '''
    workbook = xlrd.open_workbook(ExcelFile)
    worksheet = workbook.sheet_by_index(0)
    csvfile = open(CSVFile, 'wb')
    wr = csv.writer(csvfile, quoting=csv.QUOTE_ALL)

    for rownum in xrange(worksheet.nrows):
        wr.writerow(
            list(x.encode('utf-8') if type(x) == type(u'') else x
                for x in worksheet.row_values(rownum)))

    csvfile.close()




def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    '''
    Used to read Umlauts from CSV files.
    '''
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, 'utf-8') for cell in row]

def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')
