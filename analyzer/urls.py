from django.urls import path
from .views import StartAnalysisView, ResultsDashboardView, LibraryPaperListView, AllPapersListView

urlpatterns = [
    path('analyze/',             StartAnalysisView.as_view(),   name='start_analysis'),
    path('results/<uuid:session_id>/', ResultsDashboardView.as_view(), name='results_dashboard'),
    path('papers/',              LibraryPaperListView.as_view(), name='library_papers'),
    path('papers/all/',          AllPapersListView.as_view(),    name='all_papers'),
]
