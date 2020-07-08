from django.forms import ModelForm

from .models import Comment, Post


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ['group', 'image', 'text']
        labels = {
            'group': 'Для какой группы пост пишете?',
            'text': 'А что пишете?',
            'image': 'Сюда можно картинку добавить.',
        }
        help_texts = {
            'group': 'Если ни для какой - оставьте поле пустым.',
            'text': 'Напишите здесь текст своего поста.',
            'image': 'Только картинки.',
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        labels = {'text': 'Что скажете?'}
        help_texts = {'text': 'Поделитесь мнением о прочитанном посте'}
