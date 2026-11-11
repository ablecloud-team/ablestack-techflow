#!/usr/bin/env python3
"""Read-only selection for the Community quality schedule; never posts or marks work complete."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request


ORIGIN = 'https://community.ablecloud.io'


def _safe_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if (parsed.scheme != 'https' or parsed.netloc != 'community.ablecloud.io'
            or not parsed.path.startswith('/api/') or parsed.username or parsed.password):
        raise ValueError('unexpected Community API pagination origin')
    return url


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Community API redirects are not allowed')


def fetch_json(url: str) -> dict:
    opener = urllib.request.build_opener(_NoRedirect)
    with opener.open(_safe_url(url), timeout=20) as response:
        return json.load(response)


def _pages(fetch, url: str):
    seen = set()
    for _ in range(1000):
        if not url:
            return
        _safe_url(url)
        if url in seen:
            raise ValueError('pagination loop')
        seen.add(url)
        page = fetch(url)
        yield page
        url = (page.get('links') or {}).get('next')
    raise ValueError('Community scan exceeded its page bound')


def _visible(item: dict) -> bool:
    attrs = item.get('attributes') or {}
    return not attrs.get('isHidden') and not attrs.get('hiddenAt') and attrs.get('isApproved') is not False


def human_signature(discussion: dict, posts: list[dict], assistant_id: str) -> tuple[str, list[str]]:
    """Own AI/KB edits do not create an endless scheduled-review feedback loop."""
    if not assistant_id.isdigit():
        raise ValueError('assistant identity must be supplied explicitly')
    humans = []
    for post in posts:
        attrs = post.get('attributes') or {}
        if not _visible(post) or attrs.get('contentType') != 'comment':
            continue
        author = (((post.get('relationships') or {}).get('user') or {}).get('data') or {}).get('id')
        if not author:
            raise ValueError('post author metadata is incomplete')
        if str(author) == assistant_id:
            continue
        content = attrs.get('content') or attrs.get('contentHtml') or ''
        humans.append({'id': str(post['id']), 'authorId': str(author),
                       'bodyHash': hashlib.sha256(content.encode('utf-8')).hexdigest(),
                       'editedAt': attrs.get('editedAt')})
    humans.sort(key=lambda row: (int(row['id']) if row['id'].isdigit() else 0, row['id']))
    selected = (((discussion.get('relationships') or {}).get('bestAnswerPost') or {}).get('data') or {}).get('id')
    payload = {'humans': humans, 'bestAnswerPostId': str(selected or '')}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    return digest, [row['id'] for row in humans]


def review_candidates(fetch, ledger: dict, cutoff: str, assistant_id: str) -> list[dict]:
    start = datetime.fromisoformat(cutoff.replace('Z', '+00:00'))
    if start.tzinfo is None:
        raise ValueError('cutoff must include its timezone')
    topics = {}
    list_url = ORIGIN + '/api/discussions?' + urllib.parse.urlencode({
        'sort': '-createdAt', 'include': 'bestAnswerPost', 'page[limit]': 50})
    for page in _pages(fetch, list_url):
        reached_boundary = False
        for topic in page.get('data') or []:
            created = datetime.fromisoformat(topic['attributes']['createdAt'].replace('Z', '+00:00'))
            if created < start:
                reached_boundary = True
                continue
            if _visible(topic):
                topics[str(topic['id'])] = topic
        if reached_boundary:
            break
    records = ledger.get('discussions') or {}
    # Previously processed KBs remain monitored even when first created before the
    # new-question cutoff (for example the explicitly reviewed Discussion 199).
    for topic_id, record in records.items():
        if topic_id in topics or not (record.get('knowledgeBasePostId') or record.get('monitorLateSolutions')):
            continue
        if not topic_id.isdigit():
            raise ValueError('invalid tracked discussion ID')
        try:
            topic = fetch(ORIGIN + f'/api/discussions/{topic_id}?include=bestAnswerPost')['data']
        except urllib.error.HTTPError as exc:
            if exc.code in {404, 410}:
                continue
            raise
        if str(topic['id']) != topic_id:
            raise ValueError('tracked topic mismatch')
        if _visible(topic):
            topics[topic_id] = topic
    result = []
    for topic_id, topic in topics.items():
        posts_url = ORIGIN + '/api/posts?' + urllib.parse.urlencode({
            'filter[discussion]': topic_id, 'include': 'user', 'sort': 'createdAt', 'page[limit]': 50})
        posts = [post for page in _pages(fetch, posts_url) for post in page.get('data') or []]
        signature, humans = human_signature(topic, posts, assistant_id)
        record = records.get(topic_id) or {}
        needs_review = record.get('stage') != 'completed' or record.get('humanSignature') != signature
        selected = (((topic.get('relationships') or {}).get('bestAnswerPost') or {}).get('data') or {}).get('id')
        result.append({'discussionId': topic_id, 'createdAt': topic['attributes']['createdAt'],
                       'humanSignature': signature, 'visibleHumanPostIds': humans,
                       'bestAnswerPostId': str(selected or ''), 'needsReview': needs_review,
                       'stage': record.get('stage'),
                       'reason': 'unfinished' if record.get('stage') != 'completed' else 'changed-or-legacy-signature' if needs_review else 'unchanged'})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--cutoff', default='2026-11-04T00:00:00+09:00')
    parser.add_argument('--assistant-user-id', required=True)
    args = parser.parse_args()
    ledger = json.loads(args.ledger.read_text(encoding='utf-8')) if args.ledger.exists() else {}
    print(json.dumps(review_candidates(fetch_json, ledger, args.cutoff, args.assistant_user_id), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
