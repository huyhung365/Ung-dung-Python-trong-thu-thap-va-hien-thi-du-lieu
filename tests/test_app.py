"""Kiểm thử ngoại tuyến; fixture dưới đây là dữ liệu tổng hợp, không phải thời tiết thật."""
import csv
import io
import json
import sys
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app


def fixture():
    return {'latitude':21.05, 'longitude':105.89, 'timezone':'Asia/Bangkok',
            'utc_offset_seconds':25200, 'hourly':{
                'time':[1789232400,1789236000],
                'temperature_2m':[None,30.5],
                'relative_humidity_2m':[80,79],
                'shortwave_radiation':[0,155.0]}}


class WeatherTests(unittest.TestCase):
    def setUp(self):
        self.params=app.parse_inputs({})

    def test_input_boundaries_and_nan(self):
        for key, value in [('latitude','91'),('longitude','-181'),('latitude','nan'),
                           ('past_days','93'),('forecast_days','17'),('past_days','1.5')]:
            with self.subTest(key=key,value=value), self.assertRaises(app.InputError):
                app.parse_inputs({key:[value]})
        with self.assertRaises(app.InputError):
            app.parse_inputs({'past_days':['0'],'forecast_days':['0']})
        with self.assertRaises(app.InputError):
            app.parse_inputs({'latitude':['1','2']})
        self.assertEqual(app.parse_inputs({'past_days':['92'],'forecast_days':['16']})['past_days'],92)

    def test_missing_is_not_zero_and_csv_is_exact(self):
        result=app.normalise(fixture(),self.params,datetime(2026,9,13,tzinfo=timezone.utc))
        self.assertIsNone(result['rows'][0]['temperature_2m'])
        self.assertEqual(result['rows'][0]['shortwave_radiation'],0)
        self.assertEqual(result['meta']['missing_values'],1)
        raw=app.csv_bytes(result)
        self.assertTrue(raw.startswith(b'\xef\xbb\xbf'))
        exported=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
        self.assertEqual(len(exported),2)
        self.assertEqual(exported[0]['temperature_c'],'')
        self.assertEqual(exported[0]['shortwave_radiation_w_m2'],'0')
        self.assertEqual(exported[1]['temperature_c'],'30.5')
        self.assertEqual(exported[1]['time_utc'],result['rows'][1]['time_utc'])

    def test_bad_provider_arrays_rejected(self):
        raw=fixture();raw['hourly']['temperature_2m']=[20]
        with self.assertRaises(app.WeatherError): app.normalise(raw,self.params)
        raw=fixture();raw['hourly']['time'].reverse()
        with self.assertRaises(app.WeatherError): app.normalise(raw,self.params)

    def test_local_day_boundary(self):
        # 2026-09-13 00:00 ở UTC+7 = 2026-09-12 17:00 UTC.
        midnight=datetime(2026,9,12,17,tzinfo=timezone.utc).timestamp()
        raw=fixture();raw['hourly']['time']=[midnight-3600,midnight]
        result=app.normalise(raw,self.params,datetime(2026,9,13,tzinfo=timezone.utc))
        self.assertEqual([r['period'] for r in result['rows']],['past_model','forecast'])


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def test_routes_snapshot_download_and_validation(self):
        with app.LOCK:
            app.CACHE.clear();app.SNAPSHOTS.clear()
        with patch.object(app,'fetch_provider',return_value=fixture()) as fetch:
            with urlopen(self.base+'/api/weather') as response:
                result=json.load(response)
            with urlopen(self.base+'/api/weather') as response:
                self.assertEqual(json.load(response)['id'],result['id'])
            self.assertEqual(fetch.call_count,1)
            with urlopen(self.base+'/api/export?id='+result['id']) as response:
                rows=list(csv.DictReader(io.StringIO(response.read().decode('utf-8-sig'))))
                self.assertIn('attachment',response.headers['Content-Disposition'])
            self.assertEqual(len(rows),len(result['rows']))
            self.assertEqual(fetch.call_count,1)
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base+'/api/weather?latitude=NaN')
        self.assertEqual(error.exception.code,400)
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base+'/api/export?id=unknown')
        self.assertEqual(error.exception.code,410)
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base+'/../app.py')
        self.assertEqual(error.exception.code,404)
        with urlopen(self.base+'/') as response:
            self.assertIn('Weather',response.read().decode())

    def test_provider_error_shown_as_502(self):
        with app.LOCK: app.CACHE.clear()
        with patch.object(app,'fetch_provider',side_effect=app.WeatherError('Offline')):
            with self.assertRaises(HTTPError) as error:
                urlopen(self.base+'/api/weather')
            self.assertEqual(error.exception.code,502)
            self.assertEqual(json.load(error.exception)['error'],'Offline')

    def test_browser_fallback_saved_and_exported_by_python(self):
        body=json.dumps({'params':app.parse_inputs({}), 'data':fixture()}).encode()
        request=Request(self.base+'/api/import',data=body,headers={'Content-Type':'application/json'})
        with urlopen(request) as response:
            result=json.load(response)
        self.assertIn('Python processing',result['meta']['source'])
        with urlopen(self.base+'/api/export?id='+result['id']) as response:
            rows=list(csv.DictReader(io.StringIO(response.read().decode('utf-8-sig'))))
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['temperature_c'],'')
        self.assertEqual(rows[1]['temperature_c'],'30.5')
        with urlopen(self.base+'/') as response:
            policy=response.headers['Content-Security-Policy']
        self.assertIn("connect-src 'self' https://api.open-meteo.com;",policy)
        with app.LOCK:
            self.assertNotIn(result['id'],[token for _,token in app.CACHE.values()])

    def test_import_rejects_invalid_and_oversized_payloads(self):
        for body in [b'{}',b'null',b'{',json.dumps({'params':{},'data':{}}).encode()]:
            request=Request(self.base+'/api/import',data=body,headers={'Content-Type':'application/json'})
            with self.assertRaises(HTTPError) as error: urlopen(request)
            self.assertEqual(error.exception.code,400)
        request=Request(self.base+'/api/import',data=b'{}',headers={
            'Content-Type':'application/json','Content-Length':'4000001'})
        with self.assertRaises(HTTPError) as error: urlopen(request)
        self.assertEqual(error.exception.code,400)


if __name__=='__main__': unittest.main()
