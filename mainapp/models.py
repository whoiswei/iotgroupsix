from django.db import models
from django.contrib.auth.models import User

class Project(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=100)
    story_intro = models.TextField(blank=True, null=True)
    story_image = models.ImageField(upload_to='project_images/', blank=True, null=True)
    max_errors = models.PositiveIntegerField(default=3, help_text="Maximum allowed errors before game over")
    time_limit = models.PositiveIntegerField(default=3600, help_text="Global time limit in seconds")
    success_text = models.TextField(blank=True, null=True, help_text="Custom text shown on success")
    failure_text = models.TextField(blank=True, null=True, help_text="Custom text shown on failure")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class ProjectModule(models.Model):
    MODULE_CHOICES = [
        (1, '方向指令模組'),
        (2, '鑰匙模組'),
        (3, '調頻模組'),
        (4, 'RGB模組'),
        (5, '摩斯密碼模組'),
        (6, '旋鈕模組'),
        (7, '密碼模組'),
        (8, '拆線模組'),
        (9, '符號指撥開關模組'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='modules')
    module_type = models.IntegerField(choices=MODULE_CHOICES)
    order = models.PositiveIntegerField(default=0)
    time_limit = models.PositiveIntegerField(default=60, help_text="Time limit in seconds")
    story_text = models.TextField(blank=True, null=True, help_text="Story context for this module")
    story_image = models.ImageField(upload_to='module_images/', blank=True, null=True)
    config_data = models.JSONField(default=dict, blank=True, help_text="JSON data containing the answers/config for the module")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.project.title} - Module {self.get_module_type_display()} ({self.order})"

class ProjectImage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='project_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class ProjectModuleImage(models.Model):
    module = models.ForeignKey(ProjectModule, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='module_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class ProjectSuccessImage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='success_images')
    image = models.ImageField(upload_to='project_success/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class ProjectFailureImage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='failure_images')
    image = models.ImageField(upload_to='project_failure/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class GameSession(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    current_module_index = models.PositiveIntegerField(default=0)
    errors_committed = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, default='playing')  # 'playing', 'success', 'failed'
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session for {self.project.title} - Step {self.current_module_index} ({self.status})"