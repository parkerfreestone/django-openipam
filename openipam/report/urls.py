from django.conf.urls import url

from openipam.report import views


urlpatterns = [
    url(r"^disabled/$", views.DisabledHostsView.as_view(), name="reports_disabled"),
    url(
        r"^server_hosts/$", views.ServerHostsView.as_view(), name="reports_server_hosts"
    ),
    url(r"^host_dns/$", views.HostDNSView.as_view(), name="reports_host_dns"),
    url(r"^ptr_dns/$", views.PTRDNSView.as_view(), name="reports_ptr_dns"),
    url(r"^$", views.DashboardView.as_view(), name="reports_dashboard"),
]
