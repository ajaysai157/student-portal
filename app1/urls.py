from django.urls import path
from . import views

urlpatterns=[
    path('',views.home,name='home'),
    path('register/',views.register,name='registration'),
    path('students-list/',views.students_list,name='students_list'),
    path('update-student/<str:student_id>/',views.update_student,name='update_student'),
    path('delete-student/<str:student_id>/',views.delete_student,name='delete_student'),
    path('student/<str:student_id>/', views.student_detail, name='student_detail')
]