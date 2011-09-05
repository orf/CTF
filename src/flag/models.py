from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin
import util
import re
from django import forms
import datetime


ANSWER_REGEX = re.compile("^[a-zA-Z0-9\s]+$") # Match a-z, A-Z, 0-9 and whitespace

class Feedback(models.Model):
    user = models.ForeignKey(User, related_name="feedback")
    text = models.TextField()

# Settings object
class CTFSetting(models.Model):
    event_title = models.CharField(max_length=100)
    workshop_title = models.CharField(max_length=150)
    workshop_date = models.DateField()
    logo = models.ImageField(upload_to="static/uploads/")
    points_for_first_answer = models.PositiveIntegerField()
    workshop_finished = models.BooleanField()
    
    primary_trainer = models.CharField(max_length=512)
    secondary_trainer = models.CharField(max_length=512)

admin.site.register(CTFSetting)

# Extention of the user class
class AdditionalUserInformation(models.Model):
    user = models.OneToOneField(User, related_name="additional_info")
    
    company = models.CharField(max_length=254, null=True)
    title   = models.CharField(max_length=254, null=True)
    
    points = models.IntegerField(null=True)

    def get_right_answers(self):
        return Answer.objects.filter(user=self.user).filter(correct=True)
    
# Questions
class Question(util.OrderedModel):
    title = models.CharField(max_length=1024)
    question = models.CharField(max_length=2048)
    answer = models.CharField(max_length=2048)
    
    active = models.BooleanField(default=False, db_index=True)
    started = models.DateTimeField(null=True)
    finish = models.DateTimeField(null=True)
    
    urls = models.TextField(null=True, blank=True)
    
    points = models.PositiveIntegerField()
    
    def get_time_left(self):
        return round((self.finish - datetime.datetime.now()).total_seconds(),0)
    
    def is_active(self):
        if not self.active:
            return False
        if (self.finish - datetime.datetime.now()).total_seconds() < 0:
            self.active = False
            self.save()
        return self.active
    
    def iter_urls(self):
        return self.urls.split("\n")
    
    def has_answered(self, user):
        return self.answers.filter(user=user).exists()
    
    def get_answer(self, user):
        try:
            return self.answers.filter(user=user).get()
        except Answer.DoesNotExist:
            return None
        
    def get_correct_answers(self):
        return self.answers.filter(answer=self.answer)
        
    def enumerate_answers(self):
        # Latest answers first
        return self.answers.order_by("submitted").select_related().all()
    
    def get_first(self):
        return self.answers.filter(correct=True).order_by("submitted")[0]
    
    def get_first_time(self):
        return self.get_first().submitted
        
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('title','question','points','order_link')
    exclude = ("active","started", "finish")

admin.site.register(Question, QuestionAdmin)


# Answers
class Answer(models.Model):
    answer = models.TextField(db_index=True)
    question = models.ForeignKey(Question, related_name="answers",db_index=True)
    user   = models.ForeignKey(User, related_name="answers", db_index=True)
    submitted = models.DateTimeField(auto_now=True, db_index=True)
    
    correct = models.BooleanField()
    
    def is_first(self):
        if self.question.answers.filter(correct=True).filter(submitted__lt=self.submitted).count():
            return False
        return True
    
    @staticmethod
    def is_answer_valid(answer):
        if not bool(ANSWER_REGEX.match(answer)):
            raise forms.ValidationError("Only alphanumeric characters please")