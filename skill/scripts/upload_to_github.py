"""Upload rule files to GitHub via API (no git/gh CLI needed).

Usage:
  python upload_to_github.py --token <PAT> --repo <repo-name> [--private] --files a.list b.list

Requires token scopes:
  classic : public_repo (public repos) / repo (private)
  fine-grained: Contents=read/write + Administration=read/write (create repo)

Files are uploaded to the repository ROOT using their local basename.
"""
import argparse
import base64
import json
import pathlib
import sys
import urllib.error
import urllib.request

API = 'https://api.github.com'


def call(url, token, method='GET', payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', 'Bearer ' + token)
    req.add_header('Accept', 'application/vnd.github+json')
    req.add_header('User-Agent', 'rule-uploader')
    if data:
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode('utf-8', 'replace')
            return r.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', 'replace')
        try:
            body = json.loads(body)
        except Exception:
            pass
        return e.code, body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--token', required=True)
    ap.add_argument('--repo', required=True)
    ap.add_argument('--private', action='store_true', help='default is public')
    ap.add_argument('--files', nargs='+', required=True)
    ap.add_argument('--description', default='Ad-block domain ruleset mirror (Jinx blacklist, converted for mihomo / Surge)')
    args = ap.parse_args()

    status, me = call(API + '/user', args.token)
    if status != 200:
        print('AUTH FAILED:', status, me)
        sys.exit(1)
    owner = me['login']
    print('authenticated as:', owner)

    status, res = call(API + '/user/repos', args.token, 'POST', {
        'name': args.repo,
        'description': args.description,
        'private': args.private,
        'auto_init': True,
    })
    if status == 201:
        print('repo created:', res['html_url'])
    elif status == 422:
        print('repo already exists, reusing')
        status2, res2 = call('%s/repos/%s/%s' % (API, owner, args.repo), args.token)
        if status2 != 200:
            print('cannot access repo:', status2, res2)
            sys.exit(1)
    else:
        print('repo create failed:', status, res)
        sys.exit(1)

    raw_base = 'https://raw.githubusercontent.com/%s/%s/main/' % (owner, args.repo)

    for f in args.files:
        p = pathlib.Path(f)
        if not p.exists():
            print('  MISSING', f)
            continue
        content = base64.b64encode(p.read_bytes()).decode()
        path_in_repo = p.name
        url = '%s/repos/%s/%s/contents/%s' % (API, owner, args.repo, path_in_repo)

        st, existing = call(url, args.token)
        payload = {'message': 'add ' + path_in_repo, 'content': content}
        if st == 200 and isinstance(existing, dict) and 'sha' in existing:
            payload['sha'] = existing['sha']
            payload['message'] = 'update ' + path_in_repo

        st, res = call(url, args.token, 'PUT', payload)
        if st in (200, 201):
            print('  OK   %-36s %s' % (path_in_repo, res['content']['size']))
        else:
            print('  FAIL %-36s %s %s' % (path_in_repo, st, res))

    print()
    print('raw urls:')
    for f in args.files:
        print('  ' + raw_base + pathlib.Path(f).name)


if __name__ == '__main__':
    main()
