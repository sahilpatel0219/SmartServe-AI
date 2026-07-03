from datetime import datetime, timezone, date
from bson import ObjectId
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Membership
from mongo import collections as col


def _get_business(request):
    from core.utils import get_active_business
    return get_active_business(request)


@login_required
def index_view(request):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    employees = list(col.employees().find({'business_id': business.mongo_id}, sort=[('name', 1)]))
    for emp in employees:
        emp['str_id'] = str(emp['_id'])
    return render(request, 'staff/index.html', {'business': business, 'employees': employees})


@login_required
def add_employee_view(request):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Employee name is required.')
        else:
            col.employees().insert_one({
                'business_id': business.mongo_id,
                'name': name,
                'role': request.POST.get('role', '').strip(),
                'phone': request.POST.get('phone', '').strip(),
                'email': request.POST.get('email', '').strip(),
                'salary': float(request.POST.get('salary', 0) or 0),
                'join_date': request.POST.get('join_date', '').strip(),
                'status': 'active',
                'created_at': datetime.now(timezone.utc),
            })
            messages.success(request, f'"{name}" added to staff.')
            return redirect('staff:index')
    return render(request, 'staff/add_employee.html', {'business': business})


@login_required
def edit_employee_view(request, employee_id):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id
    employee = col.employees().find_one({'_id': ObjectId(employee_id), 'business_id': bid})
    if not employee:
        messages.error(request, 'Employee not found.')
        return redirect('staff:index')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Employee name is required.')
        else:
            col.employees().update_one(
                {'_id': ObjectId(employee_id)},
                {'$set': {
                    'name': name,
                    'role': request.POST.get('role', '').strip(),
                    'phone': request.POST.get('phone', '').strip(),
                    'email': request.POST.get('email', '').strip(),
                    'salary': float(request.POST.get('salary', 0) or 0),
                    'join_date': request.POST.get('join_date', '').strip(),
                    'status': request.POST.get('status', 'active').strip(),
                    'updated_at': datetime.now(timezone.utc),
                }},
            )
            messages.success(request, f'"{name}" updated.')
            return redirect('staff:index')
    employee['str_id'] = str(employee['_id'])
    return render(request, 'staff/edit_employee.html', {'business': business, 'employee': employee})


@login_required
def delete_employee_view(request, employee_id):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    col.employees().delete_one({'_id': ObjectId(employee_id), 'business_id': business.mongo_id})
    messages.success(request, 'Employee removed.')
    return redirect('staff:index')


@login_required
def mark_attendance_view(request):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id
    employees = list(col.employees().find({'business_id': bid, 'status': 'active'}))
    today_str = date.today().isoformat()
    today_attendance = {
        a['employee_id']: a['status']
        for a in col.attendance().find({'business_id': bid, 'date': today_str})
    }
    # Attach a string id + today's status to each employee for the template
    for emp in employees:
        emp['str_id'] = str(emp['_id'])
        emp['att_status'] = today_attendance.get(emp['str_id'], '')
    if request.method == 'POST':
        for emp in employees:
            emp_id = str(emp['_id'])
            status = request.POST.get(f'att_{emp_id}', 'absent')
            col.attendance().update_one(
                {'business_id': bid, 'employee_id': emp_id, 'date': today_str},
                {'$set': {'status': status, 'marked_at': datetime.now(timezone.utc)}},
                upsert=True,
            )
        messages.success(request, f'Attendance marked for {today_str}.')
        return redirect('staff:index')
    return render(request, 'staff/attendance.html', {
        'business': business,
        'employees': employees,
        'today': today_str,
        'today_attendance': today_attendance,
    })
