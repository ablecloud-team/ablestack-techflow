import copy
import importlib.util
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location('community_review_candidates',
    Path(__file__).resolve().parents[3] / 'tools' / 'community_review_candidates.py')
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)


def topic(topic_id='200', created='2026-11-04T01:00:00Z', selected='550', **attributes):
    return {'id': topic_id, 'attributes': {'createdAt': created, **attributes},
            'relationships': {'bestAnswerPost': {'data': {'id': selected}}}}


def post(post_id='559', author='101', text='멀티패스 설정 후 해결되었습니다.', **attributes):
    return {'id': post_id, 'attributes': {'contentType': 'comment', 'contentHtml': text, **attributes},
            'relationships': {'user': {'data': {'id': author}}}}


class ScheduledReviewTests(unittest.TestCase):
    def setUp(self):
        self.topic = topic()
        self.posts = [post('540', '68', '최초 질문'), post(), post('550', '40', 'KB')]
        signature, _ = review.human_signature(self.topic, self.posts, '40')
        self.ledger = {'discussions': {'200': {'stage': 'completed', 'humanSignature': signature}}}

    def fetch(self, url):
        if '/api/discussions?' in url:
            return {'data': [self.topic]}
        if '/api/posts?' in url:
            return {'data': self.posts}
        raise AssertionError(url)

    def run_scan(self):
        return review.review_candidates(self.fetch, self.ledger, '2026-11-04T00:00:00+09:00', '40')[0]

    def test_completed_unchanged_and_own_kb_edit_are_skipped(self):
        self.assertFalse(self.run_scan()['needsReview'])
        self.posts[2]['attributes'].update(contentHtml='갱신된 AI KB', editedAt='2026-11-11T03:00:00Z')
        self.assertFalse(self.run_scan()['needsReview'])

    def test_new_human_result_reopens_completed_review(self):
        self.posts.append(post('560', '101', '추가 해결 결과'))
        self.assertTrue(self.run_scan()['needsReview'])

    def test_human_edit_or_solution_change_reopens_review(self):
        self.posts[1]['attributes']['contentHtml'] = '수정한 실제 해결 방법'
        self.assertTrue(self.run_scan()['needsReview'])
        self.posts[1]['attributes']['contentHtml'] = '멀티패스 설정 후 해결되었습니다.'
        self.topic['relationships']['bestAnswerPost']['data']['id'] = '560'
        self.assertTrue(self.run_scan()['needsReview'])

    def test_unfinished_and_legacy_records_are_never_silently_completed(self):
        self.ledger['discussions']['200']['stage'] = 'kb_pending'
        self.assertTrue(self.run_scan()['needsReview'])
        self.ledger['discussions']['200'] = {'stage': 'completed'}
        self.assertTrue(self.run_scan()['needsReview'])

    def test_hidden_post_is_excluded_and_source_removal_changes_signature(self):
        self.posts.append(post('570', isHidden=True))
        self.assertFalse(self.run_scan()['needsReview'])
        self.posts[1]['attributes']['isHidden'] = True
        result = self.run_scan()
        self.assertTrue(result['needsReview'])
        self.assertNotIn('559', result['visibleHumanPostIds'])

    def test_topics_and_posts_paginate_and_manually_tracked_older_199_is_included(self):
        self.ledger['discussions']['199'] = {'stage': 'completed', 'knowledgeBasePostId': '550'}
        topic_next = review.ORIGIN + '/api/discussions?page[offset]=50'
        post_next = review.ORIGIN + '/api/posts?page[offset]=50'
        calls = []
        def fetch(url):
            calls.append(url)
            if url == topic_next:
                return {'data': [topic('203'), topic('198', '2026-11-03T01:00:00Z')]}
            if url == post_next:
                return {'data': [post('560')]}
            if '/api/discussions?' in url:
                return {'data': [self.topic], 'links': {'next': topic_next}}
            if '/api/discussions/199?' in url:
                return {'data': topic('199', '2026-11-03T01:00:00Z')}
            if '/api/posts?' in url:
                return {'data': [post('540')], 'links': {'next': post_next}}
            raise AssertionError(url)
        result = review.review_candidates(fetch, self.ledger, '2026-11-04T00:00:00+09:00', '40')
        self.assertEqual({'199', '200', '203'}, {row['discussionId'] for row in result})
        self.assertTrue(all(row['visibleHumanPostIds'] == ['540', '560'] for row in result))
        self.assertIn(topic_next, calls)

    def test_hidden_topic_not_reviewed_and_no_ledger_or_body_is_written(self):
        before = copy.deepcopy(self.ledger)
        result = self.run_scan()
        self.assertEqual(before, self.ledger)
        self.assertNotIn('멀티패스', str(result))
        self.topic['attributes']['isHidden'] = True
        self.assertEqual([], review.review_candidates(self.fetch, self.ledger, '2026-11-04T00:00:00+09:00', '40'))

    def test_missing_identity_wrong_origin_and_pagination_loop_fail_closed(self):
        with self.assertRaises(ValueError):
            review.human_signature(self.topic, self.posts, '')
        self.posts[0]['relationships'] = {}
        with self.assertRaises(ValueError):
            self.run_scan()
        for url in ('http://community.ablecloud.io/api/posts', 'https://example.org/api/posts',
                    'https://community.ablecloud.io/other', 'https://user:secret@community.ablecloud.io/api/posts'):
            with self.assertRaises(ValueError):
                review._safe_url(url)
        url = review.ORIGIN + '/api/posts'
        with self.assertRaisesRegex(ValueError, 'loop'):
            list(review._pages(lambda _: {'data': [], 'links': {'next': url}}, url))
        with self.assertRaisesRegex(ValueError, 'redirects'):
            review._NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.org/api/posts')


if __name__ == '__main__':
    unittest.main()
