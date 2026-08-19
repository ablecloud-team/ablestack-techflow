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

  forumApp.initializers.add('ablecloud-community-theme-tag-date', function () {
    var pendingFrame = 0;
    var schedule = function () {
      window.cancelAnimationFrame(pendingFrame);
      pendingFrame = window.requestAnimationFrame(function () {
        formatTagDiscussionDates(document);
      });
    };

    schedule();

    new MutationObserver(schedule).observe(document.body, {
      childList: true,
      characterData: true,
      subtree: true,
    });
  });

  module.exports = {};
})();
