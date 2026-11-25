"""YouTubeの新しいコメントを見て、辞書に合うものだけ どっちゃん が返信する。
環境変数: YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN（GitHub Secrets）, DRY_RUN=1 なら送らない。
- 10文字超え → 何もしない（skipped に記録）
- 辞書に合う → 返信（1回の実行で最大 MAX_REPLIES 件）
- 合わない   → pending.json に積む（Claudeが返信案を作り、承認されたら dict.json に追加 → 次の実行で返信）
クォータ: 一覧1ユニット、返信1件50ユニット（1日10,000まで無料）。"""
import os, json, time, urllib.request, urllib.parse
from match import match
H = os.path.dirname(os.path.abspath(__file__))
DRY = os.environ.get('DRY_RUN', '0') == '1'
MAX_REPLIES = 10
API = 'https://www.googleapis.com/youtube/v3/'

def token():
    d = urllib.parse.urlencode({'client_id': os.environ['YT_CLIENT_ID'], 'client_secret': os.environ['YT_CLIENT_SECRET'],
                                'refresh_token': os.environ['YT_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode()
    return json.load(urllib.request.urlopen('https://oauth2.googleapis.com/token', d))['access_token']

def call(tok, path, q=None, body=None):
    url = API + path + ('?' + urllib.parse.urlencode(q) if q else '')
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                               headers={'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(r))

def load(n, d):
    p = os.path.join(H, n)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else d

def save(n, v):
    json.dump(v, open(os.path.join(H, n), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def main():
    D = load('dict.json', []); VID = load('videos.json', {})   # YouTube videoId → 動画の名前(e001等)
    st = load('yt_state.json', {'done': {}}); pend = {}
    tok = token()
    me = call(tok, 'channels', {'part': 'id', 'mine': 'true'})['items'][0]['id']
    th = call(tok, 'commentThreads', {'part': 'snippet,replies', 'allThreadsRelatedToChannelId': me, 'order': 'time', 'maxResults': 50, 'textFormat': 'plainText'})
    sent = 0
    for t in th.get('items', []):
        cid = t['id']; s = t['snippet']; c = s['topLevelComment']['snippet']
        if cid in st['done'] or c.get('authorChannelId', {}).get('value') == me: continue
        if any(r['snippet'].get('authorChannelId', {}).get('value') == me for r in t.get('replies', {}).get('comments', [])):
            st['done'][cid] = 'already'; continue
        vid = s.get('videoId'); ep = VID.get(vid)
        m = match(c['textOriginal'], D, ep)
        if m['action'] == 'skip':
            st['done'][cid] = 'skip'
        elif m['action'] == 'reply':
            if sent >= MAX_REPLIES: continue
            print(('[DRY] ' if DRY else '') + f"reply {ep or vid}: {c['textOriginal']!r} -> {m['reply']!r}")
            if not DRY:
                call(tok, 'comments', {'part': 'snippet'}, {'snippet': {'parentId': cid, 'textOriginal': m['reply']}})
                st['done'][cid] = 'replied:' + m['key']; time.sleep(3)
            sent += 1
        else:
            pend[cid] = {'video': ep or vid, 'text': c['textOriginal'], 'at': c['publishedAt']}
    save('yt_state.json', st); save('pending.json', pend)
    print(f'sent {sent}, pending {len(pend)}')

if __name__ == '__main__':
    main()
