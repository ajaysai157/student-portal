from django.db import models

# Create your models here.
class Students(models.Model):
    SECTION_CHOICES = [
        (1, "Section 1"),
        (2, "Section 2"),
        (3, "Section 3"),
    ]
    student_name=models.CharField(max_length=30)
    student_id=models.CharField(max_length=15,unique=True)
    student_branch=models.CharField(max_length=40)
    student_section=models.IntegerField(choices=SECTION_CHOICES)
    student_image=models.ImageField(upload_to='student_images/', blank=True, null=True)

    class Meta:
        db_table='Students'

    def __str__(self):
        return f"{self.student_name}({self.student_id[6:]})"