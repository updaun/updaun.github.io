---
layout: page
title: AWS Solution Architect Associate
permalink: /aws-saa/
---

<div class="aws-saa-page">
  <p>AWS Solution Architect Associate 자격증을 준비하며 공부한 내용을 정리한 페이지입니다.</p>
  
  <h2>포스트 목록</h2>
  <ul class="post-list">
    {% for post in site.categories.aws-saa %}
      <li>
        <span class="post-meta">{{ post.date | date: "%Y년 %m월 %d일" }}</span>
        <h3>
          <a class="post-link" href="{{ post.url | relative_url }}">{{ post.title }}</a>
        </h3>
        {% if post.excerpt %}
          <p>{{ post.excerpt | strip_html | truncatewords: 30 }}</p>
        {% endif %}
      </li>
    {% endfor %}
  </ul>
</div>
