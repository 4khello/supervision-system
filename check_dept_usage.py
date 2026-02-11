#!/usr/bin/env python
"""
Script to check which departments are linked to data (supervisors/researches)
and which ones can be safely deleted.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Department, Supervisor, Research

print("=" * 80)
print("DEPARTMENTS WITH DATA LINKS")
print("=" * 80)

for dept in Department.objects.all().order_by('id'):
    supervisors_count = Supervisor.objects.filter(department=dept).count()
    researches_count = Research.objects.filter(department=dept).count()
    
    has_data = supervisors_count > 0 or researches_count > 0
    
    status = "✓ HAS DATA" if has_data else "✗ NO DATA - CAN DELETE"
    
    print(f"\nID {dept.id:2d}: {dept.name:30s} | {status}")
    if supervisors_count > 0:
        print(f"         └─ {supervisors_count} supervisor(s)")
    if researches_count > 0:
        print(f"         └─ {researches_count} research(es)")

print("\n" + "=" * 80)
print("DEPARTMENTS TO DELETE (NO DATA LINKED)")
print("=" * 80)

to_delete = []
for dept in Department.objects.all():
    supervisors_count = Supervisor.objects.filter(department=dept).count()
    researches_count = Research.objects.filter(department=dept).count()
    if supervisors_count == 0 and researches_count == 0:
        to_delete.append(dept)
        print(f"ID {dept.id:2d}: {dept.name}")

print(f"\nTotal to delete: {len(to_delete)}")
