# -*- coding: utf-8 -*-
from django import template
from django import forms
from django.http import HttpResponse, Http404, StreamingHttpResponse, FileResponse
from django.shortcuts import render, render_to_response
from django.template import Context, loader
from django.views.generic import View, TemplateView, ListView, DetailView
from django.db.models import Q
from django.core.cache import caches
from django.core.exceptions import PermissionDenied
from django.core.cache.backends.base import InvalidCacheBackendError
from django.contrib import auth
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from blog.models import Article, Category, Carousel, Column, Nav, News
from vmaig_comments.models import Comment
from vmaig_auth.models import VmaigUser
from vmaig_system.models import Link
from vmaig_auth.forms import VmaigUserCreationForm, VmaigPasswordRestForm
from django.conf import settings
import datetime
import time
import json
import logging
import markdown
from django.http import JsonResponse
import time

# 缓存
try:
    cache = caches['redis']
except InvalidCacheBackendError as e:
    cache = caches['default']

# logger
logger = logging.getLogger(__name__)


class BaseMixin(object):
    def get_context_data(self, *args, **kwargs):
        context = super(BaseMixin, self).get_context_data(**kwargs)
        try:
            # 网站标题等内容
            if 'website_title' not in context:
                context['website_title'] = settings.WEBSITE_TITLE

            context['website_welcome'] = settings.WEBSITE_WELCOME
            # 热门文章
            context['hot_article_list'] = \
                Article.objects.order_by("-view_times")[0:10]
            # 导航条
            context['nav_list'] = Nav.objects.filter(status=0)
            # 最新评论
            context['latest_comment_list'] = \
                Comment.objects.order_by("-create_time")[0:10]
            # 友情链接
            context['links'] = Link.objects.order_by('create_time').all()
            colors = ['primary', 'success', 'info', 'warning', 'danger']
            for index, link in enumerate(context['links']):
                link.color = colors[index % len(colors)]
            # 用户未读消息数
            user = self.request.user
            if user.is_authenticated:
                context['notification_count'] = \
                    user.to_user_notification_set.filter(is_read=0).count()
        except Exception as e:
            logger.error(u'[BaseMixin]加载基本信息出错')

        return context


class IndexView(BaseMixin, ListView):
    template_name = 'blog/index.html'
    context_object_name = 'article_list'
    paginate_by = settings.PAGE_NUM  # 分页--每页的数目

    def get_context_data(self, **kwargs):
        # 轮播
        kwargs['carousel_page_list'] = Carousel.objects.all()
        return super(IndexView, self).get_context_data(**kwargs)

    def get_queryset(self):
        article_list = Article.objects.filter(status=0)
        return article_list


class ArticleView(BaseMixin, DetailView):
    queryset = Article.objects.filter(Q(status=0) | Q(status=1))
    template_name = 'blog/article.html'
    context_object_name = 'article'
    slug_field = 'en_title'

    def get(self, request, *args, **kwargs):
        # 统计文章的访问访问次数
        if 'HTTP_X_FORWARDED_FOR' in request.META:
            ip = request.META['HTTP_X_FORWARDED_FOR']
        else:
            ip = request.META['REMOTE_ADDR']
        self.cur_user_ip = ip

        en_title = self.kwargs.get('slug')
        # 获取15*60s时间内访问过这篇文章的所有ip
        visited_ips = cache.get(en_title, [])

        # 如果ip不存在就把文章的浏览次数+1
        if ip not in visited_ips:
            try:
                article = self.queryset.get(en_title=en_title)
            except Article.DoesNotExist:
                logger.error(u'[ArticleView]访问不存在的文章:[%s]' % en_title)
                raise Http404
            else:
                # markdown 格式
                article.content = markdown.markdown(article.bef_content, extensions=[
                    'markdown.extensions.extra',
                    'markdown.extensions.codehilite',
                    'markdown.extensions.toc',
                ])
                article.view_times += 1
                article.save()
                visited_ips.append(ip)

            # 更新缓存
            cache.set(en_title, visited_ips, 15*60)

        return super(ArticleView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        # 评论
        en_title = self.kwargs.get('slug', '')
        kwargs['comment_list'] = \
            self.queryset.get(en_title=en_title).comment_set.all()

        article = self.queryset.get(en_title=en_title)
        kwargs['website_title'] = article.title

        return super(ArticleView, self).get_context_data(**kwargs)


class AllView(BaseMixin, ListView):
    template_name = 'blog/all.html'
    context_object_name = 'article_list'

    def get_context_data(self, **kwargs):
        kwargs['category_list'] = Category.objects.all()
        kwargs['PAGE_NUM'] = settings.PAGE_NUM
        return super(AllView, self).get_context_data(**kwargs)

    def get_queryset(self):
        article_list = Article.objects.filter(
            status=0
        ).order_by("-pub_time")[0:settings.PAGE_NUM]
        return article_list

    def post(self, request, *args, **kwargs):
        val = self.request.POST.get("val", "")
        sort = self.request.POST.get("sort", "time")
        start = self.request.POST.get("start", 0)
        end = self.request.POST.get("end", settings.PAGE_NUM)

        start = int(start)
        end = int(end)

        if sort == "time":
            sort = "-pub_time"
        elif sort == "recommend":
            sort = "-view_times"
        else:
            sort = "-pub_time"

        if val == "all":
            article_list = \
                Article.objects.filter(status=0).order_by(sort)[start:end+1]
        else:
            try:
                article_list = Category.objects.get(
                                   name=val
                               ).article_set.filter(
                                   status=0
                               ).order_by(sort)[start:end+1]
            except Category.DoesNotExist:
                logger.error(u'[AllView]此分类不存在:[%s]' % val)
                raise PermissionDenied

        isend = len(article_list) != (end-start+1)

        article_list = article_list[0:end-start]

        html = ""
        for article in article_list:
            html += template.loader.get_template(
                'blog/include/all_post.html'
            ).render({'post': article})

        mydict = {"html": html, "isend": isend}
        return HttpResponse(
            json.dumps(mydict),
            content_type="application/json"
        )


class SearchView(BaseMixin, ListView):
    template_name = 'blog/search.html'
    context_object_name = 'article_list'
    paginate_by = settings.PAGE_NUM

    def get_context_data(self, **kwargs):
        kwargs['s'] = self.request.GET.get('s', '')
        return super(SearchView, self).get_context_data(**kwargs)

    def get_queryset(self):
        # 获取搜索的关键字
        s = self.request.GET.get('s', '')
        # 在文章的标题,summary和tags中搜索关键字
        article_list = Article.objects.only(
            'title', 'summary', 'tags'
        ).filter(
            Q(title__icontains=s) |
            Q(summary__icontains=s) |
            Q(tags__icontains=s),
            status=0
        )
        return article_list


class TagView(BaseMixin, ListView):
    template_name = 'blog/tag.html'
    context_object_name = 'article_list'
    paginate_by = settings.PAGE_NUM

    def get_queryset(self):
        tag = self.kwargs.get('tag', '')
        article_list = \
            Article.objects.only('tags').filter(tags__icontains=tag, status=0)

        return article_list


class CategoryView(BaseMixin, ListView):
    template_name = 'blog/category.html'
    context_object_name = 'article_list'
    paginate_by = settings.PAGE_NUM

    def get_queryset(self):
        category = self.kwargs.get('category', '')
        try:
            article_list = \
                Category.objects.get(name=category).article_set.all()
        except Category.DoesNotExist:
            logger.error(u'[CategoryView]此分类不存在:[%s]' % category)
            raise Http404

        return article_list


class UserView(BaseMixin, TemplateView):
    template_name = 'blog/user.html'

    def get(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            logger.error(u'[UserView]用户未登陆')
            return render(request, 'blog/login.html')

        slug = self.kwargs.get('slug')

        if slug == 'changetx':
            self.template_name = 'blog/user_changetx.html'
        elif slug == 'changepassword':
            self.template_name = 'blog/user_changepassword.html'
        elif slug == 'changeinfo':
            self.template_name = 'blog/user_changeinfo.html'
        elif slug == 'message':
            self.template_name = 'blog/user_message.html'
        elif slug == 'notification':
            self.template_name = 'blog/user_notification.html'

        return super(UserView, self).get(request, *args, **kwargs)

        logger.error(u'[UserView]不存在此接口')
        raise Http404

    def get_context_data(self, **kwargs):
        context = super(UserView, self).get_context_data(**kwargs)

        slug = self.kwargs.get('slug')

        if slug == 'notification':
            context['notifications'] = \
                self.request.user.to_user_notification_set.order_by(
                    '-create_time'
                ).all()

        return context


class ColumnView(BaseMixin, ListView):
    queryset = Column.objects.all()
    template_name = 'blog/column.html'
    context_object_name = 'article_list'
    paginate_by = settings.PAGE_NUM

    def get_context_data(self, **kwargs):
        column = self.kwargs.get('column', '')
        try:
            kwargs['column'] = Column.objects.get(name=column)
        except Column.DoesNotExist:
            logger.error(u'[ColumnView]访问专栏不存在: [%s]' % column)
            raise Http404

        return super(ColumnView, self).get_context_data(**kwargs)

    def get_queryset(self):
        column = self.kwargs.get('column', '')
        try:
            article_list = Column.objects.get(name=column).article.all()
        except Column.DoesNotExist:
            logger.error(u'[ColumnView]访问专栏不存在: [%s]' % column)
            raise Http404

        return article_list


class NewsView(BaseMixin, TemplateView):
    template_name = 'blog/news.html'

    def get_context_data(self, **kwargs):
        timeblocks = []

        # 获取开始和终止的日期
        start_day = self.request.GET.get("start", "0")
        end_day = self.request.GET.get("end", "6")
        start_day = int(start_day)
        end_day = int(end_day)

        start_date = datetime.datetime.now()

        last_new = News.objects.order_by("-pub_time").first()
        if last_new is not None:
            start_date = last_new.pub_time

        # 获取url中时间断的资讯
        for x in range(start_day, end_day+1):
            date = start_date - datetime.timedelta(x)
            news_list = News.objects.filter(
                pub_time__year=date.year,
                pub_time__month=date.month,
                pub_time__day=date.day
            )

            if news_list:
                timeblocks.append(news_list)

        kwargs['timeblocks'] = timeblocks
        kwargs['active'] = start_day/7  # li中那个显示active

        return super(NewsView, self).get_context_data(**kwargs)


from django.views import View
from blog.utils import *
import os

class UserList(View):
    def get(self, request):
        user_data = VmaigUser.objects.filter(is_superuser=0).all()
        res = []
        for data in user_data:
            res.append({
                'user_name': data.username,
                'img': data.img
            })
        return JsonResponse({"status": 100, "data": res})


class TimeTest(View):
    def get(self, request):
        num = int(request.GET.get('num', 3))
        time.sleep(num)
        return JsonResponse({"status": 100, 'time': num})


class WxCallBack(View):
    def post(self, request):
        print("接受的xml数据:%s" % request.body)
        data_dict = trans_xml_to_dict(request.body)
        print("解析后的json数据%s" % data_dict)

        print("返回数据。。。。。。。。。。。。")
        return HttpResponse(trans_dict_to_xml({'return_code': 'SUCCESS', 'return_msg': 'OK'}))


class AliCallBack(View):
    def post(self, request):
        data_dict = request.body.decode('utf-8')
        print("回调支付结果接收到的参数：%s" % data_dict)
        return HttpResponse('success')


class AliReturn(View):
    def get(self, request):
        params = request.GET.dict()
        print("重定向时获取的参数：%s" % params)
        return HttpResponse("成功咯。。。。。。。。。。。")


class DownloadFile(View):
    def get(self, request):
        file_path = request.GET.get('file_path', '')
        if not file_path:
            return JsonResponse({"code": 500, "msg": "未获取到文件路径"})
        if not os.path.exists(file_path):
            return JsonResponse({"code": 500, "msg": "文件不存在"})

        if not file_path.startswith('/qqc_data'):
            return JsonResponse({"code": 500, "msg": "文件格式异常"})

        file_name = os.path.split(file_path)[1]
        print(file_name, "###########################")

        def file_iterator(file_path, chunk_size=8096):
            """
            文件生成器,防止文件过大，导致内存溢出
            :param file_path: 文件绝对路径
            :param chunk_size: 块大小
            :return: 生成器
            """
            with open(file_path, mode='rb') as f:
                while True:
                    c = f.read(chunk_size)
                    if c:
                        yield c
                    else:
                        break

        response = StreamingHttpResponse(file_iterator(file_path))
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment;filename="{}"'.format(file_name)
        return response


class UploadFile(View):
    def post(self, request):
        file = request.FILES.get('file', '')
        if not file:
            return JsonResponse({"code": 500, "msg": "not file dta"})
        file_name = file.name
        upload_dir_path = '/qqc_data/upload_file_data/'
        if not os.path.exists(upload_dir_path):
            return JsonResponse({"code": 500, "msg": "not file dir"})
        with open(os.path.join(upload_dir_path, file_name), 'wb') as fp:
            for i in file.chunks():
                fp.write(i)
        return JsonResponse({"code": 200, "msg": "上传成功"})
