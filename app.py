"""Ứng dụng thời tiết: Python standard library + Open-Meteo + HTML/CSS/JS.
Chạy: python app.py ; Chia sẻ LAN: python app.py --lan
"""
import argparse
import csv
import io
import json
import math
import socket
import threading
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parent
STATIC = BASE / 'static' if (BASE / 'static').is_dir() else BASE
API_URL = 'https://api.open-meteo.com/v1/forecast'
VARIABLES = ('temperature_2m', 'relative_humidity_2m', 'shortwave_radiation')
CACHE_SECONDS = 600
EXPORT_SECONDS = 3600
MAX_SNAPSHOTS = 64
SNAPSHOTS = OrderedDict()
CACHE = {}
LOCK = threading.Lock()


class InputError(ValueError):
    pass


class WeatherError(Exception):
    pass


def parse_inputs(query):
    """Kiểm tra đầu vào cả ở server, không chỉ ở trình duyệt."""
    def number(name, default, low, high, integer=False):
        values = query.get(name, [str(default)])
        if len(values) != 1:
            raise InputError('Mỗi tham số chỉ được nhập một lần.')
        try:
            value = float(values[0])
        except (ValueError, TypeError):
            raise InputError(f'{name}: vui lòng nhập số hợp lệ.')
        if not math.isfinite(value) or not low <= value <= high:
            raise InputError(f'{name} phải nằm trong khoảng {low} đến {high}.')
        if integer and not value.is_integer():
            raise InputError(f'{name} phải là số nguyên.')
        return int(value) if integer else value

    result = {
        'latitude': number('latitude', 21.0285, -90, 90),
        'longitude': number('longitude', 105.8542, -180, 180),
        'past_days': number('past_days', 7, 0, 92, True),
        'forecast_days': number('forecast_days', 3, 0, 16, True),
    }
    if result['past_days'] + result['forecast_days'] == 0:
        raise InputError('Hãy chọn ít nhất một ngày quá khứ hoặc dự báo.')
    return result


def fetch_provider(params):
    query = dict(params, hourly=','.join(VARIABLES), timezone='auto',
                 timeformat='unixtime', temperature_unit='celsius')
    url = API_URL + '?' + urlencode(query)
    request = Request(url, headers={'User-Agent': 'StudentWeatherProject/1.0',
                                   'Accept': 'application/json'})
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read(4_000_001)
        if len(raw) > 4_000_000:
            raise WeatherError('Dữ liệu trả về quá lớn. Hãy giảm số ngày.')
        data = json.loads(raw)
    except HTTPError as exc:
        if exc.code == 429:
            raise WeatherError('Nguồn dữ liệu đang giới hạn lượt truy cập. Hãy thử lại sau.') from exc
        raise WeatherError(f'Nguồn thời tiết trả lỗi HTTP {exc.code}. Hãy thử lại sau.') from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise WeatherError('Không kết nối được Open-Meteo. Kiểm tra Internet của máy chạy Python rồi thử lại.') from exc
    except (ValueError, UnicodeError) as exc:
        raise WeatherError('Nguồn thời tiết trả dữ liệu không hợp lệ.') from exc
    if not isinstance(data, dict) or data.get('error'):
        raise WeatherError('Open-Meteo không thể cung cấp dữ liệu cho yêu cầu này.')
    return data


def search_locations(query):
    """Tra cứu điểm địa danh ở Việt Nam; không phải dữ liệu trung bình toàn tỉnh."""
    values = query.get('name', [''])
    if len(values) != 1 or not 2 <= len(values[0].strip()) <= 80:
        raise InputError('Nhập tên tỉnh/thành phố từ 2 đến 80 ký tự.')
    name = values[0].strip()
    # Nguồn hỗ trợ tìm có dấu/không dấu. Bỏ tiền tố hành chính khi người dùng nhập.
    import re
    name = re.sub(r'^(?:thành phố|thanh pho|tỉnh|tinh|tp\.?)\s+', '', name, flags=re.I).strip()
    if len(name) < 2:
        raise InputError('Hãy nhập tên địa điểm sau tỉnh/thành phố.')
    url = 'https://geocoding-api.open-meteo.com/v1/search?' + urlencode({
        'name': name, 'count': 20, 'language': 'vi', 'format': 'json', 'countryCode': 'VN'})
    try:
        request = Request(url, headers={'User-Agent': 'StudentWeatherProject/1.0'})
        with urlopen(request, timeout=20) as response:
            raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise WeatherError('Kết quả tìm kiếm quá lớn. Hãy nhập tên cụ thể hơn.')
        data = json.loads(raw)
        if not isinstance(data, dict) or data.get('error'):
            raise ValueError('Invalid geocoding response')
        places = data.get('results', [])
        if not isinstance(places, list):
            raise ValueError('Invalid results')
        results = []
        for place in places:
            if place.get('country_code') != 'VN':
                continue
            lat, lon = float(place['latitude']), float(place['longitude'])
            if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
                raise ValueError('Invalid coordinates')
            parts = [place['name'], place.get('admin2'), place.get('admin1'), place.get('country', 'Việt Nam')]
            label = ' · '.join(dict.fromkeys(part for part in parts if isinstance(part, str) and part))
            results.append({'name': place['name'], 'label': label, 'latitude': lat, 'longitude': lon})
        return {'results': results}
    except HTTPError as exc:
        raise WeatherError('Nguồn tìm địa điểm tạm thời không đáp ứng. Hãy thử lại sau.') from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise WeatherError('Không kết nối được nguồn địa điểm. Kiểm tra Internet hoặc nhập tọa độ trực tiếp.') from exc
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise WeatherError('Nguồn tìm địa điểm trả về dữ liệu không hợp lệ.') from exc


def normalise(data, params, now=None):
    """Giữ timestamp UTC để không nhầm giờ mùa hè; UI đổi sang múi giờ địa điểm."""
    now = now or datetime.now(timezone.utc)
    try:
        hourly = data['hourly']
        stamps = hourly['time']
        zone = data['timezone']
        offset = int(data['utc_offset_seconds'])
        if not isinstance(zone, str) or not isinstance(stamps, list) or not stamps:
            raise ValueError('No times')
        for variable in VARIABLES:
            if not isinstance(hourly[variable], list) or len(hourly[variable]) != len(stamps):
                raise ValueError('Mismatched arrays')
        # Offset hiện tại chỉ dùng tìm mốc 00:00 hôm nay của địa điểm.
        # Các giờ quá khứ được giữ ở UTC; trình duyệt áp dụng quy tắc DST khi hiển thị.
        local_now = now.astimezone(timezone(timedelta(seconds=offset)))
        today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        rows = []
        previous = None
        for i, stamp in enumerate(stamps):
            if not isinstance(stamp, (int, float)) or not math.isfinite(stamp):
                raise ValueError('Invalid timestamp')
            if previous is not None and stamp <= previous:
                raise ValueError('Unsorted timestamps')
            previous = stamp
            row = {'time_utc': datetime.fromtimestamp(stamp, timezone.utc).isoformat(),
                   'timestamp': stamp,
                   'period': 'past_model' if stamp < today_start else 'forecast'}
            for variable in VARIABLES:
                value = hourly[variable][i]
                if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value)):
                    raise ValueError('Invalid measurement')
                row[variable] = value  # Giữ None, không biến dữ liệu thiếu thành số 0.
            rows.append(row)
        return {
            'rows': rows,
            'meta': {'requested': params, 'grid_latitude': data['latitude'],
                     'grid_longitude': data['longitude'], 'timezone': zone,
                     'fetched_at_utc': now.isoformat(), 'source': 'Open-Meteo Forecast API',
                     'units': {'temperature_2m': '°C', 'relative_humidity_2m': '%',
                               'shortwave_radiation': 'W/m²'},
                     'missing_values': sum(row[v] is None for row in rows for v in VARIABLES)},
        }
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise WeatherError('Dữ liệu nguồn thiếu trường, sai thứ tự giờ hoặc không đúng cấu trúc.') from exc


def get_snapshot(params):
    key = tuple(params[k] for k in ('latitude', 'longitude', 'past_days', 'forecast_days'))
    now = time.time()
    with LOCK:
        cached = CACHE.get(key)
        if cached and now - cached[0] < CACHE_SECONDS and cached[1] in SNAPSHOTS:
            return SNAPSHOTS[cached[1]][1]
    result = normalise(fetch_provider(params), params)
    return save_snapshot(result, key)


def save_snapshot(result, key=None):
    result['id'] = uuid.uuid4().hex
    with LOCK:
        SNAPSHOTS[result['id']] = (time.time(), result)
        if key is not None:
            CACHE[key] = (time.time(), result['id'])
        while len(SNAPSHOTS) > MAX_SNAPSHOTS:
            SNAPSHOTS.popitem(last=False)
        for old_key, (_, token) in list(CACHE.items()):
            if token not in SNAPSHOTS:
                del CACHE[old_key]
    return result


def csv_bytes(snapshot):
    """Xuất đúng snapshot đang hiển thị, không gọi API lại khi bấm tải."""
    out = io.StringIO(newline='')
    writer = csv.writer(out)
    writer.writerow(['time_utc', 'timezone', 'period', 'temperature_c',
                     'relative_humidity_percent', 'shortwave_radiation_w_m2',
                     'requested_latitude', 'requested_longitude', 'grid_latitude',
                     'grid_longitude', 'source', 'fetched_at_utc'])
    meta = snapshot['meta']
    for row in snapshot['rows']:
        writer.writerow([row['time_utc'], meta['timezone'], row['period'],
                         row['temperature_2m'], row['relative_humidity_2m'],
                         row['shortwave_radiation'], meta['requested']['latitude'],
                         meta['requested']['longitude'], meta['grid_latitude'],
                         meta['grid_longitude'], meta['source'], meta['fetched_at_utc']])
    return out.getvalue().encode('utf-8-sig')


class Handler(BaseHTTPRequestHandler):
    def send_content(self, status, content, mime, extra=None):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self' https://api.open-meteo.com; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        try:
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def json_response(self, status, obj):
        self.send_content(status, json.dumps(obj, ensure_ascii=False, allow_nan=False).encode(),
                          'application/json; charset=utf-8')

    def do_POST(self):
        # Browser transport fallback; validation, normalisation and CSV stay in Python.
        if urlsplit(self.path).path != '/api/import':
            self.json_response(404, {'error': 'Không tìm thấy trang.'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 4_000_000:
                raise InputError('Dung lượng dữ liệu không hợp lệ.')
            if self.headers.get_content_type() != 'application/json':
                raise InputError('Yêu cầu dữ liệu JSON.')
            payload = json.loads(self.rfile.read(length))
            params = parse_inputs({k: [v] for k, v in payload['params'].items()})
            result = normalise(payload['data'], params)
            if len(result['rows']) > 24 * 109:
                raise InputError('Số dòng dữ liệu vượt giới hạn.')
            result['meta']['source'] = 'Open-Meteo Forecast API (browser transport; Python processing)'
            self.json_response(200, save_snapshot(result))
        except (InputError, WeatherError, ValueError, TypeError, KeyError, AttributeError) as exc:
            self.json_response(400, {'error': 'Dữ liệu dự phòng không hợp lệ: ' + str(exc)})

    def do_GET(self):
        path = urlsplit(self.path)
        query = parse_qs(path.query, keep_blank_values=True)
        if path.path == '/api/locations':
            try:
                self.json_response(200, search_locations(query))
            except InputError as exc:
                self.json_response(400, {'error': str(exc)})
            except WeatherError as exc:
                self.json_response(502, {'error': str(exc)})
            return
        if path.path == '/api/weather':
            try:
                self.json_response(200, get_snapshot(parse_inputs(query)))
            except InputError as exc:
                self.json_response(400, {'error': str(exc)})
            except WeatherError as exc:
                self.json_response(502, {'error': str(exc)})
            return
        if path.path == '/api/export':
            token = query.get('id', [''])[0]
            with LOCK:
                saved = SNAPSHOTS.get(token)
            if not saved or time.time() - saved[0] > EXPORT_SECONDS:
                self.json_response(410, {'error': 'Phiên tải CSV đã hết hạn. Hãy lấy dữ liệu lại.'})
                return
            snapshot = saved[1]
            lat = snapshot['meta']['requested']['latitude']
            lon = snapshot['meta']['requested']['longitude']
            filename = f'weather_{lat}_{lon}_{token[:8]}.csv'
            self.send_content(200, csv_bytes(snapshot), 'text/csv; charset=utf-8',
                              {'Content-Disposition': f'attachment; filename="{filename}"'})
            return
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                 '/style.css': ('style.css', 'text/css; charset=utf-8'),
                 '/logo_hust.jpg': ('logo_hust.jpg', 'image/jpeg')}
        if path.path not in files:
            self.json_response(404, {'error': 'Không tìm thấy trang.'})
            return
        name, mime = files[path.path]
        self.send_content(200, (STATIC / name).read_bytes(), mime)


def lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(('192.0.2.1', 80))  # Chọn giao diện; không gửi gói dữ liệu.
            return sock.getsockname()[0]
    except OSError:
        return '<IPv4-cua-may>'


def main():
    parser = argparse.ArgumentParser(description='Website dữ liệu thời tiết cho đồ án Python')
    parser.add_argument('--lan', action='store_true', help='Cho phép máy khác trong LAN truy cập')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('Port phải từ 1 đến 65535')
    host = '0.0.0.0' if args.lan else '127.0.0.1'
    try:
        server = ThreadingHTTPServer((host, args.port), Handler)
    except OSError as exc:
        parser.exit(1, f'Không mở được cổng {args.port}: {exc}. Thử --port 8001\n')
    print(f'Mở trên máy này: http://localhost:{args.port}', flush=True)
    if args.lan:
        print(f'Chia sẻ cùng Wi-Fi/LAN: http://{lan_ip()}:{args.port}', flush=True)
    print('Nhấn Ctrl+C để dừng. Dữ liệu thật cần Internet trên máy chạy Python.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
