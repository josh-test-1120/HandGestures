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
	path("summary/", views.summary, name="summary"),
	path("summary_page_update/", views.summary_page_update, name="summary_page_update"),
	path("demo_page_update/", views.demo_page_update, name="demo_page_update"),
	path("structure/", views.structure, name="structure"),
	path("demo/",views.demo, name="demo"),
	path("machine_learning/", views.machine_learning, name="machine_learning"),
	path("live-demo/", views.live_demo, name="live_demo"),
	path("contact/", views.contact, name='contact'),
	path("live_demo_prediction/", views.live_demo_prediction, name="live_demo_prediction"),
	path("download-template/", views.download_template, name="download_template"),
	path("upload-contribution/", views.upload_contribution, name="upload_contribution"),
	#path('api/report/', views.api_report, name='api_report'),  # Example

	# Regex matcher
	#re_path(r'^$', views.index, name='index'),
	#re_path(r'^course/add$', views.course_add, name='course_add'),
	#re_path(r'^course/destroy/(?P<course_id>\d+)$', views.course_destroy, name='destroy'),
	#re_path(r'^course/delete/(?P<course_id>\d+)$', views.course_remove, name='course_remove'),
	#re_path(r'^course/comment/(?P<course_id>\d+)$', views.course_comment, name='course_comment_show'),
	#re_path(r'^course/comment/add/(?P<course_id>\d+)$', views.course_comment_add, name='course_comment_add'),
	#re_path(r'^course/comment/delete/(?P<comment_id>\d+)$', views.course_comment_delete, name='course_comment_delete'),
]