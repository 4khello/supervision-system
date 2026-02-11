#!/usr/bin/env python
"""
Script to delete the 11 duplicate departments that have no data.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Department

# IDs to delete (the ones with no data)
ids_to_delete = [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22]

print("Deleting duplicate departments...")
print("=" * 60)

for dept_id in ids_to_delete:
    dept = Department.objects.filter(id=dept_id).first()
    if dept:
        print(f"✓ Deleting ID {dept_id}: {dept.name}")
        dept.delete()

print("\n" + "=" * 60)
print("Remaining departments (with actual data):")
print("=" * 60)

for dept in Department.objects.all().order_by('id'):
    print(f"ID {dept.id:2d}: {dept.name}")

print(f"\nTotal departments remaining: {Department.objects.count()}")
