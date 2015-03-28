from django import forms

class UploadFileForm(forms.Form):
    line_end = forms.CharField(max_length=4,required = False)
    delimiter = forms.CharField(max_length=1,required = False)
    escape = forms.CharField(max_length=1,required = False)
    quotechar = forms.CharField(max_length=1,required = False)
    #won't get automatically refilled for security reasons http://stackoverflow.com/questions/3097982/how-to-make-a-django-form-retain-a-file-after-failing-validation
    upload_file = forms.FileField(required = False)
    hidden_filename_field = forms.CharField(widget=forms.HiddenInput(),required = False)
    #hidden_csv_content_field = forms.CharField(widget=forms.HiddenInput(),required = False)
    hidden_csv_raw_field = forms.CharField(widget=forms.HiddenInput(),required = False)
    #hidden_csv_dialect_field = forms.CharField(widget=forms.HiddenInput(),required = False)

class DataChoiceForm(forms.Form):
    list = [('1','choose'), ('2','your'),('3','file'), ('4','here'), ]
    fileList = forms.ChoiceField( choices = list, required = False,)
    fileList.widget.attrs['class'] = 'data_source_select'
    fileList.widget.attrs['size'] = '5'
    initial={'max_number': '3'}

class CsvColumnChoiceForm(forms.Form):
    FAVORITE_COLORS_CHOICES = (('blue', 'Blue'),
                            ('green', 'Green'),
                            ('black', 'Black'))
    columns = forms.MultipleChoiceField(required=False,
        widget=forms.CheckboxSelectMultiple, choices=FAVORITE_COLORS_CHOICES)
