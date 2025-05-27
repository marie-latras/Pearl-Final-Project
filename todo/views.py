# todo/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .models import Task
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import F, Case, When, Value, IntegerField

@login_required
def task_list(request):
    tasks = Task.objects.filter(user=request.user)
    current_filter = request.GET.get('filter', 'all')
    
    if current_filter == 'active':
        tasks = tasks.filter(completed=False)
    elif current_filter == 'completed':
        tasks = tasks.filter(completed=True)
    
    # Sort tasks: incomplete tasks first, then by deadline (null last), then by creation date
    tasks = tasks.annotate(
        deadline_null=Case(
            When(deadline__isnull=True, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by(
        'completed',
        'deadline_null',
        F('deadline').asc(nulls_last=True),
        '-created_at'
    )
    
    total_tasks = Task.objects.filter(user=request.user).count()
    completed_tasks = Task.objects.filter(user=request.user, completed=True).count()
    
    context = {
        'tasks': tasks,
        'current_filter': current_filter,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'current_date': timezone.now(),
    }
    return render(request, 'todo/index.html', context)

@login_required
def add_task(request):
    current_filter = request.GET.get('filter', 'all')
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        deadline_str = request.POST.get('deadline')
        
        if title:
            task = Task(
                user=request.user,
                title=title,
                description=description
            )
            
            # Handle deadline if provided
            if deadline_str:
                try:
                    # Convert the datetime-local input to a timezone-aware datetime
                    deadline = datetime.fromisoformat(deadline_str)
                    if deadline.tzinfo is None:
                        deadline = timezone.make_aware(deadline)
                    task.deadline = deadline
                except ValueError:
                    messages.error(request, 'Invalid deadline format!')
                    return redirect(reverse('task_list') + f'?filter={current_filter}')
            
            task.save()
            messages.success(request, 'Task added successfully!')
            return redirect(reverse('task_list') + f'?filter={current_filter}')
        else:
            messages.error(request, 'Title is required!')
    return redirect(reverse('task_list') + f'?filter={current_filter}')

@login_required
def toggle_task(request, task_id):
    current_filter = request.GET.get('filter', 'all')
    task = get_object_or_404(Task, id=task_id, user=request.user)
    task.completed = not task.completed
    task.save()
    messages.success(request, f'Task "{task.title}" marked as {"completed" if task.completed else "incomplete"}!')
    return redirect(reverse('task_list') + f'?filter={current_filter}')

@login_required
def delete_task(request, task_id):
    current_filter = request.GET.get('filter', 'all')
    task = get_object_or_404(Task, id=task_id, user=request.user)
    task.delete()
    messages.success(request, f'Task "{task.title}" deleted!')
    return redirect(reverse('task_list') + f'?filter={current_filter}')

@login_required
def clear_completed(request):
    current_filter = request.GET.get('filter', 'all')
    completed_tasks = Task.objects.filter(user=request.user, completed=True)
    count = completed_tasks.count()
    completed_tasks.delete()
    messages.success(request, f'{count} completed task(s) cleared!')
    return redirect(reverse('task_list') + f'?filter={current_filter}')

@login_required
def calendar_view(request):
    # Get the current timezone-aware datetime
    current_date = timezone.now()
    year = int(request.GET.get('year', current_date.year))
    month = int(request.GET.get('month', current_date.month))
    
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1

    # Create timezone-aware datetime objects for start and end of month
    start_date = timezone.make_aware(datetime(year, month, 1))
    if month == 12:
        end_date = timezone.make_aware(datetime(year + 1, 1, 1)) - timedelta(days=1)
    else:
        end_date = timezone.make_aware(datetime(year, month + 1, 1)) - timedelta(days=1)

    # Get the weekday of the first day (0 = Monday, 6 = Sunday)
    first_day = start_date
    starting_day = first_day.weekday()
    days_in_month = (end_date - start_date).days + 1

    # Fetch tasks for the current month
    tasks = Task.objects.filter(
        user=request.user,
        deadline__date__gte=start_date.date(),
        deadline__date__lte=end_date.date()
    )

    # Group tasks by day
    tasks_by_day = {}
    for task in tasks:
        if task.deadline:
            day = task.deadline.day
            if day not in tasks_by_day:
                tasks_by_day[day] = []
            tasks_by_day[day].append(task)

    # Build calendar
    calendar = []
    date = 1
    for i in range(6):  # 6 weeks
        week = []
        for j in range(7):  # 7 days
            if i == 0 and j < starting_day:
                week.append({'day': '', 'tasks': []})
            elif date > days_in_month:
                week.append({'day': '', 'tasks': []})
            else:
                week.append({
                    'day': date,
                    'tasks': tasks_by_day.get(date, [])
                })
                date += 1
        calendar.append(week)
        if date > days_in_month:
            break

    context = {
        'calendar': calendar,
        'month': month,
        'year': year,
        'today': current_date,
        'prev_month': month - 1 if month > 1 else 12,
        'prev_year': year if month > 1 else year - 1,
        'next_month': month + 1 if month < 12 else 1,
        'next_year': year if month < 12 else year + 1,
    }
    return render(request, 'todo/calendar.html', context)