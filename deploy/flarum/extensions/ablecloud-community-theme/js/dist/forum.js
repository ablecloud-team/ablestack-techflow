(function () {
  'use strict';

  var forumAppModule = flarum.core.compat['forum/app'];
  var forumApp = forumAppModule.default || forumAppModule;
  var relativeDatePattern = /(?:방금|전$|후$)/;
  var absoluteDatePattern = /^(\d{4})-(\d{2})-(\d{2})/;

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
