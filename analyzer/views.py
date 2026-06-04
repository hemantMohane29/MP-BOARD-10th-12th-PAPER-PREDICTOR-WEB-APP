"""
PROJECT ARCHITECTURE MAP:

--- DATABASE (analyzer/models.py) ---
1. LibraryPaper               : Pre-loaded PDFs managed by admin; students select from these.
2. AnalysisSession             : One analysis run per student (tracks status, user, class, subject).
3. ExamPaper                   : Links a session to a LibraryPaper; get_pdf_path() feeds the pipeline.
4. AnalysisResult              : Stores Stage 2 + Stage 3 Gemini JSON output.

--- SERVER LOGIC (analyzer/views.py) ---
5. LibraryPaperListView.get()  : Returns filtered list of available papers as JSON.
6. StartAnalysisView.post()    : Creates session + ExamPaper records from paper_ids, starts background thread.
7. run_pipeline_worker()       : Coordinates the full AI pipeline in a background thread.
8. ResultsDashboardView.get()  : Polls status; returns completed results or processing status.

--- AI ENGINE (analyzer/services.py) ---
9. extract_text_with_sarvam()  : OCR — reads PDF, returns Hindi markdown text.
10. run_gemini_stage_2()       : Finds repeated questions and predicts next exam questions.
11. run_gemini_stage_3()       : Generates study tips and difficulty breakdown.
"""

import threading
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.http import JsonResponse

from .models import AnalysisSession, ExamPaper, AnalysisResult, LibraryPaper
from .services import AIPipelineOrchestrator


@user_passes_test(lambda u: u.is_superuser, login_url='/login/')
def admin_bulk_upload_view(request):
    """
    Custom Admin Dashboard for bulk uploading and managing papers.
    """
    papers = LibraryPaper.objects.all().order_by('subject', '-year', 'title')
    
    # Categorize papers by class and subject
    categorized_papers = {
        '10th': {},
        '12th': {}
    }
    for paper in papers:
        c = paper.student_class or '10th'
        s = paper.subject or 'Other'
        if c not in categorized_papers:
            categorized_papers[c] = {}
        if s not in categorized_papers[c]:
            categorized_papers[c][s] = []
            
        categorized_papers[c][s].append(paper)
        
    context = {
        'papers': papers,
        'categorized_papers': categorized_papers
    }
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # ─── ADMIN MANAGEMENT LOGIC ───
        if action == 'make_admin':
            email = request.POST.get('admin_email', '').strip()
            
            # Validate Email Format
            try:
                validate_email(email)
            except ValidationError:
                context['error'] = "Invalid email format."
                return render(request, 'bulk_upload.html', context)
                
            # Check if user exists
            user = User.objects.filter(username=email).first()
            if user:
                user.is_superuser = True
                user.is_staff = True
                user.save()
                context['success'] = f"Success! {email} was upgraded to an Admin."
            else:
                user = User.objects.create_superuser(username=email, email=email, password='Admin@123')
                context['success'] = f"Created new Admin {email} with default password: Admin@123"
                
            return render(request, 'bulk_upload.html', context)
            
        # ─── BULK UPLOAD LOGIC ───
        student_class = request.POST.get('student_class')
        subject = request.POST.get('subject')
        files = request.FILES.getlist('pdf_files')
        
        if not files:
            context['error'] = 'No files selected.'
            return render(request, 'bulk_upload.html', context)
            
        import re
        success_count = 0
        for f in files:
            title = f.name.rsplit('.', 1)[0]
            year_match = re.search(r'(20\d{2})', f.name)
            year = year_match.group(1) if year_match else "N/A"
            
            LibraryPaper.objects.create(
                title=title,
                student_class=student_class,
                subject=subject,
                year=year,
                pdf_file=f
            )
            success_count += 1
            
        # Re-fetch and categorize papers for the success page context
        papers = LibraryPaper.objects.all().order_by('subject', '-year', 'title')
        categorized_papers = {'10th': {}, '12th': {}}
        for paper in papers:
            c = paper.student_class or '10th'
            s = paper.subject or 'Other'
            if c not in categorized_papers:
                categorized_papers[c] = {}
            if s not in categorized_papers[c]:
                categorized_papers[c][s] = []
            categorized_papers[c][s].append(paper)
            
        context['papers'] = papers
        context['categorized_papers'] = categorized_papers
        context['success'] = f'Successfully added {success_count} papers to the database!'
        
    return render(request, 'bulk_upload.html', context)

@user_passes_test(lambda u: u.is_superuser, login_url='/login/')
def delete_paper_view(request, paper_id):
    """
    Deletes a LibraryPaper. Supports AJAX JSON deletion response.
    """
    if request.method == 'POST':
        paper = get_object_or_404(LibraryPaper, id=paper_id)
        paper.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({"status": "success", "message": "Paper successfully deleted."})
    return redirect('admin_home')

@user_passes_test(lambda u: u.is_superuser, login_url='/login/')
def delete_papers_bulk_view(request):
    """
    Deletes multiple LibraryPaper records in bulk. Supports AJAX/JSON.
    """
    if request.method == 'POST':
        import json
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                paper_ids = data.get('paper_ids', [])
            else:
                paper_ids = request.POST.getlist('paper_ids')
            
            if paper_ids:
                paper_ids = [int(pid) for pid in paper_ids]
                deleted_count = LibraryPaper.objects.filter(id__in=paper_ids).delete()[0]
                if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
                    return JsonResponse({"status": "success", "message": f"Successfully deleted {deleted_count} papers."})
        except Exception as e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
                return JsonResponse({"status": "error", "message": str(e)}, status=400)
            
    return redirect('admin_home')


class LibraryPaperListView(APIView):
    """
    GET /api/papers/?class=10th&subject=Science&year=all
    Returns JSON list of active LibraryPaper records for the given filters.
    """
    def get(self, request):
        class_filter   = request.query_params.get('class', '10th')
        subject_filter = request.query_params.get('subject', 'Science')
        year_filter    = request.query_params.get('year', 'all')

        papers = LibraryPaper.objects.filter(
            student_class=class_filter,
            subject=subject_filter
        )
        if year_filter != 'all':
            years = year_filter.split(',')
            papers = papers.filter(year__in=years)

        papers_data = [
            {
                'id':            p.id,
                'title':         p.title,
                'title_hindi':   p.title_hindi,
                'student_class': p.student_class,
                'subject':       p.subject,
                'year':          p.year,
                'set_name':      p.set_name,
                'total_marks':   p.total_marks,
                'uploaded_at':   p.uploaded_at.isoformat() if p.uploaded_at else None,
            }
            for p in papers
        ]

        return Response({'papers': papers_data, 'count': len(papers_data)})


class AllPapersListView(APIView):
    """
    GET /api/papers/all/
    Returns all active papers grouped — used by the Papers browse page.
    """
    def get(self, request):
        papers = LibraryPaper.objects.all()
        papers_data = [
            {
                'id':            p.id,
                'title':         p.title,
                'title_hindi':   p.title_hindi,
                'student_class': p.student_class,
                'subject':       p.subject,
                'year':          p.year,
                'set_name':      p.set_name,
                'total_marks':   p.total_marks,
                'uploaded_at':   p.uploaded_at.isoformat() if p.uploaded_at else None,
            }
            for p in papers
        ]
        return Response({'papers': papers_data, 'count': len(papers_data)})


class StartAnalysisView(APIView):
    """
    POST /api/analyze/
    Body JSON: { "paper_ids": [1,2,3], "student_class": "10th", "subject": "Science" }
    Creates session + ExamPaper records from library paper IDs, starts AI pipeline thread.
    """
    def post(self, request, *args, **kwargs):
        student_class = request.data.get('student_class')
        subject       = request.data.get('subject')
        paper_ids     = request.data.get('paper_ids', [])

        if not student_class or not subject:
            return Response({"error": "Class and Subject required."}, status=status.HTTP_400_BAD_REQUEST)

        if not paper_ids or len(paper_ids) < 2 or len(paper_ids) > 5:
            return Response({"error": "Please select 2 to 5 papers."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            library_papers = list(LibraryPaper.objects.filter(id__in=paper_ids))
            if len(library_papers) < 2:
                return Response({"error": "Selected papers not found in library."}, status=status.HTTP_400_BAD_REQUEST)

            # Check if there is a previously completed session with the exact same papers
            paper_ids_sorted = sorted([p.id for p in library_papers])
            previous_completed_session = None
            completed_sessions = AnalysisSession.objects.filter(
                student_class=student_class,
                subject=subject,
                status='completed'
            ).order_by('-created_at')
            
            for s in completed_sessions:
                s_paper_ids = sorted(list(s.papers.values_list('library_paper_id', flat=True)))
                if s_paper_ids == paper_ids_sorted:
                    if hasattr(s, 'result') and s.result.stage_2_deduplicated_json:
                        previous_completed_session = s
                        break
            
            if previous_completed_session:
                print(f"[StartAnalysis] Reusing completed Session {previous_completed_session.id} for the same selected papers.")
                with transaction.atomic():
                    session = AnalysisSession.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        student_class=student_class,
                        subject=subject,
                        status='completed'
                    )
                    for lib_paper in library_papers:
                        prev_ep = ExamPaper.objects.filter(session=previous_completed_session, library_paper=lib_paper).first()
                        ExamPaper.objects.create(
                            session=session,
                            library_paper=lib_paper,
                            ocr_raw_text=prev_ep.ocr_raw_text if prev_ep else "",
                            extracted_questions_json=prev_ep.extracted_questions_json if prev_ep else None
                        )
                    AnalysisResult.objects.create(
                        session=session,
                        stage_2_deduplicated_json=previous_completed_session.result.stage_2_deduplicated_json,
                        stage_3_dl_insights_json=previous_completed_session.result.stage_3_dl_insights_json
                    )
                return Response(
                    {"message": "Analysis completed.", "session_id": str(session.id)},
                    status=status.HTTP_202_ACCEPTED
                )

            with transaction.atomic():
                session = AnalysisSession.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    student_class=student_class,
                    subject=subject,
                    status='processing'
                )
                for lib_paper in library_papers:
                    ExamPaper.objects.create(session=session, library_paper=lib_paper)

            threading.Thread(target=self.run_pipeline_worker, args=(session.id,)).start()

            return Response(
                {"message": "Analysis started.", "session_id": str(session.id)},
                status=status.HTTP_202_ACCEPTED
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def run_pipeline_worker(self, session_id):
        session = AnalysisSession.objects.get(id=session_id)
        papers  = list(ExamPaper.objects.filter(session=session))
        orchestrator = AIPipelineOrchestrator()

        try:
            results = orchestrator.run_full_pipeline(session, papers)
            AnalysisResult.objects.create(
                session=session,
                stage_2_deduplicated_json=results['stage_2'],
                stage_3_dl_insights_json=results['stage_3']
            )
            session.status = 'completed'
            session.save()

        except Exception as e:
            print(f"Pipeline crashed for Session {session_id}: {str(e)}")
            session.status = 'failed'
            session.error_message = str(e)
            session.save()


class ResultsDashboardView(APIView):
    """
    GET /api/results/<uuid:session_id>/
    Polled by frontend every 3 seconds. Returns status or completed results.
    
    POST /api/results/<uuid:session_id>/
    Cancels an active session. Body: { "action": "cancel" }
    """
    def get(self, request, session_id):
        try:
            session = AnalysisSession.objects.get(id=session_id)

            if session.status == 'completed':
                result = AnalysisResult.objects.get(session=session)
                return Response({
                    "status": "completed",
                    "stage_2_insights":            result.stage_2_deduplicated_json,
                    "stage_3_predictive_dashboard": result.stage_3_dl_insights_json,
                }, status=status.HTTP_200_OK)

            elif session.status == 'failed':
                error_msg = session.error_message if session.error_message else "An unknown AI error occurred."
                return Response({"status": "failed", "error": error_msg},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response({"status": session.status, "message": "Analyzing..."},
                                status=status.HTTP_202_ACCEPTED)

        except AnalysisSession.DoesNotExist:
            return Response({"error": "Session Not Found"}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, session_id):
        action = request.data.get('action')
        if action == 'cancel':
            try:
                session = AnalysisSession.objects.get(id=session_id)
                if session.status in ['processing', 'extracting', 'analyzing', 'pending']:
                    session.status = 'failed'
                    session.error_message = "Analysis was stopped by the user."
                    session.save()
                    return Response({"message": "Analysis session cancelled successfully."}, status=status.HTTP_200_OK)
                return Response({"error": "Session is not active."}, status=status.HTTP_400_BAD_REQUEST)
            except AnalysisSession.DoesNotExist:
                return Response({"error": "Session Not Found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)
