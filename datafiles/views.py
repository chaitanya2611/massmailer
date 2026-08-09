from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings

from .forms import DataFileUploadForm
from .models import DataFile
from .parsing import parse_tabular_file


@login_required
def list_files(request):
    files = request.user.data_files.all()
    return render(request, "datafiles/list.html", {"files": files})


@login_required
def upload_file(request):
    if request.method == "POST":
        form = DataFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = request.FILES["file"]
            if uploaded.size > settings.MAX_UPLOAD_SIZE_BYTES:
                form.add_error("file", f"File is too large. Max size is {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB.")
            else:
                try:
                    columns, records, detected_email = parse_tabular_file(uploaded)
                except Exception as exc:
                    form.add_error("file", f"Couldn't parse this file: {exc}")
                else:
                    data_file = form.save(commit=False)
                    data_file.user = request.user
                    data_file.original_filename = uploaded.name
                    data_file.columns = columns
                    data_file.row_count = len(records)
                    data_file.detected_email_column = detected_email
                    data_file.save()
                    messages.success(request, f"Uploaded {uploaded.name} — {len(records)} rows, {len(columns)} columns detected.")
                    return redirect("datafiles:detail", pk=data_file.pk)
    else:
        form = DataFileUploadForm()

    return render(request, "datafiles/upload.html", {"form": form})


@login_required
def file_detail(request, pk):
    data_file = get_object_or_404(DataFile, pk=pk, user=request.user)
    preview_rows = []
    try:
        data_file.file.open("rb")
        _, records, _ = parse_tabular_file(data_file.file)
        preview_rows = records[:10]
    except Exception:
        preview_rows = []
    finally:
        try:
            data_file.file.close()
        except Exception:
            pass

    return render(request, "datafiles/detail.html", {"data_file": data_file, "preview_rows": preview_rows})
