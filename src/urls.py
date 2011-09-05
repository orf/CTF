from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'flag.views.home'),
    url(r'^login$', 'flag.views.login'),
    url(r'^logout$', 'flag.views.logout'),
    url(r'^register$', 'flag.views.register'),
    url(r'^list_users$', 'flag.views.list_users'),
    url(r'^export_users$','flag.views.export_users'),
    url(r'^q/(?P<question_id>\d+)$', 'flag.views.question'),
    url(r'^q/(?P<question_id>\d+)/extra_time$', 'flag.views.boost_time'),
    url(r'^u/(?P<nickname>\w+)$','flag.views.view_user'),
    url(r'^stats$','flag.views.stats'),
    url(r'^feedback$','flag.views.feedback'),
    url(r'^final_points$','flag.views.finalize_points'),
    url(r'^generate_report$','flag.views.generate_report'),
    url(r'^active/(?P<question_id>\d+)$', 'flag.views.toggle_active'),
    url(r'^admin/orderedmove/(?P<direction>up|down)/(?P<model_type_id>\d+)/(?P<model_id>\d+)/$', 'flag.views.admin_move_ordered_model', name="admin-move"),
    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
