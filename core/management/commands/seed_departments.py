from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Department, DepartmentUser

class Command(BaseCommand):
    help = 'Seeds the correct departments and creates a user for each.'

    def handle(self, *args, **options):
        # 1. Create Superuser (Admin) optional check
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write(self.style.SUCCESS("Superuser 'admin' created."))

        # 2. Correct Departments List
        dept_names = [
            "الإدارة الرياضية",
            "التدريب الرياضي",
            "الجمباز",
            "الرياضات الجماعية",
            "الرياضات المائية",
            "ألعاب قوى",
            "العلوم النفسية",
            "المنازلات",
            "خارجي",
            "طرق التدريس",
            "علوم الصحة",
        ]

        for i, name in enumerate(dept_names, start=1):
            # Create/Get Department
            dept, created = Department.objects.get_or_create(name=name)
            
            # Create User (user_1, user_2, etc.)
            # Or maybe named after department for clarity? Let's stick to user_X for simplicity or user_deptname?
            # User requested "Dept User", let's keep user_1..11 mapped to these new names.
            username = f"user_{i}"
            user = User.objects.filter(username=username).first()
            if not user:
                user = User.objects.create_user(username=username, password='password123')
                self.stdout.write(self.style.SUCCESS(f"Created User: {username}"))
            
            # Link/Update Department
            # Remove old link if exists
            DepartmentUser.objects.filter(user=user).delete()
            DepartmentUser.objects.create(user=user, department=dept)
            
            self.stdout.write(self.style.SUCCESS(f"Linked {username} -> {name}"))

        self.stdout.write(self.style.SUCCESS("Seeding completed with correct departments."))
