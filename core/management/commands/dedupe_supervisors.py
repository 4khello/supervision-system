# =========================================
# file: core/management/commands/dedupe_supervisors.py
# =========================================
import re
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Supervisor, ResearchSupervision


def norm(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"\s+", " ", name)
    return name


class Command(BaseCommand):
    help = "Merge duplicate supervisors by normalized name."

    @transaction.atomic
    def handle(self, *args, **options):
        groups = defaultdict(list)
        for s in Supervisor.objects.all().order_by("id"):
            groups[norm(s.name)].append(s)

        merged = 0
        deleted = 0
        moved_links = 0

        for _, items in groups.items():
            if len(items) <= 1:
                continue

            keep = items[0]
            for cand in items:
                if cand.department_id is not None:
                    keep = cand
                    break

            for dup in [x for x in items if x.id != keep.id]:
                for link in ResearchSupervision.objects.filter(supervisor=dup).select_related("research"):
                    obj, created = ResearchSupervision.objects.get_or_create(
                        research=link.research,
                        supervisor=keep,
                        defaults={"role": link.role},
                    )
                    if created:
                        moved_links += 1

                if keep.department_id is None and dup.department_id is not None:
                    keep.department_id = dup.department_id
                    keep.save(update_fields=["department"])

                dup.delete()
                deleted += 1

            merged += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Groups merged: {merged} | Duplicates deleted: {deleted} | Links moved: {moved_links}"
        ))