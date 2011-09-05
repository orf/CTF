from django import forms
from django.contrib.auth.forms import UserCreationForm
import models


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = models.Feedback
        fields = ("text",)


class RegisterForm(UserCreationForm):
    email   = forms.EmailField(required=True)
    
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30, required=False)
    
    company = forms.CharField(max_length=254, required=False)
    title   = forms.CharField(max_length=254, required=False)
    
    class Meta:
        model = models.User
        fields = ('username','email','password1','password2')
        
class AnswerForm(forms.Form):
    answer = forms.CharField(max_length=1024, validators=[models.Answer.is_answer_valid])
    
class ActivateForm(forms.Form):
    runtime = forms.IntegerField()