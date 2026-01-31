# =========================================
# file: core/views.py
# (لو هتسلموه لفرونت يعمل صفحات HTML/JS)
# =========================================
from collections import defaultdict

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from .models import Supervisor, ResearchSupervision, Research


def supervisors_list(request):
    supervisors = (
        Supervisor.objects
        .filter(is_active=True)
        .select_related("department")
        .annotate(
            researchers_count=Count(
                "researchsupervision__research",
                filter=Q(researchsupervision__research__researcher_type=Research.ResearcherType.RESEARCHER),
                distinct=True,
            ),
            assistants_count=Count(
                "researchsupervision__research",
                filter=Q(researchsupervision__research__researcher_type=Research.ResearcherType.ASSISTANT),
                distinct=True,
            ),
        )
        .order_by("name")
    )
    return render(request, "supervisors_list.html", {"supervisors": supervisors})


def supervisor_detail(request, pk):
    supervisor = get_object_or_404(Supervisor.objects.select_related("department"), pk=pk)

    links = (
        ResearchSupervision.objects
        .filter(supervisor=supervisor)
        .select_related("research", "research__department")
        .order_by("research__researcher_name")
    )

    research_ids = [l.research_id for l in links]
    co_map = defaultdict(list)

    all_links = (
        ResearchSupervision.objects
        .filter(research_id__in=research_ids)
        .select_related("supervisor")
    )
    for l in all_links:
        if l.supervisor_id != supervisor.id:
            co_map[l.research_id].append(l.supervisor.name)

    researchers = []
    assistants = []

    for l in links:
        item = {
            "research": l.research,
            "role": l.role,
            "co_supervisors": "، ".join(sorted(set(co_map.get(l.research_id, [])))),
        }
        if l.research.researcher_type == Research.ResearcherType.ASSISTANT:
            assistants.append(item)
        else:
            researchers.append(item)

    ctx = {
        "supervisor": supervisor,
        "researchers": researchers,
        "assistants": assistants,
        "researchers_count": len({x["research"].id for x in researchers}),
        "assistants_count": len({x["research"].id for x in assistants}),
    }
    return render(request, "supervisor_detail.html", ctx)