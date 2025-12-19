from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import StudentProfile, LearningData
from django.db.models import Avg, F, FloatField, ExpressionWrapper
from django.http import Http404, JsonResponse, HttpResponseBadRequest, HttpResponseForbidden


# Landing page
def home(request):
    return render(request, 'index.html')


# Student Registration
def register(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        student_id = request.POST.get('student_id')
        course = request.POST.get('course')
        email = request.POST.get('email')

        # Create user and save email if provided
        user = User.objects.create_user(username=username, password=password, email=email)
        StudentProfile.objects.create(
            user=user,
            student_id=student_id,
            course=course
        )
        # Redirect to login with a flag so template can show success message
        return redirect(reverse('login') + '?registered=true')

    return render(request, 'student_registration.html')


# Student Login
def user_login(request):
    # Support `next` parameter so users return to the page they requested
    next_url = request.POST.get('next') or request.GET.get('next') or None

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Try direct username authentication first
        user = authenticate(username=username, password=password)

        # If that fails, allow users to login using their email address
        if not user:
            try:
                user_obj = User.objects.get(email__iexact=username)
            except User.DoesNotExist:
                user_obj = None

            if user_obj:
                user = authenticate(username=user_obj.username, password=password)

        if user:
            login(request, user)
            # Prefer next URL when provided, otherwise go to dashboard
            if next_url:
                return redirect(next_url)
            return redirect('dashboard')
        # Authentication failed -> show error on template
        return render(request, 'student_login.html', {'login_error': 'Invalid credentials. Please try again.'})

    return render(request, 'student_login.html')


# Dashboard
@login_required
def dashboard(request):
    profile = StudentProfile.objects.get(user=request.user)
    records = LearningData.objects.filter(student=profile)

    avg_score = 0
    if records.exists():
        avg_score = sum(
            (r.quiz_score + r.assignment_score) / 2
            for r in records
        ) / records.count()

    context = {
        'profile': profile,
        'records': records,
        'avg_score': round(avg_score, 2)
    }

    return render(request, 'student_dashboard.html', context)


# Learning module input page
@login_required
def learning_module(request):
    if request.method == 'POST':
        profile = StudentProfile.objects.get(user=request.user)

        LearningData.objects.create(
            student=profile,
            quiz_score=request.POST['quiz'],
            assignment_score=request.POST['assignment'],
            time_spent_hours=request.POST['time']
        )
        return redirect('dashboard')

    return render(request, 'learning_module_viewer.html')


# API: create learning data (AJAX)
@login_required
def learning_create(request):
    if request.method != 'POST':
        return HttpResponseBadRequest('POST required')

    profile = StudentProfile.objects.get(user=request.user)
    try:
        quiz = int(request.POST.get('quiz'))
        assignment = int(request.POST.get('assignment'))
        time_spent = float(request.POST.get('time'))
    except (TypeError, ValueError):
        return HttpResponseBadRequest('Invalid input')

    ld = LearningData.objects.create(
        student=profile,
        quiz_score=quiz,
        assignment_score=assignment,
        time_spent_hours=time_spent,
    )

    return JsonResponse({'success': True, 'id': ld.id, 'quiz': ld.quiz_score, 'assignment': ld.assignment_score, 'time': ld.time_spent_hours})


@login_required
def learning_update(request, pk):
    if request.method != 'POST':
        return HttpResponseBadRequest('POST required')

    try:
        ld = LearningData.objects.get(pk=pk)
    except LearningData.DoesNotExist:
        return HttpResponseBadRequest('Not found')

    if ld.student.user != request.user:
        return HttpResponseForbidden('Not allowed')

    try:
        quiz = int(request.POST.get('quiz'))
        assignment = int(request.POST.get('assignment'))
        time_spent = float(request.POST.get('time'))
    except (TypeError, ValueError):
        return HttpResponseBadRequest('Invalid input')

    ld.quiz_score = quiz
    ld.assignment_score = assignment
    ld.time_spent_hours = time_spent
    ld.save()

    return JsonResponse({'success': True})


@login_required
def learning_delete(request, pk):
    if request.method != 'POST':
        return HttpResponseBadRequest('POST required')

    try:
        ld = LearningData.objects.get(pk=pk)
    except LearningData.DoesNotExist:
        return HttpResponseBadRequest('Not found')

    if ld.student.user != request.user:
        return HttpResponseForbidden('Not allowed')

    ld.delete()
    return JsonResponse({'success': True})


@login_required
def learning_list(request):
    # return current user's learning entries
    profile = StudentProfile.objects.get(user=request.user)
    qs = LearningData.objects.filter(student=profile).order_by('-id')
    data = []
    for ld in qs:
        data.append({'id': ld.id, 'quiz': ld.quiz_score, 'assignment': ld.assignment_score, 'time': ld.time_spent_hours})
    return JsonResponse({'results': data})


# Logout
def user_logout(request):
    logout(request)
    return redirect('login')


# Engagement analytics view
@login_required
def engagement(request):
    # Expression for average performance per LearningData record
    eng_expr = ExpressionWrapper((F('quiz_score') + F('assignment_score')) / 2.0, output_field=FloatField())

    agg = LearningData.objects.aggregate(avg_eng=Avg(eng_expr), avg_time=Avg('time_spent_hours'))
    overall_engagement = round(agg['avg_eng'] or 0, 2)
    avg_time = round(agg['avg_time'] or 0, 2)

    active_students = StudentProfile.objects.filter(learningdata__isnull=False).distinct().count()

    # Per-student aggregates
    student_averages = LearningData.objects.values('student__user__username').annotate(
        avg_eng=Avg(eng_expr), avg_time=Avg('time_spent_hours')
    ).order_by('-avg_eng')

    engagement_list = []
    for s in student_averages:
        engagement_list.append({
            'name': s.get('student__user__username'),
            'last_active': 'N/A',
            'avg_time': round(s.get('avg_time') or 0, 2),
            'engagement': round(s.get('avg_eng') or 0, 2),
        })

    # Chart data (labels = student names, values = engagement)
    engagement_labels = [s['name'] for s in engagement_list]
    engagement_values = [s['engagement'] for s in engagement_list]

    # Top modules placeholder (no Module model available)
    top_modules = []

    context = {
        'overall_engagement': overall_engagement,
        'avg_time': avg_time,
        'active_students': active_students,
        'completion_rate': 0,
        'top_modules': top_modules,
        'engagement_list': engagement_list,
        'engagement_labels': engagement_labels,
        'engagement_values': engagement_values,
    }

    return render(request, 'engagement.html', context)
