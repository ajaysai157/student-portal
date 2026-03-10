from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Students
from django.contrib import messages


# Home Page
def home(request):
    return render(request,'home_page.html')


# Students List (PUBLIC)
def students_list(request):

    students = Students.objects.all()

    return render(request, 'students_list.html', {'students': students})


# Student Detail Page (PUBLIC)
def student_detail(request, student_id):

    student = get_object_or_404(Students, student_id=student_id)

    return render(request, 'student_detail.html', {'student': student})


# Register Student
def register(request):
    if request.method == 'POST':
        student_name = request.POST.get('student_name')
        student_id = request.POST.get('student_id')
        student_branch = request.POST.get('student_branch')
        student_section = request.POST.get('student_section')
        student_image = request.FILES.get('student_image')

        Students.objects.create(
            student_name=student_name,
            student_id=student_id,
            student_branch=student_branch,
            student_section=student_section,
            student_image=student_image
        )
        messages.success(request, "Student registered successfully!")
        return redirect('students_list')

    return render(request, 'register_student.html')


# Update Student
def update_student(request, student_id):
    student = get_object_or_404(Students, student_id=student_id)
    if request.method == 'POST':
        student.student_name = request.POST.get('student_name')
        student.student_branch = request.POST.get('student_branch')
        student.student_section = request.POST.get('student_section')
        if request.FILES.get('student_image'):
            student.student_image = request.FILES.get('student_image')

        student.save()
        messages.success(request, "Student updated successfully!")
        return redirect('students_list')
    return render(request, 'update_student.html', {'student': student})


# Delete Student
def delete_student(request, student_id):
    student = get_object_or_404(Students, student_id=student_id)
    student.delete()
    messages.success(request, "Student deleted successfully!")

    return redirect('students_list')