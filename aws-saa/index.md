---
layout: page
title: AWS Solution Architect Associate
permalink: /aws-saa/
---

<div class="aws-saa-page">
  <div class="page-intro">
    <p>🚀 AWS Solution Architect Associate 자격증을 준비하며 공부한 내용을 정리한 페이지입니다.</p>
    <p>체계적인 학습과 실전 문제 풀이를 통해 AWS 클라우드 아키텍처 전문성을 키워보세요!</p>
  </div>
  
  <h2>📚 학습 포스트</h2>
  <ul class="post-list">
    {% assign aws_posts = site.posts | where_exp: "post", "post.categories contains 'AWS'" %}
    {% for post in aws_posts %}
      <li>
        <div class="post-meta">{{ post.date | date: "%Y년 %m월 %d일" }}</div>
        <h3>
          <a class="post-link" href="{{ post.url | relative_url }}">{{ post.title }}</a>
        </h3>
        {% if post.categories %}
        <div class="post-categories">
          {% for category in post.categories %}
          <span class="post-category">{{ category }}</span>
          {% endfor %}
        </div>
        {% endif %}
        {% if post.excerpt %}
          <p class="post-excerpt">{{ post.excerpt | strip_html | truncatewords: 25 }}</p>
        {% endif %}
      </li>
    {% endfor %}
  </ul>
  
  {% if aws_posts.size == 0 %}
  <div class="no-posts">
    <p>아직 AWS 관련 포스트가 없습니다. 곧 업데이트됩니다! 😊</p>
  </div>
  {% endif %}
</div>
