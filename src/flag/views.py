# Create your views here.
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.contrib.auth import authenticate, login as user_login, logout as user_logout
from django.db.models import Q, F, Count, Avg
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from util import OrderedModel
from django.contrib import messages
from django.shortcuts import redirect
import forms
import models
import datetime
import csv
import re

ALPHANUMERIC = re.compile("^(\w|\s)+$")

def render_response(req, *args, **kwargs):
    kwargs['context_instance'] = RequestContext(req)
    if len(args) > 1:
        args[1]["questions"] = models.Question.objects.all()#.filter(active=True)
        try:
            args[1]['ctf_settings'] = models.CTFSetting.objects.get()
        except Exception:
            args[1]['ctf_settings'] = None
    return render_to_response(*args, **kwargs)

@login_required
def list_users(request):
    if not request.user.is_superuser:
        return redirect("/")
    users = models.User.objects.filter(is_superuser=False).all()
    
    return render_response(request, "list_users.html",{"users":users})

@login_required
def feedback(request):
    
    if request.method == "POST":
        form = forms.FeedbackForm(request.POST)
        if form.is_valid():
            # Has the user already given some feedback?
            print form.cleaned_data["text"]
            if not ALPHANUMERIC.match(form.cleaned_data["text"].strip(" ")):
                messages.error(request, "Alphanumeric characters only please")
                return redirect("/feedback")
            
            if request.user.feedback.count():
                feedback = request.user.feedback.get()
            else: feedback = models.Feedback()
            feedback.user = request.user
            feedback.text = form.cleaned_data["text"]
            feedback.save()
            messages.info(request, "Thank you for your feedback!")
            return redirect("/")            
    else:
        
        if request.user.feedback.count():
            form = forms.FeedbackForm(initial={"text":request.user.feedback.get().text})
        else:
            form = forms.FeedbackForm()
    
    return render_response(request, "feedback.html", {"form":form})

@login_required
def export_users(request):
    if not request.user.is_superuser:
        return redirect("/")
    
    settings = models.CTFSetting.objects.get()
    response = HttpResponse(content_type="text/plain")
    writer = csv.writer(response, delimiter=",", quotechar="|", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["Username","Email","First Name","Last Name","Company","Title","Answer count",
                     "Correct answers","First answers count","Points", "Feedback"])
    for user in models.User.objects.filter(is_superuser=False).all():
        company = ""
        title = ""
        if user.additional_info:
            company = user.additional_info.company
            title = user.additional_info.title
        feedback = ""
        if user.feedback.count():
            feedback = user.feedback.get().text
        points = 0
        first = 0
        for answer in user.answers.filter(correct=True):
            points+=answer.question.points
            if answer.is_first():
                first+=1
                points+=settings.points_for_first_answer
        
        writer.writerow([user.username, user.email,
                         user.first_name, user.last_name,
                         company, title,
                         user.answers.count(),
                         user.answers.filter(correct=True).count(),
                         first, 
                         points, feedback
                         ])
    return response


@login_required
def finalize_points(request):
    if not request.user.is_superuser:
        return redirect("/")
    settings = models.CTFSetting.objects.get()
    for user in models.User.objects.filter(is_superuser=False).all():
        points = 0
        for answer in user.answers.filter(correct=True):
            points+=answer.question.points
            if answer.is_first():
                points+=settings.points_for_first_answer
        user.additional_info.points = points
        user.additional_info.save()
    
    settings.workshop_finished = True
    settings.save()
    
    messages.info(request, "Completed")
    return redirect("/")

@login_required
def view_user(request, nickname):
    user = get_object_or_404(models.User, username=nickname)
    if not request.user.is_superuser:
        return redirect("/")
    return render_response(request, "user.html", {"user":user})

@login_required
def generate_report(request):
    # Get the users rank
    settings = models.CTFSetting.objects.get()
    if not settings.workshop_finished:
        messages.error(request, "Go away")
        return redirect("/")
    
    u = list(models.User.objects.distinct().values_list("additional_info__points",flat=True).filter(is_superuser=False) \
             .order_by("-additional_info__points").all())
    count = models.User.objects.filter(is_superuser=False).count()

    try:
        rank = u.index(request.user.additional_info.points) + 1
    except ValueError:
        rank = -1
    
    return render_response(request, "report.html",{"user":request.user,
                                                   "rank":rank,
                                                   "total":count})
    

@login_required
def stats(request):
    if models.Question.objects.filter(active=True).filter(finish__gt=datetime.datetime.now()).count():
        return render_response(request, "stats.html",{"failed":True})
    settings = models.CTFSetting.objects.get()
    answers = request.user.answers.order_by("id").all()
    correct = request.user.answers.filter(correct=True).all()
    points = 0
    # Fuck it, this is so inneficient but I am so fucking tired of Django's shit ORM
    # and jumping through its retarded hoops to get shit done. 
    first_correct_answers = []
    for item in correct:
        if not item.question.answers.filter(correct=True).filter(submitted__lt=item.submitted).count():
            first_correct_answers.append(item)
            points+=settings.points_for_first_answer
        points+=item.question.points
    
    return render_response(request, "stats.html",{"answers":answers,
                                                  "correct":correct,
                                                  "first":first_correct_answers,
                                                  "points":points,
                                                  "failed":False})

@login_required
def boost_time(request, question_id):
    question = get_object_or_404(models.Question, id=question_id)
    if not request.method == "POST":
        return redirect("/")
   
    if not request.user.is_superuser:
        return redirect("/")
    
    if not question.is_active():
        messages.error(request, "You cannot add time to a disabled question!")
    
    extra_time = request.POST["extra_time"]
    if not extra_time.isdigit():
        messages.error(request, "Invalid extra time")
        return redirect("/q/%s"%question.id)
    
    extra_time = int(extra_time)
    
    question.finish += datetime.timedelta(minutes=extra_time)
    question.save()
    messages.success(request, "Added %s minutes to the countdown"%(extra_time))
    return redirect("/q/%s"%question.id)
    

@login_required
def toggle_active(request, question_id):
    question = get_object_or_404(models.Question, id=question_id)
    if not request.method == "POST":
        return redirect("/")
   
    if not request.user.is_superuser:
        return redirect("/")
    

    if question.is_active() == True:
        question.active = False
        question.finish = None
    else:
        form = forms.ActivateForm(request.POST)
        if not form.is_valid():
            messages.error(request, "You did not specify a integer for the countdown")
            return redirect("/q/%s"%question.id)
        question.active = True
        question.finish = datetime.datetime.now()+datetime.timedelta(minutes=form.cleaned_data["runtime"])
        
    if not question.started:
        question.started = datetime.datetime.now()

    
    question.save()
    
    messages.success(request, "Question %s active set to %s"%(question.id, question.active))
    return redirect("/q/%s"%question.id)
    

@login_required
def question(request, question_id):
    question = get_object_or_404(models.Question, id=question_id)
    answer = question.get_answer(request.user)
    if request.method == "POST":
        if not question.is_active():
            messages.error(request, "You sly dog, this question is not active")
            return redirect("/q/%s"%question.id)
        form = forms.AnswerForm(request.POST)
        if form.is_valid():
            # sorted!
            if not answer:
                answer = models.Answer()
            answer.answer = form.cleaned_data["answer"].strip()
            answer.question = question
            answer.user = request.user
            answer.correct = answer.answer == question.answer
            answer.save()
            return redirect("/q/%s"%question.id)
    else:
        if answer:
            form = forms.AnswerForm(initial={"answer":answer.answer})
        else:
            form = forms.AnswerForm()
            
    time_left = 0
    if question.finish:
        time_left = (question.finish - datetime.datetime.now()).total_seconds
        
    return render_response(request, "question.html", {"question":question,
                                                      "answer":answer,
                                                      "form":form,
                                                      "activate_form":forms.ActivateForm(),
                                                      "time_left":time_left})


@login_required
def home(request):
    return render_response(request, "index.html",{})


def login(request):
    if request.user.is_authenticated():
        return redirect("/")
    
    if request.method == "GET":
        return render_response(request, "login.html")
    
    user = request.POST.get("user",None)
    password = request.POST.get("password",None)
    if not user or not password:
        messages.error(request, "No username or password specified")
        return redirect("/login")
    user = authenticate(username=user, password=password)
    if user == None:
        messages.error(request, "Invalid credentials")
        return redirect("/login")
    user_login(request, user)
    messages.info(request, "Welcome %s"%user.username)
    return redirect("/")


def logout(request):
    user_logout(request)
    messages.info(request, "You have been logged out")
    return redirect("/")


def register(request):
    if request.method == "POST":
        form = forms.RegisterForm(request.POST)
        if form.is_valid():
            # do some shit
            user = form.save(False)
            user.email = form.cleaned_data["email"]
            user.first_name = form.cleaned_data["first_name"]
            user.last_name  = form.cleaned_data["last_name"] or ""
            user.save()
            
            # Make some info
            additional = models.AdditionalUserInformation()
            additional.user = user
            additional.company = form.cleaned_data["company"]
            additional.title = form.cleaned_data["title"]
            additional.points = 0
            additional.save()
            
            messages.info(request, "Thank you for registering! You can now login using your username and password")
            return redirect("/login")
            
    else:
        form = forms.RegisterForm()
    
    return render_response(request, "register.html", {"form":form})


@staff_member_required
@transaction.commit_on_success
def admin_move_ordered_model(request, direction, model_type_id, model_id):
    if direction == "up":
        OrderedModel.move_up(model_type_id, model_id)
    else:
        OrderedModel.move_down(model_type_id, model_id)
    
    ModelClass = ContentType.objects.get(id=model_type_id).model_class()
    
    app_label = ModelClass._meta.app_label
    model_name = ModelClass.__name__.lower()

    url = "/admin/%s/%s/" % (app_label, model_name)
    
    return HttpResponseRedirect(url)