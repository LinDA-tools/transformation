from django.http import HttpResponseRedirect
from django.shortcuts import render, render_to_response
from django.template import RequestContext
from .forms import *
from django.core.urlresolvers import reverse
import csv
from io import TextIOWrapper


def index(request):
    print("CSV")
    if request.method == 'POST':
        # handle the uploaded file here
        raise





def csv_upload(request):
    if request.method == 'POST':
        
        # if page was loaded without a selecting a file in html form    
        if not request.FILES:
            form = UploadFileForm(request.POST)
            if request.POST and form.is_valid():
                # content  is passed on via hidden html input fields
                csvRows = eval(form.cleaned_data['hidden_csvContent_field'])
                csv_dialect = None
                uploadFileName = form.cleaned_data['hidden_filename_field']
            # if page is loaded without POST
            else: 
                csvRows = None
                csv_dialect = None
                uploadFileName = 'no file selected'
        # when an upload file was selected in html form
        else:
            print("first else")
            form = UploadFileForm(request.POST, request.FILES)
        
            uploadFileName = request.FILES['upload_file'].name

            if form.is_valid():
                csvRows = []
                csvLines = []
                rows = []
                csv_dialect = {}

                # https://docs.python.org/2/library/csv.html#
                with TextIOWrapper(request.FILES['upload_file'].file, encoding=request.encoding) as csvfile:
                    #Sniffer guesses CSV parameters / dialect
                    dialect = csv.Sniffer().sniff(csvfile.read(1024))
                    csvfile.seek(0)
                    print("DIALECT")
                    # ['delimiter', 'doublequote', 'escapechar', 'lineterminator', 'quotechar', 'quoting', 'skipinitialspace']
                    csv_dialect['delimiter']=dialect.delimiter
                    csv_dialect['escape']=dialect.escapechar
                    csv_dialect['quotechar']=dialect.quotechar
                    csv_dialect['line_end']=dialect.lineterminator.replace('\r', 'cr').replace('\n', 'lf')

                    
                    #print(dir(dialect))
                    #print(dialect.delimiter)
                    csvreader = csv.reader(csvfile, dialect)
                    for row in csvreader:
                        csvRows.append(row)

        html_post_data = {'form': form, 'csvContent': csvRows, 'csvDialect': csv_dialect, 'filename': uploadFileName}
                # which button was pressed?
                # http://stackoverflow.com/questions/866272/how-can-i-build-multiple-submit-buttons-django-form
        if 'button_upload' in request.POST:
            return render_to_response('transformation/csv_upload.html', html_post_data, context_instance=RequestContext(request))
        elif 'button_next' in request.POST:
            return render_to_response('transformation/csv_column_choice.html', html_post_data, context_instance=RequestContext(request))
                # TODO send datamodel id here instead of csv content
    # html GET
    else:
        print('HTML GET!')
        form = UploadFileForm()
        return render_to_response('transformation/csv_upload.html', {'form': form}, context_instance=RequestContext(request))





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
