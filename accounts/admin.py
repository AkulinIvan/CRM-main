from django.contrib import admin


from accounts.models import Address, User, AddressSpecializationAssignment, ExecutorProfile

admin.site.register(User)
admin.site.register(AddressSpecializationAssignment)

class AddressAdmin(admin.ModelAdmin):
    list_display = ('street', 'building', 'apartment', 'management_company')
    list_filter = ('management_company', 'street')
    # filter_horizontal = ('assigned_executors',)
    search_fields = ('street', 'building', 'apartment')

admin.site.register(Address, AddressAdmin)
admin.site.register(ExecutorProfile)