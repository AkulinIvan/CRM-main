from django.db import models


class ManagementCompany(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    
    def __str__(self):
        return self.name
    
    def executor_count(self):
        from accounts.models import User
        return self.user_set.filter(role=User.Role.EXECUTOR).count()
    
    def master_count(self):
        from accounts.models import User
        return self.user_set.filter(role=User.Role.MASTER).count()
    
    def active_tickets_count(self):
        from tickets.models import Ticket
        return self.tickets.filter(status__in=[
            Ticket.Status.NEW,
            Ticket.Status.ASSIGNED,
            Ticket.Status.IN_PROGRESS
        ]).count()
        
    def get_masters(self):
        """Возвращает всех мастеров компании"""
        from accounts.models import User
        return User.objects.filter(
            management_company=self,
            role=User.Role.MASTER
        )
    
    def get_executors(self):
        """Возвращает всех исполнителей компании"""
        from accounts.models import User
        return User.objects.filter(
            management_company=self,
            role=User.Role.EXECUTOR
        )
