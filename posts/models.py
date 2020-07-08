from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Group(models.Model):
    title = models.CharField(max_length=200, verbose_name='Название')
    slug = models.SlugField(unique=True, verbose_name='Идентификатор')
    description = models.TextField(
        max_length=200,
        verbose_name='Описание группы'
    )

    def __str__(self):
        return self.title


class Post(models.Model):
    text = models.TextField(verbose_name='Текст статьи')
    pub_date = models.DateTimeField(
        "Дата публикации", 
        auto_now_add=True, 
        db_index=True
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="posts",
        blank=True,
        null=True
    )
    author = models.ForeignKey(User, models.CASCADE, "posts")
    image = models.ImageField(upload_to='posts/', blank=True, null=True)

    class Meta:
        ordering = ['-pub_date']

    def __str__(self):
        return self.text

    
class Comment(models.Model):
    post = models.ForeignKey(Post, models.CASCADE, "comments")
    author = models.ForeignKey(User, models.CASCADE, "comment")
    text = models.TextField("Текст комментария")
    created = models.DateTimeField("Дата публикации", auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.text


class Follow(models.Model):
    user = models.ForeignKey(User, models.CASCADE, "follower")
    author = models.ForeignKey(User, models.CASCADE, "following")

    class Meta:
        unique_together = ["user", "author"]
