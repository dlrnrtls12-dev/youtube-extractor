import json
from pathlib import Path
import unittest
from desktop import canonical_url, transcript, options

class Tests(unittest.TestCase):
    def test_url(self):
        self.assertEqual(canonical_url('https://youtu.be/HrdLYO5vwh0?t=21'), 'https://www.youtube.com/watch?v=HrdLYO5vwh0')
        for value in ['https://youtube.com.evil.com/watch?v=HrdLYO5vwh0','https://user@youtube.com/watch?v=HrdLYO5vwh0','https://youtube.com:3000/watch?v=HrdLYO5vwh0']:
            with self.assertRaises(ValueError): canonical_url(value)

    def test_subtitles(self):
        value=json.dumps({'events':[{'tStartMs':1250,'dDurationMs':1500,'segs':[{'utf8':v}]} for v in ['진행자: 안녕 &amp;', '반갑습니다.', '출연자: 네.']]})
        self.assertEqual(transcript(value),'진행자: 안녕 & 반갑습니다.\n\n출연자: 네.\n')
        self.assertIn('00:00:01,250 --> 00:00:02,750',transcript(value,'srt'))

    def test_no_video_download_for_subtitle(self):
        args=options('https://youtu.be/HrdLYO5vwh0','subtitle','720','ko',Path('out'))
        self.assertIn('--skip-download',args)
        self.assertNotIn('-x',args)
        self.assertEqual(args[-2],'--')

if __name__ == '__main__': unittest.main()
