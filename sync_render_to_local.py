import argparse
import json
import urllib.request
import urllib.error
import urllib.parse
import http.cookiejar


def make_session_opener():
    cookie_jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))


def post_json(opener, url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with opener.open(req, timeout=20) as response:
        return json.loads(response.read().decode('utf-8'))


def get_json(opener, url):
    req = urllib.request.Request(url, method='GET')
    with opener.open(req, timeout=20) as response:
        return json.loads(response.read().decode('utf-8'))


def login_admin(opener, base_url, store_code, password):
    return post_json(opener, f"{base_url.rstrip('/')}/api/login", {
        'role': 'admin',
        'password': password,
        'store_code': store_code,
        'staff_name': ''
    })


def main():
    parser = argparse.ArgumentParser(description='Renderの店舗データをローカルに同期')
    parser.add_argument('--remote-url', required=True, help='Render側URL (例: https://xxx.onrender.com)')
    parser.add_argument('--local-url', default='http://127.0.0.1:5000', help='ローカルURL')
    parser.add_argument('--store-code', required=True, help='同期する店舗コード')
    parser.add_argument('--remote-password', default='admin123', help='Render側の管理者パスワード')
    parser.add_argument('--local-password', default='admin123', help='ローカル側の管理者パスワード')
    args = parser.parse_args()

    remote = make_session_opener()
    local = make_session_opener()

    try:
        remote_login = login_admin(remote, args.remote_url, args.store_code, args.remote_password)
        if not remote_login.get('success'):
            raise RuntimeError('Render側ログインに失敗しました')

        exported = get_json(remote, f"{args.remote_url.rstrip('/')}/api/store-data/export")
        if not exported.get('success'):
            raise RuntimeError('Render側エクスポートに失敗しました')

        data = exported.get('data')
        if not isinstance(data, dict):
            raise RuntimeError('Render側データ形式が不正です')

        local_login = login_admin(local, args.local_url, args.store_code, args.local_password)
        if not local_login.get('success'):
            raise RuntimeError('ローカル側ログインに失敗しました')

        imported = post_json(local, f"{args.local_url.rstrip('/')}/api/store-data/import", {'data': data})
        if not imported.get('success'):
            raise RuntimeError('ローカル側インポートに失敗しました')

        print('同期完了')
        print(json.dumps({
            'store_code': args.store_code,
            'remote_url': args.remote_url,
            'local_url': args.local_url,
            'staff_count': len(data.get('staff', {})),
            'shift_days': len(data.get('shifts', {}))
        }, ensure_ascii=False, indent=2))

    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f'HTTPエラー: {e.code}')
        print(body)
        raise SystemExit(1)
    except Exception as e:
        print(f'同期エラー: {e}')
        raise SystemExit(1)


if __name__ == '__main__':
    main()
