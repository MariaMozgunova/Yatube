from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Comment, Follow, Group, Post, User


@override_settings(CACHES={
    'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}
    }
)
class TestUser(TestCase):
    def check_post_info(self, post, author, group, text):
        """Проверка данных поста"""
        self.assertEqual(
            post.author, 
            author, 
            msg=f"Целевой автор не соответствует автору поста"
        )
        self.assertEqual(
            post.group, 
            group, 
            msg=f"Целевая группа не соответствует группе поста"
        )
        self.assertEqual(
            post.text, 
            text, 
            msg=f"Целевой текст не соответствует тексту поста"
        )

    def check_appears(self, urls, sended_post):
        """Пост post появляется на каждой странице списка urls"""
        for url in urls:
            resp = self.client.get(url)
            
            paginator = resp.context.get("paginator")
            if paginator is not None:
                post = resp.context["page"][0]
            else:
                post = resp.context["post"]

            self.check_post_info(
                post, 
                sended_post.author, 
                sended_post.group, 
                sended_post.text
            )

    def setUp(self):
        self.text = "New post"
        self.user = User.objects.create_user(username="user1", password="123")

    def test_profile_created(self):
        """После регистрации создается персональная страница пользователя."""
        response = self.client.get(
            reverse("profile",
            args=[self.user.username])
        )
        self.assertEqual(
            response.status_code,
            200,
            msg="Страница пользователя не найдена"
        )

    def test_authorised_new(self):
        """Авторизованный пользователь может опубликовать пост."""
        self.client.force_login(self.user)
        self.client.post(
            reverse("new_post"),
            {"text": self.text},
            follow=True
        )
        post = Post.objects.get(author=self.user)
        self.check_post_info(post, self.user, None, self.text)
        self.check_appears([reverse("index")], post)

        self.assertEqual(
            Post.objects.count(),
            1,
            msg="Новый пост не создаётся"
        )

    def test_not_new(self):
        """Неавторизованный посетитель не может опубликовать пост."""
        response = self.client.post(
            reverse("new_post"),
            {"text": self.text},
            follow=True
        )
        
        self.assertRedirects(
            response, 
            "/auth/login/?next=%2Fnew%2F", 
            msg_prefix="При попытке опубликовать пост неавторизованный " 
                       "посетитель должен быть перенаправлен на страницу "
                       "авторизации"
        )

        self.assertEqual(
            Post.objects.count(),
            0,
            msg="Неавторизованный посетитель не может опубликовать пост"
        )

    def test_new_appears(self):
        """
        После публикации поста новая запись появляется на: 
        -главной странице сайта,
        -на персональной странице пользователя,
        -и на отдельной странице поста.
        """

        self.client.force_login(self.user)
        self.client.post(reverse("new_post"), {"text": self.text})
        post = Post.objects.get(author=self.user)
        self.check_post_info(post, self.user, None, self.text)

        self.check_appears(
            [
                reverse("index"),
                reverse("profile", args=[self.user.username]),
                reverse("post", args=[self.user.username, post.id])
            ], 
            post
        )

    def test_can_edit(self):
        """
        Авторизованный пользователь может отредактировать свой пост и
        его содержимое изменится на всех связанных страницах.
        """

        self.client.force_login(self.user)
        
        group_old = Group.objects.create(slug="cars", title="Cars")
        group_new = Group.objects.create(slug="bikes", title="Bikes")

        post_id = Post.objects.create(
            author=self.user, 
            text=self.text, 
            group=group_old
        ).id
        self.text = "Changed"
        response = self.client.post(
            reverse("post_edit", args=[self.user.username, post_id]),
            {"group": group_new.id, "text": self.text},
            follow=True
        )
        post = Post.objects.get(author=self.user)
        self.check_post_info(post, self.user, group_new, self.text)

        self.check_appears(
            [
                reverse("index"),
                reverse("profile", args=[self.user.username]),
                reverse("post", args=[self.user.username, post_id]),
                reverse("group_posts", args=[group_new.slug])
            ], 
            post
        )
        
        response = self.client.get(
            reverse("group_posts",
            args=[group_old.slug])
        )
        self.assertNotContains(
            response, 
            post, 
            msg_prefix="После изменения группы поста, пост должен быть "
                       "удалён со страницы соответствующей группы"
        )


class TestHandler(TestCase):
    def test_page_not_found(self):
        "Cервер возвращает код 404, если страница не найдена."
        resp = self.client.get("/group/group/group/group/")
        self.assertEqual(
            resp.status_code, 
            404, 
            msg="Неверный статус-код при обработке ошибок"
        )
        self.assertTemplateUsed(
            resp,
            "misc/404.html",
            msg_prefix="Если страница не найдена, " 
                       "должен использоваться шаблон '404.html'"
        )


@override_settings(CACHES={
    'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}
    }
)
class TestImage(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user1", password="123")
        self.client.force_login(self.user)

    def test_img(self):
        group = Group.objects.create(slug="cars", title="Cars")
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9'
            b'\x04\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00'
            b'\x00\x02\x02\x4c\x01\x00\x3b'
        ) 
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        post_id = Post.objects.create(
            author=self.user, 
            text="post with image", 
            image=uploaded, 
            group=group
        ).id
        urls = [
            reverse("profile", args=[self.user.username]),
            reverse("post", args=[self.user.username, post_id]),
            reverse("group_posts", args=[group.slug]),
            reverse("index"),
        ]
        
        for url in urls:
            resp = self.client.get(url)
            paginator = resp.context.get("paginator")
            
            if paginator is not None:
                post = resp.context["page"][0]
            else:
                (resp.context["post"])
                post = resp.context["post"]
            self.assertTrue(post.image)
            self.assertContains(resp, '<img class="card-img" src=')

    def test_not_image(self):
        """Cрабатывает защита от загрузки файлов неграфических форматов"""
        txt = SimpleUploadedFile(
            name='test.txt',
            content=b'some text',
            content_type='text/plain'
        )
        resp = self.client.post( 
            reverse("new_post"),  
            {"text": "post with image", "image": txt} 
        ) 
        self.assertFormError(
            resp, 
            "form", 
            "image", 
            "Загрузите правильное изображение. Файл, который вы загрузили, " +
            "поврежден или не является изображением."
        )
        

class TestCache(TestCase):
    def get_index(self):
        self.client.get(reverse("index"))
        return make_template_fragment_key("index_page")

    def test_cache(self):
        """
        Cписок записей главной страницы хранится в кэше 
        и обновляется раз в 20 секунд.
        """

        self.user = User.objects.create_user(username="user1", password="123")
        cache_created = cache.get(self.get_index())
        Post.objects.create(author=self.user, text="some text")
        self.assertEqual(
            cache_created, 
            cache.get(self.get_index()), 
            msg="Кеш не сохраняется"
        )        
        cache.clear()
        self.assertNotEqual(
            cache_created, 
            cache.get(self.get_index()), 
            msg="Кеш должен сохраняться только в течении 20 секунд"
        )


class TestFollow(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user", password="123")
        self.user1 = User.objects.create_user(
            username="user1", 
            password="123"
        )
        self.client.force_login(self.user)
    
    def test_follow(self):
        """
        Авторизованный пользователь может 
        подписываться на других пользователей.
        """

        self.client.post(
            reverse("profile_follow", args=[self.user1.username])
        )
        self.assertEqual(Follow.objects.count(), 1)

    def test_unfollow(self):
        """
        Авторизованный пользователь может удалять 
        из подписок надоевших графоманов.
        """

        Follow.objects.create(user=self.user, author=self.user1)
        self.client.post(
            reverse("profile_unfollow", args=[self.user1.username])
        )
        self.assertEqual(Follow.objects.count(), 0)
    
    def test_follower(self):
        """
        Новая запись пользователя появляется 
        в ленте тех, кто на него подписан.
        """

        Follow.objects.create(user=self.user, author=self.user1)
        post = Post.objects.create(author=self.user1, text="New post")
        resp = self.client.get(reverse("follow_index"))
        self.assertIn(
            post, 
            resp.context["page"], 
            msg="Пользователь, подписанный на автра, должен видет его посты " 
                f"на странице {reverse('follow_index')}"
        )

    def test_not_follower(self):
        """
        Новая запись пользователя отсутствует
        в ленте тех, кто на него не подписан.
        """

        post = Post.objects.create(author=self.user1, text="New post")
        resp = self.client.get(reverse("follow_index"))
        self.assertNotIn(
            post, 
            resp.context["page"], 
            msg="Пользователь, не подписанный на автра, не может видет "
                f"его посты на странице {reverse('follow_index')}"
        )

    def test_can_comment(self):
        """Авторизированный пользователь может комментировать посты."""
        text = "New comment"
        post_id = Post.objects.create(author=self.user1, text=text).id
        self.client.post(
            reverse("add_comment", args=[self.user1.username, post_id]), 
            {"text": text}
        )
        self.assertEqual(
            Comment.objects.first().author, 
            self.user, 
            msg="Неправильно задаётся автор комментария."
        )
        self.assertEqual(
            Comment.objects.first().text, 
            text, 
            msg="Неправильно задаётся текст комментария."
        )
    
    def test_cannot_comment(self):
        """Неавторизированный пользователь не может комментировать посты."""
        self.client.logout()
        text = "New comment"
        post_id = Post.objects.create(author=self.user1, text=text).id
        self.client.post(
            reverse("add_comment", args=[self.user1.username, post_id]), 
            {"text": text}
        )
        self.assertEqual(
            Comment.objects.count(), 
            0, 
            msg="Только авторизированный пользователь может "
                "комментировать посты."
        )
