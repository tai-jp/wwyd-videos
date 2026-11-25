"""どっちゃんの返信辞書。 python3 match.py "コメント" [dict.json]
- 10文字を超えるコメント → skip（返事しない）
- 辞書のキーと十分似ている → その返信を使う（承認済み）
- 似たものがない → new（Claudeが返信案を作り、承認されたら辞書に追加）
似ている基準：正規化した文字列の一致率 = 1 - 編集距離/長い方の文字数 が 0.8 以上
（10文字なら8文字以上同じ）。3文字以下は完全一致のみ。"""
import sys, json, re, unicodedata
MAXLEN = 10

def norm(s):
    s = unicodedata.normalize('NFKC', s).lower()
    s = re.sub(r'[\s。、．，,.!！?？~〜ー…・「」『』()（）]', '', s)
    s = re.sub(r'(w|草|笑)\1+', r'\1', s)      # wwww→w
    s = re.sub(r'(.)\1{2,}', r'\1\1', s)        # すごーーーい等の連続を2つに
    return s

def lev(a, b):
    p = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        c = [i]
        for j, y in enumerate(b, 1):
            c.append(min(p[j] + 1, c[j - 1] + 1, p[j - 1] + (x != y)))
        p = c
    return p[-1]

def sim(a, b):
    if not a or not b: return 0.0
    if max(len(a), len(b)) <= 3: return 1.0 if a == b else 0.0
    return 1 - lev(a, b) / max(len(a), len(b))

def match(comment, D, video=None):
    D = [e for e in D if e.get('video') in (None, video)]   # video付きの項目はその動画だけ
    n = norm(comment)
    if len(unicodedata.normalize('NFKC', comment.strip())) > MAXLEN: return {'action': 'skip', 'why': '10文字超え'}
    if not n: return {'action': 'new', 'why': '絵文字だけ等'} if comment.strip() else {'action': 'skip', 'why': '空'}
    best = max(D, key=lambda e: sim(n, norm(e['key'])), default=None)
    if best and sim(n, norm(best['key'])) >= 0.8:
        return {'action': 'reply', 'key': best['key'], 'reply': best['reply'], 'sim': round(sim(n, norm(best['key'])), 2)}
    return {'action': 'new', 'why': '辞書に似たものなし'}

if __name__ == '__main__':
    D = json.load(open(sys.argv[2] if len(sys.argv) > 2 else 'dict.json'))
    print(json.dumps(match(sys.argv[1], D, sys.argv[3] if len(sys.argv) > 3 else None), ensure_ascii=False))
