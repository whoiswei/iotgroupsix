from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .models import Project, ProjectModule, ProjectImage, ProjectModuleImage, ProjectSuccessImage, ProjectFailureImage, GameSession
import json

try:
    import paho.mqtt.publish as mqtt_publish
except ImportError:
    mqtt_publish = None

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
        time_limit_str = request.POST.get('time_limit', '3600')
        try:
            max_errors = int(max_errors_str)
        except ValueError:
            max_errors = 3
            
        try:
            time_limit = int(time_limit_str)
        except ValueError:
            time_limit = 3600

        success_text = request.POST.get('success_text')
        failure_text = request.POST.get('failure_text')

        if not project:
            project = Project.objects.create(
                creator=request.user, 
                title=title, 
                story_intro=story_intro,
                max_errors=max_errors,
                time_limit=time_limit,
                success_text=success_text,
                failure_text=failure_text
            )
        else:
            project.title = title
            project.story_intro = story_intro
            project.max_errors = max_errors
            project.time_limit = time_limit
            project.success_text = success_text
            project.failure_text = failure_text
            project.save()
            
        # Handle custom success result images (multiple)
        if 'success_images' in request.FILES:
            project.success_images.all().delete()
            for img in request.FILES.getlist('success_images'):
                ProjectSuccessImage.objects.create(project=project, image=img)
            
        # Handle custom failure result images (multiple)
        if 'failure_images' in request.FILES:
            project.failure_images.all().delete()
            for img in request.FILES.getlist('failure_images'):
                ProjectFailureImage.objects.create(project=project, image=img)
            
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
    success_image_urls = []
    failure_image_urls = []
    if project:
        project_image_urls = [img.image.url for img in project.images.all()]
        if not project_image_urls and project.story_image:
            project_image_urls = [project.story_image.url]
        success_image_urls = [img.image.url for img in project.success_images.all()]
        failure_image_urls = [img.image.url for img in project.failure_images.all()]
        
    return render(request, 'mainapp/creator_form.html', {
        'project': project, 
        'project_image_urls': json.dumps(project_image_urls),
        'success_image_urls_json': json.dumps(success_image_urls),
        'failure_image_urls_json': json.dumps(failure_image_urls),
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
      
      project_image_urls = [img.image.url for img in project.images.all()]
      if not project_image_urls and project.story_image:
          project_image_urls = [project.story_image.url]
          
      modules_list = []
      for mod in project.modules.all():
          image_urls = [img.image.url for img in mod.images.all()]
          if not image_urls and mod.story_image:
              image_urls = [mod.story_image.url]
              
          modules_list.append({
              'module_type': mod.module_type,
              'time_limit': mod.time_limit,
              'story': mod.story_text or '',
              'image_urls': image_urls,
              'config': mod.config_data or {}
          })
      modules_json = json.dumps(modules_list)
      success_image_urls = [img.image.url for img in project.success_images.all()]
      failure_image_urls = [img.image.url for img in project.failure_images.all()]
      return render(request, 'mainapp/player_play.html', {
          'project': project,
          'project_image_urls_json': json.dumps(project_image_urls),
          'play_modules_json': modules_json,
          'success_image_urls_json': json.dumps(success_image_urls),
          'failure_image_urls_json': json.dumps(failure_image_urls),
      })

@csrf_exempt
@login_required
def api_start_game(request, project_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'}, status=400)
    
    project = get_object_or_404(Project, id=project_id)
    
    # Deactivate any previous sessions for this project
    GameSession.objects.filter(project=project, is_active=True).update(is_active=False)
    
    # Create new game session
    session = GameSession.objects.create(
        project=project,
        current_module_index=0,
        errors_committed=0,
        status='playing',
        is_active=True
    )
    
    # Format module configurations to send to MQTT
    modules_data = []
    for mod in project.modules.all():
        modules_data.append({
            'order': mod.order,
            'module_type': mod.module_type,
            'module_name': mod.get_module_type_display(),
            'time_limit': mod.time_limit,
            'config': mod.config_data or {}
        })
        
    mqtt_payload = {
        'session_id': session.id,
        'project_id': project.id,
        'total_time': project.time_limit,
        'max_errors': project.max_errors,
        'modules': modules_data
    }
    
    # Send MQTT message
    mqtt_sent = False
    if mqtt_publish:
        try:
            mqtt_publish.single(
                "escaperoom/game/start",
                payload=json.dumps(mqtt_payload),
                hostname="127.0.0.1",
                port=1883
            )
            mqtt_sent = True
        except Exception as e:
            pass

    return JsonResponse({
        'status': 'success',
        'session_id': session.id,
        'mqtt_sent': mqtt_sent
    })

@login_required
def api_game_status(request, session_id):
    session = get_object_or_404(GameSession, id=session_id)
    return JsonResponse({
        'status': 'success',
        'session_id': session.id,
        'current_module_index': session.current_module_index,
        'errors_committed': session.errors_committed,
        'game_status': session.status,
        'is_active': session.is_active
    })

@csrf_exempt
def api_game_event(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'}, status=400)
        
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        event = data.get('event')  # 'module_solved', 'wrong_answer', 'game_over', 'game_win'
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON body'}, status=400)
        
    session = get_object_or_404(GameSession, id=session_id)
    
    if not session.is_active or session.status != 'playing':
        return JsonResponse({'status': 'success', 'message': 'Session is not active or game already ended', 'game_status': session.status})
        
    total_modules = session.project.modules.count()
    
    if event == 'module_solved':
        session.current_module_index += 1
        if session.current_module_index >= total_modules:
            session.status = 'success'
            session.is_active = False
    elif event == 'wrong_answer':
        session.errors_committed += 1
        if session.errors_committed >= session.project.max_errors:
            session.status = 'failed'
            session.is_active = False
    elif event == 'game_over':
        session.status = 'failed'
        session.is_active = False
    elif event == 'game_win':
        session.status = 'success'
        session.is_active = False
        
    session.save()
    
    # Notify Node-RED/Hardware that the game has ended
    if session.status in ['failed', 'success']:
        try:
            import paho.mqtt.publish as mqtt_publish
            mqtt_publish.single(
                "escaperoom/game/stop",
                payload=json.dumps({'session_id': session.id, 'status': session.status}),
                hostname="127.0.0.1",
                port=1883
            )
        except Exception:
            pass
    
    return JsonResponse({
        'status': 'success',
        'session_id': session.id,
        'current_module_index': session.current_module_index,
        'errors_committed': session.errors_committed,
        'game_status': session.status
    })

@csrf_exempt
def toggle_pi_led(request):
    if request.method == 'POST':
        try:
            import paho.mqtt.publish as mqtt_publish
            mqtt_publish.single(
                "escaperoom/pi/led_toggle",
                payload=json.dumps({'action': 'toggle'}),
                hostname="127.0.0.1",
                port=1883
            )
            return JsonResponse({'status': 'success', 'message': 'MQTT sent'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)