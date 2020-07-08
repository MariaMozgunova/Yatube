from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Comment, Follow, Group, Post, User


def check_follows(user, author):
    """"Подписан ли user на author"""
    try:
        Follow.objects.get(user=user, author=author)
        return True
    except:
        return False


def index(request):
    """Вывод 10 записей на главную страницу"""
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'index.html',
        {'page': page, "paginator": paginator, "index_view": True}
    )


def group_posts(request, slug):
    """Возвращение страницы сообщества и вывод новых записей"""
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        "group.html",
        {"group": group, "page": page, "paginator": paginator}
    )


@login_required
def new_post(request):
    """Создание новой записи"""
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('index')

    return render(request, 'new.html', {'form': form, "is_edit": False})


def profile(request, username):
    """Возвращение  информации об авторе и его постов"""
    user = get_object_or_404(User, username=username)
    post_list = user.posts.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        "profile.html",
        {"author": user, 
         "page": page, 
         "paginator": paginator, 
         "following": check_follows(request.user, user)
        }
    )


def post_view(request, username, post_id):
    """Возвращение отдельного поста и комментариев"""
    form = CommentForm()
    user = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, id=post_id, author=user)
    comments_list = post.comments.all()
    paginator = Paginator(comments_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request, 
        "post.html", 
        {"author": post.author, 
         "comment_context": comments_list,
         "post": post, 
         "items": page, 
         "form": form,
         "following": check_follows(request.user, user)
        } 
    )


@login_required
def post_edit(request, username, post_id):
    post = get_object_or_404(Post, id=post_id, author__username=username)

    if request.user != post.author:
        return redirect('post', username=username, post_id=post_id)
    
    form = PostForm(
        request.POST or None, 
        files=request.FILES or None, 
        instance=post
    )        
    if request.POST and form.is_valid():
        form.save()
        return redirect('post', username=username, post_id=post_id)
                
    return render(
        request,
        'new.html',
        {'form': form, 'is_edit': True, 'post': post}
    )


@login_required
def add_comment(request, username, post_id):
    """Создание комментария к посту"""
    form = CommentForm(request.POST or None)
    if request.POST and form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = get_object_or_404(
            Post, 
            pk=post_id, 
            author__username=username
        )
        comment.save()
    
    return redirect('post', username=username, post_id=post_id)


def page_not_found(request, exception):
    """Страница не найдена"""
    return render(
        request, 
        "misc/404.html", 
        {"path": request.path}, 
        status=404
    )


def server_error(request):
    """Ошибка сервера"""
    return render(request, "misc/500.html", status=500)


@login_required
def follow_index(request):
    """Посты авторов, на которых подписан текущий пользователь."""
    post_list = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request, 
        "follow.html", 
        {"page": page, "follow": True, "paginator": paginator}
    )


@login_required
def profile_follow(request, username):
    """Подписка на интересного автора."""
    author = get_object_or_404(User, username=username)
    if author != request.user:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect(request.META.get('HTTP_REFERER') or "index")


@login_required
def profile_unfollow(request, username):
    """Отписка от надоевшего графомана."""
    follow = get_object_or_404(
        Follow, 
        user=request.user, 
        author__username=username
    )
    follow.delete()
    return redirect(request.META.get('HTTP_REFERER') or "index")
