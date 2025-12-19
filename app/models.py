from django.db import models
from django.contrib.auth.models import User

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20)
    course = models.CharField(max_length=100)

    def __str__(self):
        return self.user.username


class LearningData(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    quiz_score = models.IntegerField()
    assignment_score = models.IntegerField()
    time_spent_hours = models.FloatField()

    def performance_score(self):
        return (self.quiz_score + self.assignment_score) / 2
