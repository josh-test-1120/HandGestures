# Import statements for application
from django.urls import path, include, re_path
# Import your views
from . import views
# Use this if you want to import views from other applications
# from ../<other_app> import views as <other_app_view_name>

app_name = 'main_app' 

# URL patterns to process for the application
urlpatterns = [
     # Home page
    path("", views.index, name="index"),
    path('api/data/', views.api_data, name='api_data'),  # API testing
	#re_path(r'^$', views.index, name='index'),
	#re_path(r'^course/add$', views.course_add, name='course_add'),
	#re_path(r'^course/destroy/(?P<course_id>\d+)$', views.course_destroy, name='destroy'),
	#re_path(r'^course/delete/(?P<course_id>\d+)$', views.course_remove, name='course_remove'),
	#re_path(r'^course/comment/(?P<course_id>\d+)$', views.course_comment, name='course_comment_show'),
	#re_path(r'^course/comment/add/(?P<course_id>\d+)$', views.course_comment_add, name='course_comment_add'),
	#re_path(r'^course/comment/delete/(?P<comment_id>\d+)$', views.course_comment_delete, name='course_comment_delete'),
]
