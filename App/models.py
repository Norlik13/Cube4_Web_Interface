from django.db import models


class Customer(models.Model):
    idCustomer = models.AutoField(primary_key=True)
    customer_name = models.CharField(max_length=255, unique=True)
    mail_address = models.EmailField(unique=True)
    password = models.CharField(max_length=255)  # Not hashed, as per your requirement

    def __str__(self):
        return self.customer_name

