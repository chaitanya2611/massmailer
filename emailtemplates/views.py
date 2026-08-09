from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from datafiles.models import DataFile
from datafiles.parsing import parse_tabular_file

from .forms import EmailTemplateForm
from .merge import extract_variables, missing_variables, render_merge
from .models import EmailTemplate


@login_required
def list_templates(request):
    templates = request.user.templates.all()
    return render(request, "emailtemplates/list.html", {"templates": templates})


@login_required
def create_template(request):
    return _edit_or_create(request, instance=None)


@login_required
def edit_template(request, pk):
    instance = get_object_or_404(EmailTemplate, pk=pk, user=request.user)
    return _edit_or_create(request, instance=instance)


def _edit_or_create(request, instance):
    if request.method == "POST":
        form = EmailTemplateForm(request.POST, instance=instance)
        if form.is_valid():
            template = form.save(commit=False)
            template.user = request.user
            template.variables_used = extract_variables(template.subject, template.body)
            template.save()
            messages.success(request, f"Saved template “{template.name}”.")
            return redirect("emailtemplates:list")
    else:
        form = EmailTemplateForm(instance=instance)

    data_files = request.user.data_files.all()
    selected_file_id = request.GET.get("data_file") or request.POST.get("data_file")
    selected_file = None
    columns = []
    if selected_file_id:
        selected_file = data_files.filter(pk=selected_file_id).first()
        if selected_file:
            columns = selected_file.columns
    elif data_files.exists():
        selected_file = data_files.first()
        columns = selected_file.columns

    return render(
        request,
        "emailtemplates/form.html",
        {
            "form": form,
            "instance": instance,
            "data_files": data_files,
            "selected_file": selected_file,
            "columns": columns,
        },
    )


@login_required
def preview_partial(request):
    """
    HTMX endpoint: given the in-progress subject/body and a data file + row
    index, render the merged preview for that row and flag missing variables.
    """
    subject = request.POST.get("subject", "")
    body = request.POST.get("body", "")
    data_file_id = request.POST.get("data_file")
    row_index = int(request.POST.get("row_index") or 0)

    row = {}
    row_count = 0
    if data_file_id:
        data_file = DataFile.objects.filter(pk=data_file_id, user=request.user).first()
        if data_file:
            try:
                data_file.file.open("rb")
                _, records, _ = parse_tabular_file(data_file.file)
                row_count = len(records)
                if records:
                    row = records[max(0, min(row_index, row_count - 1))]
            finally:
                try:
                    data_file.file.close()
                except Exception:
                    pass

    context = {
        "rendered_subject": render_merge(subject, row),
        "rendered_body": render_merge(body, row),
        "missing": missing_variables(subject, row) + [v for v in missing_variables(body, row) if v not in missing_variables(subject, row)],
        "row_index": row_index,
        "row_count": row_count,
    }
    return render(request, "emailtemplates/_preview.html", context)
