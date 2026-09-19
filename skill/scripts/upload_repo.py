# -*- coding: utf-8 -*-
"""把文件上传到 GitHub 仓库（支持子目录路径，纯 REST API，无需 git/gh）。

用法:
  python upload_repo.py --token <PAT> --repo <owner/name> \
      --map local1:path/in/repo1 local2:path/in/repo2 ...

上传后自动回拉 raw 内容比对 md5，确保"传上去的就是本地这份"。
"""
import argparse
import base64
import hashlib
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

API = 'https://api.github.com'


def call(url, token, method='GET', payload=None, retry=3):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', 'Bearer ' + token)
    req.add_header('Accept', 'application/vnd.github+json')
    req.add_header('User-Agent', 'wb-rule-uploader')
    if data:
        req.add_header('Content-Type', 'application/json')
    last = None
    for i in range(retry):
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
        except Exception as e:            # 网络抖动
            last = e
            time.sleep(2 + 2 * i)
    return 0, str(last)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--token', required=True)
    ap.add_argument('--repo', required=True, help='owner/name')
    ap.add_argument('--map', nargs='+', required=True, help='local_path:repo_path')
    ap.add_argument('--message', default='update ruleset')
    args = ap.parse_args()

    st, me = call(API + '/user', args.token)
    if st != 200:
        print('AUTH FAILED:', st, me)
        sys.exit(1)
    print('authenticated as:', me['login'])
    print()

    ok = True
    for item in args.map:
        # 用 rpartition：Windows 路径带盘符冒号(C:/...)，只能按最后一个冒号切
        local, sep, remote = item.rpartition(':')
        if not remote:
            local, remote = item, pathlib.Path(item).name
        p = pathlib.Path(local)
        if not p.exists():
            print('  MISSING %s' % local)
            ok = False
            continue

        raw = p.read_bytes()
        md5_local = hashlib.md5(raw).hexdigest()
        url = '%s/repos/%s/contents/%s' % (API, args.repo, remote)

        st, cur = call(url, args.token)
        payload = {
            'message': '%s: %s' % (args.message, remote),
            'content': base64.b64encode(raw).decode(),
        }
        action = 'create'
        if st == 200 and isinstance(cur, dict) and 'sha' in cur:
            payload['sha'] = cur['sha']
            action = 'update'
        elif st not in (200, 404):
            print('  FAIL %-34s 读现状失败 %s %s' % (remote, st, cur))
            ok = False
            continue

        st, res = call(url, args.token, 'PUT', payload)
        if st not in (200, 201):
            print('  FAIL %-34s %s %s' % (remote, st, res))
            ok = False
            continue
        sha = res['content']['sha']
        print('  %-6s %-34s %7d B  sha=%s' % (action, remote, len(raw), sha[:10]))

        # 回拉校验
        st2, back = call('%s/repos/%s/contents/%s?ref=main' % (API, args.repo, remote), args.token)
        if st2 == 200 and 'content' in back:
            got = base64.b64decode(back['content'])
            md5_remote = hashlib.md5(got).hexdigest()
            same = md5_remote == md5_local
            print('           回拉校验: %s (%s vs %s)' % ('OK' if same else '!! 不一致',
                                                       md5_local[:10], md5_remote[:10]))
            ok &= same
        else:
            print('           回拉校验: !! 读取失败 %s' % st2)
            ok = False

    print()
    print('总判定:', '全部成功' if ok else '存在失败项')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
