from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from .models import Project, ProjectModule, ProjectImage, ProjectModuleImage
import json

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    login_form = AuthenticationForm()
    register_form = UserCreationForm()
    
    if request.method == 'POST':
        if 'login' in request.POST:
            login_form = AuthenticationForm(request, data=request.POST)
            if login_form.is_valid():
                user = login_form.get_user()
                login(request, user)
                return redirect('dashboard')
        elif 'register' in request.POST:
            register_form = UserCreationForm(request.POST)
            if register_form.is_valid():
                user = register_form.save()
                login(request, user)
                return redirect('dashboard')
        
    return render(request, 'mainapp/home.html', {
        'login_form': login_form,
        'register_form': register_form
    })

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def dashboard(request):
    return render(request, 'mainapp/dashboard.html')

@login_required
def creator_list(request):
    projects = Project.objects.filter(creator=request.user)
    return render(request, 'mainapp/creator_list.html', {'projects': projects})

@login_required
def creator_form(request, project_id=None):
    if project_id:
        project = get_object_or_404(Project, id=project_id, creator=request.user)
    else:
        project = None

    if request.method == 'POST':
        title = request.POST.get('title')
        story_intro = request.POST.get('story_intro')
        max_errors_str = request.POST.get('max_errors', '3')
        try:
            max_errors = int(max_errors_str)
        except ValueError:
            max_errors = 3

        if not project:
            project = Project.objects.create(
                creator=request.user, 
                title=title, 
                story_intro=story_intro,
                max_errors=max_errors
            )
        else:
            project.title = title
            project.story_intro = story_intro
            project.max_errors = max_errors
            project.save()
            
        # Handle Project Images upload (multiple)
        if 'project_images' in request.FILES:
            # If new images are uploaded, delete old ones
            project.images.all().delete()
            for img in request.FILES.getlist('project_images'):
                ProjectImage.objects.create(project=project, image=img)

        modules_data = request.POST.get('modules_data', '[]')
        try:
            modules = json.loads(modules_data)
            submitted_ids = []
            for idx, mod in enumerate(modules):
                mod_id = mod.get('id')
                module_obj = None
                if mod_id:
                    try:
                        module_obj = ProjectModule.objects.get(id=mod_id, project=project)
                        module_obj.module_type = mod['module_type']
                        module_obj.order = idx
                        module_obj.time_limit = mod.get('time_limit', 60)
                        module_obj.story_text = mod.get('story_text', '')
                        module_obj.config_data = mod.get('config_data', {})
                        module_obj.save()
                    except ProjectModule.DoesNotExist:
                        pass
                
                if not module_obj:
                    module_obj = ProjectModule.objects.create(
                        project=project,
                        module_type=mod['module_type'],
                        order=idx,
                        time_limit=mod.get('time_limit', 60),
                        story_text=mod.get('story_text', ''),
                        config_data=mod.get('config_data', {})
                    )
                
                # Check for multiple file input for this module
                file_key = f'module_images_{idx}'
                if file_key in request.FILES:
                    module_obj.images.all().delete()
                    for img in request.FILES.getlist(file_key):
                        ProjectModuleImage.objects.create(module=module_obj, image=img)
                
                submitted_ids.append(module_obj.id)
                
            # Delete any modules that were removed in the UI
            project.modules.exclude(id__in=submitted_ids).delete()
        except Exception as e:
            pass
            
        return redirect('creator_list')

    # Serialize modules list to JSON string for the template
    modules_list = []
    if project:
        for mod in project.modules.all():
            image_urls = [img.image.url for img in mod.images.all()]
            # Fallback to legacy single image if exists and no multiple images
            if not image_urls and mod.story_image:
                image_urls = [mod.story_image.url]
                
            modules_list.append({
                'id': mod.id,
                'module_type': mod.module_type,
                'module_name': mod.get_module_type_display(),
                'time_limit': mod.time_limit,
                'story_text': mod.story_text or '',
                'config_data': mod.config_data or {},
                'image_urls': image_urls
            })
    modules_json = json.dumps(modules_list)
    
    project_image_urls = []
    if project:
        project_image_urls = [img.image.url for img in project.images.all()]
        if not project_image_urls and project.story_image:
            project_image_urls = [project.story_image.url]
        
    return render(request, 'mainapp/creator_form.html', {
        'project': project, 
        'project_image_urls': json.dumps(project_image_urls),
        'module_choices': ProjectModule.MODULE_CHOICES,
        'modules_json': modules_json
    })

@login_required
def creator_delete(request, project_id):
    project = get_object_or_404(Project, id=project_id, creator=request.user)
    if request.method == 'POST':
        project.delete()
        return redirect('creator_list')
    return render(request, 'mainapp/creator_confirm_delete.html', {'project': project})

@login_required
def player_list(request):
      projects = Project.objects.all()
      return render(request, 'mainapp/player_list.html', {'projects': projects})

@login_required
def player_play(request, project_id):
      project = get_object_or_404(Project, id=project_id)
      modules_list = []
      for mod in project.modules.all():
          modules_list.append({
              'module_type': mod.module_type,
              'time_limit': mod.time_limit,
              'story': mod.story_text or '',
              'image_url': mod.story_image.url if mod.story_image else '',
              'config': mod.config_data or {}
          })
      modules_json = json.dumps(modules_list)
      return render(request, 'mainapp/player_play.html', {
          'project': project,
          'play_modules_json': modules_json
      })