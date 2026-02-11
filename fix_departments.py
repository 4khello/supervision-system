#!/usr/bin/env python
"""
Script to clean department names - remove English text and keep only Arabic.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Department

# Mapping of current names to cleaned Arabic-only names
DEPT_MAPPING = {
    "Biology": "الأحياء",
    "botany": "علم النبات",
    "Chemistry": "الكيمياء",
    "Computer Science": "علوم الحاسوب",
    "Geology": "الجيولوجيا",
    "Information Systems": "نظم المعلومات",
    "Management": "الإدارة",
    "Mathematics": "الرياضيات",
    "Physics": "الفيزياء",
    "Statistics": "الإحصاء",
    "Zoology": "علم الحيوان",
}

# Direct mapping for exact matches
EXACT_MAPPING = {dept: dept for dept in DEPT_MAPPING.values()}

def clean_department_names():
    """Clean department names to show only Arabic."""
    all_depts = Department.objects.all()
    
    print(f"Found {all_depts.count()} departments\n")
    print("Current department names:")
    print("-" * 60)
    
    updated_count = 0
    
    for dept in all_depts:
        print(f"ID {dept.id}: {dept.name}")
        
        # Check if name should be updated
        if dept.name in DEPT_MAPPING:
            arabic_name = DEPT_MAPPING[dept.name]
            print(f"  → Will update to: {arabic_name}")
            dept.name = arabic_name
            dept.save()
            updated_count += 1
            print(f"  ✓ Updated!")

    print("\n" + "-" * 60)
    print(f"Updated {updated_count} departments")
    print("-" * 60)
    print("After cleaning:")
    print("-" * 60)
    
    for dept in Department.objects.all():
        print(f"ID {dept.id}: {dept.name}")

if __name__ == '__main__':
    clean_department_names()
