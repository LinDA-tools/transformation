from django.http import HttpResponseRedirect
from django.shortcuts import render, render_to_response
from django.template import RequestContext
from .forms import *
from django.core.urlresolvers import reverse
import csv
import xlrd
from io import TextIOWrapper
from io import StringIO


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
            if request.POST and form.is_valid():
                print("PATH 1.1")
                print(str(form.cleaned_data))
                # content  is passed on via hidden html input fields
                if form.cleaned_data['hidden_csv_raw_field']:
                    csv_raw = form.cleaned_data['hidden_csv_raw_field']
                    csv_rows, csv_dialect = process_csv(StringIO(form.cleaned_data['hidden_csv_raw_field']), form)
                    print(csv_rows)
                    print(csv_dialect)
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
                    # the file is also provided in raw formatting, so users can appy changes (choose csv params) without reloading file 
                    csv_raw = csvfile.read()
                    csv_rows, csv_dialect = process_csv(csvfile, form)

        html_post_data = {'form': form, 'csvContent': csv_rows[:11], 'csvRaw': csv_raw, 'csvDialect': csv_dialect, 'filename': uploadFileName}

                # which button was pressed?
                # http://stackoverflow.com/questions/866272/how-can-i-build-multiple-submit-buttons-django-form
        if 'button_upload' in request.POST:
            return render_to_response('transformation/csv_upload.html', html_post_data, context_instance=RequestContext(request))
        elif 'button_next' in request.POST:
            return render_to_response('transformation/csv_column_choice.html', html_post_data, context_instance=RequestContext(request))
                # TODO send datamodel id here instead of csv content
    # html GET
    else:

        print("PATH 4")
        print('HTML GET!')
        form = UploadFileForm()
        return render_to_response('transformation/csv_upload.html', {'form': form}, context_instance=RequestContext(request))


def process_csv(csvfile, form):
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
    csvreader = csv.reader(csvfile, dialect)
    for row in csvreader:
        csv_rows.append(row)

    return [csv_rows, csv_dialect]

def Excel2CSV(ExcelFile, CSVFile):
     workbook = xlrd.open_workbook(ExcelFile)
     worksheet = workbook.sheet_by_index(0)
     csvfile = open(CSVFile, 'wb')
     wr = csv.writer(csvfile, quoting=csv.QUOTE_ALL)

     for rownum in xrange(worksheet.nrows):
         wr.writerow(
             list(x.encode('utf-8') if type(x) == type(u'') else x
                  for x in worksheet.row_values(rownum)))

     csvfile.close()

def csv_column_choice(request):
    if request.method == 'POST':
        form = CsvColumnChoiceForm(request.POST, request.FILES)
        if form.is_valid():
            print('  --  csv column choice: POST  --  ')
            return render_to_response('transformation/csv_column_choice.html', {'form': form}, context_instance=RequestContext(request))
        else:
            print('form not valid')
            print(form.errors)
    else:
        print('Form not valid!')
        form = DataChoiceForm()
    return render_to_response('transformation/csv_column_choice.html', {'form': form}, context_instance=RequestContext(request))





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
