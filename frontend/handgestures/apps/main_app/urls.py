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
	path("summary/", views.summary, name="summary"), # Summary page
	path("summary_page_update/", views.summary_page_update, name="summary_page_update"), #Summary page update
	path("demo_page_update/", views.demo_page_update, name="demo_page_update"), # Demo page update
	path("structure/", views.structure, name="structure"), # Structure page
	path("demo/",views.demo, name="demo"), # Demo page
    path("machine_learning/", views.machine_learning, name="machine_learning"), # Machine Learning page
	path("live-demo/", views.live_demo, name="live_demo"), # Live demo page
	path("contact/",views.contact, name ='contact'), # Contact page
	
]
