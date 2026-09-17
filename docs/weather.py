"""Python chạy trong trình duyệt bằng Pyodide, độc lập với máy tác giả."""
import asyncio
import csv
import io
import json
import math
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlencode
from collections import OrderedDict
from pyodide.http import pyfetch

VARIABLES = ('temperature_2m', 'relative_humidity_2m', 'shortwave_radiation')
SNAPSHOTS = OrderedDict()
CACHE = {}
class InputError(ValueError):
    pass

class WeatherError(Exception):
    pass

def parse_inputs(query):
    """Kiểm tra đầu vào trước khi gọi nguồn dữ liệu."""
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

async def fetch_json(url):
    try:
        response = await asyncio.wait_for(pyfetch(url), timeout=30)
        if response.status == 429:
            raise WeatherError('Nguồn dữ liệu giới hạn lượt truy cập. Hãy thử lại sau.')
        if not response.ok:
            raise WeatherError('Nguồn dữ liệu tạm thời không đáp ứng. Hãy thử lại.')
        data = await response.json()
        if not isinstance(data, dict) or data.get('error'):
            raise WeatherError('Nguồn trả về dữ liệu không hợp lệ.')
        return data
    except WeatherError:
        raise
    except Exception as exc:
        raise WeatherError('Không kết nối được nguồn dữ liệu. Kiểm tra Internet và thử lại.') from exc


async def browser_locations(query):
    values = query.get('name', [''])
    if len(values) != 1 or not 2 <= len(values[0].strip()) <= 80:
        raise InputError('Nhập tên tỉnh/thành phố từ 2 đến 80 ký tự.')
    name = re.sub(r'^(?:thành phố|thanh pho|tỉnh|tinh|tp\.?)\s+', '', values[0].strip(), flags=re.I).strip()
    if len(name) < 2:
        raise InputError('Hãy nhập tên địa điểm sau tỉnh/thành phố.')
    data = await fetch_json('https://geocoding-api.open-meteo.com/v1/search?' + urlencode({
        'name':name, 'count':20, 'language':'vi', 'format':'json', 'countryCode':'VN'}))
    results = []
    for place in data.get('results', []):
        if place.get('country_code') != 'VN':
            continue
        lat, lon = float(place['latitude']), float(place['longitude'])
        if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise WeatherError('Tọa độ nguồn không hợp lệ.')
        parts = [place['name'], place.get('admin2'), place.get('admin1'), place.get('country','Việt Nam')]
        label = ' · '.join(dict.fromkeys(part for part in parts if isinstance(part,str) and part))
        results.append({'name':place['name'],'label':label,'latitude':lat,'longitude':lon})
    return {'results':results}


async def browser_weather(query):
    params = parse_inputs(query)
    key = tuple(params[k] for k in ('latitude','longitude','past_days','forecast_days'))
    cached = CACHE.get(key)
    if cached and time.time()-cached[0] < 600 and cached[1] in SNAPSHOTS:
        return SNAPSHOTS[cached[1]][1]
    request = dict(params, hourly=','.join(VARIABLES), timezone='auto', timeformat='unixtime', temperature_unit='celsius')
    result = normalise(await fetch_json('https://api.open-meteo.com/v1/forecast?' + urlencode(request)), params)
    result['id'] = uuid.uuid4().hex
    SNAPSHOTS[result['id']] = (time.time(),result)
    CACHE[key] = (time.time(),result['id'])
    while len(SNAPSHOTS)>32:
        SNAPSHOTS.popitem(last=False)
    for old_key,(_,token) in list(CACHE.items()):
        if token not in SNAPSHOTS:
            del CACHE[old_key]
    return result


async def dispatch(path, query_string):
    """Giao diện gọi Python; CSV và bộ dữ liệu đều được xử lý tại đây."""
    try:
        query = parse_qs(query_string, keep_blank_values=True)
        if path == '/api/weather':
            data = await browser_weather(query)
        elif path == '/api/locations':
            data = await browser_locations(query)
        elif path == '/api/export':
            saved = SNAPSHOTS.get(query.get('id',[''])[0])
            if not saved or time.time()-saved[0] > 3600:
                return json.dumps({'status':410,'body':{'error':'Phiên tải CSV đã hết hạn. Hãy lấy dữ liệu lại.'}})
            return json.dumps({'status':200,'csv':csv_bytes(saved[1]).decode('utf-8-sig')},ensure_ascii=False)
        else:
            return json.dumps({'status':404,'body':{'error':'Không tìm thấy chức năng.'}})
        return json.dumps({'status':200,'body':data},ensure_ascii=False,allow_nan=False)
    except InputError as exc:
        return json.dumps({'status':400,'body':{'error':str(exc)}},ensure_ascii=False)
    except WeatherError as exc:
        return json.dumps({'status':502,'body':{'error':str(exc)}},ensure_ascii=False)
    except Exception:
        return json.dumps({'status':502,'body':{'error':'Không xử lý được dữ liệu nguồn. Hãy thử lại.'}},ensure_ascii=False)
