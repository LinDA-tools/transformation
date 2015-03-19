from django import forms

class UploadFileForm(forms.Form):
    separator = forms.CharField(max_length=1,required = False)
    delimiter = forms.CharField(max_length=1,required = False)
    escape = forms.CharField(max_length=1,required = False)
    quotechar = forms.CharField(max_length=1,required = False)
    #won't get automatically refilled for security reasons http://stackoverflow.com/questions/3097982/how-to-make-a-django-form-retain-a-file-after-failing-validation
    file = forms.FileField()
