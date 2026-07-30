from datetime import datetime, timezone, date

from bson import ObjectId
from bson.errors import InvalidId
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from mongo import collections as col
from .tenancy import require_business


def _serialize(emp):
    emp['id'] = str(emp.pop('_id'))
    return emp


class EmployeeListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business, _ = require_business(request)
        employees = list(col.employees().find({'business_id': business.mongo_id}, sort=[('name', 1)]))
        return Response({'employees': [_serialize(e) for e in employees]})

    def post(self, request):
        business, _ = require_business(request)
        data = request.data
        name = str(data.get('name', '')).strip()
        if not name:
            return Response({'error': 'Employee name is required.'}, status=status.HTTP_400_BAD_REQUEST)
        doc = {
            'business_id': business.mongo_id,
            'name': name,
            'role': str(data.get('role', '')).strip(),
            'phone': str(data.get('phone', '')).strip(),
            'email': str(data.get('email', '')).strip(),
            'salary': float(data.get('salary') or 0),
            'join_date': str(data.get('join_date', '')).strip(),
            'status': 'active',
            'created_at': datetime.now(timezone.utc),
        }
        result = col.employees().insert_one(doc)
        doc['_id'] = result.inserted_id
        return Response(_serialize(doc), status=status.HTTP_201_CREATED)


class EmployeeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, business, employee_id):
        try:
            oid = ObjectId(employee_id)
        except InvalidId:
            return None
        return col.employees().find_one({'_id': oid, 'business_id': business.mongo_id})

    def patch(self, request, employee_id):
        business, _ = require_business(request)
        employee = self._get(business, employee_id)
        if not employee:
            return Response({'error': 'Employee not found.'}, status=status.HTTP_404_NOT_FOUND)
        data = request.data
        name = str(data.get('name', employee.get('name', ''))).strip()
        if not name:
            return Response({'error': 'Employee name is required.'}, status=status.HTTP_400_BAD_REQUEST)
        updates = {
            'name': name,
            'role': str(data.get('role', employee.get('role', ''))).strip(),
            'phone': str(data.get('phone', employee.get('phone', ''))).strip(),
            'email': str(data.get('email', employee.get('email', ''))).strip(),
            'salary': float(data.get('salary', employee.get('salary', 0)) or 0),
            'join_date': str(data.get('join_date', employee.get('join_date', ''))).strip(),
            'status': str(data.get('status', employee.get('status', 'active'))).strip(),
            'updated_at': datetime.now(timezone.utc),
        }
        col.employees().update_one({'_id': employee['_id'], 'business_id': business.mongo_id}, {'$set': updates})
        employee.update(updates)
        return Response(_serialize(employee))

    def delete(self, request, employee_id):
        business, _ = require_business(request)
        try:
            oid = ObjectId(employee_id)
        except InvalidId:
            return Response({'error': 'Employee not found.'}, status=status.HTTP_404_NOT_FOUND)
        col.employees().delete_one({'_id': oid, 'business_id': business.mongo_id})
        return Response(status=status.HTTP_204_NO_CONTENT)


class AttendanceView(APIView):
    """
    GET: today's active employees + their attendance status.
    POST: bulk upsert {employee_id: status} for today.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business, _ = require_business(request)
        bid = business.mongo_id
        employees = list(col.employees().find({'business_id': bid, 'status': 'active'}))
        today_str = date.today().isoformat()
        today_attendance = {
            a['employee_id']: a['status']
            for a in col.attendance().find({'business_id': bid, 'date': today_str})
        }
        for emp in employees:
            emp['id'] = str(emp.pop('_id'))
            emp['att_status'] = today_attendance.get(emp['id'], '')
        return Response({'employees': employees, 'today': today_str})

    def post(self, request):
        business, _ = require_business(request)
        bid = business.mongo_id
        today_str = date.today().isoformat()
        statuses = request.data.get('statuses') or {}  # {employee_id: status}
        for employee_id, att_status in statuses.items():
            col.attendance().update_one(
                {'business_id': bid, 'employee_id': employee_id, 'date': today_str},
                {'$set': {'status': att_status, 'marked_at': datetime.now(timezone.utc)}},
                upsert=True,
            )
        return Response({'ok': True, 'date': today_str})
