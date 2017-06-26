import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import Comment, Post, Like
from .forms import CommentForm, PostForm


def post_list(request):
    post_list = Post.objects.prefetch_related('tag_set', 'like_user_set__profile', 'comment_set__author__profile').select_related('author__profile').all()
    comment_form = CommentForm()

    paginator = Paginator(post_list, 3)
    page_num = request.POST.get('page')

    try:
        posts = paginator.page(page_num)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)

    if request.is_ajax(): # Ajax request 여부 확인
        return render(request,'post/post_list_ajax.html',{
            'posts': posts,
            'comment_form': comment_form,
        })

    if request.method == 'POST' :
        tag = request.POST.get('tag')
        tag_clean = ''.join(e for e in tag if e.isalnum()) #특수문자 삭제
        return redirect('post:post_search', tag_clean)

    return render(request, 'post/post_list.html', {
        'posts': posts,
        'comment_form': comment_form,
    })

@login_required
def post_new(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            post.tag_save()
            messages.info(request, '새 글이 등록되었습니다.')
            return redirect('post:post_list')

    else:
        form = PostForm()
    return render(request, 'post/post_form.html', {
        'form': form,
    })

@login_required
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user:
        messages.warning(request, '잘못된 접근입니다.')
        return redirect('post:post_list')

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save()
            post.tag_set.all().delete()
            post.tag_save()
            messages.success(request, '수정완료')
            return redirect('post:post_list')

    else:
        form = PostForm(instance=post)
    return render(request, 'post/post_form.html', {
        'form': form,
    })

@login_required
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user or request.method == 'GET':
        messages.warning(request, '잘못된 접근입니다.')
        return redirect('post:post_list')

    if request.method == 'POST':
        post.delete()
        messages.success(request, '삭제완료')
        return redirect('post:post_list')

def post_search(request, tag):
    post_list = Post.objects.filter(tag_set__name__iexact=tag).select_related('author__profile').prefetch_related('tag_set', 'like_user_set__profile')

    paginator = Paginator(post_list, 3)
    page_num = request.POST.get('page')

    try:
        posts = paginator.page(page_num)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)

    if request.is_ajax(): # Ajax request 여부 확인
        print('ajax 동작!!')
        return render(request,'post/post_list_ajax.html',{
            'posts': posts,
        })

    return render(request, 'post/post_list_search.html', {
        'tag': tag,
        'posts': posts,
        'paginator': paginator,
    })


@login_required
@require_POST # 해당 뷰는 POST method 만 받는다.
def post_like(request):
    pk = request.POST.get('pk', None)
    post = get_object_or_404(Post, pk=pk)
    post_like, post_like_created = post.like_set.get_or_create(user=request.user)

    if not post_like_created:
        post_like.delete()
        message = "좋아요 취소"
    else:
        message = "좋아요"

    context = {'like_count': post.like_count,
               'message': message,
               'nickname': request.user.profile.nickname }

    return HttpResponse(json.dumps(context), content_type="application/json")


@login_required
def comment_new(request, post_pk):
    post = get_object_or_404(Post, pk=post_pk)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()
            return redirect("post:post_list")
    return redirect("post:post_list")
