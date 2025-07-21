---
layout: default
title: "카테고리별 포스트"
description: "Up & Daun 블로그의 모든 카테고리별 포스트를 확인하세요."
permalink: /categories/
sitemap: true
---

<div class="categories-page">
    <div class="hero-section">
        <h1 class="hero-title">📚 카테고리별 포스트</h1>
        <p class="hero-subtitle">관심있는 주제의 포스트들을 찾아보세요</p>
    </div>

    <div class="categories-container">
        {% assign categories = site.categories | sort %}
        {% for category in categories %}
        <div class="category-section" id="{{ category[0] | slugify }}">
            <h2 class="category-title">
                <a href="#{{ category[0] | slugify }}">{{ category[0] }}</a>
                <span class="post-count">({{ category[1].size }})</span>
            </h2>
            
            <div class="category-posts">
                {% assign posts = category[1] | sort: 'date' | reverse %}
                {% for post in posts %}
                <article class="category-post-card">
                    <div class="post-date">{{ post.date | date: "%Y.%m.%d" }}</div>
                    <h3 class="post-title">
                        <a href="{{ post.url }}">{{ post.title }}</a>
                    </h3>
                    {% if post.excerpt %}
                    <p class="post-excerpt">{{ post.excerpt | strip_html | truncatewords: 20 }}</p>
                    {% endif %}
                    {% if post.tags %}
                    <div class="post-tags-inline">
                        {% for tag in post.tags limit: 3 %}
                        <span class="tag-inline">#{{ tag }}</span>
                        {% endfor %}
                    </div>
                    {% endif %}
                </article>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
    </div>
</div>

<!-- 구조화된 데이터 -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "CollectionPage",
  "name": "카테고리별 포스트",
  "description": "{{ page.description }}",
  "url": "{{ page.url | absolute_url }}",
  "mainEntity": {
    "@type": "ItemList",
    "numberOfItems": {{ site.categories.size }},
    "itemListElement": [
      {% for category in site.categories %}
      {
        "@type": "CreativeWork",
        "name": "{{ category[0] }}",
        "description": "{{ category[0]}} 관련 포스트 {{ category[1].size }}개",
        "url": "{{ page.url | absolute_url }}#{{ category[0] | slugify }}",
        "numberOfItems": {{ category[1].size }}
      }{% unless forloop.last %},{% endunless %}
      {% endfor %}
    ]
  },
  "breadcrumb": {
    "@type": "BreadcrumbList",
    "itemListElement": [
      {
        "@type": "ListItem",
        "position": 1,
        "name": "홈",
        "item": "{{ site.url }}"
      },
      {
        "@type": "ListItem",
        "position": 2,
        "name": "카테고리",
        "item": "{{ page.url | absolute_url }}"
      }
    ]
  }
}
</script>
