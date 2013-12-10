from django.contrib import admin
from django.utils.translation import ugettext, ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User as AuthUser, Group as AuthGroup, Permission as AuthPermission
from django.contrib.admin import SimpleListFilter
from django.utils.encoding import force_text
from django.contrib.admin.views.main import ChangeList
from django.db.models import Q

from openipam.dns.models import Domain
from openipam.hosts.models import Host
from openipam.network.models import Network
from openipam.user.models import User, Group, Permission, UserToGroup, HostToGroup, NetworkToGroup, PoolToGroup, DomainToGroup
from openipam.user.forms import AuthUserCreateAdminForm, AuthUserChangeAdminForm, AuthGroupAdminForm, \
    UserObjectPermissionAdminForm, GroupObjectPermissionAdminForm

from guardian.models import UserObjectPermission, GroupObjectPermission

import autocomplete_light


class AuthUserAdmin(UserAdmin):
    add_form = AuthUserCreateAdminForm
    form = AuthUserChangeAdminForm

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions',)}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    # def save_formset(self, request, form, formset, change):
    #     assert False, change


class AuthGroupAdmin(GroupAdmin):
    pass
    #form = AuthGroupAdminForm


class AuthPermissionAdmin(admin.ModelAdmin):
    list_filter = ('content_type__app_label',)
    list_select_related = True
    search_fields = ('name', 'content_type__name', 'content_type__app_label',)


class UserPermissionInline(admin.TabularInline):
    model = UserToGroup
    fk_name = 'uid'
    readonly_fields = ('changed_by', 'changed')
    #form = UserPermissionInlineForm

    def has_change_permission(self, request, obj=None):
        return False


class GroupPermissionInline(admin.TabularInline):
    model = UserToGroup
    fk_name = 'gid'


class UserAdmin(admin.ModelAdmin):
    search_fields = ('username',)


class GroupTypeFilter(admin.SimpleListFilter):
    title = 'group type'

    parameter_name = 'type'

    def lookups(self, request, model_admin):
        return (
            ('group', 'Groups'),
            ('user', 'Users'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'user':
            return queryset.filter(name__istartswith='user_')
        if self.value() == 'group':
            return queryset.exclude(name__istartswith='user_')

    def choices(self, cl):
        # yield {
        #     'selected': self.value() is None,
        #     'query_string': cl.get_query_string({}, [self.parameter_name]),
        #     'display': _('All'),
        # }
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == force_text(lookup),
                'query_string': cl.get_query_string({
                    self.parameter_name: lookup,
                }, []),
                'display': title,
            }



class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'permissions', 'lhosts', 'ldomains', 'lnetworks', 'lpools', 'users')
    list_filter = (GroupTypeFilter,)
    search_fields = ('name',)
    form = autocomplete_light.modelform_factory(Group)
    list_per_page = 200

    def get_queryset(self, request):
        qs = super(GroupAdmin, self).get_queryset(request)

        if not request.GET.get('type', None):
            return qs.prefetch_related('domains', 'hosts', 'networks', 'pools', 'user_groups').exclude(name__istartswith='user_')

        return qs

    def ldomains(self, obj):
        return '<a href="../domaintogroup/?group=%s">%s</a>' % (obj.pk, obj.domains.count())
    ldomains.short_description = 'Domains'
    ldomains.allow_tags = True

    def lhosts(self, obj):
        return '<a href="../hosttogroup/?group=%s">%s</a>' % (obj.pk, obj.hosts.count())
    lhosts.short_description = 'Hosts'
    lhosts.allow_tags = True

    def lnetworks(self, obj):
        return '<a href="../networktogroup/?group=%s">%s</a>' % (obj.pk, obj.networks.count())
    lnetworks.short_description = 'Networks'
    lnetworks.allow_tags = True

    def lpools(self, obj):
        return '<a href="../pooltogroup/?group=%s">%s</a>' % (obj.pk, obj.pools.count())
    lpools.short_description = 'Pools'
    lpools.allow_tags = True

    def permissions(self, obj):
        perms = set([ug.permissions.name for ug in obj.user_groups.all()])
        return ','.join(perms)

    def host_permissions(self, obj):
        perms = set([ug.host_permissions.name for ug in obj.user_groups.all()])
        return ','.join(perms)

    def users(self, obj):
        return '<a href="../user/?group=%s">%s</a>' % (obj.pk, obj.user_groups.count())
    users.allow_tags = True


class PermissionAdmin(admin.ModelAdmin):
    pass


# class UserObjectPermissionFilter(SimpleListFilter):
#     title = 'permission'
#     parameter_name = 'permission'

#     def lookups(self, request, model_admin):
#         permissions = AuthPermission.objects.select_related().filter(
#             Q(codename__icontains='is_owner') | Q(codename__icontains='add_records_to')
#         )
#         permisssion_filters = [(permission.id, permission,) for permission in permissions]

#         return tuple(permisssion_filters)

#     def queryset(self, request, queryset):

#         if self.value():
#             permission = AuthPermission.objects.get(id=self.value())

#             queryset = UserObjectPermission.objects.filter(permission=permission)

#         return queryset


class ObjectPermissionFilter(SimpleListFilter):
    title = 'permission'
    parameter_name = 'permission'

    def lookups(self, request, model_admin):
        permissions = AuthPermission.objects.select_related().filter(
            Q(codename__icontains='is_owner') | Q(codename__icontains='add_records_to')
        )
        permisssion_filters = [(permission.id, permission,) for permission in permissions]

        return tuple(permisssion_filters)

    def queryset(self, request, queryset):

        if self.value():
            permission = AuthPermission.objects.get(id=self.value())
            queryset = queryset.filter(permission=permission)

        return queryset


class ObjectFilter(SimpleListFilter):
    title = 'Object'
    parameter_name = 'object'

    def lookups(self, request, model_admin):
        objects = ContentType.objects.select_related().filter(
            Q(permission__codename__icontains='is_owner') | Q(permission__codename__icontains='add_records_to')
        ).distinct()
        objects_filters = [(obj.id, obj,) for obj in objects]

        return tuple(objects_filters)

    def queryset(self, request, queryset):

        if self.value():
            queryset = queryset.filter(content_type__id=self.value())

        return queryset


class ObjectPermissionSearchChangeList(ChangeList):
    "Changelist to do advanced object perms search"

    def get_query_set(self, request):
        search_qs = request.GET.get('q', '')
        term = search_qs.split(':')[-1]
        if search_qs.startswith('domain:') and term:
            domains = [domain.pk for domain in Domain.objects.filter(name__istartswith=term)]
            qs = self.root_queryset.filter(object_pk__in=domains, content_type__name='domain')
        elif search_qs.startswith('host:') and term:
            hosts = [host.pk for host in Host.objects.filter(hostname__istartswith=term)]
            qs = self.root_queryset.filter(object_pk__in=hosts, content_type__name='host')
        elif search_qs.startswith('network:') and term:
            networks = [network.pk for network in Network.objects.filter(network__istartswith=term)]
            qs = self.root_queryset.filter(object_pk__in=networks, content_type__name='network')
        else:
            qs = super(ObjectPermissionSearchChangeList, self).get_query_set(request)

        return qs


class UserObjectPermissionAdmin(admin.ModelAdmin):
    form = UserObjectPermissionAdminForm
    list_display = ('user', 'object_name', 'permission',)
    list_filter = (ObjectPermissionFilter,)
    search_fields = ('user__username', '^object_pk')

    def get_changelist(self, request, **kwargs):
        return ObjectPermissionSearchChangeList

    def change_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        extra_context['readonly'] = True
        return super(UserObjectPermissionAdmin, self).change_view(request, object_id, extra_context=extra_context)

    def get_queryset(self, request):
        qs = super(UserObjectPermissionAdmin, self).queryset(request)
        qs = qs.prefetch_related('user', 'permission', 'content_object').all()
        return qs

    def save_model(self, request, obj, form, change):
        obj.content_type_id = form.cleaned_data['object_id'].split('-')[0]
        obj.object_pk = form.cleaned_data['object_id'].split('-')[1]
        obj.save()

    def object_name(self, obj):
        c_obj = obj.content_type.model_class().objects.get(pk=obj.object_pk)
        return '%s - %s' % (obj.content_type.model, c_obj)
    object_name.short_description = 'Object'


class GroupObjectPermissionAdmin(admin.ModelAdmin):
    list_display = ('group', 'object_name', 'permission',)
    list_filter = (ObjectPermissionFilter, ObjectFilter)
    form = GroupObjectPermissionAdminForm
    search_fields = ('group__name', '^object_pk', 'group__user__username')

    def get_changelist(self, request, **kwargs):
        return ObjectPermissionSearchChangeList

    def save_model(self, request, obj, form, change):
        obj.content_type_id = form.cleaned_data['object_id'].split('-')[0]
        obj.object_pk = form.cleaned_data['object_id'].split('-')[1]
        obj.save()

    def object_name(self, obj):
        #c_obj = obj.content_type.model_class().objects.get(pk=obj.object_pk)
        return '%s - %s' % (obj.content_type.model, obj.content_object)
        #return obj.content_object
    object_name.short_description = 'Object'


class UserGroupTypeFilter(admin.SimpleListFilter):
    title = 'group'

    parameter_name = 'group'

    def lookups(self, request, model_admin):
        groups = Group.objects.exclude(name__istartswith='user_')
        group_vals = [(group.pk, group.name) for group in groups]

        return tuple(group_vals)

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(group__pk=self.value())

    def choices(self, cl):
        yield {
            'selected': self.value() is None,
            'query_string': cl.get_query_string({}, [self.parameter_name]),
            'display': _('All'),
        }
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == force_text(lookup),
                'query_string': cl.get_query_string({
                    self.parameter_name: lookup,
                }, []),
                'display': title,
            }


class UserToGroupAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'permissions', 'host_permissions')
    list_filter = (UserGroupTypeFilter,)
    form = autocomplete_light.modelform_factory(UserToGroup)


class HostToGroupAdmin(admin.ModelAdmin):
    list_display = ('host', 'group')
    form = autocomplete_light.modelform_factory(HostToGroup)


class DomainToGroupAdmin(admin.ModelAdmin):
    list_display = ('domain', 'group')
    list_filter = (UserGroupTypeFilter,)
    form = autocomplete_light.modelform_factory(DomainToGroup)


class NetworkToGroupAdmin(admin.ModelAdmin):
    list_display = ('network', 'group')
    form = autocomplete_light.modelform_factory(NetworkToGroup)


class PoolToGroupAdmin(admin.ModelAdmin):
    list_display = ('pool', 'group')
    form = autocomplete_light.modelform_factory(PoolToGroup)


admin.site.register(User, AuthUserAdmin)
admin.site.unregister(AuthGroup)
admin.site.register(AuthGroup, AuthGroupAdmin)
admin.site.register(AuthPermission, AuthPermissionAdmin)

admin.site.register(Group, GroupAdmin)
admin.site.register(Permission, PermissionAdmin)

admin.site.register(UserToGroup, UserToGroupAdmin)
admin.site.register(HostToGroup, HostToGroupAdmin)
admin.site.register(DomainToGroup, DomainToGroupAdmin)
admin.site.register(NetworkToGroup, NetworkToGroupAdmin)
admin.site.register(PoolToGroup, PoolToGroupAdmin)

admin.site.register(UserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(GroupObjectPermission, GroupObjectPermissionAdmin)
