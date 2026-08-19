(function () {
  'use strict';

  var forumAppModule = flarum.core.compat['forum/app'];
  var forumApp = forumAppModule.default || forumAppModule;
  var relativeDatePattern = /(?:방금|전$|후$)/;
  var absoluteDatePattern = /^(\d{4})-(\d{2})-(\d{2})/;
  var discussionItemEnhancedAttribute = 'data-ablecloud-post-structure';

  function formatDiscussionCreatedAt(createdAt) {
    if (!(createdAt instanceof Date) || Number.isNaN(createdAt.getTime())) {
      return '';
    }

    var elapsed = Math.max(0, Date.now() - createdAt.getTime());
    var minute = 60 * 1000;
    var hour = 60 * minute;
    var day = 24 * hour;

    if (elapsed < minute) {
      return '방금';
    }

    if (elapsed < hour) {
      return Math.floor(elapsed / minute) + '분 전';
    }

    if (elapsed < day) {
      return Math.floor(elapsed / hour) + '시간 전';
    }

    if (elapsed < 7 * day) {
      return Math.floor(elapsed / day) + '일 전';
    }

    return String(createdAt.getFullYear()).slice(-2) + '년 ' + (createdAt.getMonth() + 1) + '월 ' + createdAt.getDate() + '일';
  }

  function appendMetaPart(meta, className, text) {
    if (!text) {
      return;
    }

    if (meta.childElementCount) {
      var separator = document.createElement('span');
      separator.className = 'ablecloud-DiscussionMeta-separator';
      separator.setAttribute('aria-hidden', 'true');
      separator.textContent = '·';
      meta.appendChild(separator);
    }

    var part = document.createElement('span');
    part.className = className;
    part.textContent = text;
    meta.appendChild(part);
  }

  function buildDiscussionSummary(discussion) {
    var firstPost = discussion && typeof discussion.firstPost === 'function' ? discussion.firstPost() : null;

    if (!firstPost || typeof firstPost.contentPlain !== 'function') {
      return '';
    }

    return String(firstPost.contentPlain() || '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function findDiscussionThumbnail(discussion) {
    var firstPost = discussion && typeof discussion.firstPost === 'function' ? discussion.firstPost() : null;
    var contentHtml = firstPost && typeof firstPost.contentHtml === 'function' ? firstPost.contentHtml() : '';

    if (!contentHtml) {
      return null;
    }

    var template = document.createElement('template');
    template.innerHTML = String(contentHtml);
    var sourceImage = template.content.querySelector('img[src]');

    if (!sourceImage) {
      return null;
    }

    var resolvedUrl;

    try {
      resolvedUrl = new URL(sourceImage.getAttribute('src'), window.location.origin);
    } catch (error) {
      return null;
    }

    if (!['http:', 'https:'].includes(resolvedUrl.protocol)) {
      return null;
    }

    return {
      src: resolvedUrl.href,
      alt: sourceImage.getAttribute('alt') || sourceImage.getAttribute('title') || '게시물 첨부 이미지 미리보기',
    };
  }

  function enhanceDiscussionListItems(root) {
    root.querySelectorAll('.DiscussionList-discussions > li[data-id]').forEach(function (listItem) {
      if (listItem.getAttribute(discussionItemEnhancedAttribute) === 'true') {
        return;
      }

      var discussion = forumApp.store.getById('discussions', listItem.getAttribute('data-id'));
      var content = listItem.querySelector('.DiscussionListItem-content');
      var main = content && content.querySelector('.DiscussionListItem-main');
      var title = main && main.querySelector('.DiscussionListItem-title');

      if (!discussion || !content || !main || !title) {
        return;
      }

      var user = typeof discussion.user === 'function' ? discussion.user() : null;
      var author = user && typeof user.displayName === 'function' ? user.displayName() : '';
      var category = main.querySelector('.TagLabel-name');
      var meta = document.createElement('div');
      meta.className = 'ablecloud-DiscussionMeta';
      meta.setAttribute('aria-label', '토론 작성 정보');
      appendMetaPart(meta, 'ablecloud-DiscussionMeta-category', category && category.textContent.trim());
      appendMetaPart(meta, 'ablecloud-DiscussionMeta-author', author);
      appendMetaPart(
        meta,
        'ablecloud-DiscussionMeta-time',
        formatDiscussionCreatedAt(typeof discussion.createdAt === 'function' ? discussion.createdAt() : null)
      );
      content.insertBefore(meta, main);

      var summaryText = buildDiscussionSummary(discussion);

      if (summaryText) {
        var summary = document.createElement('p');
        summary.className = 'ablecloud-DiscussionSummary';
        summary.textContent = summaryText;
        title.insertAdjacentElement('afterend', summary);
      }

      var thumbnail = findDiscussionThumbnail(discussion);

      if (thumbnail) {
        var thumbnailFrame = document.createElement('span');
        var thumbnailImage = document.createElement('img');
        thumbnailFrame.className = 'ablecloud-DiscussionThumbnail';
        thumbnailFrame.setAttribute('aria-hidden', 'true');
        thumbnailImage.src = thumbnail.src;
        thumbnailImage.alt = thumbnail.alt;
        thumbnailImage.loading = 'lazy';
        thumbnailImage.decoding = 'async';
        thumbnailFrame.appendChild(thumbnailImage);
        main.appendChild(thumbnailFrame);
        main.classList.add('ablecloud-DiscussionMain--withThumbnail');
      }

      var badges = content.querySelector('.DiscussionListItem-badges');

      if (badges && badges.querySelector('.item-bestAnswer')) {
        badges.setAttribute('aria-label', '해결된 토론');
      }

      listItem.setAttribute(discussionItemEnhancedAttribute, 'true');
    });
  }

  function formatTagDiscussionDates(root) {
    root.querySelectorAll('.TagTile-lastPostedDiscussion time[datetime]').forEach(function (time) {
      var current = time.textContent.trim();

      if (relativeDatePattern.test(current)) {
        return;
      }

      var matched = (time.getAttribute('datetime') || '').match(absoluteDatePattern);

      if (!matched) {
        return;
      }

      var formatted = matched[1].slice(-2) + '년 ' + Number(matched[2]) + '월 ' + Number(matched[3]) + '일';

      if (current !== formatted) {
        time.textContent = formatted;
      }
    });
  }

  function normalizeDiscussionListTargets(root) {
    root.querySelectorAll('.DiscussionListItem-main[href]').forEach(function (link) {
      var url = new URL(link.getAttribute('href'), window.location.origin);
      var canonicalPath = url.pathname.replace(/(\/d\/[^/]+)\/\d+\/?$/, '$1');

      if (canonicalPath === url.pathname) {
        return;
      }

      link.setAttribute('href', canonicalPath + url.search);
      link.setAttribute('data-ablecloud-start-from-top', 'true');
    });
  }

  function openDiscussionFromTop(event) {
    var link = event.target.closest && event.target.closest('.DiscussionListItem-main[data-ablecloud-start-from-top="true"]');

    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }

    var href = link.getAttribute('href');

    event.preventDefault();
    event.stopImmediatePropagation();

    window.location.assign(href);
  }

  forumApp.initializers.add('ablecloud-community-theme-tag-date', function () {
    var pendingFrame = 0;
    var schedule = function () {
      window.cancelAnimationFrame(pendingFrame);
      pendingFrame = window.requestAnimationFrame(function () {
        formatTagDiscussionDates(document);
        normalizeDiscussionListTargets(document);
        enhanceDiscussionListItems(document);
      });
    };

    schedule();

    new MutationObserver(schedule).observe(document.body, {
      childList: true,
      characterData: true,
      subtree: true,
    });

    document.addEventListener('click', openDiscussionFromTop, true);
  });

  module.exports = {};
})();
