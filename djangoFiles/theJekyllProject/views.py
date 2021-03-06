# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.shortcuts import redirect
from django.views import View
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.views.generic.edit import UpdateView
from django.views.generic.edit import DeleteView
from django.views.generic.list import ListView
from django.contrib.auth.models import User
from django.contrib.auth.models import AnonymousUser

from markdown2 import Markdown

from theJekyllProject.forms import AddPageForm
from theJekyllProject.forms import AddPostForm
from theJekyllProject.forms import ContactForm
from theJekyllProject.forms import RepoForm
from theJekyllProject.forms import SiteExcludeForm
from theJekyllProject.forms import SitePluginForm
from theJekyllProject.forms import SiteProfileForm
from theJekyllProject.forms import SiteThemeForm
from theJekyllProject.forms import SiteSocialProfileForm

from theJekyllProject.functions import add_theme_name
from theJekyllProject.functions import assign_boolean_to_comments
from theJekyllProject.functions import change_site_baseurl
from theJekyllProject.functions import convert_content
from theJekyllProject.functions import copy_jekyll_files
from theJekyllProject.functions import create_config_file
from theJekyllProject.functions import create_file_name
from theJekyllProject.functions import create_repo
from theJekyllProject.functions import fill_other_tables_from_config_file
from theJekyllProject.functions import fill_repo_table_for_old_repo
from theJekyllProject.functions import find_required_files
from theJekyllProject.functions import get_repo_list
from theJekyllProject.functions import git_clone_repo
from theJekyllProject.functions import header_content
from theJekyllProject.functions import move_file
from theJekyllProject.functions import page_header_content
from theJekyllProject.functions import push_online
from theJekyllProject.functions import run_git_script
from theJekyllProject.functions import read_all_pages
from theJekyllProject.functions import save_post_database
from theJekyllProject.functions import save_page_database
from theJekyllProject.functions import save_post_category_database
from theJekyllProject.functions import save_site_data
from theJekyllProject.functions import save_site_theme_data
from theJekyllProject.functions import save_repo_data
from theJekyllProject.functions import select_main_site
from theJekyllProject.functions import write_file
from theJekyllProject.functions import write_page_file

from theJekyllProject.models import Page
from theJekyllProject.models import Post
from theJekyllProject.models import PostCategory
from theJekyllProject.models import Repo
from theJekyllProject.models import SiteData
from theJekyllProject.models import SiteSocialProfile
from theJekyllProject.models import SiteTheme
from theJekyllProject.models import Contact


class IndexView(FormView):
    template_name = 'theJekyllProject/index.html'
    form_class = ContactForm

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if(form.is_valid()):
            first_name = request.POST['first_name']
            last_name = request.POST['last_name']
            email = request.POST['email']
            message = request.POST['message']
            jeklog_email = 'jeklogjek@gmail.com'
            contact = Contact(
                first_name = first_name,
                last_name = last_name,
                email = email,
                message = message
            )
            contact.save()

            subject = "New mail from " + first_name + " " + last_name + " " + email
            send_mail(subject, message, email, [jeklog_email], fail_silently=False)

        return render(request, 'theJekyllProject/contact_status.html')


class RepoListView(LoginRequiredMixin, TemplateView):

    def get(self, request, *args, **kwargs):
        user = request.user
        user = User.objects.get(username=user.username)
        social = user.social_auth.get(provider='github')
        user_token = social.extra_data['access_token']

        repo_list = get_repo_list(user_token)

        return render(request, 'theJekyllProject/repo_list.html', context={
            'repo_list': repo_list,
        })


class CreateRepoView(LoginRequiredMixin, FormView):
    template_name = 'theJekyllProject/create_repo.html'
    form_class = RepoForm
    form_valid_message = 'Repository created successfully'
    form_invalid_message = 'Repository not created'

    def get(self, request, *args, **kwargs):
        user = request.user
        user = User.objects.get(username=user.username)
        social = user.social_auth.get(provider='github')
        user_token = social.extra_data['access_token']

        repo_list = get_repo_list(user_token)

        return render(request, 'theJekyllProject/create_repo.html', context={
            'repo_list': repo_list,
            'form': self.form_class,
        })

    def post(self, request, *args, **kwargs):
        user = request.user
        form = self.form_class(request.POST)
        if form.is_valid():
            repo = request.POST['repo']
            try:
                create_repo(user, repo)
                save_repo_data(user, repo)
                copy_jekyll_files(user, repo)
                read_all_pages(user, repo)
                add_theme_name(user, repo)
                change_site_baseurl(user, repo)
                run_git_script(user, repo)
            except:
                # FIXME Give a proper error message
                pass

        return HttpResponseRedirect(reverse('home'))


class AddPostView(LoginRequiredMixin, FormView):
    """AddPostView to add post

    Example:
        Click on the Add post button when the user is logged in.
        We can add posts only if the user is logged in.

    TODO:
        * Make this view for logged in people only: Not done
        * Load the form: Not Done
        * convert the stuff as required: Not Done
        * Make new files: Not Done
        * Put the files at right places: Not Done
    """
    template_name = 'theJekyllProject/addpost.html'
    form_class = AddPostForm

    def post(self, request, *args, **kwargs):
        user = request.user
        form = self.form_class(request.POST)
        repo = Repo.objects.get(user=user, main=True)
        if form.is_valid():
            author = request.POST['author']
            comments = request.POST['comments']
            date = request.POST['date']
            time = request.POST['time']
            layout = request.POST['layout']
            title = request.POST['title']
            content = request.POST['content']
            category = request.POST['category']

            # This is a turnaround... I don't know why it happened.
            # Checkbox produces 'on' as the result when selected.
            comments = assign_boolean_to_comments(comments)

            # save stuff to the post database
            post = save_post_database(repo, author, comments, date, time, layout, title, content)

            # save stuff to the post_category database
            save_post_category_database(post, category)

            # Create file name
            file_name = create_file_name(date, title)

            # Create header content for the markdown file
            head_content = header_content(author, comments, date, time, layout, title)

            # Convert the body content to markdown
            body_content = convert_content(content)

            # Write the content into files
            write_file(file_name, head_content, body_content)

            # Move file to correct location
            move_file(file_name, user, repo)

            # Push the code online
            push_online(user, repo)
        return HttpResponseRedirect(reverse('home'))


class PostListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'theJekyllProject/post_list.html'
    context_object_name = "post_list"
    paginate_by = 5

    def get_queryset(self):
        user = self.request.user
        repo = Repo.objects.get(user=user, main=True)
        post_list = Post.objects.order_by('-date').filter(repo=repo)
        return post_list


class PostUpdateView(LoginRequiredMixin, FormView):
    form_class = AddPostForm
    template_name = 'theJekyllProject/addpost.html'

    def get_form_kwargs(self):
        pk = self.kwargs['pk']
        try:
            post = Post.objects.get(pk=pk)
            author = post.author
            comments = post.comments
            date = post.date
            time = post.time
            layout = post.layout
            title = post.title
            content = post.content
            # FIXME get is used as we can only category for now
            post_category = PostCategory.objects.get(post=post)
            category = post_category.category
        except:
            pass

        form_kwargs = super(PostUpdateView, self).get_form_kwargs()
        form_kwargs.update({
            'initial': {
                'author': author,
                'comments': comments,
                'date': date,
                'time': time,
                'layout': layout,
                'title': title,
                'content': content,
                'category': category
            }
        })
        return form_kwargs

    def post(self, request, *args, **kwargs):
        user = request.user
        pk = self.kwargs['pk']
        form = self.form_class(request.POST)
        repo = Repo.objects.get(user=user, main=True)
        if form.is_valid():
            author = request.POST['author']
            comments = request.POST['comments']
            date = request.POST['date']
            time = request.POST['time']
            layout = request.POST['layout']
            title = request.POST['title']
            content = request.POST['content']
            category = request.POST['category']

            # This is a turnaround... I don't know why it happened.
            # Checkbox produces 'on' as the result when selected.
            comments = assign_boolean_to_comments(comments)

            # save stuff to the post database
            post = save_post_database(repo, author, comments, date, time, layout, title, content, pk)

            # save stuff to the post_category database
            save_post_category_database(post, category, pk)

            file_name = create_file_name(date, title)

            # Create header content for the markdown file
            head_content = header_content(author, comments, date, time, layout, title)

            # Convert the body content to markdown
            body_content = convert_content(content)

            # Write the content into files
            write_file(file_name, head_content, body_content)

            # Move file to correct location
            move_file(file_name, user, repo)

            # send the changes online
            push_online(user, repo)
        return HttpResponseRedirect(reverse('home'))


class AddPageView(LoginRequiredMixin, FormView):
    """AddPageView to add page

    Example:
        Click on the Add page button when the user is logged in.
        We can add pages only if the user is logged in.

    Tasks:
        * Make this view for logged in people only.
        * Load the form:
        * convert the taken html to markdown
        * create and move the files to proper locations
        * Push the code to the repository.
    """
    template_name = 'theJekyllProject/addpage.html'
    form_class = AddPageForm

    def post(self, request, *args, **kwargs):
        user = request.user
        form = self.form_class(request.POST)
        repo = Repo.objects.get(user=user, main=True)
        if form.is_valid():
            title = request.POST['title']
            permalink = request.POST['permalink']
            content = request.POST['content']

            # save stuff to the page database
            page = save_page_database(repo, title, permalink, content)

            # Create header content for the markdown file
            head_content = page_header_content(title, permalink)

            # Convert the body content to markdown
            body_content = convert_content(content)

            # Write the content into files
            write_page_file(title.lower(), user, repo, head_content, body_content)

            # Push the code online
            push_online(user, repo)
        return HttpResponseRedirect(reverse('page-list'))


class PageUpdateView(LoginRequiredMixin, FormView):
    """PageUpdateView to add page

    Example:
        Click on any of the page when the user is logged in.
        We can update the content of pages only if the user is logged in.

    Tasks:
        * Make this view for logged in people only.
        * Load the form with content from the database
        * convert the taken html to markdown
        * create and move the files to proper locations
        * Push the code to the repository
    """
    form_class = AddPageForm
    template_name = 'theJekyllProject/addpage.html'

    def get_form_kwargs(self):
        pk = self.kwargs['pk']
        try:
            page = Page.objects.get(pk=pk)
            title = page.title
            permalink = page.permalink
            content = page.content
        except:
            pass

        form_kwargs = super(PageUpdateView, self).get_form_kwargs()
        form_kwargs.update({
            'initial': {
                'title': title,
                'permalink': permalink,
                'content': content,
            }
        })
        return form_kwargs

    def post(self, request, *args, **kwargs):
        user = request.user
        pk = self.kwargs['pk']
        form = self.form_class(request.POST)
        repo = Repo.objects.get(user=user, main=True)
        if form.is_valid():
            title = request.POST['title']
            permalink = request.POST['permalink']
            content = request.POST['content']

            page = save_page_database(repo, title, permalink, content, pk)

            # Create header content for the markdown file
            head_content = page_header_content(title, permalink)

            # Convert the body content to markdown
            body_content = convert_content(content)

            # Write the content into files
            write_page_file(title.lower(), user, repo, head_content, body_content)

            # Push the code online
            push_online(user, repo)
        return HttpResponseRedirect(reverse('page-update', args=[pk]))


class PageListView(LoginRequiredMixin, ListView):
    model = Page
    template_name = 'theJekyllProject/page_list.html'
    context_object_name = "page_list"

    def get_queryset(self):
        user = self.request.user
        repo = Repo.objects.get(user=user, main=True)
        page_list = Page.objects.filter(repo=repo)
        return page_list


class SiteProfileView(LoginRequiredMixin, FormView):
    template_name = 'theJekyllProject/siteprofile.html'
    form_class = SiteProfileForm

    def get_form_kwargs(self):
        user = self.request.user
        user = User.objects.get(username=user.username)
        repo = Repo.objects.get(user=user, main=True)
        try:
            site_data = SiteData.objects.get(repo=repo)
            title = site_data.title
            description = site_data.description
            avatar = site_data.avatar

        except:
            title = 'Your new site'
            description = 'Single line description of the site'
            # FIXME add an image initial
            avatar = 'An image'

        form_kwargs = super(SiteProfileView, self).get_form_kwargs()
        form_kwargs.update({
            'initial': {
                'title': title,
                'description': description,
                'avatar': avatar,
            }
        })
        return form_kwargs

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = request.user
            title = request.POST['title']
            description = request.POST['description']
            avatar = request.POST['avatar']
            # save stuff to the database
            repo = Repo.objects.get(user=user, main=True)
            save_site_data(repo, title, description, avatar)
            create_config_file(user, repo)
            push_online(user, repo)
            return HttpResponseRedirect(reverse('home'))


class ChooseSiteView(LoginRequiredMixin, ListView):
    model = Repo
    template_name = 'theJekyllProject/choose_site.html'
    context_object_name = 'site_list'

    def get_queryset(self):
        site_list = Repo.objects.filter(user=self.request.user)
        return site_list


class SelectMainSiteView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        pk = self.kwargs['pk']
        user = self.request.user
        select_main_site(user, pk)
        return HttpResponseRedirect(reverse('home'))


class DecideHomeView(View):
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            return redirect(reverse('index'))
        user = self.request.user
        repo = Repo.objects.filter(user=user)
        if(len(repo) is 0):
            return redirect(reverse('create-repo'))
        else:
            return redirect(reverse('home'))


class SiteSocialProfileView(LoginRequiredMixin, FormView):
    template_name = 'theJekyllProject/socialprofile.html'
    form_class = SiteSocialProfileForm

    def get_form_kwargs(self):
        user = self.request.user
        user = User.objects.get(username=user.username)
        try:
            SiteSocialProfile.objects.get(user=user)
            dribbble = SiteSocialProfile.objects.get(user=user).dribbble
            email = SiteSocialProfile.objects.get(user=user).email
            facebook = SiteSocialProfile.objects.get(user=user).facebook
            flickr = SiteSocialProfile.objects.get(user=user).flickr
            github = SiteSocialProfile.objects.get(user=user).github
            instagram = SiteSocialProfile.objects.get(user=user).instagram
            linkedin = SiteSocialProfile.objects.get(user=user).linkedin
            pinterest = SiteSocialProfile.objects.get(user=user).pinterest
            rss = SiteSocialProfile.objects.get(user=user).rss
            twitter = SiteSocialProfile.objects.get(user=user).twitter
            stackoverflow = SiteSocialProfile.objects.get(user=user).stackoverflow
            youtube = SiteSocialProfile.objects.get(user=user).youtube
            googleplus = SiteSocialProfile.objects.get(user=user).googleplus
            disqus = SiteSocialProfile.objects.get(user=user).disqus
            google_analytics = SiteSocialProfile.objects.get(user=user).google_analytics
        except:
            dribbble = ''
            email = ''
            facebook = ''
            flickr = ''
            github = ''
            instagram = ''
            linkedin = ''
            pinterest = ''
            rss = ''
            twitter = ''
            stackoverflow = ''
            youtube = ''
            googleplus = ''
            disqus = ''
            google_analytics = ''

        form_kwargs = super(SiteSocialProfileView, self).get_form_kwargs()
        form_kwargs.update({
            'initial': {
                'dribbble': dribbble,
                'email': email,
                'facebook': facebook,
                'flickr': flickr,
                'github': github,
                'instagram': instagram,
                'linkedin': linkedin,
                'pinterest': pinterest,
                'rss': rss,
                'twitter': twitter,
                'stackoverflow': stackoverflow,
                'youtube': youtube,
                'googleplus': googleplus,
                'disqus': disqus,
                'google_analytics': google_analytics,
            }
        })
        return form_kwargs

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = request.user
            repo = Repo.objects.get(user=user, main=True)
            dribbble = request.POST['dribbble']
            email = request.POST['email']
            facebook = request.POST['facebook']
            flickr = request.POST['flickr']
            github = request.POST['github']
            instagram = request.POST['instagram']
            linkedin = request.POST['linkedin']
            pinterest = request.POST['pinterest']
            rss = request.POST['rss']
            twitter = request.POST['twitter']
            stackoverflow = request.POST['stackoverflow']
            youtube = request.POST['youtube']
            googleplus = request.POST['googleplus']
            disqus = request.POST['disqus']
            google_analytics = request.POST['google_analytics']

            site_social_profile = SiteSocialProfile(
                user = user,
                dribbble = dribbble,
                email = email,
                facebook = facebook,
                flickr = flickr,
                github = github,
                instagram = instagram,
                linkedin = linkedin,
                pinterest = pinterest,
                rss = rss,
                twitter = twitter,
                stackoverflow = stackoverflow,
                youtube = youtube,
                googleplus = googleplus,
                disqus = disqus,
                google_analytics = google_analytics
            )
            site_social_profile.save()
            create_config_file(user, repo)
            push_online(user, repo)
            return HttpResponseRedirect(reverse('socialprofile'))


class SitePluginView(LoginRequiredMixin, FormView):
    template_name = 'theJekyllProject/siteplugin.html'
    form_class = SitePluginForm

class SiteExcludeView(LoginRequiredMixin, FormView):
    template_name = 'theJekyllProject/siteexclude.html'
    form_class = SiteExcludeForm


class SiteThemeView(LoginRequiredMixin, FormView):
    template_name = 'theJekyllProject/sitetheme.html'
    form_class = SiteThemeForm

    def get_form_kwargs(self):
        user = self.request.user
        user = User.objects.get(username=user.username)
        try:
            SiteTheme.objects.get(user=user)
            theme = SiteTheme.objects.get(user=user).theme
        except:
            theme = ''

        form_kwargs = super(SiteThemeView, self).get_form_kwargs()
        form_kwargs.update({
            'initial': {
                'theme': theme,
            }
        })
        return form_kwargs

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = request.user
            repo = Repo.objects.get(user=user, main=True)
            theme = request.POST['theme']
            save_site_theme_data(repo, theme)
            create_config_file(user, repo)
            push_online(user, repo)
            return HttpResponseRedirect(reverse('sitetheme'))


class BlogView(LoginRequiredMixin, View):
    """BlogView to see the created blog

    Example:
        Triggers when:
        User clicks on the visit the blog button when logged in
        This will take you to the Existing blog

    Tasks:
        * View for logged in users only.
        * Place the link in the user options
        * Redirect to the correct link.
        * If the repo_name is equal to username.github.io
          then redirect to username.github.io only
    """  
    def get(self, request, *args, **kwargs):
        user = request.user
        repo = Repo.objects.get(user=user, main=True)
        if(repo.repo != (user.username + '.github.io')):
            return redirect('http://' + user.username + '.github.io/' + repo.repo)
        else:
            return redirect('http://' + user.username + '.github.io/')


class UseOldRepo(LoginRequiredMixin, View):
    """UseOldRepo to register a repo on already created Repository.

    Example:
        Triggers when:
        User clicks on one of the already created repository
        clamining that the repo contains the required files.

    Tasks:
        * View for logged in users only.
        * Select any repo from the repo list
        * Make some earlier checks
        * Clone the repo
        * Check if the required contents are present or not
        * If yes do the required operations:
            * Fill repo table
            * Select Main Site
        * Else give an error message
        * Integrate celery to show the amount of task completed
    """
    def get(self, request, *args, **kwargs):
        user = request.user
        repo_name = kwargs['repo_name']
        # Check the git tree first
        git_clone_repo(user.username, repo_name)
        if(find_required_files(user.username, repo_name)):
            repo = fill_repo_table_for_old_repo(user.username, repo_name)
            select_main_site(user, repo.pk)
            fill_other_tables_from_config_file(user.username, repo_name)
            find_posts(user.username, repo_name)
            find_pages(user.username, repo_name)
            

        else:
            pass # or give errors