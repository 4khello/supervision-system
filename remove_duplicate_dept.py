#!/usr/bin/env python
"""
Script to remove duplicate department ID 23 (ألعاب قوى)
Keep only ID 7 (العاب قوى)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Department

# Delete the duplicate department
dept = Department.objects.filter(id=23).first()
if dept:
    print(f"Deleting department: ID {dept.id}: {dept.name}")
    dept.delete()
    print("✓ Deleted successfully!")
else:
    print("Department ID 23 not found")

# Show remaining departments
print("\nRemaining departments:")
print("-" * 60)
for dept in Department.objects.all().order_by('name'):
    print(f"ID {dept.id}: {dept.name}")
